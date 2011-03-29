import re
from copy import deepcopy
from xml.dom import minidom, getDOMImplementation

from .util import openAnything, ReadableException
from .constraints import *
from .pathfeatures import PathDescription, Join, SortOrder, SortOrderList

class Query(object):

    def __init__(self, model, service=None, validate=True):
        self.model = model
        self.name = ''
        self.description = ''
        self.service = service
        self.do_verification = validate
        self.path_descriptions = []
        self.joins = []
        self.constraint_dict = {}
        self.uncoded_constraints = []
        self.views = []
        self._sort_order_list = SortOrderList()
        self._logic_parser = LogicParser(self)
        self._logic = None
        self.constraint_factory = ConstraintFactory()

    @classmethod
    def from_xml(cls, xml, *args, **kwargs):
        """
        Deserialise a query serialised to XML
        --------------------------------------

         Query.from_xml(xml) -> intermine.query.Query

         May throw: QueryParseError, if the query cannot be parsed
                    ModelError,      if the query has illegal paths in it
                    ConstraintError, if the constraints don't make sense

        This method is used to instantiate serialised queries.
        It is used by intermine.webservice.Service objects
        to instantiate Template objects and it can be used
        to read in queries you have saved to a file. 

        The xml argument can be a file, url or string containing xml
        """
        obj = cls(*args, **kwargs)
        obj.do_verification = False
        f = openAnything(xml)
        doc = minidom.parse(f)
        f.close()

        queries = doc.getElementsByTagName('query')
        assert len(queries) == 1, "wrong number of queries in xml"
        q = queries[0]
        obj.name = q.getAttribute('name')
        obj.description = q.getAttribute('description')
        obj.add_view(q.getAttribute('view'))
        for p in q.getElementsByTagName('pathDescription'):
            path = p.getAttribute('pathString')
            description = p.getAttribute('description')
            obj.add_path_description(path, description)
        for j in q.getElementsByTagName('join'):
            path = j.getAttribute('path')
            style = j.getAttribute('style')
            obj.add_join(path, style)
        for c in q.getElementsByTagName('constraint'):
            args = {}
            args['path'] = c.getAttribute('path')
            if args['path'] is None:
                if c.parentNode.tagName != "node":
                    msg = "Constraints must have a path"
                    raise QueryParseError(msg)
                args['path'] = c.parentNode.getAttribute('path')
            args['op'] = c.getAttribute('op')
            args['value'] = c.getAttribute('value')
            args['code'] = c.getAttribute('code')
            args['subclass'] = c.getAttribute('type')
            args['editable'] = c.getAttribute('editable')
            args['optional'] = c.getAttribute('switchable')
            args['extra_value'] = c.getAttribute('extraValue')
            args['loopPath'] = c.getAttribute('loopPath')
            values = []
            for val_e in c.getElementsByTagName('value'):
                texts = []
                for node in val_e.childNodes:
                    if node.nodeType == node.TEXT_NODE: texts.append(node.data)
                values.append(' '.join(texts))
            if len(values) > 0: args["values"] = values
            for k, v in args.items():
                if v is None or v == '': del args[k]
            if "loopPath" in args:
                args["op"] = {
                    "=" : "IS",
                    "!=": "IS NOT"
                }.get(args["op"])
            con = obj.add_constraint(**args)
            if not con:
                raise ConstraintError("error adding constraint with args: " + args)
        obj.verify()        

        return obj

    def verify(self):
        """
        Validate the query
        ------------------

         Query.validate()

         Will throw: ModelError, QueryError, ConstraintError, if the 
                     query fails to validate

        Invalid queries will fail to run, and it is not always
        obvious why. The validation routine checks to see that 
        the query will not cause errors on execution, and tries to
        provide informative error messages.

        This method is called immediately after a query is fully 
        deserialised.
        """
        self.verify_views()
        self.verify_constraint_paths()
        self.verify_join_paths()
        self.verify_pd_paths()
        self.validate_sort_order()
        self.do_verification = True

    def add_view(self, *paths):
        """
        Add one or more views to the list of output columns
        ---------------------------------------------------

         Query.add_view(view(s)...) 

        This is the main method for adding views to the list
        of output columns. As well as appending views, it
        will also split a single, space or comma delimited
        string into multiple paths, and flatten out lists, or any
        combination. It will also immediately try to validate 
        the views.

        Output columns must be valid paths according to the 
        data model, and they must represent attributes of tables
        (see intermine.model.Model, intermine.model.Path 
        intermine.model.Attribute)
        """
        views = []
        for p in paths:
            if isinstance(p, (set, list)):
                views.extend(list(p))
            else:
                views.extend(re.split("(?:,?\s+|,)", p))
        if self.do_verification: self.verify_views(views)
        self.views.extend(views)

    def verify_views(self, views=None):
        """
        Check to see if the views given are valid
        -----------------------------------------

         Query.verify_views()

         Will throw ModelError, ConstraintError if the views are invalid

        This method checks to see if the views:
          - are valid according to the model
          - represent attributes

        (see: intermine.model.Attribute)
        """
        if views is None: views = self.views
        for path in views:
            path = self.model.make_path(path, self.get_subclass_dict())
            if not path.is_attribute():
                raise ConstraintError("'" + str(path) 
                        + "' does not represent an attribute")

    def add_constraint(self, *args, **kwargs):
        """
        Add a constraint (filter on records)
        --------------------------------------

         Query.add_constraint(arg...) -> intermine.constraints.?

        This method will try to make a constraint from the arguments
        given, trying each of the classes it knows of in turn 
        to see if they accept the arguments. This allows you 
        to add constraints of different types without having to know
        or care what their classes or implementation details are.
        All constraints derive from intermine.constraints.Constraint, 
        and they all have a path attribute, but are otherwise diverse.

        Before adding the constraint to the query, this method
        will also try to check that the constraint is valid by 
        calling Query.verify_constraint_paths()

        (see intermine.constraints)
        """
        con = self.constraint_factory.make_constraint(*args, **kwargs)
        if self.do_verification: self.verify_constraint_paths([con])
        if hasattr(con, "code"): 
            self.constraint_dict[con.code] = con
        else:
            self.uncoded_constraints.append(con)
        
        return con

    def verify_constraint_paths(self, constraints=None):
        """
        Check that the constraints are valid
        --------------------------------------

         Query.verify_constraint_paths()

         Will throw ModelError, ConstraintError, if the constraints are 
              not valid

        This method will check the path attribute of each constraint.
        In addition it will:
          - Check that BinaryConstraints have an Attribute as their path
          - Check that TernaryConstraints have a Reference as theirs
          - Check that SubClassConstraints have a correct subclass relationship
          - Check that LoopConstraints have a valid loopPath

        """
        if constraints is None: constraints = self.constraints
        for con in constraints:
            pathA = self.model.make_path(con.path, self.get_subclass_dict())
            if isinstance(con, TernaryConstraint):
                if pathA.get_class() is None:
                    raise ConstraintError("'" + str(pathA) + "' does not represent a class, or a reference to a class")
            elif isinstance(con, BinaryConstraint):
                if not pathA.is_attribute():
                    raise ConstraintError("'" + str(pathA) + "' does not represent an attribute")
            elif isinstance(con, SubClassConstraint):
                pathB = self.model.make_path(con.subclass, self.get_subclass_dict())
                if not pathB.get_class().isa(pathA.get_class()):
                    raise ConstraintError("'" + con.subclass + "' is not a subclass of '" + con.path + "'")
            elif isinstance(con, LoopConstraint):
                self.model.validate_path(con.loopPath, self.get_subclass_dict())

    @property
    def constraints(self):
        """
        Returns the constraints of the query
        -------------------------------------

         Query.constraints -> list(intermine.constraints.Constraint)

        Constraints are returned in the order of their code (normally
        the order they were added to the query) and with any
        subclass contraints at the end.
        """
        ret = sorted(self.constraint_dict.values(), key=lambda con: con.code)
        ret.extend(self.uncoded_constraints)
        return ret

    def get_constraint(self, code):
        """
        Returns the constraint with the given code
        -------------------------------------------

         Query.get_constraint(code) -> intermine.constraints.CodedConstraint

        Returns the constraint with the given code, if if exists.
        If no such constraint exists, it throws a ConstraintError
        """
        if code in self.constraint_dict: 
            return self.constraint_dict[code]
        else:
            raise ConstraintError("There is no constraint with the code '"  
                                    + code + "' on this query")
        
    def add_join(self, *args ,**kwargs):
        """
        Add a join statement to the query
        ----------------------------------

         Query.add_join(args...) -> intermine.pathfeatures.Join
        
         May throw: ModelError, if the path is invalid
                    TypeError, if the join style is invalid

        A join statement is used to determine if references should
        restrict the result set by only including those references
        exist. For example, if one had a query with the view:
        
          "Gene.name", "Gene.proteins.name"

        Then in the normal case (that of an INNER join), we would only 
        get Genes that also have at least one protein that they reference.
        Simply by asking for this output column you are placing a 
        restriction on the information you get back. 
        
        If in fact you wanted all genes, regardless of whether they had  
        proteins associated with them or not, but if they did 
        you would rather like to know _what_ proteins, then you need
        to specify this reference to be an OUTER join:

         query.add_join("Gene.proteins", "OUTER")

        Now you will get many more rows of results, some of which will
        have "null" values where the protein name would have been,

        This method will also attempt to validate the join by calling
        Query.verify_join_paths(). Joins must have a valid path, the 
        style can be either INNER or OUTER (defaults to OUTER,
        as the user does not need to specify inner joins, since all
        references start out as inner joins), and the path 
        must be a reference.
        """
        join = Join(*args, **kwargs)
        if self.do_verification: self.verify_join_paths([join])
        self.joins.append(join)
        return join

    def verify_join_paths(self, joins=None):
        """
        Check that the joins are valid
        -------------------------------

         Query.verify_join_paths()

         May throw: ModelError, QueryError if the paths are not
                    valid

        Joins must have valid paths, and they must refer to references.
        """
        if joins is None: joins = self.joins
        for join in joins:
            path = self.model.make_path(join.path, self.get_subclass_dict())
            if not path.is_reference():
                raise QueryError("'" + join.path + "' is not a reference")

    def add_path_description(self, *args ,**kwargs):
        path_description = PathDescription(*args, **kwargs)
        if self.do_verification: self.verify_pd_paths([path_description])
        self.path_descriptions.append(path_description)
        return path_description

    def verify_pd_paths(self, pds=None):
        if pds is None: pds = self.path_descriptions
        for pd in pds: 
            self.model.validate_path(pd.path, self.get_subclass_dict())

    @property
    def coded_constraints(self):
        return sorted(self.constraint_dict.values(), key=lambda con: con.code)

    def get_logic(self):
        if self._logic is None:
            return reduce(lambda x, y: x+y, self.coded_constraints)
        else:
            return self._logic

    def set_logic(self, value):
        if isinstance(value, LogicGroup):
            logic = value
        else: 
            logic = self._logic_parser.parse(value)
        if self.do_verification: self.validate_logic(logic)
        self._logic = logic

    def validate_logic(self, logic=None):
        if logic is None: logic = self._logic
        logic_codes = set(logic.get_codes())
        for con in self.coded_constraints:
            if con.code not in logic_codes:
                raise QueryError("Constraint " + con.code + repr(con) 
                        + " is not mentioned in the logic: " + str(logic))

    def get_default_sort_order(self):
        try:
            return SortOrderList((self.views[0], SortOrder.ASC))
        except IndexError:
            raise QueryError("Query view is empty")

    def get_sort_order(self):
        if self._sort_order_list.is_empty():
            return self.get_default_sort_order()         
        else:
            return self._sort_order_list

    def add_sort_order(self, path, direction=SortOrder.ASC):
        so = SortOrder(path, direction)
        if self.do_verification: self.validate_sort_order(so)
        self._sort_order_list.append(so)

    def validate_sort_order(self, *so_elems):
        if not so_elems:
            so_elems = self._sort_order_list
        
        for so in so_elems:
            self.model.validate_path(so.path, self.get_subclass_dict())
            if so.path not in self.views:
                raise QueryError("Sort order element is not in the view: " + so.path)

    def get_subclass_dict(self):
        subclass_dict = {}
        for c in self.constraints:
            if isinstance(c, SubClassConstraint):
                subclass_dict[c.path] = c.subclass
        return subclass_dict

    def results(self, row="list"):
        path = self.get_results_path()
        params = self.to_query_params()
        view = self.views
        return self.service.get_results(path, params, row, view)

    def get_results_path(self):
        return self.service.QUERY_PATH

    def get_results_list(self, rowformat="list"):
        return self.service.get_results_list(
                self.get_results_path(),
                self.to_query_params(),
                rowformat,
                self.views)

    def children(self):
        return sum([self.path_descriptions, self.joins, self.constraints], [])
        
    def to_query_params(self):
        xml = self.to_xml()
        params = {'query' : xml }
        return params
        
    def to_Node(self):
        impl  = getDOMImplementation()
        doc   = impl.createDocument(None, "query", None)
        query = doc.documentElement
        
        query.setAttribute('name', self.name)
        query.setAttribute('model', self.model.name)
        query.setAttribute('view', ' '.join(self.views))
        query.setAttribute('sortOrder', str(self.get_sort_order()))
        query.setAttribute('longDescription', self.description)
        if len(self.coded_constraints) > 1:
            query.setAttribute('constraintLogic', str(self.get_logic()))

        for c in self.children():
            element = doc.createElement(c.child_type)
            for name, value in c.to_dict().items():
                if isinstance(value, (set, list)):
                    for v in value:
                        subelement = doc.createElement(name)
                        text = doc.createTextNode(v)
                        subelement.appendChild(text)
                        element.appendChild(subelement)
                else:
                    element.setAttribute(name, value)
            query.appendChild(element)
        return query

    def to_xml(self):
        n = self.to_Node()
        return n.toxml()
    def to_formatted_xml(self):
        n = self.to_Node()
        return n.toprettyxml()

    def clone(self):
        newobj = self.__class__(self.model)
        for attr in ["joins", "views", "_sort_order_list", "_logic", "path_descriptions", "constraint_dict"]:
            setattr(newobj, attr, deepcopy(getattr(self, attr)))

        for attr in ["name", "description", "service", "do_verification", "constraint_factory"]:
            setattr(newobj, attr, getattr(self, attr))
        return newobj

class Template(Query):
    def __init__(self, *args, **kwargs):
        super(Template, self).__init__(*args, **kwargs)
        self.constraint_factory = TemplateConstraintFactory()
    @property
    def editable_constraints(self):
        isEditable = lambda x: x.editable
        return filter(isEditable, self.constraints)
    def to_query_params(self):
        p = {'name' : self.name}
        i = 1
        for c in self.editable_constraints:
            if not c.switched_on: next
            for k, v in c.to_dict().items():
                k = "extra" if k == "extraValue" else k
                k = "constraint" if k == "path" else k
                p[k + str(i)] = v
            i += 1
        return p

    def get_results_path(self):
        return self.service.TEMPLATEQUERY_PATH

    def get_adjusted_template(self, con_values):
        clone = self.clone()
        for code, options in con_values.items():
            con = clone.get_constraint(code)
            if not con.editable:
                raise ConstraintError("There is a constraint '" + code 
                                       + "' on this query, but it is not editable")
            for key, value in options.items():
                setattr(con, key, value)
        return clone

    def results(self, row="list", **con_values):
        clone = self.get_adjusted_template(con_values)
        return super(Template, clone).results(row)

    def get_results_list(self, row="list", **con_values):
        clone = self.get_adjusted_template(con_values)
        return super(Template, clone).get_results_list(row)

class QueryError(ReadableException):
    pass

class ConstraintError(QueryError):
    pass

class QueryParseError(QueryError):
    pass


import re
from copy import deepcopy
from xml.dom import minidom, getDOMImplementation

from intermine.util import openAnything
from intermine.constraints import ConstraintFactory, TemplateConstraintFactory, SubClassConstraint
from intermine.pathfeatures import PathDescription, Join

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
        self.views = []
        self._sort_order = None
        self._logic = None
        self.constraint_factory = ConstraintFactory()

    @classmethod
    def from_xml(cls, xml, *args, **kwargs):
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
                    raise ParseError(msg)
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
        self.verify_views()
        self.verify_constraint_paths()
        self.verify_join_paths()
        self.verify_pd_paths()
        self.do_verification = True

    def add_view(self, *paths):
        views = []
        for p in paths:
            if isinstance(p, (set, list)):
                views.extend(list(p))
            else:
                views.extend(re.split("(?:,?\s+|,)", p))
        if self.do_verification: self.verify_views(views)
        self.views.extend(views)

    def verify_views(self, views=None):
        if views is None: views = self.views
        for path in views:
            path = self.model.make_path(path, self.get_subclass_dict())
            if not path.is_attribute():
                raise ConstraintError(str(path) + " does not represent an attribute")

    def add_constraint(self, *args, **kwargs):
        con = self.constraint_factory.make_constraint(*args, **kwargs)
        if self.do_verification: self.verify_constraint_paths([con])
        self.constraint_dict[con.code] = con
        return con

    def verify_constraint_paths(self, constraints=None):
        if constraints is None: constraints = self.constraints
        for con in constraints:
            pathA = self.model.make_path(con.path, self.get_subclass_dict())
            if hasattr(con, 'subclass'):
                pathB = self.model.make_path(con.subclass, self.get_subclass_dict())
                if not pathB.get_class().isa(pathA.get_class()):
                    raise ConstraintError("'" + con.subclass + "' is not a subclass of '" + con.path + "'")
            if hasattr(con, "loopPath"):
                self.model.validate_path(con.loopPath, self.get_subclass_dict())

    @property
    def constraints(self):
        return sorted(self.constraint_dict.values(), key=lambda con: con.code)

    def get_constraint(self, code):
        try: 
            return self.constraint_dict[code]
        except KeyError:
            raise ConstraintError("There is no constraint with the code '"  
                                    + code + "' on this query")
        
    def add_join(self, *args ,**kwargs):
        join = Join(*args, **kwargs)
        if self.do_verification: self.verify_join_paths([join])
        self.joins.append(join)
        return join

    def verify_join_paths(self, joins=None):
        if joins is None: joins = self.joins
        for join in joins:
            path = self.model.make_path(join.path, self.get_subclass_dict())
            if not path.is_reference():
                raise ConstraintError("'" + join.path + "' is not a reference")

    def add_path_description(self, *args ,**kwargs):
        path_description = PathDescription(*args, **kwargs)
        if self.do_verification: self.verify_pd_paths([path_description])
        self.path_descriptions.append(path_description)
        return path_description

    def verify_pd_paths(self, pds=None):
        if pds is None: pds = self.path_descriptions
        for pd in pds: 
            self.model.validate_path(pd.path, self.get_subclass_dict())

    def get_logic(self):
        if self._logic is None:
            self._logic = reduce(lambda(x, y): x+y, self.constraints)
        return self._logic

    def set_logic(self, value):
        self._logic = value

    def get_sort_order(self):
        if self._sort_order is None:
            try:
                return (self.views[0], "asc")
            except IndexError:
                raise QueryError("Query view is empty")
        else:
            return self._sort_order

    def set_sort_order(self, path, direction='asc'):
        valid_directions = set(['asc', 'desc'])
        if not direction in valid_directions:
            raise TypeError("Direction must be one of " + str(valid_directions) + " not " + direction)
        self._sort_order = (path, direction)

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

    def get_results_iterator(self, rowformat="list"):
        return self.service.get_results_iterator(
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
        query.setAttribute('sortOrder', ' '.join(self.get_sort_order()))
        query.setAttribute('longDescription', self.description)

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
        for attr in ["joins", "views", "_sort_order", "_logic", "path_descriptions", "constraint_dict"]:
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

    def get_results_iterator(self, row="list", **con_values):
        clone = self.get_adjusted_template(con_values)
        return super(Template, clone).get_results_iterator(row)

class QueryError(Exception):
    pass

class ConstraintError(Exception):
    pass

            


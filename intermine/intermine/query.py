import re
from xml.dom.minidom import getDOMImplementation
from intermine.constraints import ConstraintFactory, TemplateConstraintFactory, SubClassConstraint
from intermine.pathfeatures import PathDescription, Join
from copy import deepcopy

class QueryError(Exception):
    pass

class Query(object):

    def __init__(self, model, service=None, validate=True):
        self.model = model
        self.name = ''
        self.description = ''
        self.comment = ''
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
        f = open(xml)
        doc = minidom.parse(f)
        f.close()
        for q in doc.getElementsByTagName('query'):
            obj.name = q.getAttribute('name')
            obj.description = q.getAttribute('description')
            obj.comment = q.getAttribute('comment')
            assert node.nextSibling is None, "Multiple queries"
        for p in doc.getElementsByTagName('pathDescription'):
            path = p.getAttribute('path')
            description = p.getAttribute('description')
            obj.add_path_description(path, description)
        for j in doc.getElementsByTagName('join'):
            path = j.getAttribute('path')
            style = j.getAttribute('style')
            obj.add_join(path, style)
        for c in doc.getElementsByTagName('constraint'):
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
            args['values'] = c.getAttribute('values')
            args['subclass'] = c.getAttribute('type')
            args['editable'] = c.getAttribute('editable')
            args['optional'] = c.getAttribute('switchable')
            args['extra_value'] = c.getAttribute('extraValue')
            for k, v in args:
                if v is None:
		    del args[k]
            obj.add_constraint(**args)
        return obj

    def add_view(self, *paths):
        views = []
        for p in paths:
            if isinstance(p, (set, list)):
                views.extend(list(p))
            else:
                views.extend(re.split("(?:,?\s+|,)", p))
        if self.do_verification:
            for path in views:
                self.model.validate_path(path, self.get_subclass_dict())
        self.views.extend(views)

    def add_constraint(self, *args, **kwargs):
        con = self.constraint_factory.make_constraint(*args, **kwargs)
        if self.do_verification:
            pathA = self.model.make_path(con.path, self.get_subclass_dict())
            if hasattr(con, 'subclass'):
                pathB = self.model.make_path(con.subclass, self.get_subclass_dict())
                if not pathB.get_class().isa(pathA.get_class()):
                    raise ConstraintError("'" + con.subclass + "' is not a subclass of '" + con.path + "'")
        self.constraint_dict[con.code] = con
        return con

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
        if self.do_verification:
            path = self.model.make_path(join.path, self.get_subclass_dict())
            if not path.is_reference():
                raise ConstraintError("'" + join.path + "' is not a reference")
        self.joins.append(join)
        return join

    def add_path_description(self, *args ,**kwargs):
        path_description = PathDescription(*args, **kwargs)
        if self.do_verification:
            self.model.validate_path(path_description.path, self.get_subclass_dict())
        self.path_descriptions.append(path_description)
        return path_description

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
                self.service.QUERY_PATH,
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
        query.setAttribute('comment', self.comment)

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

        for attr in ["name", "description", "comment", "service", "do_verification", "constraint_factory"]:
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
            if not c.switched_on:
		next
            for k, v in c.to_dict().items():
                p[k + str(i)] = v
            i += 1
        return p

    def get_results_path(self):
        return self.service.TEMPLATEQUERY_PATH

    def results(self, row="list", **con_values):
        clone = self.clone()
        for code, options in con_values.items():
            con = clone.get_constraint(code)
            if not con.editable:
                raise ConstraintError("There is a constraint '" + code 
                                       + "' on this query, but it is not editable")
            for key, value in options.items():
                setattr(con, key, value)
        return super(Template, clone).results(row)
            

class QueryError(Exception):
    pass

class ConstraintError(Exception):
    pass

            


import re
from xml.dom.minidom import getDOMImplementation
from intermine.constraints import make_constraint, make_template_constraint, SubClassConstraint
from intermine.pathfeatures import PathDescription, Join

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
        self.constraints = []
        self.views = []
        self._sort_order = None
        self.joins = []

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
        con = make_constraint(*args, **kwargs)
        if self.do_verification:
            self.model.validate_path(con.path, self.get_subclass_dict())
        self.constraints.append(con)
        return con
        
    def add_join(self, *args ,**kwargs):
        join = Join(*args, **kwargs)
        if self.do_verification:
            self.model.validate_path(join.path, self.get_subclass_dict())
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
        path = self.service.QUERY_PATH
        params = self.to_query_params()
        view = self.views
        return self.service.get_results(path, params, row, view)

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

class Template(Query):
    def __init__(self, *args, **kwargs):
        super(Template, self).__init__(*args, **kwargs)
        self.title 
    def add_constraint(self, *args, **kwargs):
        con = make_template_constraint(*args, **kwargs)
        self.constraints.append(con)
        return con
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
            for k, v in c.toDict:
                p[k + i] = v
            i += 1
        return p
    def results(self, **args):
        pass


            


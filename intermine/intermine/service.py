from urlparse import urlunsplit, urljoin
from xml.dom import minidom
from urllib import urlopen
from urllib import urlencode 
import csv
from query import Query, Template
from model import Model

class Service(object):
    QUERY_PATH         = '/query/results'
    MODEL_PATH         = '/model'
    TEMPLATES_PATH     = '/templates/xml'
    TEMPLATEQUERY_PATH = '/template/results'
    VERSION_PATH       = '/version'
    USER_AGENT         = 'WebserviceInterMinePerlAPIClient'
    LIST_PATH          = '/lists/xml'
    SAVEDQUERY_PATH    = '/savedqueries/xml'
    RELEASE_PATH       = '/version/release'
    SCHEME             = 'http://'

    def __init__(self, root):
        self.root = root
        self._templates = None
        self._model = None
        self._version = None
        self._release = None
    @property
    def version(self):
        if self._version is None:
            self._version = int(urlopen(self.root + self.VERSION_PATH).read())
        return self._version
    @property
    def release(self):
        if self._release is None:
            self._release = urlopen(self.root + RELEASE_PATH).read()
        return self._release

    def get_template(self, name):
        try:
            t = self.templates[name]
        except KeyError:
            raise ServiceError("There is no template called '" 
                + name + "' at this service")
        if not isinstance(t, Template):
            t = Template.from_xml(t, self.model, self)
            self.templates[name] = t
        return t 

    @property
    def templates(self):
        if self._templates is None:
            sock = urlopen(self.root + self.TEMPLATES_PATH)
            dom = minidom.parse(sock)
            sock.close()
            templates = {}
            for e in dom.getElementsByTagName('template'):
                name = e.getAttribute('name')
                if name in templates:
                    raise ServiceError("Two templates with same name: " + name)
                else:
                    templates[name] = e.toxml()
            self._templates = templates
        return self._templates

    @property
    def model(self):
        if self._model is None:
            model_url = self.root + self.MODEL_PATH
            self._model = Model(model_url)
        return self._model

    def new_query(self):
        return Query(self.model, self)

    def get_results_iterator(self, path, params, row, view):
        return ResultIterator(self.root, path, params, row, view)

    def get_results(self, path, params, row, view):
        rows = self.get_results_iterator(path, params, row, view)
        return [r for r in rows]

class ResultIterator(object):
    
    def __init__(self, root, path, params, rowformat, view):
        params.update({"format" : "csv"})
        u = root + path
        p = urlencode(params)
        u += "?" + p
        con = urlopen(u)
        self.reader = {
            "string" : lambda: con,
            "list"   : lambda: csv.reader(con),
            "dict"   : lambda: csv.DictReader(con, view)
        }.get(rowformat)()

    def __iter__(self):
        return self.reader

    def next(self):
        return self.reader.next()

class ServiceError(Exception):
    pass

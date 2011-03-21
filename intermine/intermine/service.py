from urlparse import urlunsplit, urljoin
from urllib import *
import csv
from query import Query
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
            self._version = urlopen(self.root + VERSION_PATH).read()
        return self._version
    @property
    def release(self):
        if self._release is None:
            self._release = urlopen(self.root + RELEASE_PATH).read()
        return self._release

    def get_template(self, name):
        return self.templates[name]
    @property
    def templates(self):
        if self._templates is None:
            sock = urlopen(self.root + TEMPLATES_PATH)
            dom = minidom.parse(sock)
            sock.close()
            for e in dom.getElementsByTagName('template'):
                name = e.getAttribute('name')
                temp = Template(self.model, self, e.toxml())
                if self._templates[name]:
                    raise ServiceError("Two templates with same name")
                else:
                    self._templates[name] = temp
        return self._templates

    @property
    def model(self):
        if self._model is None:
            model_url = self.root + self.MODEL_PATH
            print "Model url: ", model_url
            self._model = Model(model_url)
        return self._model

    def new_query(self):
        return Query(self.model, self)

    def get_results_iterator(self, path, params, row, view):
        params.update({"format" : "csv"})
        return ResultIterator(self.root, path, params, row, view)

    def get_results(self, path, params, row, view):
        rows = self.get_results_iterator(path, params, row, view)
        return [r for r in rows]

class ResultIterator(object):
    
    def __init__(self, root, path, params, rowformat, view):
        params.update({"format" : "csv"})
        u = root + path
        print "Going to open url: ", u
        p = urlencode(params)
        print "My params are: ", p
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

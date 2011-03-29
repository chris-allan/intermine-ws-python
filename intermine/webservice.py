from urlparse import urlunsplit, urljoin
from xml.dom import minidom
from urllib import urlopen
from urllib import urlencode 
import csv

# Local intermine imports
from .query import Query, Template
from .model import Model
from .util import ReadableException

class Service(object):
    """
    A class representing connections to different InterMine WebServices
    ===================================================================

    The intermine.webservice.Service class is the main interface for the user.
    It will provide access to queries and templates, as well as doing the
    background task of fetching the data model, and actually requesting
    the query results.

    SYNOPSIS
    --------

      from intermine.webservice import Service
      service = Service("http://www.flymine.org/query/service")

      template = service.get_template("Gene_Pathways")
      for row in template.results(A={"value":"zen"}):
        do_something_with(row)
        ...

      query = service.new_query()
      query.add_view("Gene.symbol", "Gene.pathway.name")
      query.add_constraint("Gene", "LOOKUP", "zen")
      for row in query.results():
        do_something_with(row)
        ...
      
    OVERVIEW
    -----------
    The two methods the user will be most concerned with are:
      - Service.new_query: constructs a new query to query a service with
      - Service.get_template: gets a template from the service

    TERMINOLOGY
    -----------
    "Query" is the term for an arbitrarily complex structured request for 
    data from the webservice. The user is responsible for specifying the 
    structure that determines what records are returned, and what information
    about each record is provided.

    "Template" is the term for a predefined "Query", ie: one that has been
    written and saved on the webservice you will access. The definition
    of the query is already done, but the user may want to specify the
    values of the constraints that exist on the template. Templates are accessed
    by name, and while you can easily introspect templates, it is assumed
    you know what they do when you use them

    For more information on these two important concepts, see intermine.query
    """
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
        """
        Returns the webservice version
        ------------------------------

         Service.version -> int

        The version specifies what capabilities a
        specific webservice provides. The most current 
        version is 3
        """
        if self._version is None:
            self._version = int(urlopen(self.root + self.VERSION_PATH).read())
        return self._version
    @property
    def release(self):
        """
        Returns the datawarehouse release
        ---------------------------------

         Service.release -> string

        The release is an arbitrary string used to distinguish
        releases of the datawarehouse. This usually coincides
        with updates to the data contained within. While a string,
        releases usually sort in ascending order of recentness 
        (eg: "release-26", "release-27", "release-28"). They can also
        have less machine readable meanings (eg: "beta")
        """
        if self._release is None:
            self._release = urlopen(self.root + RELEASE_PATH).read()
        return self._release

    def new_query(self):
        """
        Construct a new Query object for the given webservice
        -----------------------------------------------------

         Service.new_query() -> intermine.query.Query

        This is the standard method for instantiating new Query
        objects. Queries require access to the data model, as well
        as the service itself, so it is easiest to access them through
        this factory method.
        """
        return Query(self.model, self)

    def get_template(self, name):
        """
        Returns a template of the given name
        ------------------------------------

         Service.get_template(name) -> intermine.query.Template

         May throw: ServiceError, if the template does not exist
                    QueryParseError, if the template cannot be parsed

        Tries to retrieve a template of the given name
        from the webservice. If you are trying to fetch
        a private template (ie. one you made yourself 
        and is not available to others) then you may need to authenticate
        (see: intermine.service.Service)
        """
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
        """
        The dictionary of templates from the webservice
        -----------------------------------------------

         Service.templates -> dict(intermine.query.Template|string)

        For efficiency's sake, Templates are not parsed until
        they are required, and until then they are stored as XML
        strings. It is recommended that in most cases you would want 
        to use Service.get_template.

        You can use this property however to test for template existence though:

         if name in service.templates:
            template = service.get_template(name)

        """
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
        """
        The data model for the webservice you are querying
        --------------------------------------------------

         Service.model -> intermine.model.Model

         May throw: ModelParseError, if the model cannot be read

        This is used when constructing queries to provide them
        with information on the structure of the data model
        they are accessing. You are very unlikely to want to 
        access this object directly.

        see intermine.model.Model
        """
        if self._model is None:
            model_url = self.root + self.MODEL_PATH
            self._model = Model(model_url)
        return self._model

    def get_results(self, path, params, row, view):
        """
        Return an Iterator over the rows of the results
        ------------------------------------------------

         Service.get_results(path, params, rowformat, view)
           -> intermine.webservice.ResultIterator

        This method is called internally by the query objects
        when they are called to get results. You will not 
        normally need to call it directly
        """
        return ResultIterator(self.root, path, params, row, view)

    def get_results_list(self, path, params, row, view):
        """
        Return a list of the rows of the results
        ------------------------------------------------

         Service.get_results(path, params, rowformat, view)
           -> list(list|dict|string)

        This method is called internally by the query objects
        when they are called to get results. You will not 
        normally need to call it directly
        """
        rows = self.get_results(path, params, row, view)
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

class ServiceError(ReadableException):
    pass

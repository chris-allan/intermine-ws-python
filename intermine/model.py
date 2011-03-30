from xml.dom import minidom
import re

from .util import openAnything, ReadableException

class Class(object):
    """
    An abstraction of database tables in the data model
    ================================================
    -----------------------------------------------------
    These objects refer to the table objects in the
    InterMine ORM layer.
    -----------------------------------------------------

    SYNOPSIS
    ---------

    service = Service("http://www.flymine.org/query/service")
    model = service.model

    if "Gene" in model.classes:
        gene_cd = model.get_class("Gene")
        print "Gene has", len(gene_cd.fields), "fields"
        for field in gene_cd.fields:
            print " - ", field.name

    OVERVIEW
    ---------

    Each class can have attributes (columns) of various types,
    and can have references to other classes (tables), on either
    a one-to-one (references) or one-to-many (collections) basis

    Classes should not be instantiated by hand, but rather used
    as part of the model they belong to.

    """
    def __init__(self, name, parents):
        """
        Constructor - Creates a new Class descriptor
        ------------

          Class(name, [parent1, parent2]) -> Class

        This constructor is called when deserialising the 
        model - you should have no need to create Classes by hand

        """
        self.name = name
        self.parents = parents
        self.parent_classes = []
        self.field_dict = {}
        id = Attribute("id", "Integer", self) # All classes have the id attr
        self.field_dict["id"] = id

    def __repr__(self): 
        return '<' + self.__module__ + "." + self.__class__.__name__ + ': ' + self.name + '>'

    @property
    def fields(self):
        """
        The fields of this class
        ------------------------

          Class.fields -> list(Field)

        The fields are returned sorted by name. Fields
        includes all Attributes, References and Collections
        """
        return sorted(self.field_dict.values(), key=lambda field: field.name)

    @property
    def attributes(self):
        """The fields of this class which contain data"""
        return filter(lambda x: isinstance(x, Attribute), self.fields)

    @property
    def references(self):
        """fields which reference other objects"""
        def isRef(x): return isinstance(x, Reference) and not isinstance(x, Collection)
        return filter(isRef, self.fields)

    @property
    def collections(self):
        """fields which reference many other objects"""
        return filter(lambda x: isinstance(x, Collection), self.fields)

    def get_field(self, name):
        """
        Get a field by name
        --------------------

          Class.get_field(name) -> Field

          May throw: ModelError, if the Class does not have such a field

        The standard way of retrieving a field
        """
        if name in self.field_dict:
            return self.field_dict[name]
        else:
            raise ModelError("There is no field called %s in %s" % (name, self.name))

    def isa(self, other):
        """
        Check if self is, or inherits from other
        ----------------------------------------

          Class.isa(other) -> boolean

        This method validates statements about inheritance. 
        Returns true if the "other" is, or is within the 
        ancestry of, this class

        Other can be passed as a name (str), or as the class object itself
        """
        if isinstance(other, Class):
            other_name = other.name
        else:
            other_name = other
        if self.name == other_name:
            return True
        if other_name in self.parents:
            return True
        for p in self.parent_classes:
            if p.isa(other):
                return True
        return False
    

class Field(object):
    """
    A class representing columns on database tables
    =================================================
    --------------------------------------------------------------
    The base class for attributes, references and collections. All
    columns in DB tables are represented by fields
    ---------------------------------------------------------------

    SYNOPSIS
    ---------

        >>> service = Service("http://www.flymine.org/query/service")
            model = service.model
            cd = model.get_class("Gene")
            print "Gene has", len(cd.fields), "fields"
            for field in gene_cd.fields:
                print " - ", field

        ... Gene has 45 fields
            -  CDSs is a group of CDS objects, which link back to this as gene
            -  GLEANRsymbol is a String
            -  UTRs is a group of UTR objects, which link back to this as gene
            -  alleles is a group of Allele objects, which link back to this as gene
            -  chromosome is a Chromosome
            -  chromosomeLocation is a Location
            -  clones is a group of CDNAClone objects, which link back to this as gene
            -  crossReferences is a group of CrossReference objects, which link back to this as subject
            -  cytoLocation is a String
            -  dataSets is a group of DataSet objects, which link back to this as bioEntities
            -  downstreamIntergenicRegion is a IntergenicRegion
            -  exons is a group of Exon objects, which link back to this as gene
            -  flankingRegions is a group of GeneFlankingRegion objects, which link back to this as gene
            -  goAnnotation is a group of GOAnnotation objects
            -  homologues is a group of Homologue objects, which link back to this as gene
            -  id is a Integer
            -  interactions is a group of Interaction objects, which link back to this as gene
            -  length is a Integer
            ...
      
    see also: Attrubute, Reference, Collection
    """
    def __init__(self, name, type_name, class_origin):
        """
        Constructor - DO NOT USE
        -----------------------------

          THIS CLASS IS NOT MEANT TO BE INSTANTIATED DIRECTLY
            - use Attribute, Reference or Collection instead
            
        And even then, you are unlikely to need to do 
        so anyway: it is recommended you access fields
        through the classes generated by the model

        @params:
            - name: The name of this field (str)
            - type_name: the type of field (eg: String, CDS,...) (str)
            - class_origin: The class this field belongs to originally 
                (it may be inherited later) (Class)
        """
        self.name = name
        self.type_name = type_name
        self.type_class = None
        self.declared_in = class_origin
    def toString(self):
        return self.name + " is a " + self.type_name
    def __str__(self):
        return self.toString()


class Attribute(Field):
    """
    Attributes represent columns that contain actual data
    =======================================================

    The Attribute class inherits all the behaviour of Field
    """
    pass

class Reference(Field):
    """
    References represent columns that refer to records in other tables
    ====================================================================
    
    In addition the the behaviour and properties of Field, references
    may also have a reverse reference, if the other record points 
    back to this one as well. And all references will have their
    type upgraded to a type_class during parsing
    """
    def __init__(self, name, type_name, class_origin, reverse_ref=None):
        """
        Constructor
        -------------

        In addition to the a parameters of Field, Reference also 
        takes an optional reverse reference name (str)
        """
        self.reverse_reference_name = reverse_ref
        super(Reference, self).__init__(name, type_name, class_origin)
        self.reverse_reference = None
    def toString(self):
        s = super(Reference, self).toString()
        if self.reverse_reference is None:
            return s
        else:
            return s + ", which links back to this as " + self.reverse_reference.name

class Collection(Reference):
    """
    Collections are references which refer to groups of objects
    ============================================================

    Collections have all the same behaviour and properties as References
    """
    def toString(self):
        ret = super(Collection, self).toString().replace(" is a ", " is a group of ")
        if self.reverse_reference is None:
            return ret + " objects"
        else:
            return ret.replace(", which links", " objects, which link")
        

class Path(object):
    """
    A class representing a validated dotted string path
    =====================================================

    SYNOPSIS
    ----------

        >>> service = Service("http://www.flymine.org/query/service")
            model = service.model
            path = model.make_path("Gene.organism.name")
            path.is_attribute()
        ... True
        >>> path2 = model.make_path("Gene.proteins")
            path2.is_attribute()
        ... False
        >>> path2.is_reference()
        ... True
        >>> path2.get_class()
        ... <intermine.model.Class: gene>

    OVERVIEW
    ---------

    This class is used for performing validation on dotted path strings. 
    The simple act of parsing it into existence will validate the path
    to some extent, but there are additional methods for verifying certain
    relationships as well
    """
    def __init__(self, path_string, model, subclasses={}):
        """
        Constructor:
        -------------

          Path("Gene.name", model) -> Path

        You will not need to use this constructor directly. Instead,
        use the "make_path" method on the model to construct paths for you.
        
        @params:
            - path_string: the dotted path string (eg: Gene.proteins.name)
            - model: the model to validate the path against
            - subclasses: a dict which maps subclasses (defaults to an empty dict)
        """
        self._string = path_string
        self.parts = model.parse_path_string(path_string, subclasses)

    def __str__(self):
        return self._string

    def __repr__(self):
        return '<' + self.__module__ + "." + self.__class__.__name__ + ": " + self._string + '>'

    @property
    def end(self):
        """The descriptor for the last part of the string."""
        return self.parts[-1]

    def get_class(self):
        """Return the class object for this path, if it refers to a class
        or a reference. Attribute paths return None"""
        if self.is_class():
            return self.end
        elif self.is_reference():
            return self.end.type_class
        else:
            return None
    
    def is_reference(self):
        """Return true if the path is a reference, eg: Gene.organism or Gene.proteins
        Note: Collections are ALSO references"""
        return isinstance(self.end, Reference)

    def is_class(self):
        """Return true if the path just refers to a class, eg: Gene"""
        return isinstance(self.end, Class)

    def is_attribute(self):
        """Return true if the path refers to an attribute, eg: Gene.length"""
        return isinstance(self.end, Attribute)

class Model(object):
    """
    A class for representing the data model of an InterMine datawarehouse
    =======================================================================

    SYNOPSIS
    ----------

        >>> service = Service("http://www.flymine.org/query/service")
            model = service.model
            model.get_class("Gene")
        ... <intermine.model.Class: Gene>

    OVERVIEW
    -----------

    This class represents the data model  - ie. an abstraction
    of the database schema. It can be used to introspect what 
    data is available and how it is inter-related
    """
    def __init__(self, source):
        """
        Constructor
        ------------

          Model(xml) -> Model

        You will most like not need to create a model directly, 
        instead get one from the Service object:
        
        see: intermine.webservice.Service

        @params:
            - source -- the model.xml, as a local file, string, or url
        """
        assert source is not None
        self.source = source
        self.classes= {}
        self.parse_model(source)
        self.vivify()

    def parse_model(self, source):
        """
        Create classes, attributes, references and collections from the model.xml
        --------------------------------------------------------------------------

            Model.parse_model(source)

            May throw: ModelParseError, if there is a problem parsing the source

        The xml can be provided as a file, url or string. This method
        is called during instantiation - it does not need to be called 
        directly.
        """
        try:
            io = openAnything(source)
            doc = minidom.parse(io)
            for node in doc.getElementsByTagName('model'):
                self.name = node.getAttribute('name')
                self.package_name = node.getAttribute('package')
                assert node.nextSibling is None, "More than one model element"
                assert self.name and self.package_name, "No model name or package name"
     
            for c in doc.getElementsByTagName('class'):
                class_name = c.getAttribute('name')
                assert class_name, "Name not defined in" + c.toxml()
                def strip_java_prefix(x): 
                    return re.sub(r'.*\.', '', x)
                parents = map(strip_java_prefix, 
                        c.getAttribute('extends').split(' '))
                cl =  Class(class_name, parents)
                for a in c.getElementsByTagName('attribute'):
                    name = a.getAttribute('name')
                    type_name = strip_java_prefix(a.getAttribute('type'))
                    at = Attribute(name, type_name, cl)
                    cl.field_dict[name] = at
                for r in c.getElementsByTagName('reference'):
                    name = r.getAttribute('name')
                    type_name = r.getAttribute('referenced-type')
                    linked_field_name = r.getAttribute('reverse-reference')
                    ref = Reference(name, type_name, cl, linked_field_name)
                    cl.field_dict[name] = ref
                for co in c.getElementsByTagName('collection'):
                    name = co.getAttribute('name')
                    type_name = co.getAttribute('referenced-type')
                    linked_field_name = co.getAttribute('reverse-reference')
                    col = Collection(name, type_name, cl, linked_field_name)
                    cl.field_dict[name] = col
                self.classes[class_name] = cl
        except Exception, error:
            raise ModelParseError("Error parsing model", error)

    def vivify(self):
        """
        Make names point to instances and insert inherited fields
        ----------------------------------------------------------
        
          Model.vivify()

          May throw: ModelError, if the names point to non-existent objects

        This method ensures the model is internally consistent. This method
        is called during instantiaton. It does not need to be called
        directly.
        """
        for c in self.classes.values():
            c.parent_classes = self.to_ancestry(c)
            for pc in c.parent_classes:
                c.field_dict.update(pc.field_dict)
            for f in c.fields:
                f.type_class = self.classes.get(f.type_name)
                if hasattr(f, 'reverse_reference_name') and f.reverse_reference_name != '':
                    rrn = f.reverse_reference_name
                    f.reverse_reference = f.type_class.field_dict[rrn]

    def to_ancestry(self, cd):
        """
        Returns the lineage of the class
        -----------------------------------
        
            Model.to_ancestry(cd) -> list(classes)

        Returns the class' parents, and all the class' parents' parents
        """
        parents = cd.parents
        def defined(x): return x is not None # weeds out the java classes
        def to_class(x): return self.classes.get(x)
        ancestry = filter(defined, map(to_class, parents))
        for ancestor in ancestry:
            ancestry.extend(self.to_ancestry(ancestor))
        return ancestry

    def to_classes(self, classnames):
        """
        take a list of class names and return a list of classes
        --------------------------------------------------------

            model.to_classes(list(classnames)) -> list(classes)

            May throw: ModelError, if the classnames point to non-existent classes

        This simply maps from a list of strings to a list of 
        classes in the calling model.
        """
        return map(self.get_class, classnames)

    def get_class(self, name):
        """
        Get a class by its name, or by a dotted path
        -----------------------------------------------

            Model.get_class(name) -> class

            May throw: ModelError, if the class does not exist

        This is the recommended way of retrieving a class from
        the model. As well as handling class names, you can also
        pass in a path such as "Gene.proteins" and get the 
        corresponding class back (<intermine.model.Class: Protein>)
        """
        if name.find(".") != -1:
            path = self.make_path(name)
            if path.is_attribute():
                raise ModelError("'" + str(path) + "' is not a class")
            else:
                return path.get_class()
        if name in self.classes:
          return self.classes[name]
        else:
          raise ModelError("'" + name + "' is not a class in this model")

    def make_path(self, path, subclasses={}):
        """
        Return a path object for the given path string
        -----------------------------------------------

            Model.make_path(string) -> Path

        This is recommended manner of constructing path objects.

        see: intermine.model.Path
        """
        return Path(path, self, subclasses)

    def validate_path(self, path_string, subclasses={}):
        """
        Validate a path
        ---------------------
            
            Model.validate_path(string) -> Bool
            
            will throw: PathParseError, for invalid paths

        When you don't need to interrogate relationships
        between paths, simply using this method to validate
        a path string is enough. It guarantees that there
        is a descriptor for each section of the string, 
        with the appropriate relationships
        """
        try:
            self.parse_path_string(path_string, subclasses)
            return True
        except PathParseError, e:
            raise PathParseError("Error parsing '%s' (subclasses: %s)" 
                            % ( path_string, str(subclasses) ), e )

    def parse_path_string(self, path_string, subclasses={}):
        """
        Parse a path string into a list of descriptors - one for each section
        -----------------------------------------------------------------------
    
            Model.parse_path_string(string) -> list(descriptors)

        This method is used when making paths from a model, and 
        when validating path strings. It probably won't need to 
        be called directly.

        see: intermine.model.Model.make_path
        see: intermine.model.Model.validate_path
        see: intermine.model.Path
        """
        descriptors = []
        names = path_string.split('.')
        root_name = names.pop(0)
     
        root_descriptor = self.get_class(root_name)
        descriptors.append(root_descriptor)
     
        if root_name in subclasses:
            current_class = self.get_class(subclasses[root_name])
        else:
            current_class = root_descriptor 
     
        for field_name in names:
            field = current_class.get_field(field_name)
            descriptors.append(field)
     
            if isinstance(field, Reference):
                key = '.'.join(map(lambda x: x.name, descriptors))
                if key in subclasses:
                    current_class = self.get_class(subclasses[key])
                else: 
                    current_class = field.type_class
            else:
                current_class = None
     
        return descriptors 

class ModelError(ReadableException):
    pass

class PathParseError(ModelError):
    pass

class ModelParseError(ModelError):
    pass


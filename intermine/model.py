from xml.dom import minidom
from intermine.util import openAnything, ReadableException
import re

class Class(object):
    """A class representing classes in the Data Model,
    which is in turn an abstraction of a database table 
    in the database schema.

    Each class can have attributes (columns) of various types,
    and can have references to other classes (tables), on either
    a one-to-one (references) or one-to-many (collections) basis

    Classes should not be instantiated by hand, but rather used
    as part of the model they belong to.
    """
    def __init__(self, name, parents):
        self.name = name
        self.parents = parents
        self.parent_classes = []
        self.field_dict = {}
        id = Attribute("id", "Integer", self) # All classes have the id attr
        self.field_dict["id"] = id

    @property
    def fields(self):
        """The fields of this class"""
        return self.field_dict.values()

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
        if name in self.field_dict:
            return self.field_dict[name]
        else:
            raise ModelError("There is no field called %s in %s" % (name, self.name))

    def isa(self, other):
        """Check if self is, or inherits from other

        Other can be passed as a name, or as the class object itself
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
    """The base class for attributes, references and collections. All
    columns in DB tables are represented by fields"""
    def __init__(self, n, t, c):
        self.name = n
        self.type_name = t
        self.type_class = None
        self.declared_in = c
    def toString(self):
        return self.name + " is a " + self.type_name


class Attribute(Field):
    """Attributes are fields with their own values"""
    pass

class Reference(Field):
    """References are fields which refer to other objects, which may
    have their own values"""
    def __init__(self, n, t, c, rt):
        self.reverse_reference_name = rt
        super(Reference, self).__init__(n, t, c)
        self.reverse_reference = None
    def toString(self):
        s = super(Reference, self).toString()
        if self.reverse_reference is None:
            return s
        else:
            return s + ", which links back to this as " + self.reverse_reference.name

class Collection(Reference):
    """Collections are references which refer to groups of objects"""
    pass

class Path(object):
    """A class representing a validated dotted string path

    Arguments:
    path_string - the dotted path string (eg: Gene.proteins.name)
    model - the model to validate the path against
    subclasses - a dict which maps subclasses (defaults to an empty dict)
    """
    def __init__(self, path_string, model, subclasses={}):
        self._string = path_string
        self.parts = model.parse_path_string(path_string, subclasses)

    def __str__(self):
        return self._string

    def __repr__(self):
        return '<' + self.__class__.__name__ + ": " + self._string + '>'

    @property
    def end(self):
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
    """a class for representing the data model of an InterMine
    
    Keyword arguments:
    source -- the model.xml, as a local file, string, or url
    """
    def __init__(self, source):
        assert source is not None
        self.source = source
        self.classes= {}
        self.parse_model(source)
        self.vivify()

    def parse_model(self, source):
        """Create classes, attributes, references and collections from the model.xml
           The xml can be provided as a file, url or string"""
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
        """make names point to instances and insert inherited fields"""
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
        """Returns the lineage of the class: ie, the class' parents, and all the class' parents' parents
        model.to_ancestry(cd) -> list(classes)
        """
        parents = cd.parents
        def defined(x): return x is not None # weeds out the java classes
        def to_class(x): return self.classes.get(x)
        ancestry = filter(defined, map(to_class, parents))
        for ancestor in ancestry:
            ancestry.extend(self.to_ancestry(ancestor))
        return ancestry

    def to_classes(self, classnames):
        """take a list of class names and return a list of classes
        model.to_classes(list(classnames)) -> list(classes)
        """
        return map(self.get_class, classnames)

    def get_class(self, name):
        """Get a class by its name, or by a dotted path
        model.get_class(name) -> class
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
        """Return a path object for the given path string
        model.make_path(string) -> path
        """
        return Path(path, self, subclasses)

    def validate_path(self, path_string, subclasses={}):
        """Validate a path - raises exceptions for invalid paths
        model.validate_path(string) -> Bool
        """
        try:
            self.parse_path_string(path_string, subclasses)
            return True
        except PathParseError, e:
            raise PathParseError("Error parsing '%s' (subclasses: %s)" 
                            % ( path_string, str(subclasses) ), e )

    def parse_path_string(self, path_string, subclasses={}):
        """Parse a path string into a list of descriptors - one for each section
        model.parse_path_string(string) -> list(descriptors)
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


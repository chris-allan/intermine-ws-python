from xml.dom import minidom
from intermine.util import openAnything
import re

class Class(object):
    def find_by(a, b):
        return a 
    def __init__(self, name, parents):
        self.name = name
        self.parents = parents
        self.parent_classes = []
        self.field_dict = {}
        id = Attribute("id", "Integer", self)
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
            raise PathError("There is no field called %s in %s" % (name, self.name))

    def isa(self, other):
        """Check if self is, or inherits from other"""
        if instance_of(other, Class):
            other_name = other.name
        else:
            other_name = other
        if self.name == other.name:
            return True
        if other_name in self.parents:
            return True
        for p in self.parent_classes:
            if p.isa(other):
                return True
        return False
    

class Field(object):
    def __init__(self, n, t, c):
        self.name = n
        self.type_name = t
        self.type_class = None
        self.declared_in = c
    def toString(self):
        return self.name + " is a " + self.type_name

class Attribute(Field):
    pass

class Reference(Field):
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
    pass

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
        """Create classes, attributes, references and collections from the model.xml"""
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
        parents = cd.parents
        def defined(x): return x is not None # weeds out the java classes
        def to_class(x): return self.classes.get(x)
        ancestry = filter(defined, map(to_class, parents))
        for ancestor in ancestry:
            ancestry.extend(self.to_ancestry(ancestor))
        return ancestry

    def to_classes(self, classnames):
        """take a list of class names and return a list of classes"""
        return map(self.get_class, classnames)

    def get_class(self, name):
        """Get a class by its name"""
        if name in self.classes:
          return self.classes[name]
        else:
          raise PathError("'" + name + "' is not a valid class name for this model")

    def validate_path(self, path_string, subclasses):
        """Validate a path"""
        try:
            self.parse_path_string(path_string, subclasses)
            return True
        except PathError, e:
            raise PathError("Error parsing '%s' (subclasses: %s)" 
                            % ( path_string, str(subclasses) ), e )

    def parse_path_string(self, path_string, subclasses={}):
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

class PathError(Exception):
    pass

#xmlfile = "/home/alex/svn/dev/testmodel/dbmodel/build/model/testmodel_model.xml"
#xml = 'http://www.flymine.org/query/service/model'
#model = Model(xml)
#
#def toString(x): return x.toString()
#for x in ['Gene', 'Exon', 'Amplicon']:
#    c = model.class_by_name(x)
#    print c.name, ", which inherits from", c.parents
#    print ". attributes:", map(toString, c.attributes)
#    print ". references:", map(toString, c.references)
#    print ". collections:", map(toString, c.collections)
#
##

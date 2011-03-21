from intermine.model import Model
import unittest

class MakeModel(unittest.TestCase):
    file_name = 'data/testmodel_model.xml'
    file_contents = open(file_name).read()
    def test_make_from_file(self):
        '''should be able to make a model from a file'''
        m = Model(self.file_name)
        self.assertIsInstance(m, Model, 
                "Can't make a model from a file")
        m = Model(self.file_contents)
        self.assertIsInstance(m, Model,
                "Can't make a model from a string")

class ClassDescriptors(unittest.TestCase):
    m = Model(self.file_name)
    good_class_names = ('Employee', 'Company', 'Department')
    bad_class_names = ('Foo', 'Bar', 'Quux')
    attrs_of_CEO = ['name', 'age', 'fullTime', 'seniority']
    refs_of_CEO = ['Department']
    cols_of_CEO = ['foo']
    fields_of_CEO = sum([attrs_of_CEO, refs_of_CEO, cols_of_CEO], [])
    def test_class_exists(self):
        '''The model should have the appropriate class descriptors'''
        self.assertEquals(len(self.m.classes), 42, 
                "Doesn't have the right number of classes")
        for c in good_class_names:
            self.assertTrue(self.m.class_by_name(c), 
                    "Doesn't return a true value for " + c)
            self.assertIs(self.m.class_by_name(c).name, c,
                    "Doesn't get the right class for " + c)
        for c in bad_class_names:
            self.assertFalse(self.m.class_by_name(c),
                    "Doesn't return a false value for " + c)
    def test_class_fields(self):
        '''The classes should have the appropriate fields'''
        ceo = self.m.class_by_name('CEO')
        self.assertIs(ceo.field_called.keys, fields_of_CEO,
                "CEO has the wrong fields")
        to_name = lambda x: x.name
        self.assertIs(map(to_name, ceo.attributes, attrs_of_CEO,
                "CEO has the wrong attributes")
        self.assertIs(map(to_name, ceo.references), refs_of_CEO,
                "CEO has the wrong references")
        self.assertIS(map(to_name, ceo.collections), cols_of_CEO,
                "CEO has the wrong collections")
    def test_field_attributes(self)
        '''The fields should have the appropriate attributes'''
        f = m.class_by_name('CEO').field_called['department']
        type_class = m.class_by_name('Department')
        declarer = m.class_by_name('Employee')
        self.assertIs(f.name, 'CEO'
            "Got the name wrong")
        self.assertIs(f.type_name, 'Department'
            "Got the type name wrong")
        self.assertIs(f.declared_in, declarer,
            "Got the declarer wrong")
        self.assertIs(f.type_class, type_class,
            "Type class of reference is wrong")

if __name__ == '__main__':
    unittest.main()

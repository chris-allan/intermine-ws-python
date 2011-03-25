import threading
from intermine.model import Model, ModelError
from intermine.service import Service
from intermine.query import Query, Template, ConstraintError
import SimpleHTTPServer

import unittest

class ServerThread( threading.Thread ):
    def __init__(self):
        super(ServerThread, self).__init__()
        self.daemon = True
    def run(self):
        SimpleHTTPServer.test()

class TestInstantiation(unittest.TestCase): 

    def testMakeModel(self):
        m = Model("http://localhost:8000/test/service/model")
        self.assertTrue(isinstance(m, Model), "Can make a model")

    def testMakeService(self):
        s = Service("http://localhost:8000/test/service")
        self.assertTrue(isinstance(s, Service), "Can make a service")

class TestService(unittest.TestCase):

    ROOT = "http://localhost:8000/test/service"
     
    def setUp(self):
        self.s = Service(TestService.ROOT)

    def testRoot(self):
        self.assertEqual(TestService.ROOT, self.s.root, "it has the right root")

    def testQueryMaking(self):
        q = self.s.new_query()
        self.assertTrue(isinstance(q, Query), "Can make a query")
        self.assertEqual(q.model.name, "testmodel", "and it has the right model")

class TestQuery(unittest.TestCase):

    model = None
    expected_unary = '[<UnaryConstraint: Employee.age IS NULL>, <UnaryConstraint: Employee.name IS NOT NULL>]'
    expected_binary = '[<BinaryConstraint: Employee.age > 50000>, <BinaryConstraint: Employee.name = John>, <BinaryConstraint: Employee.end != 0>]'
    expected_multi = "[<MultiConstraint: Employee.name ONE OF ['Tom', 'Dick', 'Harry']>, <MultiConstraint: Manager.name NONE OF ['Sue', 'Jane', 'Helen']>]"
    expected_ternary = '[<TernaryConstraint: Employee LOOKUP Susan>, <TernaryConstraint: Employee LOOKUP John IN Wernham-Hogg>]'
    expected_subclass = "[<SubClassConstraint: Department.employees ISA Manager>]"

    def setUp(self):
        if self.model is None:
            self.__class__.model = Model("http://localhost:8000/test/service/model") 
        self.q = Query(self.model)

    def testAddViews(self):
        self.q.add_view("Employee.age")
        self.q.add_view("Employee.name", "Employee.department.company.name")
        self.q.add_view("Employee.department.name Employee.department.company.vatNumber")
        self.q.add_view("Employee.department.manager.name,Employee.department.company.CEO.name")
        self.q.add_view("Employee.department.manager.name, Employee.department.company.CEO.name")
        expected = [
            "Employee.age", "Employee.name", "Employee.department.company.name", 
            "Employee.department.name", "Employee.department.company.vatNumber",
            "Employee.department.manager.name", "Employee.department.company.CEO.name", 
            "Employee.department.manager.name", "Employee.department.company.CEO.name"]
        self.assertEqual(self.q.views, expected)
        with self.assertRaises(ConstraintError) as context:
            self.q.add_view("Employee.name", "Employee.age", "Employee.department")
        self.assertEqual("Employee.department does not represent an attribute", context.exception.message)

    def testConstraintProblems(self):
        with self.assertRaises(ModelError) as context:
            self.q.add_constraint('Foo', 'IS NULL')
        self.assertEqual(context.exception.message, "'Foo' is not a class in this model")

    def testUnaryConstraints(self):
        self.q.add_constraint('Employee.age', 'IS NULL')
        self.q.add_constraint('Employee.name', 'IS NOT NULL')
        self.assertEqual(self.q.constraints.__repr__(), self.expected_unary)

    def testAddBinaryConstraints(self):
        self.q.add_constraint('Employee.age', '>', 50000)
        self.q.add_constraint('Employee.name', '=', 'John')
        self.q.add_constraint('Employee.end', '!=', 0)
        self.assertEqual(self.q.constraints.__repr__(), self.expected_binary)

    def testTernaryConstraint(self):
        self.q.add_constraint('Employee', 'LOOKUP', 'Susan')
        self.q.add_constraint('Employee', 'LOOKUP', 'John', 'Wernham-Hogg')
        self.assertEqual(self.q.constraints.__repr__(), self.expected_ternary)

    def testMultiConstraint(self):
        self.q.add_constraint('Employee.name', 'ONE OF', ['Tom', 'Dick', 'Harry'])
        self.q.add_constraint('Manager.name', 'NONE OF', ['Sue', 'Jane', 'Helen'])
        self.assertEqual(self.q.constraints.__repr__(), self.expected_multi)

    def testSubclassConstraints(self):
        self.q.add_constraint('Department.employees', 'Manager')
        self.assertEqual(self.q.constraints.__repr__(), self.expected_subclass)
        with self.assertRaises(ModelError) as context:
           self.q.add_constraint('Department.company.CEO', 'Foo')
        self.assertEqual(
            context.exception.message, 
            "'Foo' is not a class in this model")
        with self.assertRaises(ConstraintError) as context:
            self.q.add_constraint('Department.company.CEO', 'Manager')
        self.assertEqual(
            context.exception.message, 
            "'Manager' is not a subclass of 'Department.company.CEO'")

    def testJoins(self):
        with self.assertRaises(TypeError) as context:
            self.q.add_join('Employee.department', 'foo')
        self.assertEqual(context.exception.message, "Unknown join style: foo")
        with self.assertRaises(ConstraintError) as context:
            self.q.add_join('Employee.age', 'inner')
        self.assertEqual(context.exception.message, 
            "'Employee.age' is not a reference")
        self.q.add_join('Employee.department', 'inner')
        self.q.add_join('Employee.department.company', 'outer')
        expected = "[<Join: Employee.department INNER>, <Join: Employee.department.company OUTER>]"
        self.assertEqual(expected, self.q.joins.__repr__())

    def testXML(self):
        self.q.add_view("Employee.name", "Employee.age", "Employee.department.name")
        self.q.add_constraint("Employee.name", "IS NOT NULL")
        self.q.add_constraint("Employee.age", ">", 10)
        self.q.add_constraint("Employee.department", "LOOKUP", "Sales", "Wernham-Hogg")
        self.q.add_constraint("Employee.department.employees.name", "ONE OF", 
            ["John", "Paul", "Mary"])
        self.q.add_constraint("Employee.department.employees", "Manager")
        self.q.add_join("Employee.department", "outer")
        expected = '<query longDescription="" model="testmodel" name="" sortOrder="Employee.name asc" view="Employee.name Employee.age Employee.department.name"><join path="Employee.department" style="OUTER"/><constraint code="A" op="IS NOT NULL" path="Employee.name"/><constraint code="B" op="&gt;" path="Employee.age" value="10"/><constraint code="C" extraValue="Wernham-Hogg" op="LOOKUP" path="Employee.department" value="Sales"/><constraint code="D" op="ONE OF" path="Employee.department.employees.name"><value>John</value><value>Paul</value><value>Mary</value></constraint><constraint path="Employee.department.employees" type="Manager"/></query>'
        self.assertEqual(expected, self.q.to_xml())

class TestTemplate(TestQuery):
    
    expected_unary = '[<TemplateUnaryConstraint: Employee.age IS NULL (editable, locked)>, <TemplateUnaryConstraint: Employee.name IS NOT NULL (editable, locked)>]'
    expected_binary = '[<TemplateBinaryConstraint: Employee.age > 50000 (editable, locked)>, <TemplateBinaryConstraint: Employee.name = John (editable, locked)>, <TemplateBinaryConstraint: Employee.end != 0 (editable, locked)>]'
    expected_multi = "[<TemplateMultiConstraint: Employee.name ONE OF ['Tom', 'Dick', 'Harry'] (editable, locked)>, <TemplateMultiConstraint: Manager.name NONE OF ['Sue', 'Jane', 'Helen'] (editable, locked)>]"
    expected_ternary = '[<TemplateTernaryConstraint: Employee LOOKUP Susan (editable, locked)>, <TemplateTernaryConstraint: Employee LOOKUP John IN Wernham-Hogg (editable, locked)>]'
    expected_subclass = '[<TemplateSubClassConstraint: Department.employees ISA Manager (editable, locked)>]'

    def setUp(self):
        super(TestTemplate, self).setUp()
        self.q = Template(self.model)

class TestQueryResults(unittest.TestCase):

    model = None
    service = Service("http://localhost:8000/test/service")

    class MockService(object):
        
        QUERY_PATH = '/QUERY-PATH'
        TEMPLATEQUERY_PATH = '/TEMPLATE-PATH'
        root = 'ROOT'

        def get_results(self, *args):
            return args
    
    def setUp(self):
        if self.model is None:
            self.__class__.model = Model("http://localhost:8000/test/service/model") 
        q = Query(self.model, self.service)
        q.add_view("Employee.name", "Employee.age", "Employee.id")
        self.query = q
        t = Template(self.model, self.service)
        t.add_view("Employee.name", "Employee.age", "Employee.id")
        t.add_constraint("Employee.name", '=', "Fred")
        t.add_constraint("Employee.age", ">", 25)
        self.template = t

    def testURLs(self):
        q = Query(self.model, self.MockService())
        q.add_view("Employee.name", "Employee.age", "Employee.id")
        q.add_constraint("Employee.name", '=', "Fred")
        q.add_constraint("Employee.age", ">", 25)

        t = Template(self.model, self.MockService())
        t.name = "TEST-TEMPLATE"
        t.add_view("Employee.name", "Employee.age", "Employee.id")
        t.add_constraint("Employee.name", '=', "Fred")
        t.add_constraint("Employee.age", ">", 25)

        expectedQ = (
            '/QUERY-PATH', 
            {
                'query': '<query longDescription="" model="testmodel" name="" sortOrder="Employee.name asc" view="Employee.name Employee.age Employee.id"><constraint code="A" op="=" path="Employee.name" value="Fred"/><constraint code="B" op="&gt;" path="Employee.age" value="25"/></query>'
            }, 
            'list', 
            ['Employee.name', 'Employee.age', 'Employee.id']
        )
        self.assertEqual(expectedQ, q.results())

        expected1 = (
            '/TEMPLATE-PATH', 
            {
             'name': 'TEST-TEMPLATE', 
             'code1': 'A', 
             'code2': 'B', 
             'path1': 'Employee.name', 
             'path2': 'Employee.age', 
             'op1': '=',
             'op2': '>', 
             'value1': 'Fred', 
             'value2': '25'
            }, 
           'list', 
           ['Employee.name', 'Employee.age', 'Employee.id'])
        self.assertEqual(expected1, t.results())

        expected2 = (
            '/TEMPLATE-PATH', 
            {
             'name': 'TEST-TEMPLATE', 
             'code1': 'A', 
             'code2': 'B', 
             'path1': 'Employee.name', 
             'path2': 'Employee.age', 
             'op1': '<',
             'op2': '>', 
             'value1': 'Tom', 
             'value2': '55'
            }, 
           'list', 
           ['Employee.name', 'Employee.age', 'Employee.id'])
        self.assertEqual(expected2, t.results(
            A = {"op": "<", "value": "Tom"},
            B = {"value": 55} 
        ))

        self.assertEqual(expected1, t.results()) 

    def testResultsList(self):
        expected = [['foo', 'bar', 'baz'],['quux','fizz','fop']]
        self.assertEqual(self.query.results(), expected)
        self.assertEqual(self.template.results(), expected)

    def testResultsDict(self):
        expected = [
            {'Employee.name':'foo', 'Employee.age':'bar', 'Employee.id':'baz'},
            {'Employee.name':'quux', 'Employee.age':'fizz', 'Employee.id':'fop'}
            ]
        self.assertEqual(self.query.results("dict"), expected)
        self.assertEqual(self.template.results("dict"), expected)

    def testResultsString(self):
        expected = [
            '"foo","bar","baz"\n',
            '"quux","fizz","fop"\n'
            ]
        self.assertEqual(self.query.results("string"), expected)
        self.assertEqual(self.template.results("string"), expected)

if __name__ == '__main__':
    server = ServerThread()
    server.start()
    unittest.main()

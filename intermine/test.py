import threading
from intermine.model import Model, ModelError
from intermine.service import Service
from intermine.query import Query, ConstraintError
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

    def setUp(self):
        self.m = Model("http://localhost:8000/test/service/model")
        self.s = Service("http://localhost:8000/test/service")

    def testAddViews(self):
        q = Query(self.m)
        q.add_view("Employee.age")
        q.add_view("Employee.name", "Employee.department.company.name")
        q.add_view("Employee.department.name Employee.department.company.vatNumber")
        q.add_view("Employee.department.manager.name,Employee.department.company.CEO.name")
        q.add_view("Employee.department.manager.name, Employee.department.company.CEO.name")
        expected = [
            "Employee.age", "Employee.name", "Employee.department.company.name", 
            "Employee.department.name", "Employee.department.company.vatNumber",
            "Employee.department.manager.name", "Employee.department.company.CEO.name", 
            "Employee.department.manager.name", "Employee.department.company.CEO.name"]
        self.assertEqual(q.views, expected)

    def testConstraintProblems(self):
        q = Query(self.m)
        with self.assertRaises(ModelError) as context:
            q.add_constraint('Foo', 'IS NULL')
        self.assertEqual(context.exception.message, "'Foo' is not a class in this model")

    def testUnaryConstraints(self):
        q = Query(self.m)
        q.add_constraint('Employee.age', 'IS NULL')
        q.add_constraint('Employee.name', 'IS NOT NULL')
        expected = '[<UnaryConstraint: Employee.age IS NULL>, <UnaryConstraint: Employee.name IS NOT NULL>]'
        self.assertEqual(q.constraints.__repr__(), expected)

    def testAddBinaryConstraints(self):
        q = Query(self.m)
        q.add_constraint('Employee.age', '>', 50000)
        q.add_constraint('Employee.name', '=', 'John')
        q.add_constraint('Employee.end', '!=', 0)
        expected = '[<BinaryConstraint: Employee.age > 50000>, <BinaryConstraint: Employee.name = John>, <BinaryConstraint: Employee.end != 0>]'
        self.assertEqual(q.constraints.__repr__(), expected)

    def testTernaryConstraint(self):
        q = Query(self.m)
        q.add_constraint('Employee', 'LOOKUP', 'Susan')
        q.add_constraint('Employee', 'LOOKUP', 'John', 'Wernham-Hogg')
        expected = '[<TernaryConstraint: Employee LOOKUP Susan>, <TernaryConstraint: Employee LOOKUP John IN Wernham-Hogg>]'
        self.assertEqual(q.constraints.__repr__(), expected)

    def testMultiConstraint(self):
        q = Query(self.m)
        q.add_constraint('Employee.name', 'ONE OF', ['Tom', 'Dick', 'Harry'])
        q.add_constraint('Manager.name', 'NONE OF', ['Sue', 'Jane', 'Helen'])
        expected = "[<MultiConstraint: Employee.name ONE OF ['Tom', 'Dick', 'Harry']>, <MultiConstraint: Manager.name NONE OF ['Sue', 'Jane', 'Helen']>]"
        self.assertEqual(q.constraints.__repr__(), expected)

    def testSubclassConstraints(self):
        q = Query(self.m)
        q.add_constraint('Department.employees', 'Manager')
        expected = "[<SubClassConstraint: Department.employees ISA Manager>]"
        self.assertEqual(q.constraints.__repr__(), expected)
        with self.assertRaises(ModelError) as context:
            q.add_constraint('Department.company.CEO', 'Foo')
        self.assertEqual(
            context.exception.message, 
            "'Foo' is not a class in this model")
        with self.assertRaises(ConstraintError) as context:
            q.add_constraint('Department.company.CEO', 'Manager')
        self.assertEqual(
            context.exception.message, 
            "'Manager' is not a subclass of 'Department.company.CEO'")

    def testJoins(self):
        q = Query(self.m)
        with self.assertRaises(TypeError) as context:
            q.add_join('Employee.department', 'foo')
        self.assertEqual(context.exception.message, "Unknown join style: foo")
        with self.assertRaises(ConstraintError) as context:
            q.add_join('Employee.age', 'inner')
        self.assertEqual(context.exception.message, 
            "'Employee.age' is not a reference")
        q.add_join('Employee.department', 'inner')
        q.add_join('Employee.department.company', 'outer')
        expected = "[<Join: Employee.department INNER>, <Join: Employee.department.company OUTER>]"
        self.assertEqual(expected, q.joins.__repr__())

    def testXML(self):
        q = Query(self.m)
        q.add_view("Employee.name", "Employee.age", "Employee.department")
        q.add_constraint("Employee.name", "IS NOT NULL")
        q.add_constraint("Employee.age", ">", 10)
        q.add_constraint("Employee.department", "LOOKUP", "Sales", "Wernham-Hogg")
        q.add_constraint("Employee.department.employees.name", "ONE OF", 
            ["John", "Paul", "Mary"])
        q.add_constraint("Employee.department.employees", "Manager")
        q.add_join("Employee.department", "outer")
        expected = '<query comment="" longDescription="" model="testmodel" name="" sortOrder="Employee.name asc" view="Employee.name Employee.age Employee.department"><join path="Employee.department" style="OUTER"/><constraint code="A" op="IS NOT NULL" path="Employee.name"/><constraint code="B" op="&gt;" path="Employee.age" value="10"/><constraint code="C" extraValue="Wernham-Hogg" op="LOOKUP" path="Employee.department" value="Sales"/><constraint code="D" op="ONE OF" path="Employee.department.employees.name"><value>John</value><value>Paul</value><value>Mary</value></constraint><constraint path="Employee.department.employees" type="Manager"/></query>'
        self.assertEqual(expected, q.to_xml())

class TestQueryResults(unittest.TestCase):
    
    def setUp(self):
        m = Model("http://localhost:8000/test/service/model")
        s = Service("http://localhost:8000/test/service")
        q = Query(m, s)
        q.add_view("Employee.name", "Employee.age", "Employee.id")
        self.query = q

    def testResultsList(self):
        expected = [['foo', 'bar', 'baz'],['quux','fizz','fop']]
        self.assertEqual(self.query.results(), expected)

    def testResultsDict(self):
        expected = [
            {'Employee.name':'foo', 'Employee.age':'bar', 'Employee.id':'baz'},
            {'Employee.name':'quux', 'Employee.age':'fizz', 'Employee.id':'fop'}
            ]
        self.assertEqual(self.query.results("dict"), expected)

    def testResultsString(self):
        expected = [
            '"foo","bar","baz"\n',
            '"quux","fizz","fop"\n'
            ]
        self.assertEqual(self.query.results("string"), expected)

if __name__ == '__main__':
    server = ServerThread()
    server.start()
    unittest.main()

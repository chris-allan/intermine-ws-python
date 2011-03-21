import threading
from intermine.model import Model
from intermine.service import Service
from intermine.query import Query
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
        self.assertEqual(
            q.views, 
            ["Employee.age", "Employee.name", "Employee.department.company.name", "Employee.department.name",
             "Employee.department.company.vatNumber","Employee.department.manager.name", "Employee.department.company.CEO.name", "Employee.department.manager.name", "Employee.department.company.CEO.name"])

    def testAddBinaryConstraints(self):
        q = Query(self.m)
        q.add_constraint('Employee.age', '>', 50000)
        q.add_constraint('Employee.name', '=', 'John')
        q.add_constraint('Employee.end', '!=', 0)
        expected = '[<BinaryConstraint: Employee.age > 50000>, <BinaryConstraint: Employee.name = John>, <BinaryConstraint: Employee.end != 0>]'

        self.assertEqual(q.constraints.__repr__(), expected)



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
                

#       print "Service root: ", s.root
#       q = s.new_query()
#
#       #m = Model('http://www.flymine.org/query/service/model')
#       #q = Query(m)
#
#       q.name = 'Foo'
#       q.description = 'a query made out of pythons'
#       q.add_view("Gene.name Gene.symbol")
#       q.add_constraint('Gene', 'LOOKUP', 'eve')
#       q.add_constraint('Gene.length', '>', 50000)
#       q.add_constraint('Gene', 'Clone')
#       q.add_constraint('Gene.symbol', 'ONE OF', ['eve', 'zen'])
#       q.add_join('Gene.alleles')
#       q.add_path_description('Gene', 'One of those gene-y things')
#       print q.to_xml()
#       print q.to_formatted_xml()
#       print q.to_query_params()
#
#       q = s.new_query()
#       q.add_view("Gene.name", "Gene.organism.name", "Gene.pathways.name")
#
#       it = q.get_results_iterator("string")
#
#       print "ITERATOR: ", it
#
#       for line in it:
#           print line
#       #finally:
#       #    server.stop()
#
#       exit()

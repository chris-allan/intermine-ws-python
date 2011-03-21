from intermine.query import Query
from intermine.model import Model
import unittest

class MakeQuery(unittest.TestCase):
    m = Model('http://www.flymine.org/query/service/model')
    def test_make_query(self):
        '''should be able to make a query'''
        q = Query(self.m)
        self.assertTrue(isinstance(q, Query))

if __name__ == '__main__':
    unittest.main()



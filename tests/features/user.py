# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

'''
These tests were found by unusual end-user use-cases.

They represent distilled versions of real failures that
are not easily categorized.

Unit tests have been added to capture each failure,
to ensure it doesn't regress in future.
'''

import unittest

from constrainedrandom import RandObj
from .. import testutils


class NonPureFunction(unittest.TestCase):
    ''' Using a non-pure function as a constraint
        may result in it being called early, and
        the variable it captures outside itself
        may not yet have been assigned. '''
    
    def test_nonpure(self, *args):
        print(f'{self.__class__.__module__}.{self.__class__.__name__}.{self._testMethodName}')

        class Container:
            ''' Dummy class to contain a variable. '''

            def __init__(self):
                self.var = None

        # Create instance of dummy class
        c = Container()

        # Create RandObj with constraint referring to
        # member of dummy class
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(10))
        def non_pure_constraint(a):
            return a < c.var
        # This line used to fail, because we'd evaluate
        # the constraint here.
        r.add_constraint(non_pure_constraint, ('a'))

        # We should be able to get here and randomize
        # after c.var is assigned.
        c.var = 5
        r.randomize()


class RandSizeListOrder(testutils.RandObjTestBase):
    '''
    Minimal test that hits a specific corner case involving
    random list length.
    The case requires:
      - more than one list depending on the same random length
      - a small total state space
      - the lists are constrained based on one another and the random length
      - the lists have a different order value from one another
      - a constraint that uses the random length to index the lists
      - fails with naive solver, or skips it
      - fails with sparsities == 1, or manually run with sparsities > 1
    The symptom seen was IndexError: list index out of range
    when applying the constraint.
    '''

    ITERATIONS = 100

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('length', domain=range(1,3), order=0)
        r.add_rand_var('list1', domain=range(-10,11), rand_length='length', order=1)
        r.add_rand_var('list2', domain=range(-10,11), rand_length='length', order=2)

        def var_not_in_list(length, list1, list2):
            # Use length as an index, as this is how the bug
            # was found in the wild.
            for i in range(length):
                if list1[i] == list2[i]:
                    return False
            return True
        r.add_constraint(var_not_in_list, ('length', 'list1', 'list2'))
        r.set_solver_mode(naive=False, sparsities=[2])
        return r

    def check(self, results):
        for result in results:
            length = result['length']
            list1 = result['list1']
            list2 = result['list2']
            self.assertEqual(len(list1), length, "list1 length was wrong")
            self.assertEqual(len(list2), length, "list2 length was wrong")
            for x1, x2 in zip(list1, list2):
                self.assertFalse(x1 == x2)
                self.assertIn(x1, range(-10, 11))
                self.assertIn(x2, range(-10, 11))

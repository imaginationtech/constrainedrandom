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

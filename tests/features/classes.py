# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

'''
Test use of classes and class methods in constraints.
'''

import unittest

from constrainedrandom import RandObj
from .. import testutils


class Foo(RandObj):
    '''
    For testing, add a variable and constraints that depend on
    member variables of the class.
    Use a constraint that can be overridden by child classes.
    '''

    def __init__(self, _min, _max, *args):
        super().__init__(*args)
        self._max = _max
        self._min = _min
        self.add_rand_var('value', domain=range(1000))
        self.add_constraint(self.value_c, ('value'))

    def value_c(self, value):
        return self._min <= value <= self._max


class Bar(Foo):
    '''
    Override the constraint in Foo.
    '''

    def value_c(self, value):
        return 11 <= value < 20


class MemberVars(testutils.RandObjTestBase):
    '''
    Test using constraints that refer to member variables in that class.
    '''

    def get_randobj(self, *args):
        r = Foo(0, 10, *args)
        return r

    def check(self, results):
        for result in results:
            value = result['value']
            self.assertGreaterEqual(value, 0)
            self.assertLessEqual(value, 10)


class MemberVarsChanged(testutils.RandObjTestBase):
    '''
    Test using constraints that refer to member variables in that class,
    having changed those member vars.
    '''

    def get_randobj(self, *args):
        r = Foo(0, 10, *args)
        r._min = 11
        r._max = 19
        return r

    def check(self, results):
        for result in results:
            value = result['value']
            self.assertGreaterEqual(value, 11)
            self.assertLessEqual(value, 19)


class ChildClassConstraint(testutils.RandObjTestBase):
    '''
    Test that overriding the constraint in a child class works.
    '''

    def get_randobj(self, *args):
        r = Bar(0, 10, *args)
        return r

    def check(self, results):
        for result in results:
            value = result['value']
            self.assertGreaterEqual(value, 11)
            self.assertLessEqual(value, 19)


class MemberVarsChangedRand(unittest.TestCase):
    '''
    Test randomizing a randobj, then
    changing member variables used in constraints,
    observing the effect of the changes.

    Can't use base class for this one, as
    we won't check determinism.
    '''

    def test_change_vars(self):
        r = Foo(0, 10)
        results = []
        for _ in range(10):
            r.randomize()
            results.append(r.get_results())
        MemberVars.check(self, results)
        r._min = 11
        r._max = 19
        results = []
        for _ in range(10):
            r.randomize()
            results.append(r.get_results())
        MemberVarsChanged.check(self, results)
        return r

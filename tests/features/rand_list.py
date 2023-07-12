# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

'''
Test random lists.
'''

from random import Random

from constrainedrandom import RandObj
from constrainedrandom.utils import unique
from .. import testutils


class RandList(testutils.RandObjTestBase):
    '''
    Test a randomized list.
    '''

    ITERATIONS = 1000

    def get_randobj(self, seed):
        r = RandObj(Random(seed))
        r.add_rand_var('listvar', domain=range(10), length=10)
        return r

    def check(self, results):
        for result in results:
            self.assertIsInstance(result['listvar'], list, "Var with length > 0 wasn't a list")
            for x in result['listvar']:
                self.assertIn(x, range(10), "Value was wrongly randomized")


class RandListConstrained(testutils.RandObjTestBase):
    '''
    Test a randomized list with constraints on the values in the list.
    '''

    ITERATIONS = 100

    def get_randobj(self, seed):
        r = RandObj(Random(seed))
        def plus_or_minus_one(listvar):
            val = listvar[0]
            for nxt_val in listvar[1:]:
                if nxt_val == val + 1 or nxt_val == val - 1:
                    val = nxt_val
                    continue
                return False
            return True
        r.add_rand_var('listvar', domain=range(10), length=10, list_constraints=(plus_or_minus_one,))
        return r

    def check(self, results):
        for result in results:
            self.assertIsInstance(result['listvar'], list, "Var with length > 0 wasn't a list")
            prev = None
            for x in result['listvar']:
                self.assertIn(x, range(10), "Value was wrongly randomized")
                if prev is not None:
                    self.assertTrue(x == prev + 1 or x == prev - 1, "list constraint not followed")
                prev = x


class RandListMultivar(testutils.RandObjTestBase):
    '''
    Test a randomized list with constraints on the values in the list,
    also with constraints over multiple variables.
    '''

    ITERATIONS = 30

    def get_randobj(self, seed):
        r = RandObj(Random(seed))
        def plus_or_minus_one(listvar):
            val = listvar[0]
            for nxt_val in listvar[1:]:
                if nxt_val == val + 1 or nxt_val == val - 1:
                    val = nxt_val
                    continue
                return False
            return True
        r.add_rand_var('listvar', domain=range(10), length=10, list_constraints=(plus_or_minus_one,))
        r.add_rand_var('x', domain=range(100), order=1)
        def in_list(x, listvar):
            return x in listvar
        r.add_constraint(in_list, ('x', 'listvar'))
        return r

    def check(self, results):
        for result in results:
            self.assertIsInstance(result['listvar'], list, "Var with length > 0 wasn't a list")
            prev = None
            for l in result['listvar']:
                self.assertIn(l, range(10), "Value was wrongly randomized")
                if prev is not None:
                    self.assertTrue(l == prev + 1 or l == prev - 1, "list constraint not followed")
                prev = l
            self.assertIn(result['x'], result['listvar'])


class RandListUnique(testutils.RandObjTestBase):
    '''
    Test that the unique constraint works on a random list.
    '''

    ITERATIONS = 1000

    def get_randobj(self, seed):
        r = RandObj(Random(seed))
        r.add_rand_var('listvar', domain=range(10), length=10, list_constraints=(unique,))
        return r

    def check(self, results):
        for result in results:
            self.assertIsInstance(result['listvar'], list, "Var with length > 0 wasn't a list")
            for x_idx, x in enumerate(result['listvar']):
                self.assertIn(x, range(10), "Value was wrongly randomized")
                for y_idx, y in enumerate(result['listvar']):
                    if x_idx != y_idx:
                        self.assertNotEqual(x, y, "List elements were not unique")


class RandListTempConstraints(testutils.RandObjTestBase):
    '''
    Test a randomized list with temporary constraints.
    '''

    ITERATIONS = 100

    def get_randobj(self, seed):
        r = RandObj(Random(seed))
        r.add_rand_var('listvar', domain=range(10), length=10)
        return r

    def check(self, results):
        for result in results:
            self.assertIsInstance(result['listvar'], list, "Var with length > 0 wasn't a list")
            for x in result['listvar']:
                self.assertIn(x, range(10), "Value was wrongly randomized")

    def get_tmp_constraints(self):
        def temp_constr(listvar):
            for x in listvar:
                if x == 5:
                    return False
            return True
        return [(temp_constr, ('listvar',))]

    def tmp_check(self, results):
        self.check(results)
        for result in results:
            for x in result['listvar']:
                self.assertNotEqual(x, 5, "Temp constraint not respected")


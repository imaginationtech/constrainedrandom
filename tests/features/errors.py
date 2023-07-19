# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

'''
Test error cases.
'''

from random import Random

from constrainedrandom import RandObj, RandomizationError

from .basic import MultiSum
from .. import testutils


class FailedMultiSum(MultiSum):
    '''
    Test the thorough solver for a problem that will always fail.

    This problem fails through being too hard rather than impossible.
    '''

    EXPECT_FAILURE = True

    def get_randobj(self, seed):
        randobj = super().get_randobj(seed)
        # Set max_iterations to 1 to ensure thorough solver is used.
        randobj._max_iterations = 1
        # Setting max domain size to 1 means all variables will be treated
        # as random, ensuring the problem will fail.
        randobj._max_domain_size = 1
        return randobj


class ImpossibleOneVar(testutils.RandObjTestBase):
    '''
    Test an impossible constraint problem with one variable.
    '''

    def get_randobj(self, seed):
        randobj = RandObj(Random(seed))
        def eq_zero(x):
            return x == 0
        randobj.add_rand_var('a', domain=[1,], constraints=[eq_zero,])
        return randobj

    def test_randobj(self):
        # Override the whole test function, because unsolvable
        # simple single variables fail on creation, rather
        # than when randomize is called.
        self.assertRaises(RandomizationError, self.get_randobj, 0)
        self.assertRaises(RandomizationError, self.get_randobj, 1)


class ImpossibleComplexVar(testutils.RandObjTestBase):
    '''
    Test an impossible constraint problem with one variable, where
    the variable state space is too large to fail on creation.
    '''

    EXPECT_FAILURE = True

    def get_randobj(self, seed):
        randobj = RandObj(Random(seed))
        def eq_minus_one(x):
            return x == -1
        randobj.add_rand_var('a', bits=64, constraints=[eq_minus_one,])
        return randobj


class ImpossibleMultiVar(testutils.RandObjTestBase):
    '''
    Test an impossible constraint problem with multiple variables.
    '''

    EXPECT_FAILURE = True

    def get_randobj(self, seed):
        randobj = RandObj(Random(seed))
        def lt_5(x):
            return x < 5
        randobj.add_rand_var('a', domain=range(10), constraints=[lt_5,])
        randobj.add_rand_var('b', domain=range(10), constraints=[lt_5,])
        def sum_gt_10(x, y):
            return x + y > 10
        randobj.add_constraint(sum_gt_10, ('a', 'b'))
        return randobj

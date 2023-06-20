# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

''' Reusable definitions for unit testing '''

import timeit
import unittest
from random import Random

from constrainedrandom import RandObj


def get_randobj_sum(seed):
    '''
    Very difficult problem to solve naively, to force the solver
    into using MultiVarProblem. Used by several tests.
    '''
    r = RandObj(Random(seed))
    # Very unlikely (1/200^3) to solve the problem naively, just skip to applying constraints.
    r.set_naive_solve(False)
    def nonzero(x):
        return x != 0
    r.add_rand_var("x", domain=range(-100, 100), order=0, constraints=(nonzero,))
    r.add_rand_var("y", domain=range(-100, 100), order=1, constraints=(nonzero,))
    r.add_rand_var("z", domain=range(-100, 100), order=1, constraints=(nonzero,))
    def sum_41(x, y, z):
        return x + y + z == 41
    r.add_multi_var_constraint(sum_41, ("x", "y", "z"))
    return r


def randobj_sum_check(instance, results):
    for result in results:
        instance.assertEqual(result['x'] + result['y'] + result['z'], 41, f'Check failed for {result=}')
        instance.assertNotEqual(result['x'], 0, f'Check failed for {result=}')


class RandObjTestsBase(unittest.TestCase):
    '''
    Provides useful utilities for testing features of constrainedrandom.
    Extend this class to create testcases.
    '''

    TEST_LENGTH_MULTIPLIER = 1

    def randomize_and_time(self, randobj, iterations, tmp_constraints=None, tmp_values=None):
        '''
        Call randobj.randomize() iterations times, time it, print performance stats,
        return the results.
        '''
        results = []
        time_taken = 0
        for _ in range(iterations):
            start_time = timeit.default_timer()
            if tmp_constraints is not None or tmp_values is not None:
                randobj.randomize(with_constraints=tmp_constraints, with_values=tmp_values)
            else:
                randobj.randomize()
            end_time = timeit.default_timer()
            time_taken += end_time - start_time
            # Extract the results
            results.append(randobj.get_results())
        hz = iterations/time_taken
        print(f'{self._testMethodName} took {time_taken:.4g}s for {iterations} iterations ({hz:.1f}Hz)')
        return results

    def assertListOfDictsEqual(self, list0, list1, msg):
        '''
        This is missing from unittest. It doesn't like it when two large lists of dictionaries
        are different and compared using `assertListEqual` or `assertEqual`.
        '''
        for i, j in zip(list0, list1):
            self.assertDictEqual(i, j, msg)

    def randobj_test(
        self,
        randobj_getter,
        iterations,
        check,
        tmp_constraints=None,
        tmp_check=None,
        tmp_values=None
    ):
        '''
        Reusable test function to randomize a RandObj for a number of iterations and perform checks.

        Tests functionality based on check argument. Reports performance stats. Tests determinism.

        randobj_getter:   function that accepts a seed and returns a RandObj to be tested.
        iterations:       number of times to call .randomize()
        check:            function accepting results (a list of dictionaries) to perform required checks.
        tmp_constraints:  (optional) temporary constraints to apply to the problem.
        tmp_check:        (optional) extra check when temporary constraints are applied.
        tmp_values:       (optional) temporary values to apply to the problem.
        '''
        iterations *= self.TEST_LENGTH_MULTIPLIER
        do_tmp_checks = tmp_constraints is not None or tmp_values is not None

        # Test with seed 0
        randobj = randobj_getter(0)
        results = self.randomize_and_time(randobj, iterations)
        check(results)
        if do_tmp_checks:
            # Check when applying temporary constraints
            tmp_results = self.randomize_and_time(randobj, iterations, tmp_constraints, tmp_values)
            if tmp_check is not None:
                tmp_check(tmp_results)
            # Check temporary constraints don't break base randomization
            post_tmp_results = self.randomize_and_time(randobj, iterations)
            check(post_tmp_results)

        # Test again with seed 0, ensuring results are the same
        randobj0 = randobj_getter(0)
        results0 = self.randomize_and_time(randobj0, iterations)
        self.assertListOfDictsEqual(results, results0, "Non-determinism detected, results were not equal")
        if do_tmp_checks:
            # Check applying temporary constraints is also deterministic
            tmp_results0 = self.randomize_and_time(randobj0, iterations, tmp_constraints, tmp_values)
            self.assertListOfDictsEqual(
                tmp_results,
                tmp_results0,
                "Non-determinism detected, results were not equal with temp constraints"
            )
            # Check temporary constraints don't break base randomization determinism
            post_tmp_results0 = self.randomize_and_time(randobj0, iterations)
            self.assertListOfDictsEqual(
                post_tmp_results,
                post_tmp_results0,
                "Non-determinism detected, results were not equal after temp constraints"
            )

        # Test with seed 1, ensuring results are different
        randobj1 = randobj_getter(1)
        results1 = self.randomize_and_time(randobj1, iterations)
        check(results1)
        self.assertNotEqual(results, results1, "Results were the same for two different seeds, check testcase.")
        if do_tmp_checks:
            # Check results are also different when applying temporary constraints
            tmp_results1 = self.randomize_and_time(randobj1, iterations, tmp_constraints, tmp_values)
            if tmp_check is not None:
                tmp_check(tmp_results1)
            self.assertNotEqual(tmp_results, tmp_results1,
                                "Results were the same for two different seeds, check testcase.")
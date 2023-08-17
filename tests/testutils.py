# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

''' Reusable definitions for unit testing '''

import random
import timeit
import unittest
from copy import deepcopy
from typing import Any, Dict, List

from constrainedrandom import RandObj, RandomizationError


def assertListOfDictsEqual(instance, list0, list1, msg) -> None:
    '''
    This is missing from unittest. It doesn't like it when two large lists of dictionaries
    are different and compared using `assertListEqual` or `assertEqual`.
    '''
    for i, j in zip(list0, list1):
        instance.assertDictEqual(i, j, msg)


class RandObjTestBase(unittest.TestCase):
    '''
    Provides useful utilities for testing features of constrainedrandom.
    Extend this class to create testcases.
    '''

    ITERATIONS = 1000
    TEST_LENGTH_MULTIPLIER = 1
    EXPECT_FAILURE = False

    def setUp(self) -> None:
        self.iterations = self.ITERATIONS * self.TEST_LENGTH_MULTIPLIER

    def get_full_test_name(self) -> str:
        '''
        Returns the full path to the test being run.
        '''
        return f'{self.__class__.__module__}.{self.__class__.__name__}.{self._testMethodName}'

    def get_randobj(self, *args) -> RandObj:
        '''
        Returns an instance of a `RandObj` for this problem, based
        on a given seed.
        '''
        pass

    def check(self, results) -> None:
        '''
        Checks the results of randomization are correct,
        according to the defined problem.
        '''
        pass

    def get_tmp_constraints(self) -> List[Any]:
        '''
        Returns temporary constraints for the problem, if any.
        '''
        return None

    def get_tmp_values(self) -> Dict[str, Any]:
        '''
        Returns temporary values for the problem, if any.
        '''
        return None

    def tmp_check(self, results) -> None:
        '''
        Checks the results of randomization are correct,
        according to the defined problem plus any
        temporary constraints/values.
        '''
        pass

    def randomize_and_time(self, randobj, iterations, tmp_constraints=None, tmp_values=None) -> List[Dict[str, Any]]:
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
        print(f'{self.get_full_test_name()} took {time_taken:.4g}s for {iterations} iterations ({hz:.1f}Hz)')
        return results

    def randomize_and_check_result(
        self,
        randobj,
        expected_results,
        do_tmp_checks,
        tmp_constraints,
        tmp_values,
        expected_tmp_results,
        expected_post_tmp_results,
        expected_add_results,
        add_tmp_constraints,
    ) -> None:
        '''
        Code to randomize a randobj and check its results against expected
        results.
        '''
        if self.EXPECT_FAILURE:
            self.assertRaises(RandomizationError, randobj.randomize)
        else:
            results = self.randomize_and_time(randobj, self.iterations)
            assertListOfDictsEqual(self, expected_results, results, "Non-determinism detected, results were not equal")
            if do_tmp_checks:
                # Check applying temporary constraints is also deterministic
                tmp_results = self.randomize_and_time(randobj, self.iterations, tmp_constraints, tmp_values)
                assertListOfDictsEqual(
                    self,
                    expected_tmp_results,
                    tmp_results,
                    "Non-determinism detected, results were not equal with temp constraints"
                )
                # Check temporary constraints don't break base randomization determinism
                post_tmp_results = self.randomize_and_time(randobj, self.iterations)
                assertListOfDictsEqual(
                    self,
                    expected_post_tmp_results,
                    post_tmp_results,
                    "Non-determinism detected, results were not equal after temp constraints"
                )
                # Add temporary constraints permanently, see what happens
                if add_tmp_constraints and tmp_constraints is not None:
                    for constr, vars in tmp_constraints:
                        randobj.add_constraint(constr, vars)
                    add_results = self.randomize_and_time(randobj, self.iterations, tmp_values=tmp_values)
                    assertListOfDictsEqual(
                        self,
                        expected_add_results,
                        add_results,
                        "Non-determinism detected, results were not equal after constraints added"
                    )

    def test_randobj(self) -> None:
        '''
        Reusable test function to randomize a RandObj for a number of iterations and perform checks.

        Tests functionality based on `self.check`.
        Reports performance stats.
        Tests determinism.
        Tests use of temporary constraints and values.
        '''
        tmp_constraints = self.get_tmp_constraints()
        tmp_values = self.get_tmp_values()
        do_tmp_checks = tmp_constraints is not None or tmp_values is not None
        results = None
        tmp_results = None
        post_tmp_results = None
        add_results = None

        # Test with seed 0
        r = random.Random(0)
        randobj = self.get_randobj(r)
        # Take a copy of the randobj for use later
        randobj_copy = deepcopy(randobj)
        if self.EXPECT_FAILURE:
            self.assertRaises(RandomizationError, randobj.randomize)
        else:
            results = self.randomize_and_time(randobj, self.iterations)
            self.check(results)
            if do_tmp_checks:
                # Check when applying temporary constraints
                tmp_results = self.randomize_and_time(randobj, self.iterations, tmp_constraints, tmp_values)
                self.tmp_check(tmp_results)
                # Check temporary constraints don't break base randomization
                post_tmp_results = self.randomize_and_time(randobj, self.iterations)
                self.check(post_tmp_results)
                # Add temporary constraints permanently, see what happens
                if tmp_constraints is not None:
                    for constr, vars in tmp_constraints:
                        randobj.add_constraint(constr, vars)
                    add_results = self.randomize_and_time(randobj, self.iterations, tmp_values=tmp_values)
                    self.tmp_check(add_results)

        # Test again with seed 0, ensuring results are the same.
        r0 = random.Random(0)
        randobj0 = self.get_randobj(r0)
        self.randomize_and_check_result(
            randobj0,
            results,
            do_tmp_checks,
            tmp_constraints,
            tmp_values,
            tmp_results,
            post_tmp_results,
            add_results,
            add_tmp_constraints=True,
        )

        # Also test the copy we took earlier.
        self.randomize_and_check_result(
            randobj_copy,
            results,
            do_tmp_checks,
            tmp_constraints,
            tmp_values,
            tmp_results,
            post_tmp_results,
            add_results,
            add_tmp_constraints=True,
        )

        # Test with seed 1, ensuring results are different
        r1 = random.Random(1)
        randobj1 = self.get_randobj(r1)
        if self.EXPECT_FAILURE:
            self.assertRaises(RandomizationError, randobj1.randomize)
        else:
            results1 = self.randomize_and_time(randobj1, self.iterations)
            self.check(results1)
            self.assertNotEqual(results, results1, "Results were the same for two different seeds, check testcase.")
            if do_tmp_checks:
                # Check results are also different when applying temporary constraints
                tmp_results1 = self.randomize_and_time(randobj1, self.iterations, tmp_constraints, tmp_values)
                self.tmp_check(tmp_results1)
                self.assertNotEqual(tmp_results, tmp_results1,
                                    "Results were the same for two different seeds, check testcase.")

        # Test using global seeding, ensuring results are the same
        random.seed(0)
        randobj0_global = self.get_randobj()
        # Take a copy for later
        randobj0_global_copy = deepcopy(randobj0_global)
        self.randomize_and_check_result(
            randobj0_global,
            results,
            do_tmp_checks,
            tmp_constraints,
            tmp_values,
            tmp_results,
            post_tmp_results,
            add_results,
            add_tmp_constraints=False,
        )

        # Re-test the the globally-seeded object
        # Must re-seed the global random package to ensure repeatability
        random.seed(0)
        self.randomize_and_check_result(
            randobj0_global,
            results,
            do_tmp_checks,
            tmp_constraints,
            tmp_values,
            tmp_results,
            post_tmp_results,
            add_results,
            add_tmp_constraints=False,
        )

        # Test the copied globally-seeded object
        # Must re-seed the global random package to ensure repeatability
        random.seed(0)
        self.randomize_and_check_result(
            randobj0_global_copy,
            results,
            do_tmp_checks,
            tmp_constraints,
            tmp_values,
            tmp_results,
            post_tmp_results,
            add_results,
            add_tmp_constraints=False,
        )

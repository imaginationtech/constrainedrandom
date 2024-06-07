# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

''' Reusable definitions for unit testing '''

import random
import unittest
from copy import deepcopy
from time import process_time
from typing import Any, Dict, List, Optional, Tuple

from constrainedrandom import RandObj

from .perf_utils import PERF_DICT, add_perf_result


def assertListOfDictsEqual(instance, list0, list1, msg) -> None:
    '''
    This is missing from unittest. It doesn't like it when two large lists of dictionaries
    are different and compared using `assertListEqual` or `assertEqual`.
    '''
    for idx, (i, j) in enumerate(zip(list0, list1)):
        instance.assertDictEqual(i, j, f"iteration {idx} failed: " + msg)


class TestBase(unittest.TestCase):
    '''
    Provides utilities for testing randomizable objects,
    and storing performance data.
    '''

    # Number of iterations to test.
    ITERATIONS = 1000
    # Global multiplier for test length, set via command line.
    TEST_LENGTH_MULTIPLIER = 1

    def setUp(self) -> None:
        self.iterations = self.ITERATIONS * self.TEST_LENGTH_MULTIPLIER

    def get_full_test_name(self) -> str:
        '''
        Returns the full path to the test being run.
        '''
        return f'{self.__class__.__module__}.{self.__class__.__name__}.{self._testMethodName}'

    def randomize_and_time(
        self,
        randobj: RandObj,
        iterations: int,
        *,
        name: Optional[str]=None,
        tmp_constraints: Optional[List[Any]]=None,
        tmp_values: Optional[Dict[str, Any]]=None
    ) -> Tuple[List[Dict[str, Any]], PERF_DICT]:
        '''
        Call randobj.randomize() iterations times, time it,
        print performance stats, return the results.

        name:       Name of randomizable object.
        randobj:    Randomizable object which must implement `randomize()`.
        iterations: Number of times to run.
        '''
        results = []
        time_taken = 0
        for _ in range(iterations):
            start_time = process_time()
            if tmp_constraints is not None or tmp_values is not None:
                randobj.randomize(with_constraints=tmp_constraints, with_values=tmp_values)
            else:
                randobj.randomize()
            end_time = process_time()
            time_taken += end_time - start_time
            # Extract the results if dealing with RandObj
            # (This code is shared with benchmarking for vsc objects)
            if isinstance(randobj, RandObj):
                results.append(randobj.get_results())
        hz = iterations/time_taken
        name_str = "" if name is None else " " + name
        print(f'{self.get_full_test_name()}:{name_str} took {time_taken:.4g}s for {iterations} iterations ({hz:.1f}Hz)')
        result_name = self.__class__.__name__ if name is None else name
        perf_result = {'time_taken': time_taken, 'iterations': iterations, 'hz': hz}
        add_perf_result(result_name, perf_result)
        return results, perf_result


class RandObjTestBase(TestBase):
    '''
    Provides useful utilities for testing features of constrainedrandom.
    Extend this class to create testcases.
    '''

    # Expected exception when calling `get_randobj`.
    EXPECTED_ERROR_INIT = None
    # Expected exception when calling `randomize_and_check_result`.
    EXPECTED_ERROR_RAND = None

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

    def randomize_and_check_result(
        self,
        randobj: RandObj,
        expected_results: List[Dict[str, Any]],
        do_tmp_checks: bool,
        tmp_constraints: Optional[List[Any]],
        tmp_values: Optional[Dict[str, Any]],
        expected_tmp_results: Optional[List[Dict[str, Any]]],
        expected_post_tmp_results: Optional[List[Dict[str, Any]]],
        expected_add_results: Optional[List[Dict[str, Any]]],
        add_tmp_constraints: bool,
    ) -> None:
        '''
        Code to randomize a randobj and check its results against expected
        results.
        '''
        if self.EXPECTED_ERROR_RAND is not None:
            self.assertRaises(self.EXPECTED_ERROR_RAND, randobj.randomize)
        else:
            results, _perf = self.randomize_and_time(randobj, self.iterations)
            assertListOfDictsEqual(self, expected_results, results, "Non-determinism detected, results were not equal")
            if do_tmp_checks:
                # Check applying temporary constraints is also deterministic
                tmp_results, _perf = self.randomize_and_time(
                    randobj,
                    self.iterations,
                    tmp_constraints=tmp_constraints,
                    tmp_values=tmp_values,
                )
                assertListOfDictsEqual(
                    self,
                    expected_tmp_results,
                    tmp_results,
                    "Non-determinism detected, results were not equal with temp constraints"
                )
                # Check temporary constraints don't break base randomization determinism
                post_tmp_results, _perf = self.randomize_and_time(randobj, self.iterations)
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
                    add_results, _perf = self.randomize_and_time(
                        randobj,
                        self.iterations,
                        tmp_values=tmp_values,
                    )
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
        if self.EXPECTED_ERROR_INIT is not None:
            self.assertRaises(self.EXPECTED_ERROR_INIT, self.get_randobj, r)
        else:
            randobj = self.get_randobj(r)
            # Take a copy of the randobj for use later
            randobj_copy = deepcopy(randobj)
            if self.EXPECTED_ERROR_RAND is not None:
                self.assertRaises(self.EXPECTED_ERROR_RAND, randobj.randomize)
            else:
                results, _perf = self.randomize_and_time(randobj, self.iterations)
                self.check(results)
                if do_tmp_checks:
                    # Check when applying temporary constraints
                    tmp_results, _perf = self.randomize_and_time(
                        randobj,
                        self.iterations,
                        tmp_constraints=tmp_constraints,
                        tmp_values=tmp_values
                    )
                    self.tmp_check(tmp_results)
                    # Check temporary constraints don't break base randomization
                    post_tmp_results, _perf = self.randomize_and_time(randobj, self.iterations)
                    self.check(post_tmp_results)
                    # Add temporary constraints permanently, see what happens
                    if tmp_constraints is not None:
                        for constr, vars in tmp_constraints:
                            randobj.add_constraint(constr, vars)
                        add_results, _perf = self.randomize_and_time(
                            randobj,
                            self.iterations,
                            tmp_values=tmp_values,
                        )
                        self.tmp_check(add_results)

        # Test again with seed 0, ensuring results are the same.
        r0 = random.Random(0)
        if self.EXPECTED_ERROR_INIT is not None:
            self.assertRaises(self.EXPECTED_ERROR_INIT, self.get_randobj, r0)
        else:
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
        if self.EXPECTED_ERROR_INIT is None:
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
        if self.EXPECTED_ERROR_INIT is not None:
            self.assertRaises(self.EXPECTED_ERROR_INIT, self.get_randobj, r1)
        else:
            randobj1 = self.get_randobj(r1)
            if self.EXPECTED_ERROR_RAND is not None:
                self.assertRaises(self.EXPECTED_ERROR_RAND, randobj1.randomize)
            else:
                results1, _perf = self.randomize_and_time(randobj1, self.iterations)
                self.check(results1)
                self.assertNotEqual(results, results1, "Results were the same for two different seeds, check testcase.")
                if do_tmp_checks:
                    # Check results are also different when applying temporary constraints
                    tmp_results1, _perf = self.randomize_and_time(
                        randobj1,
                        self.iterations,
                        tmp_constraints=tmp_constraints,
                        tmp_values=tmp_values
                    )
                    self.tmp_check(tmp_results1)
                    self.assertNotEqual(tmp_results, tmp_results1,
                                        "Results were the same for two different seeds, check testcase.")

        # Test using global seeding, ensuring results are the same
        # Don't add temp constraints this time, so that we can test this object again.
        random.seed(0)
        if self.EXPECTED_ERROR_INIT is not None:
            self.assertRaises(self.EXPECTED_ERROR_INIT, self.get_randobj)
        else:
            randobj0_global = self.get_randobj()
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
            # Must re-seed the global random module to ensure repeatability.
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
                add_tmp_constraints=True,
            )

            # TODO: Fix interaction between global random module and deepcopy.
            # Details:
            # There is an issue around copying an object that relies on the
            # global random object - the state of any copied object is tied to
            # its original.
            # Having spent a lot of time debugging this issue, it is still very
            # difficult to understand.
            # Each individual copied RandObj instance points to a new random.Random
            # instance, which shares state with the global module. It appears then
            # in some instances that the object uses the global value in the random
            # module, and in others it uses the copied one, meaning the state
            # diverges.
            # Right now, all I can conclude is it would take a lot of work to
            # fully debug it, and it can be worked around by passing objects a
            # seeded random.Random if the user desires reproducible objects.

            # TODO: Make testing of copy more thorough when above issue fixed.
            # Take a copy, to show that we can. Its behaviour can't be guaranteed
            # to be deterministic w.r.t. randobj0_global due to issues around
            # deepcopy interacting with the global random module.
            # So, just test it can randomize.
            randobj0_global_copy = deepcopy(randobj0_global)
            if self.EXPECTED_ERROR_RAND is not None:
                self.assertRaises(self.EXPECTED_ERROR_RAND, randobj0_global_copy.randomize)
            else:
                # Don't check results. Checks may fail due to the interaction
                # between deepcopy and global random. E.g. if we check that temp
                # constraints are not followed when not supplied, they may
                # be due to the interaction between random and deepcopy.
                # This just ensures it doesn't crash.
                self.randomize_and_time(randobj0_global_copy, self.iterations)
                self.randomize_and_time(
                    randobj0_global_copy,
                    self.iterations,
                    tmp_constraints=tmp_constraints,
                    tmp_values=tmp_values
                )

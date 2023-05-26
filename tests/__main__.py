# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

''' Basic tests on functionality and performance. '''

import timeit
import unittest
import sys

from argparse import ArgumentParser

from constrainedrandom import Random, RandObj
from examples.ldinstr import ldInstr


TEST_LENGTH_MULTIPLIER = 1


class RandObjTests(unittest.TestCase):
    '''
    Container for unit tests for constrainedrandom.RandObj
    '''

    def randomize_and_time(self, randobj, iterations):
        '''
        Call randobj.randomize() iterations times, time it, print performance stats,
        return the results.
        '''
        results = []
        time_taken = 0
        for _ in range(iterations):
            start_time = timeit.default_timer()
            randobj.randomize()
            end_time = timeit.default_timer()
            time_taken += end_time - start_time
            # Extract the results
            results.append(randobj.get_results())
        hz = iterations/time_taken
        print(f'{self._testMethodName} took {time_taken:.4g}s for {iterations} iterations ({hz:.1f}Hz)')
        return results

    def randobj_test(self, randobj_getter, iterations, check):
        '''
        Reusable test function to randomize a RandObj for a number of iterations and perform checks.

        Tests functionality based on check argument. Reports performance stats. Tests determinism.

        randobj_getter: function that accepts a seed and returns a RandObj to be tested.
        iterations:     number of times to call .randomize()
        check:          function accepting results (a list of dictionaries) to perform required checks.
        '''
        iterations *= TEST_LENGTH_MULTIPLIER
        # Test with seed 0
        randobj = randobj_getter(0)
        results = self.randomize_and_time(randobj, iterations)
        check(results)
        # Test again with seed 0, ensuring results are the same
        randobj0 = randobj_getter(0)
        results0 = self.randomize_and_time(randobj0, iterations)
        self.assertEqual(results, results0, "Non-determinism detected, results were not equal")
        # Test with seed 1, ensuring results are different
        randobj1 = randobj_getter(1)
        results1 = self.randomize_and_time(randobj1, iterations)
        check(results1)
        self.assertNotEqual(results, results1, "Results were the same for two different seeds, check testcase.")

    def test_basic(self):
        '''
        Test all basic single random variable features
        '''
        def get_randobj(seed):
            r = RandObj(Random(seed))
            r.add_rand_var("foo", domain=range(100))
            r.add_rand_var("bar", domain=(1,2,3,))
            r.add_rand_var("baz", bits=4)
            r.add_rand_var("bob", domain={0: 9, 1: 1})
            def not_3(foo):
                return foo != 3
            r.add_rand_var("dan", domain=range(5), constraints=not_3)
            def custom_fn(arg):
                return arg + 1
            r.add_rand_var("joe", fn=custom_fn, args=(1,))
            return r

        def check(results):
            for result in results:
                self.assertLessEqual(0, result['foo'])
                self.assertLess(result['foo'], 100)
                self.assertIn(result['bar'], (1,2,3,))
                self.assertLessEqual(0, result['baz'])
                self.assertLess(result['baz'], (1 << 4))
                self.assertIn(result['bob'], (0,1))
                self.assertIn(result['dan'], (0,1,2,4))
                self.assertEqual(result['joe'], 2)

        self.randobj_test(get_randobj, 10000, check)

    def test_multi_basic(self):
        '''
        Test a basic multi-variable constraint (easy to randomly fulfill the constraint)
        '''
        def get_randobj(seed):
            r = RandObj(Random(seed))
            r.add_rand_var("a", domain=range(10))
            r.add_rand_var("b", domain=range(10))
            r.add_rand_var("c", domain=range(5,10))
            def abc(a, b, c):
                return a < b < c
            r.add_multi_var_constraint(abc, ("a","b","c"))
            return r

        def check(results):
            for result in results:
                self.assertLess(result['a'], result['b'], f'Check failed for {result=}')
                self.assertLess(result['b'], result['c'], f'Check failed for {result=}')

        self.randobj_test(get_randobj, 100, check)

    def test_multi_plusone(self):
        '''
        Test a slightly trickier multi-variable constraint (much less likely to just randomly get it right)
        '''
        def get_randobj(seed):
            r = RandObj(Random(seed))
            # Very unlikely (1/100) to solve the problem naively, just skip to applying constraints.
            r.set_naive_solve(False)
            r.add_rand_var("x", domain=range(100), order=0)
            r.add_rand_var("y", domain=range(100), order=1)
            def plus_one(x, y):
                return y == x + 1
            r.add_multi_var_constraint(plus_one, ("x", "y"))
            return r

        def check(results):
            for result in results:
                self.assertEqual(result['y'], result['x'] + 1, f'Check failed for {result=}')

        self.randobj_test(get_randobj, 100, check)

    def test_multi_sum(self):
        '''
        Test a much trickier multi-variable constraint
        '''
        def get_randobj(seed):
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

        def check(results):
            for result in results:
                self.assertEqual(result['x'] + result['y'] + result['z'], 41, f'Check failed for {result=}')
                self.assertNotEqual(result['x'], 0, f'Check failed for {result=}')

        self.randobj_test(get_randobj, 10, check)

    def test_multi_order(self):
        '''
        Test a problem that benefits greatly from being solved in a certain order.
        '''
        def get_randobj(seed):
            r = RandObj(Random(seed))
            r.add_rand_var("a", domain=range(100), order=0)
            r.add_rand_var("b", domain=range(100), order=1)
            def mul_lt1000(a, b):
                return a * b < 1000
            r.add_multi_var_constraint(mul_lt1000, ('a', 'b'))
            r.add_rand_var("c", domain=range(100), order=2)
            def sum_lt100(a, b, c):
                return a + b + c < 100
            r.add_multi_var_constraint(sum_lt100, ('a', 'b', 'c'))
            return r

        def check(results):
            for result in results:
                self.assertLess(result['a'] * result['b'], 1000, f'Check failed for {result=}')
                self.assertLess(result['a'] + result['b'] + result['c'], 100, f'Check failed for {result=}')

        self.randobj_test(get_randobj, 100, check)

    def test_dist(self):
        '''
        Test a distribution
        '''
        def get_randobj(seed):
            r = RandObj(Random(seed))
            r.add_rand_var("dist", domain={0: 25, 1 : 25, range(2,5): 50})
            return r

        # Work out what the distribution should be
        iterations = 10000
        modified_iterations = iterations * TEST_LENGTH_MULTIPLIER
        quarter = modified_iterations // 4
        half = modified_iterations // 2
        # Allow 10% leeway
        q_delta = quarter // 10
        h_delta = half // 10
        quarter_range = range(quarter - q_delta, quarter + q_delta + 1)
        half_range = range(half - h_delta, half + h_delta + 1)

        def check(results):
            count_zeroes = 0
            count_ones = 0
            count_two_plus = 0
            for result in results:
                val = result['dist']
                if val == 0:
                    count_zeroes += 1
                elif val == 1:
                    count_ones += 1
                elif 2 <= val < 5:
                    count_two_plus += 1
                else:
                    self.fail("too high!")
            # Check it's roughly the right distribution
            self.assertIn(count_zeroes, quarter_range)
            self.assertIn(count_ones, quarter_range)
            self.assertIn(count_two_plus, half_range)

        self.randobj_test(get_randobj, iterations, check)

    def test_instr(self):
        '''
        Test something that looks like an instruction opcode, one of the desired
        use cases for this library.
        '''
        def get_randobj(seed):
            ld_instr = ldInstr(Random(seed))
            return ld_instr

        def check(results):
            for result in results:
                if result['wb']:
                    self.assertNotEqual(result['src0'], result['dst0'])
                address = result['src0_value'] + result['imm0']
                self.assertLess(address, 0xffffffff)
                self.assertEqual(address & 3, 0)

        self.randobj_test(get_randobj, 100, check)


def parse_args():
    parser = ArgumentParser(description='Run unit tests for constrainedrandom library')
    parser.add_argument('--length-mul', type=int, default=1, help='Multiplier for test length, when desiring greater certainty on performance.')
    args, extra = parser.parse_known_args()
    return args, extra


if __name__ == "__main__":
    args, extra = parse_args()
    TEST_LENGTH_MULTIPLIER = args.length_mul
    # Reconstruct argv
    argv = [sys.argv[0]] + extra
    unittest.main(argv=argv)

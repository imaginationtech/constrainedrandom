# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

''' Basic tests on functionality and performance. '''

import unittest
import sys

from argparse import ArgumentParser
from functools import partial
from enum import Enum, IntEnum
from random import Random

from constrainedrandom.utils import unique
from constrainedrandom import RandObj
from examples.ldinstr import ldInstr
from . import utils


class RandObjTests(utils.RandObjTestsBase):
    '''
    Container for unit tests for constrainedrandom.RandObj
    '''

    def test_basic(self):
        '''
        Test all basic single random variable features
        '''

        class MyEnum(Enum):
            A = 'a'
            B = 'b'

        class MyIntEnum(IntEnum):
            ONE = 1
            TWO = 2

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
            r.add_rand_var("enum", domain=MyEnum)
            r.add_rand_var("int_enum", domain=MyIntEnum)
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
                self.assertIn(result['enum'], (MyEnum.A, MyEnum.B))
                self.assertIn(result['int_enum'], (1, 2))

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
        self.randobj_test(utils.get_randobj_sum, 10, partial(utils.randobj_sum_check,self))

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
        modified_iterations = iterations * self.TEST_LENGTH_MULTIPLIER
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

    def test_temp_constraint(self):
        '''
        Test using a simple temporary constraint.
        '''
        def get_randobj(seed):
            r = RandObj(Random(seed))
            r.add_rand_var('a', domain=range(10))
            return r

        def tmp_constraint(a):
            return a < 5

        def check(results):
            seen_gt_4 = False
            for result in results:
                self.assertIn(result['a'], range(10))
                if result['a'] >= 5:
                    seen_gt_4 = True
            self.assertTrue(seen_gt_4, "Temporary constraint followed when not given")

        def tmp_check(results):
            for result in results:
                self.assertIn(result['a'], range(5))

        self.randobj_test(get_randobj, 1000, check, [(tmp_constraint, ('a',))], tmp_check)

    def test_temp_multi_constraint(self):
        '''
        Test using a temporary multi-variable constraint.
        '''
        def get_randobj(seed):
            r = RandObj(Random(seed))
            r.add_rand_var('a', domain=range(10))
            r.add_rand_var('b', domain=range(100))
            return r

        def check(results):
            seen_tmp_constraint_false = False
            for result in results:
                self.assertIn(result['a'], range(10))
                self.assertIn(result['b'], range(100))
                if result['a'] * result['b'] >= 200 and result['a'] >= 5:
                    seen_tmp_constraint_false = True
            self.assertTrue(seen_tmp_constraint_false, "Temporary constraint followed when not given")

        def tmp_check(results):
            for result in results:
                # Do normal checks
                self.assertIn(result['a'], range(10))
                self.assertIn(result['b'], range(100))
                # Also check the temp constraint is followed
                self.assertLess(result['a'] * result['b'], 200)

        def a_mul_b_lt_200(a, b):
            return a * b < 200

        self.randobj_test(
            get_randobj,
            1000,
            check,
            [(a_mul_b_lt_200, ('a', 'b'))],
            tmp_check
        )

    def test_mixed_temp_constraints(self):
        '''
        Test using a temporary multi-variable constraint, with a single-variable constraint.
        '''
        def get_randobj(seed):
            r = RandObj(Random(seed))
            r.add_rand_var('a', domain=range(10))
            r.add_rand_var('b', domain=range(100))
            return r

        def check(results):
            seen_tmp_constraint_false = False
            for result in results:
                self.assertIn(result['a'], range(10))
                self.assertIn(result['b'], range(100))
                if result['a'] * result['b'] >= 200 and result['a'] >= 5:
                    seen_tmp_constraint_false = True
            self.assertTrue(seen_tmp_constraint_false, "Temporary constraint followed when not given")

        def tmp_check(results):
            for result in results:
                # Do normal checks
                self.assertIn(result['a'], range(5))
                self.assertIn(result['b'], range(100))
                # Also check the temp constraint is followed
                self.assertLess(result['a'] * result['b'], 200)

        def a_lt_5(a):
            return a < 5

        def a_mul_b_lt_200(a, b):
            return a * b < 200

        self.randobj_test(
            get_randobj,
            1000,
            check,
            [(a_lt_5, ('a',)), (a_mul_b_lt_200, ('a', 'b'))],
            tmp_check
        )

    def test_tricky_temp_constraints(self):
        '''
        Force use of MultiVarProblem with a difficult problem, and
        also use temporary constraints.
        '''
        # Use a few extra temporary constraints to make the problem even harder
        def tmp_abs_sum_xy_lt50(x, y):
            return abs(x) + abs(y) < 50

        def tmp_x_mod2(x):
            return x % 2 == 0

        def tmp_yz_mod3(y, z):
            return (y + z) % 3 == 0

        # Check that we see x and y sum to greater than 50 when
        # the temporary constraint isn't in place
        def check(results):
            # Normal checks
            utils.randobj_sum_check(self, results)
            # Temp constraint not respected - check for at least one instance
            # where all conditions are not respected
            temp_constraint_respected = True
            for result in results:
                if result['x'] + result['y'] >= 50 and \
                    result['x'] % 2 != 0 and \
                    (result['y'] + result['z']) % 3 != 0:
                    temp_constraint_respected = False
            self.assertFalse(
                temp_constraint_respected,
                "Temp constraint should not be followed when not applied"
            )

        # Check that the temp constraint is respected
        def tmp_check(results):
            # Normal checks
            utils.randobj_sum_check(self, results)
            # Temp constraint respected
            for result in results:
                self.assertLess(result['x'] + result['y'], 50, "Temp constraint not respected")
                self.assertTrue(result['x'] % 2 == 0, "Temp constraint not respected")
                self.assertTrue((result['y'] + result['z']) % 3 == 0, "Temp constraint not respected")

        self.randobj_test(
            utils.get_randobj_sum,
            30,
            check,
            [(tmp_abs_sum_xy_lt50, ('x', 'y')),
             (tmp_x_mod2, ('x',)),
             (tmp_yz_mod3, ('y', 'z'))],
            tmp_check
        )

    def test_with_values(self):
        '''
        Basic test for with_values.
        '''
        def get_randobj(seed):
            r = RandObj(Random(seed))
            r.add_rand_var('a', domain=range(10))
            r.add_rand_var('b', domain=range(100))
            return r

        with_values = {'b': 52}

        def check(results):
            # Ensure we see the temporary value violated at least once
            non_52_seen = False
            for result in results:
                self.assertIn(result['a'], range(10))
                self.assertIn(result['b'], range(100))
                if result['b'] != 52:
                    non_52_seen = True
            self.assertTrue(non_52_seen, "Temporary value used when it shouldn't be")

        def tmp_check(results):
            for result in results:
                self.assertIn(result['a'], range(10))
                self.assertEqual(result['b'], 52)

        self.randobj_test(get_randobj, 1000, check, None, tmp_check, with_values)

    def test_with_values_with_constraints(self):
        '''
        Test how with_values and with_constraints interact.
        '''
        def get_randobj(seed):
            r = RandObj(Random(seed))
            r.add_rand_var('a', domain=range(10))
            r.add_rand_var('b', domain=range(100))
            return r

        def check(results):
            seen_tmp_constraint_false = False
            seen_tmp_value_false = False
            for result in results:
                self.assertIn(result['a'], range(10))
                self.assertIn(result['b'], range(100))
                if result['a'] * result['b'] >= 200 and result['a'] >= 5:
                    seen_tmp_constraint_false = True
                if result['a'] != 3:
                    seen_tmp_value_false = True
            self.assertTrue(seen_tmp_constraint_false, "Temporary constraint followed when not given")
            self.assertTrue(seen_tmp_value_false, "Temporary value followed when not given")

        def tmp_check(results):
            for result in results:
                # Do normal checks
                self.assertIn(result['a'], range(5))
                self.assertIn(result['b'], range(100))
                # Also check the temp constraint is followed
                self.assertLess(result['a'] * result['b'], 200)
                # Check the temp value has been followed
                self.assertEqual(result['a'], 3)

        def a_lt_5(a):
            return a < 5

        def a_mul_b_lt_200(a, b):
            return a * b < 200

        tmp_values = {'a': 3}

        self.randobj_test(
            get_randobj,
            1000,
            check,
            [(a_lt_5, ('a',)), (a_mul_b_lt_200, ('a', 'b'))],
            tmp_check,
            tmp_values
        )

    def test_tricky_temp_values(self):
        '''
        Force use of MultiVarProblem with a difficult problem, and
        also use temporary constraints and temporary values.
        '''
        # Use a few extra temporary constraints to make the problem even harder
        def tmp_abs_sum_xy_lt50(x, y):
            return abs(x) + abs(y) < 50

        def tmp_x_mod2(x):
            return x % 2 == 0

        def tmp_yz_mod3(y, z):
            return (y + z) % 2 == 1

        tmp_values = {'x': 6}

        # Check that we see x and y sum to greater than 50 when
        # the temporary constraint isn't in place
        def check(results):
            # Normal checks
            utils.randobj_sum_check(self, results)
            # Temp constraint not respected - check for at least one instance
            # where all conditions are not respected
            temp_constraint_respected = True
            temp_value_respected = True
            for result in results:
                if result['x'] + result['y'] >= 50 and \
                    (result['x'] % 2 == 1 or \
                     (result['y'] + result['z']) % 2 == 0):
                    temp_constraint_respected = False
                if result['x'] != 6:
                    temp_value_respected = False
            self.assertFalse(
                temp_constraint_respected,
                "Temp constraint should not be followed when not applied"
            )
            self.assertFalse(
                temp_value_respected,
                "Temp value should not be followed when not applied"
            )

        # Check that the temp constraint is respected
        def tmp_check(results):
            # Normal checks
            utils.randobj_sum_check(self, results)
            # Temp constraint respected
            for result in results:
                self.assertLess(result['x'] + result['y'], 50, "Temp constraint not respected")
                self.assertTrue(result['x'] % 2 == 0, "Temp constraint not respected")
                self.assertTrue((result['y'] + result['z']) % 2 == 1, "Temp constraint not respected")
                self.assertEqual(result['x'], 6, "Temp value not respected")

        self.randobj_test(
            utils.get_randobj_sum,
            50,
            check,
            [(tmp_abs_sum_xy_lt50, ('x', 'y')),
             (tmp_x_mod2, ('x',)),
             (tmp_yz_mod3, ('y', 'z'))],
            tmp_check,
            tmp_values
        )

    def test_list(self):
        '''
        Test a randomized list.
        '''
        def get_randobj(seed):
            r = RandObj(Random(seed))
            r.add_rand_var('listvar', domain=range(10), length=10)
            return r

        def check(results):
            for result in results:
                self.assertIsInstance(result['listvar'], list, "Var with length > 0 wasn't a list")
                for x in result['listvar']:
                    self.assertIn(x, range(10), "Value was wrongly randomized")

        self.randobj_test(get_randobj, 1000, check)

    def test_list_constrained(self):
        '''
        Test a randomized list with constraints on the values in the list.
        '''
        def get_randobj(seed):
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

        def check(results):
            for result in results:
                self.assertIsInstance(result['listvar'], list, "Var with length > 0 wasn't a list")
                prev = None
                for x in result['listvar']:
                    self.assertIn(x, range(10), "Value was wrongly randomized")
                    if prev is not None:
                        self.assertTrue(x == prev + 1 or x == prev - 1, "list constraint not followed")
                    prev = x

        self.randobj_test(get_randobj, 100, check)

    def test_list_multivar(self):
        '''
        Test a randomized list with constraints on the values in the list,
        also with constraints over multiple variables.
        '''
        def get_randobj(seed):
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
            r.add_multi_var_constraint(in_list, ('x', 'listvar'))
            return r

        def check(results):
            for result in results:
                self.assertIsInstance(result['listvar'], list, "Var with length > 0 wasn't a list")
                prev = None
                for l in result['listvar']:
                    self.assertIn(l, range(10), "Value was wrongly randomized")
                    if prev is not None:
                        self.assertTrue(l == prev + 1 or l == prev - 1, "list constraint not followed")
                    prev = l
                self.assertIn(result['x'], result['listvar'])

        self.randobj_test(get_randobj, 30, check)


    def test_list_unique(self):
        '''
        Test that the unique constraint works on a random list.
        '''
        def get_randobj(seed):
            r = RandObj(Random(seed))
            r.add_rand_var('listvar', domain=range(10), length=10, list_constraints=(unique,))
            return r

        def check(results):
            for result in results:
                self.assertIsInstance(result['listvar'], list, "Var with length > 0 wasn't a list")
                for x_idx, x in enumerate(result['listvar']):
                    self.assertIn(x, range(10), "Value was wrongly randomized")
                    for y_idx, y in enumerate(result['listvar']):
                        if x_idx != y_idx:
                            self.assertNotEqual(x, y, "List elements were not unique")

        self.randobj_test(get_randobj, 1000, check)


def parse_args():
    parser = ArgumentParser(description='Run unit tests for constrainedrandom library')
    parser.add_argument(
        '--length-mul',
        type=int,
        default=1,
        help='Multiplier for test length, when desiring greater certainty on performance.')
    args, extra = parser.parse_known_args()
    return args, extra


if __name__ == "__main__":
    args, extra = parse_args()
    RandObjTests.TEST_LENGTH_MULTIPLIER = args.length_mul
    # Reconstruct argv
    argv = [sys.argv[0]] + extra
    unittest.main(argv=argv)

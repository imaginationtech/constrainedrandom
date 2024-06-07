# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

'''
Test is_pure function from utils.
'''

import unittest

from constrainedrandom.utils import is_pure


global_immutable_var = 2
global_mutable_var = []


# Class-based methods
class Dummy:

    def __init__(self, _min, _max):
        self._max = _max
        self._min = _min

    def check_value(self, value):
        return self._min <= value <= self._max

    def check_value_bad_name(myself, value):
        return myself._min <= value <= myself._max

    def return_mutable(self, x=global_mutable_var):
        return x

    def return_immutable(self, x=global_immutable_var):
        return x

    def impure(self):
        return global_immutable_var

dummy_instance = Dummy(0, 10)


# Global functions
def pure_global_fn(value):
    return value % 1 != 0

def impure_global_fn(value):
    global global_immutable_var
    return value + global_immutable_var

def pure_global_fn_args(x=global_immutable_var):
    # pure because the default is an immutable type
    return x

def impure_global_fn_args(x=global_mutable_var):
    # impure because the default is a mutable type
    return x

# Local functions
def make_impure_local_fns():
    local_variable = 4
    def get_local_variable():
        return local_variable
    def get_global_immutable_variable():
        return global_immutable_var
    def impure_global_default(x=global_mutable_var):
        # impure because the default is a mutable type
        return x
    return (get_local_variable, get_global_immutable_variable, impure_global_default)

def make_pure_local_fns():
    def pure_local_fn(x):
        return x + 1
    def pure_local_fn_args(x=2):
        return x * 4
    def pure_global_default(x=global_immutable_var):
        # pure because the default is an immutable type
        return x + 1
    return (pure_local_fn, pure_local_fn_args, pure_global_default)

impure_local_functions = make_impure_local_fns()
pure_local_functions = make_pure_local_fns()


# Global lambdas
impure_global_lambda = lambda : global_immutable_var
pure_global_lambda = lambda : 2
# impure because the default is a mutable type
impure_global_lambda_args = lambda x=global_mutable_var : x
# pure because the default is an immutable type
pure_global_lambda_args = lambda x=global_immutable_var : x


# Local lambdas
def make_impure_local_lambdas():
    local_immutable_var = 42
    local_mutable_var = [24]
    impure_local_lambda = lambda : global_immutable_var
    impure_local_lambda_args = lambda x=global_mutable_var : x
    impure_local_lambda_local_immutable_var = lambda : local_immutable_var
    impure_local_lambda_local_mutable_var = lambda : local_mutable_var
    impure_local_lambda_local_mutable_var_args = lambda x=local_mutable_var : x
    return (
        impure_local_lambda,
        impure_local_lambda_args,
        impure_local_lambda_local_immutable_var,
        impure_local_lambda_local_mutable_var,
        impure_local_lambda_local_mutable_var_args,
        )

def make_pure_local_lambdas():
    local_immutable_var = 20
    pure_local_lambda = lambda : 2
    pure_local_lambda_args = lambda x=global_immutable_var : x
    # This gets optimized so the variable isn't bound
    pure_local_lambda_local_immutable_var_args = lambda x=local_immutable_var : x
    return (pure_local_lambda, pure_local_lambda_args, pure_local_lambda_local_immutable_var_args)

impure_local_lambdas = make_impure_local_lambdas()
pure_local_lambdas = make_pure_local_lambdas()


class IsPureTests(unittest.TestCase):
    '''
    Test the ``is_pure`` function from ``utils``.
    '''

    def test_class_methods(self):
        '''
        Test whether methods defined in a class are correctly
        identified as pure or impure.
        '''
        # Class methods when not used with an instance are pure,
        # except if they reference a global variable.
        self.assertEqual(is_pure(Dummy.check_value), True)
        self.assertEqual(is_pure(Dummy.check_value_bad_name), True)
        self.assertEqual(is_pure(Dummy.return_mutable), False)
        self.assertEqual(is_pure(Dummy.return_immutable), True)
        self.assertEqual(is_pure(Dummy.impure), False)
        # "Bound" class methods are impure.
        self.assertEqual(is_pure(dummy_instance.check_value), False)
        self.assertEqual(is_pure(dummy_instance.check_value_bad_name), False)
        self.assertEqual(is_pure(dummy_instance.return_mutable), False)
        self.assertEqual(is_pure(dummy_instance.return_immutable), False)
        self.assertEqual(is_pure(dummy_instance.impure), False)

    def test_global_functions(self):
        '''
        Test whether globally-scoped functions are correctly
        identified as pure or impure.
        '''
        self.assertEqual(is_pure(pure_global_fn), True)
        self.assertEqual(is_pure(impure_global_fn), False)
        self.assertEqual(is_pure(pure_global_fn_args), True)
        self.assertEqual(is_pure(impure_global_fn_args), False)

    def test_impure_local_functions(self):
        '''
        Test whether locally-scoped functions are correctly
        identified as pure or impure.
        '''
        for fn in impure_local_functions:
            self.assertEqual(is_pure(fn), False, str(fn))

    def test_pure_local_functions(self):
        '''
        Test whether locally-scoped functions are correctly
        identified as pure or impure.
        '''
        for fn in pure_local_functions:
            self.assertEqual(is_pure(fn), True, str(fn))

    def test_global_lambdas(self):
        '''
        Test whether globally-scoped lambdas are correctly
        identified as pure or impure.
        '''
        self.assertEqual(is_pure(impure_global_lambda), False)
        self.assertEqual(is_pure(pure_global_lambda), True)
        self.assertEqual(is_pure(impure_global_lambda_args), False)
        self.assertEqual(is_pure(pure_global_lambda_args), True)

    def test_impure_local_lambdas(self):
        '''
        Test whether locally-scoped lambdas are correctly
        identified as impure.
        '''
        for fn in impure_local_lambdas:
            self.assertEqual(is_pure(fn), False, str(fn))

    def test_pure_local_lambdas(self):
        '''
        Test whether locally-scoped lambdas are correctly
        identified as pure.
        '''
        for fn in pure_local_lambdas:
            self.assertEqual(is_pure(fn), True, str(fn))

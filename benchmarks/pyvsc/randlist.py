# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

'''
Random list examples where constrainedrandom has previously struggled.
'''

from constrainedrandom import RandObj
from constrainedrandom.utils import unique
import vsc

from ..benchmark_utils import BenchmarkTestCase


@vsc.randobj
class vscRandListSumZero(object):

    def __init__(self):
        self.listvar = vsc.rand_list_t(vsc.int8_t(), 10)

    @vsc.constraint
    def listvar_c(self):
        with vsc.foreach(self.listvar) as l:
            l >= -10
            l < 11

    @vsc.constraint
    def listvar_sum_c(self):
        sum(self.listvar) == 0


class crRandListSumZero(RandObj):

    def __init__(self, *args):
        super().__init__(*args)
        self.add_rand_var('listvar', domain=range(-10, 11), length=10)
        self.add_constraint(self.sum_0, ('listvar',))

    def sum_0(self, listvar):
        return sum(listvar) == 0


class crRandListSumZeroFaster(RandObj):

    def __init__(self, *args):
        super().__init__(*args)
        self.add_rand_var('listvar', domain=range(-10, 11), length=10, disable_naive_list_solver=True)
        self.add_constraint(self.sum_0, ('listvar',))

    def sum_0(self, listvar):
        return sum(listvar) == 0


class VSCRandListSumZero(BenchmarkTestCase):
    '''
    Test random list example where the list must sum to zero.
    '''

    def get_randobjs(self):
        return {
            'vsc': vscRandListSumZero(),
            'cr': crRandListSumZero(),
            'cr_faster': crRandListSumZeroFaster(),
        }

    def check_perf(self, results):
        self.assertGreater(results['cr']['hz'], results['vsc']['hz'])
        self.assertGreater(results['cr_faster']['hz'], results['vsc']['hz'])
        # This testcase is typically 20x faster, which may vary depending
        # on machine. Ensure it doesn't fall below 15x.
        speedup = results['cr']['hz'] / results['vsc']['hz']
        self.assertGreater(speedup, 15, "Performance has degraded!")
        speedup = results['cr_faster']['hz'] / results['vsc']['hz']
        self.assertGreater(speedup, 15, "Performance has degraded!")


@vsc.randobj
class vscRandListUnique(object):

    def __init__(self):
        self.listvar = vsc.rand_list_t(vsc.uint8_t(), 10)

    @vsc.constraint
    def listvar_c(self):
        with vsc.foreach(self.listvar) as l:
            l >= 0
            l < 10

    @vsc.constraint
    def listvar_unique_c(self):
        vsc.unique(self.listvar)


class crRandListUnique(RandObj):

    def __init__(self, *args):
        super().__init__(*args)
        self.add_rand_var('listvar', domain=range(10), length=10, list_constraints=[unique])


class crRandListUniqueFaster(RandObj):

    def __init__(self, *args):
        super().__init__(*args)
        self.add_rand_var('listvar',
            domain=range(10),
            length=10,
            list_constraints=[unique],
            disable_naive_list_solver=True,
        )


class VSCRandListUnique(BenchmarkTestCase):
    '''
    Test random list example where the list must be unique.
    '''

    def get_randobjs(self):
        return {
            'vsc': vscRandListUnique(),
            'cr': crRandListUnique(),
            'cr_faster': crRandListUniqueFaster(),
        }

    def check_perf(self, results):
        self.assertGreater(results['cr_faster']['hz'], results['vsc']['hz'])
        self.assertGreater(results['cr']['hz'], results['vsc']['hz'])
        # With the naive solver, this testcase is typically 3-4x faster,
        # which may vary depending on machine. Ensure it doesn't fall
        # below 2x.
        speedup = results['cr']['hz'] / results['vsc']['hz']
        self.assertGreater(speedup, 2, "Performance has degraded!")
        # This testcase is typically 10-13x faster, which may vary depending
        # on machine. Ensure it doesn't fall below 10x.
        speedup = results['cr_faster']['hz'] / results['vsc']['hz']
        self.assertGreater(speedup, 10, "Performance has degraded!")

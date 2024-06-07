# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

from constrainedrandom import RandObj
import vsc

from ..benchmark_utils import BenchmarkTestCase


@vsc.randobj
class vsc_in(object):

    def __init__(self):
        self.a = vsc.rand_bit_t(8)
        self.b = vsc.rand_bit_t(8)
        self.c = vsc.rand_bit_t(8)
        self.d = vsc.rand_bit_t(8)

    @vsc.constraint
    def ab_c(self):

       self.a in vsc.rangelist(1, 2, vsc.rng(4,8))
       self.c != 0
       self.d != 0

       self.c < self.d
       self.b in vsc.rangelist(vsc.rng(self.c,self.d))


class cr_in(RandObj):
    '''
    Basic implementation, does thes same thing as vsc_in. No ordering hints.
    '''

    def __init__(self):
        super().__init__()

        self.add_rand_var('a', domain=[1,2] + list(range(4,8)))
        self.add_rand_var('b', bits=8, constraints=(lambda b : b != 0,))
        self.add_rand_var('c', bits=8)
        self.add_rand_var('d', bits=8, constraints=(lambda d : d != 0,))

        def c_lt_d(c, d):
            return c < d
        self.add_constraint(c_lt_d, ('c', 'd'))

        def b_in_range(b, c, d):
            return b in range(c, d)
        self.add_constraint(b_in_range, ('b', 'c', 'd'))


class cr_in_order(RandObj):
    '''
    cr_in, but with ordering hints.
    '''

    def __init__(self):
        super().__init__()

        self.add_rand_var('a', domain=[1,2] + list(range(4,8)), order=0)
        self.add_rand_var('b', bits=8, constraints=(lambda b : b != 0,), order=2)
        self.add_rand_var('c', bits=8, order=0)
        self.add_rand_var('d', bits=8, constraints=(lambda d : d != 0,), order=1)

        def c_lt_d(c, d):
            return c < d
        self.add_constraint(c_lt_d, ('c', 'd'))

        def b_in_range(b, c, d):
            return b in range(c, d)
        self.add_constraint(b_in_range, ('b', 'c', 'd'))


class VSCIn(BenchmarkTestCase):
    '''
    Random object using 'in' keyword from pyvsc documentation.
    '''

    def get_randobjs(self):
        return {
            'vsc': vsc_in(),
            'cr': cr_in(),
            'cr_order': cr_in_order(),
        }

    def check_perf(self, results):
        self.assertGreater(results['cr']['hz'], results['vsc']['hz'])
        self.assertGreater(results['cr_order']['hz'], results['vsc']['hz'])
        # This testcase is typically 13-15x faster, which may vary depending
        # on machine. Ensure it doesn't fall below 10x.
        speedup = results['cr']['hz'] / results['vsc']['hz']
        self.assertGreater(speedup, 10, "Performance has degraded!")
        speedup = results['cr_order']['hz'] / results['vsc']['hz']
        self.assertGreater(speedup, 10, "Performance has degraded!")

# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

'''
Random list examples where constrainedrandom has previously struggled.
'''

from constrainedrandom import RandObj
from constrainedrandom.utils import unique
import vsc


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
        def sum_0(listvar):
            return sum(listvar) == 0
        self.add_constraint(sum_0, ('listvar',))


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

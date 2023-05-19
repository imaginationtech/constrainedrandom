# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

'''
Implement realistic load instruction case from constrainedrandom examples.ldinstr
'''

import vsc

@vsc.randobj
class vsc_ldinstr(object):

    def __init__(self):
        self.imm0 = vsc.rand_bit_t(11)
        self.src0 = vsc.rand_bit_t(5)
        self.dst0 = vsc.rand_bit_t(5)
        self.wb = vsc.rand_bit_t(1)
        self.enc = 0xfa800000
        # Make this the same as in examples.ldinstr
        self.src0_value_getter = lambda : 0xfffffbcd

    @vsc.constraint
    def wb_src0_dst0(self):
        with vsc.if_then(self.wb == 1):
            self.src0 != self.dst0

    @vsc.constraint
    def sum_src0_imm0(self):
        self.imm0 + self.src0_value_getter() <= 0xffffffff
        (self.imm0 + self.src0_value_getter()) & 3 == 0

# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

'''
Reusable utility functions to perform commonly required bitwise operations.
'''

def get_bitslice(val: int, hi: int, lo: int):
    '''
    Function to get a bit slice from a value.
    Equivalent behaviour to SystemVerilog, i.e.
    ``get_bitslice(val, hi, lo)`` in Python
    is the same as:
    ``val[hi:lo]`` in SV.

    :param val: The value to slice.
    :param hi: The highest bit index of the desired slice.
    :param hi: The lowest bit index of the desired slice.
    :return: The requested bit slice.
    :raises AssertionError: If lo > hi.
    '''
    assert lo <= hi, "low index must be less than or equal to high index"
    size = hi - lo + 1
    mask = (1 << size) - 1
    return (val >> lo) & mask


def set_bitslice(val: int, hi: int, lo: int, new_val: int):
    '''
    Function to take a value and set a slice of bits to
    a particular value. The function returns that new
    value. The input value is unaffected.
    Equivalent behaviour to SystemVerilog, i.e.
    ``val = set_bitslice(val, hi, lo, new_val)`` in Python
    is the same as:
    ``val[hi:lo] = new_val`` in SV.

    :param val: The value to modify.
    :param hi: The highest bit index of the desired slice.
    :param hi: The lowest bit index of the desired slice.
    :param new_val: The new value to be assigned to the slice.
    :return: The modified value.
    :raises AssertionError: If lo > hi.
    '''
    assert lo <= hi, "low index must be less than or equal to high index"
    size = hi - lo + 1
    mask = (1 << size) - 1
    new_val = new_val & mask
    not_mask = ((1 << val.bit_length()) - 1) & ~(mask << lo)
    return (val & not_mask) | (new_val << lo)

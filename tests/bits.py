# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

'''
Test bitwise operations.
'''

import unittest

from constrainedrandom.bits import get_bitslice, set_bitslice


class BitsliceTests(unittest.TestCase):

    def test_get_bitslice(self):
        print("Testing get_bitslice...")
        self.assertEqual(get_bitslice(0xdeadbeef, 11, 8), 0xe)
        self.assertEqual(get_bitslice(0xdeadbeef, 3, 0), 0xf)
        self.assertEqual(get_bitslice(0xdeadbeef, 4, 0), 0xf)
        self.assertEqual(get_bitslice(0xdeadbeef, 6, 1), 0x37)
        self.assertEqual(get_bitslice(0xdeadbeef, 19, 12), 0xdb)
        self.assertEqual(get_bitslice(0xdeadbeef, 31, 0), 0xdeadbeef)
        self.assertEqual(get_bitslice(0xdeadbeef, 32, 0), 0xdeadbeef)
        self.assertEqual(get_bitslice(0xdeadbeef, 0, 0), 0x1)
        self.assertEqual(get_bitslice(0xdeadbeef, 4, 4), 0x0)
        self.assertEqual(get_bitslice(0xdeadbeef, 34, 32), 0x0)
        print("... done testing get_bitslice.")

    def test_set_bitslice(self):
        print("Testing set_bitslice...")
        self.assertEqual(set_bitslice(0xf00, 1, 0, 2), 0xf02)
        self.assertEqual(set_bitslice(0xf00, 3, 2, 2), 0xf08)
        self.assertEqual(set_bitslice(0xf00, 2, 1, 2), 0xf04)
        self.assertEqual(set_bitslice(0xf00, 11, 8, 0), 0x0)
        self.assertEqual(set_bitslice(0xf00, 11, 8, 3), 0x300)
        self.assertEqual(set_bitslice(0xf00, 12, 11, 3), 0x1f00)
        self.assertEqual(set_bitslice(0, 12, 11, 3), 0x1800)
        self.assertEqual(set_bitslice(0, 15, 0, 0xdeadbeef), 0xbeef)
        self.assertEqual(set_bitslice(0, 31, 16, 0xdeadbeef), 0xbeef0000)
        self.assertEqual(set_bitslice(0xcafef00d, 15, 0, 0xdeadbeef), 0xcafebeef)
        self.assertEqual(set_bitslice(0xcafef00d, 31, 16, 0xdeadbeef), 0xbeeff00d)
        print("... done testing set_bitslice.")

    def test_errors(self):
        print("Testing bitslice errors...")
        # lo > hi
        self.assertRaises(AssertionError, get_bitslice, 0xdeadbeef, 3, 5)
        self.assertRaises(AssertionError, set_bitslice, 0xdeadbeef, 3, 5, 3)
        print("... done testing bitslice errors.")

# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

'''
Test all supported features.

Test for determinism within one thread, record performance.
'''

import unittest
import sys

from argparse import ArgumentParser

from . import testutils
# Import all tests for unittest to run
from .bits import *
from .determinism import *
from .features.basic import *
from .features.errors import *
from .features.rand_list import *
from .features.temp import *


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
    testutils.RandObjTestBase.TEST_LENGTH_MULTIPLIER = args.length_mul
    # Reconstruct argv
    argv = [sys.argv[0]] + extra
    unittest.main(argv=argv)

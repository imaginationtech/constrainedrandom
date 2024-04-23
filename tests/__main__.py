# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

'''
Test all supported features.

Test for determinism within one thread, record performance.
'''

import json
import unittest
import sys

from argparse import ArgumentParser
from collections import defaultdict
from datetime import datetime
from time import time
from typing import Optional

from . import testutils
# Import all tests for unittest to run
from .bits import *
from .determinism import *
from .is_pure import *
from .features.basic import *
from .features.classes import *
from .features.errors import *
from .features.rand_list import *
from .features.temp import *
from .features.user import *


def parse_args():
    parser = ArgumentParser(description='Run unit tests for constrainedrandom library')
    parser.add_argument(
        '--length-mul',
        type=int,
        default=1,
        help='Multiplier for test length, when desiring greater certainty on performance.')
    parser.add_argument(
        '--perf',
        action="store_true",
        help="Enable performance result dump.",
    )
    parser.add_argument(
        '--perf-results-file',
        type=str,
        default=None,
        help='File location to write performance results.'
    )
    parser.add_argument(
        '--perf-results-tag',
        type=str,
        default=None,
        help="Custom name to tag this performance run."
    )
    args, extra = parser.parse_known_args()
    return args, extra


def dump_perf_data(perf_results_file: Optional[str], perf_results_tag: Optional[str]):
    # Tag results
    timestamp = datetime.fromtimestamp(time()).strftime('%Y-%m-%d-%H%M%S')
    if perf_results_file is None:
        if perf_results_tag is not None:
            perf_results_file = f"perf-results-{perf_results_tag}.json"
        else:
            perf_results_file = f"perf-results-{timestamp}.json"
    if perf_results_tag is None:
        perf_results_tag = timestamp
    perf_results = testutils.RandObjTestBase.PERF_RESULTS
    perf_results_final = {}
    for test_name, result_list in perf_results.items():
        perf_results_final[test_name] = defaultdict(list)
        perf_results_final[test_name][perf_results_tag] += result_list
    print(f"Writing performance results to '{perf_results_file}' with tag '{perf_results_tag}'")
    with open(perf_results_file, "wt") as json_file:
        json_file.write(json.dumps(perf_results_final))


if __name__ == "__main__":
    args, extra = parse_args()
    testutils.RandObjTestBase.TEST_LENGTH_MULTIPLIER = args.length_mul
    # Reconstruct argv
    argv = [sys.argv[0]] + extra
    result = unittest.main(argv=argv, exit=False).result
    if args.perf:
        dump_perf_data(args.perf_results_file, args.perf_results_tag)
    if result.wasSuccessful():
        retcode = 0
    else:
        retcode = 1
    sys.exit(retcode)

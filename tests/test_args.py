# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

''' Reusable argument parser for testing and benchmarks. '''


from argparse import ArgumentParser

def get_argparser() -> ArgumentParser:
    '''
    Get common ArgumentParser for testing.
    '''
    parser = ArgumentParser(description='Run tests for constrainedrandom library')
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
    return parser

import unittest
import sys

from . import testutils
from .perf_utils import dump_perf_data
from .test_args import get_argparser


def main():
    '''
    Shared main function for testing and benchmarks.
    '''
    parser = get_argparser()
    args, extra = parser.parse_known_args()
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

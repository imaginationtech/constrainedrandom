# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

'''
Benchmark against pyvsc library for equivalent testcases.
'''

import unittest
import timeit
import sys

from argparse import ArgumentParser
from random import Random

from benchmarks.pyvsc.basic import vsc_basic, cr_basic
from benchmarks.pyvsc.in_keyword import vsc_in, cr_in, cr_in_order
from benchmarks.pyvsc.ldinstr import vsc_ldinstr
from examples.ldinstr import ldInstr


TEST_LENGTH_MULTIPLIER = 1


class BenchmarkTests(unittest.TestCase):

    def run_one(self, name, randobj, iterations):
        '''
        Benchmark one object that implements the .randomize() function
        for N iterations.
        '''
        start_time = timeit.default_timer()
        for _ in range(iterations):
            randobj.randomize()
        end_time = timeit.default_timer()
        total_time = end_time - start_time
        hz = iterations / total_time
        print(f'{self._testMethodName}: {name} took {total_time:.4g}s for {iterations} iterations ({hz:.1f}Hz)')
        return total_time, hz

    def run_benchmark(self, randobjs, iterations, check):
        '''
        Reusable function to run a fair benchmark between
        two or more randomizable objects.

        randobjs:   dictionary where key is name, value is an object that implements .randomize()
        iterations: how many times to call .randomize()
        check:      function taking a dictionary of results to check.
        '''
        iterations *= TEST_LENGTH_MULTIPLIER
        results = {}
        winner = None
        best_hz = 0
        for name, randobj in randobjs.items():
            total_time, hz = self.run_one(name, randobj, iterations)
            if hz > best_hz:
                winner = name
                best_hz = hz
            # Store both total time and Hz in case the test wants to specify
            # checks on how long should be taken in wall clock time.
            results[name] = total_time, hz
        print(f'{self._testMethodName}: The winner is {winner} with {best_hz:.1f}Hz!')
        # Print summary of hz delta
        for name, (_total_time, hz) in results.items():
            if name == winner:
                continue
            speedup = best_hz / hz
            print(f'{self._testMethodName}: {winner} was {speedup:.2f}x faster than {name}')
        check(results)

    def test_basic(self):
        '''
        Test basic randomizable object.
        '''
        randobjs = {'vsc': vsc_basic(), 'cr': cr_basic(Random(0))}
        def check(results):
            self.assertGreater(results['cr'][1], results['vsc'][1])
            # This testcase is typically 40-50x faster, which may vary depending
            # on machine. Ensure it doesn't fall below 30x.
            speedup = results['cr'][1] / results['vsc'][1]
            self.assertGreater(speedup, 30, "Performance has degraded!")
        self.run_benchmark(randobjs, 100, check)

    def test_in(self):
        '''
        Test object using 'in' keyword.
        '''
        randobjs = {
            'vsc': vsc_in(),
            'cr': cr_in(Random(0)),
            'cr_order': cr_in_order(Random(0)),
        }
        def check(results):
            self.assertGreater(results['cr'][1], results['vsc'][1])
            # This testcase is typically 13-15x faster, which may vary depending
            # on machine. Ensure it doesn't fall below 10x.
            speedup = results['cr'][1] / results['vsc'][1]
            self.assertGreater(speedup, 10, "Performance has degraded!")
        self.run_benchmark(randobjs, 100, check)

    def test_ldinstr(self):
        '''
        Test LD instruction example.
        '''
        randobjs = {
            'vsc': vsc_ldinstr(),
            'cr': ldInstr(Random(0)),
        }
        def check(results):
            self.assertGreater(results['cr'][1], results['vsc'][1])
            # This testcase is typically 13-15x faster, which may vary depending
            # on machine. Ensure it doesn't fall below 10x.
            speedup = results['cr'][1] / results['vsc'][1]
            self.assertGreater(speedup, 10, "Performance has degraded!")
        self.run_benchmark(randobjs, 100, check)


def parse_args():
    parser = ArgumentParser(description='Run unit tests for constrainedrandom library')
    parser.add_argument('--length-mul', type=int, default=1, help='Multiplier for test length, when desiring greater certainty on performance.')
    args, extra = parser.parse_known_args()
    return args, extra


if __name__ == "__main__":
    args, extra = parse_args()
    TEST_LENGTH_MULTIPLIER = args.length_mul
    # Reconstruct argv
    argv = [sys.argv[0]] + extra
    unittest.main(argv=argv)

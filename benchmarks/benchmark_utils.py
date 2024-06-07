import random
from typing import Any, Dict

from tests.perf_utils import PERF_DICT
from tests.testutils import TestBase


class BenchmarkTestCase(TestBase):
    '''
    Class to be overridden to provide benchmark
    test cases.
    '''

    def test_benchmark(self):
        '''
        Reusable function to run a fair benchmark between
        two or more randomizable objects.
        '''
        results = {}
        winner = None
        best_hz = 0
        randobjs = self.get_randobjs()
        for name, randobj in randobjs.items():
            # Attempt fairness by re-seeding each time
            random.seed(0)
            full_name = self.__class__.__name__ + f".{name}"
            _result, perf_result = self.randomize_and_time(randobj, self.iterations, name=full_name)
            if perf_result['hz'] > best_hz:
                winner = name
                best_hz = perf_result['hz']
            # Store both total time and Hz in case the test wants to specify
            # checks on how long should be taken in wall clock time.
            results[name] = perf_result
        print(f'{self._testMethodName}: The winner is {winner} with {best_hz:.2f}Hz!')
        # Print summary of hz delta
        for name, perf_result in results.items():
            if name == winner:
                continue
            speedup = best_hz / perf_result['hz']
            print(f'{self._testMethodName}: {winner} was {speedup:.2f}x faster than {name}')
        self.check_perf(results)

    def check_perf(self, perf_results: Dict[str, PERF_DICT]):
        '''
        Implement this to check the expected performance results
        for a given testcase.

        perf_results: Performance results as captured.
        '''
        raise NotImplementedError("Benchmark test cases should check performance")

    def get_randobjs(self) -> Dict[str, Any]:
        '''
        Implement this to return the objects to test.

        Returns a dictionary with index as the string name
        of the random object, value as the object which implements
        `.randomize()`.
        '''
        raise NotImplementedError("Benchmark test cases must implement get_randobjs()")

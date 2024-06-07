# Benchmarks

These benchmarks are intended as developer-facing. They contain checks to ensure that performance has not degraded.

## Extra requirements

You need to install [`pyvsc`](https://pyvsc.readthedocs.io/en/latest/introduction.html) in order to run the benchmarks. This is not included in `pyproject.toml` as a dependency to avoid making installation size bigger than necessary.

## Running

To run, from the root of constrainedrandom:

```
python3 -m benchmarks
```

## Defining new benchmarks

Benchmark test cases should inherit from `benchmarks.benchmark_utils.BenchmarkTestCase`.

Each test case should implement a `get_randobjs()` method. This returns a dictionary of the random objects to be tested. Each should implement the `randomize()` function and be equivalent.

Each test case should also implement a `check_perf()` method, so that the expected results are defined in an executable, checkable manner.

## Shared framework

The benchmarks use a shared testing framework with the unit tests. However, they are kept separate so that users don't have to install `pyvsc` to ensure basic functionality of constrainedrandom.

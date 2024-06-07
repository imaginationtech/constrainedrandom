# Tests

These tests are developer-facing tests for anyone modifying `constrainedrandom`.

## Running the tests

From the root of the `constrainedrandom` repo:

```
python3 -m tests
```

This invokes Python `unittest.main()` on all tests. You can optionally specify one test to run, e.g.

```
python3 -m tests BasicFeatures
```

Note: this tests your current local copy of the code, and is not yet integrated with the build/release process.

## Performance data and graphs

Performance data can be dumped while running tests, and graphs can be plotted of this data to compare different test runs. This can be useful while making changes that might impact performance.

Note: comparing performance data is only meaningful when the data is produced with directly comparable hardware under comparable load. It is left entirely to the user to ensure appropriate testing conditions.

To create performance data and graphs, first run the tests with `--perf`:

```
python3 -m tests --perf
```

Tests can optionally be tagged using `--perf-results-tag <tag>`. This can be useful to identify tests run with particular changes.

Creating performance graphs requires the [`bokeh`](https://bokeh.org/) package to be installed at a version >= v3.4.1. This is not included in `constrainedrandom`'s `pyproject.toml` dependencies to avoid a bloated installation.

To plot performance graphs, run the following:

```
python3 -m tests.plot_perf_results <json files>
```

This will output an HTML file which can be viewed in a browser.

# `constrainedrandom`

A package for creating and solving constrained randomization problems.

Use this package to create SystemVerilog-style "declarative" randomizable objects in Python.

This is achieved by providing wrappers around the Python [`random`](https://docs.python.org/3/library/random.html) and [`constraint`](https://pypi.org/project/python-constraint/) packages, and aims to be as efficient as possible in a language like Python.


## Installation

```bash
$ pip install constrainedrandom
```

## Documentation

[Read the docs here](https://constrainedrandom.readthedocs.io/en/latest/)

To build the documentation yourself:
```bash
$ cd docs
$ make html
```

The index page is at `docs/_build/html/index.html` - you can open this in a web browser.

## Contributions

Please feel free to contribute to the project, following these guidelines:
- Please contribute by creating a fork and submitting a pull request.
- Pull requests should be as small as possible to resolve the issue they are trying to address.
- Pull requests must respect the goals of the library, as stated in the documentation.
- Pull requests should maintain backwards compatibility at least as far as Python 3.8.
- Pull requests should pass all the tests in the `tests/` directory. Run `python -m tests`.
- Pull requests should take care not to make performance worse except for cases which require bug fixes. Run `python -m tests` and `python -m benchmarks`.
- Pull requests should update the documentation for any added/changed functionality.

## `TODO`
  - Add proper CI using tox or similar, testing Python versions 3.8..current
  - Add equivalent SystemVerilog testcases for benchmarking.

## Contact the author(s)

Will Keen - william.keen@imgtec.com

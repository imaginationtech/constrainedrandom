# `constrainedrandom`

A package for creating and solving constrained randomization problems.

Use this package to create SystemVerilog-style "declarative" randomizable objects in Python.

This is achieved by providing wrappers around the Python [`random`](https://docs.python.org/3/library/random.html) and [`constraint`](https://pypi.org/project/python-constraint/) packages, and aims to be as efficient as possible in a language like Python.

## This project has moved!

Effective 1 November 2024, Will Keen (the author of this repository) is no longer employed by Imagination Technologies.

Therefore, to enable the original author to continue maintaining it, the repository has been forked:
https://github.com/will-keen/constrainedrandom

The license of the project remains the MIT license. Imagination Technologies' right to be recognized as the copyright holder has been maintained.

Both the PyPi page and the Read The Docs page have been changed to point to the new project location. All releases from 1.2.2 onwards will be released from the fork.

Releases up to and including 1.2.1 will remain here for posterity. The author will do all future development work on the fork.

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

## Tests and benchmarks

Please see `tests/README.md` and `benchmarks/README.md` for more information.

## Releases/versioning

Releases are created using tags from the repository and can be found on [PyPI](https://pypi.org/project/constrainedrandom/).

Versioning attempts to follow [Semantic Versioning](https://semver.org/).

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

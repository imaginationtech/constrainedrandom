Introduction
============

``constrainedrandom`` is a package for creating and solving constrained randomization problems.

Use this package to create SystemVerilog-style "declarative" randomizable objects in Python.

This is achieved by providing wrappers around the Python random_ and constraint_ packages, and aims to be as efficient as possible in a language like Python.


Goals of ``constrainedrandom``
------------------------------

These goals should define the future development of ``constrainedrandom``.

The package should be:

    - Easy-to-use for those with a SystemVerilog/verification background.
        - This package is aimed at a pre-silicon verification audience who are familiar with SystemVerilog.
        - It does not need to exactly replicate the syntax and oddities of SystemVerilog, but it must adhere to the principle of declarative randomization.
    - Repeatable.
        - i.e. gives the same results deterministically across multiple runs with the same seed.
    - Fast.
        - Or at least as fast as can be expected from a Python package rather than say C/C++.
        - Originally, the creation of the package was motivated by pyvsc_.
        - pyvsc_ is feature-rich and user-friendly for those with an SV background, but we found it was not fast enough for production usage.
        - This package aims to achieve at least a 10x speedup over pyvsc_. See the ``benchmarks/`` directory or run ``python -m benchmarks`` for testing.

Motivation
----------

Why bother with a Python package for this? Why not just use procedural randomization?

In pre-silicon verification, a lot of time is spent writing constrained random testcases. Many developers are used to SystemVerilog, a language which provides a rich set of built-in randomization features. These are written in a declarative manner.

While it (almost always?) produces a faster program when a user manually writes procedural code to randomize their variables, it is certainly easier not to have to think about that problem and instead delegate it. Writing constraints declaratively is perceived by many verification engineers to make development easier. Ease of development must be traded off against program speed (which is the same reason Python exists, and we don't all write C all the time).

For example, imagine you want to generate three random numbers between -10 and 10 that sum together to make 0. You could write procedural code that looks like this:

..  code-block:: python

    import random

    random.seed(0)

    def get_three():
        '''
        Returns three random numbers between -10 and 10 that sum to zero.
        '''
        # Get the first random number, a.
        a = random.randrange(-10, 11)
        # Get the second random number, b.
        # a + b can't be more than 10 or less than -10.
        # -10 <= a + b
        # -10 - a <= b
        lower_limit = max(-10, -10 - a)
        # a + b <= 10
        # b <= 10 - a
        upper_limit = min(10, 10 - a)
        b = random.randrange(lower_limit, upper_limit + 1)
        # Get the third random number. a + b + c = 0.
        c = -(a + b)
        return {'a': a, 'b': b, 'c': c}

This is all well and good, and gets the right answer. (Although, the only truly 'free' variable is ``a``, as the others depend on its value, and therefore ``b`` and ``c`` are skewed towards a normal-ish distrubution around 0.)

However, with the procedural implementation, the user had to think up a correct way to get what they wanted. It's not immediately obvious from reading the code what it does - only the docstring tells us.

With declarative-style constrained randomization, we can pretty easily read the problem being described in the code. Consdier the following:

.. code-block:: python

    import random

    from constrainedrandom import Random, RandObj

    random.seed(0)

    # Create randomizable object
    r = RandObj()
    r.add_rand_var('a', domain=range(-10,11))
    r.add_rand_var('b', domain=range(-10,11))
    r.add_rand_var('c', domain=range(-10,11))
    def sum_zero(a, b, c):
        return a + b + c == 0
    r.add_constraint(sum_zero, ('a', 'b', 'c'))

    def constrainedrand_get_three():
        r.randomize()
        return r.get_results()

It's fairly obvious that we've got three random variables with one constraint that applies to all three of them. It's quicker for the programmer to write this and easier for teammates to read it and understand what it does. The programmer doesn't have to care how to solve the constraint, just that they need to declare it.

The procedural code is faster to execute, but the declarative approach saves developer time. This package aims to provide an efficient way for the user to write constrained randomization problems in the declarative style.

.. _random: https://docs.python.org/3/library/random.html
.. _constraint: https://pypi.org/project/python-constraint/
.. _pyvsc: https://github.com/fvutils/pyvsc
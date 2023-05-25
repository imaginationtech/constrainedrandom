How to use ``constrainedrandom``
================================

The following is a guide on how to use all the features of ``constrainedrandom``.

Code snippets are provided and the user is encouraged to try them out.

Repeatability
-------------

The library provides two main user-facing classes, ``Random`` and ``RandObj``.

The ``Random`` class inherits from the standard Python ``random.Random`` class. It provides repeatable randomization when given the same seed.

..  code-block:: python

    from constrainedrandom import Random

    # Use seed 0
    rand1 = Random(0)
    for _ in range(5):
        print(rand1.randrange(10))

    # Use seed 0 again, this will produce the same 5 random values
    rand2 = Random(0)
    for _ in range(5):
        print(rand2.randrange(10))

The ``RandObj`` class accepts an instance of ``Random`` in its constructor.
The usage model is to use one ``Random`` object per seed in a program, and to pass it to all the ``RandObj`` objects used in the program, to ensure that results are repeatable.

..  code-block:: python

    from constrainedrandom import Random, RandObj

    def my_function(seed, name):
        rand = Random(seed)
        # Create two random objects with the same shared random generator.
        randobj1 = RandObj(rand)
        randobj1.add_rand_var("a", domain=range(10))
        randobj2 = RandObj(rand)
        randobj2.add_rand_var("b", bits=4)

        # Create and print some random values
        values = []
        for _ in range(5):
            randobj1.randomize()
            randobj2.randomize()
            values.append(f"a={randobj1.a}, b={randobj2.b}")
        print(name, values)

    # Using the same seed will produce the same results
    my_function(0, "first call:")
    my_function(0, "second call:")
    # Using a different seed produces different results
    my_function(1, "third call:")

Adding random variables
-----------------------

The ``RandObj`` class provides a means to create randomizable objects. The user may either inherit from ``RandObj``, or simply create instances of it, depending on the problem they are trying to solve.

A ``RandObj`` has random variables. Each random variable will be randomized to one of its possible values when the ``randomize()`` method is called.

The method to add a random variable is ``add_rand_var``, which accepts a number of arguments. At mimimum, the user must specify a name for the variable, and a means to determine its possible values. The possible values can be expressed either as a size in bits, a "domain", or a custom function and its arguments.

``bits``
________

Using the ``bits`` argument to ``add_rand_var`` means that the random variable's possible values are all the values that would fit into a bit field value of that width. For example, if the user used ``r.add_rand_var('a', bits=8)``, variable ``a`` would have possible values ``0 <= value < (1 << 8)``.

..  code-block:: python

    from constrainedrandom import Random, RandObj

    rand = Random(0)
    # Create an instance of RandObj
    r = RandObj(rand)
    # Add a random variable called 'fred', which is 8 bits wide
    r.add_rand_var('fred', bits=8)
    # Add another random variable called 'bob', which is 4 bits wide
    r.add_rand_var('bob', bits=4)
    # Randomize all variables
    r.randomize()
    # Once randomized the first time, variables are attributes of the object
    print(r.fred)
    print(r.bob)

``domain``
__________

A "domain" denotes the possible values of the variable. A domain is one of:
 - a ``range`` of possible values
 - a ``list`` or ``tuple`` of possible values
 - a ``dict`` specifying a weighted distribution of possible values (which may itself contain a ``range`` of possible values).

..  code-block:: python

    from constrainedrandom import Random, RandObj

    rand = Random(0)
    r = RandObj(rand)
    # Add a random variable called 'foo',
    # whose value is greater than or equal to 4 and less than 42
    r.add_rand_var('foo', domain=range(4, 42))
    # Add a random variable called 'bar',
    # whose value is one of the first 5 prime numbers
    r.add_rand_var('bar', domain=(2, 3, 5, 7, 11))
    # Add a random variable called 'baz',
    # whose value is a distribution weighted to choose 0 half of the time,
    # 1 a quarter of the time, and 2 <= value < 10 a quarter of the time.
    r.add_rand_var(
        'baz',
        domain={
            0: 50,
            1: 25,
            range(2,10): 25
        }
    )
    r.randomize()

``fn``
______

A custom function can be provided to dertermine the value of a random variable. Such a custom function is provided via the ``fn`` argument.

It is optional whether the function requires arguments. If it does, these can also be specified as a ``tuple`` and passed via the ``args`` argument.

The custom function will be called to determine the value of the random variable. If arguments are provided via the ``args`` argument, these will be passed to the function when it is called.

..  code-block:: python

    from constrainedrandom import Random, RandObj

    import time

    rand = Random(0)
    r = RandObj(rand)
    # Add a random variable called 'time',
    # whose value is determined by calling the function time.time
    r.add_rand_var('time', fn=time.time)
    # Add a random variable called 'time_plus_one',
    # whose value is determined by calling our custom function 'my_func'
    # with argument 1
    def my_func(time_delta):
        return time.time() + time_delta
    r.add_rand_var('time_plus_one', fn=my_func, args=(1,))
    # Note that calling randomize here just calls these functions to
    # populate the variables.
    r.randomize()
    print(r.time, r.time_plus_one)
    time.sleep(1)
    # This will call the functions again, yielding different results.
    r.randomize()
    print(r.time, r.time_plus_one)

Sometimes, we want the custom function to perform procedural randomization, if it's easier to express what we want that way.

.. note::
    In order to maintain repeatability, the function should not perform randomization independent from the same instance of ``Random`` used to control the ``RandObj``'s seeding.

The following is OK because the function uses the same random seeding object as the ``RandObj`` instance that it is added to:

..  code-block:: python

    from constrainedrandom import Random, RandObj

    rand = Random(0)
    r = RandObj(rand)

    # Add a random variable called 'multiple_of_4',
    # whose value is determined by calling the function rand_mul_by_4

    def rand_mul_by_4():
        val = rand.randrange(1,10)
        return val * 4

    r.add_rand_var('multiple_of_4', fn=rand_mul_by_4)
    r.randomize()

However, the following is *not* OK because the ``rand_mul_by_4`` function is not seeded by the same object as the ``RandObj`` instance. This will give unrepeatable results because ``rand_mul_by_4`` is using the base Python ``random`` package instead:

..  code-block:: python

    import random
    from constrainedrandom import Random, RandObj

    rand = Random(0)
    r = RandObj(rand)

    # Add a random variable called 'multiple_of_4',
    # whose value is determined by calling the function rand_mul_by_4

    def rand_mul_by_4():
        val = random.randrange(1,10)
        return val * 4

    r.add_rand_var('multiple_of_4', fn=rand_mul_by_4)
    r.randomize()

Constraints
-----------

Constraints restrict the possible values of one or more of the random variables.

There are two types of constraints:

**Single-variable constraints**
    affect one variable only, and must be added to the variable when ``add_rand_var`` is called.

**Multi-variable constraints**
    affect more than one variable, and must be added to the ``RandObj`` instance after the associated variables are added.

All constraints are expressed as a function taking the relevant random variables as arguments, and returing ``True`` if the constraint is satisfied and ``False`` otherwise.

E.g. let's say we want to add a constraint that the value of a variable must not be zero. To define a function expressing that constraint, we would write the following:

.. code-block:: python

    def not_zero(x):
        return x != 0

This function returns ``True`` when called with a value that is not zero, and ``False`` if the value is equal to zero, i.e. the constraint is satisfied for a value that is non-zero, but not satisfied when the value is zero.

.. code-block::

    >>> not_zero(1)
    True
    >>> not_zero(0)
    False

Constraints should be used as sparingly as possible, as they are the main source of complexity when it comes to solving these problems.

Single-variable constraints
___________________________

Single-variable constraints constrain one variable only. They are not as much of a burden as multi-variable constraints because they don't introduce dependencies between variables.

..  code-block:: python

    from constrainedrandom import Random, RandObj

    rand = Random(0)
    r = RandObj(rand)

    # Add a random variable called 'plus_minus', which follows these rules:
    # -10 < plus_minus < 10
    # plus_minus != 0

    # We define a function to act as a constraint, it returns True if the
    # constraint is satisfied and False if it isn't:
    def not_zero(x):
        return x != 0
    r.add_rand_var('plus_minus', domain=range(-9, 10), constraints=(not_zero,))
    r.randomize()

Equally we could have used a ``lambda`` above for brevity:

..  code-block:: python

    r.add_rand_var('plus_minus', domain=range(-9, 10), constraints=(lambda x : x != 0,))

Note that the above example would be more efficiently implemented by replacing the constraint by providing a more precise domain:

..  code-block:: python

    r.add_rand_var('plus_minus', domain=list(range(-9, -1)) + list(range(1,10)))

Sometimes, however, it is just much easier to express what you want with a constraint:

..  code-block:: python

    def not_reserved_values(x):
        return x not in (0xdeadbeef, 0xcafef00d)
    r.add_rand_var(
        'address',
        domain={
            range(0x00000000, 0x10000000) : 10,
            range(0x10000000, 0xd0000000) : 1,
            range(0xd0000000, 0xffffffff) : 5,
        },
        constraints=(not_reserved_values,)
    )

The above simply restricts the values of ``address`` never to be ``0xdeadbeeef`` or ``0xcafef00d``, without otherwise affecting the distribution of values.

Multi-variable constraints
__________________________

Usually the most useful part of declarative-style constrained random testing is adding constraints that affect the value of multiple variables. Unfortunately, it is also the biggest single source of complexity when solving problems.

In ``constrainedrandom`` multi-variable constraints are added to a ``RandObj`` instance separately from the variables they affect.

..  code-block:: python

    from constrainedrandom import Random, RandObj

    rand = Random(0)
    r = RandObj(rand)
    # Add two random variables whose sum should not overflow 16 bits
    r.add_rand_var('op0', bits=16)
    r.add_rand_var('op1', bits=16)
    # Define a function to describe the constraint that the sum
    # should not overflow 16 bits
    def not_overflow_16(x, y):
        return (x + y) < (1 << 16)
    r.add_multi_var_constraint(not_overflow_16, ('op0', 'op1'))
    r.randomize()

Ordering hints
--------------

Sometimes, a randomization problem is much easier to solve if the variables are considered in a specific order.

Consider this example:

..  code-block:: python

    from constrainedrandom import Random, RandObj

    rand = Random(0)
    r = RandObj(rand)
    r.add_rand_var("x", range(100))
    r.add_rand_var("y", range(100))
    def plus_one(x, y):
        return y == x + 1
    r.add_multi_var_constraint(plus_one, ("x", "y"))
    r.randomize()

In the above example, ``y`` must equal ``x + 1``. If we randomize the two variables at the same time and check the constraints, this is hard to get right randomly (a probability of 0.001).

If we randomize the variables in an order, e.g. ``x`` first then ``y`` second, the problem becomes trivially easy. We can hint to the library what order might be most performant using ordering hints.

The ``order`` argument to ``add_rand_var`` allows us to specify what order to attempt to solve the variables with respect to one another. It defaults to ``order=0`` if not specified.

..  code-block:: python

    # Solve x first, then y
    r.add_rand_var("x", range(100), order=0)
    r.add_rand_var("y", range(100), order=1)

Many problems will be faster to solve if the user specifies a sensible ordering hint. (Obviously, the above problem is a bit silly, and in practice the user should only randomize one variable and then add one to it.)

.. warning::
    It is possible to significantly slow down the solver speed with bad ordering hints, so only use them when you are sure the order you've specified is faster.

Disabling naive solution
------------------------

The default, low-effort way to solve the problem is to randomize the variables and check the concrete values against the constraints. After a certain number of failed attempts, the solver gives up the low-effort/naive approach and constructs a proper constraint solution problem.

The example given above in `Ordering hints`_ is very hard to solve by just randomizing and checking. We can force the solver to skip the step where it randomizes and checks the constraints by disabling naive constraint solution:

..  code-block:: python

    r.set_naive_solve(False)

This means we will always construct a full constraint satisfaction problem rather than just randomizing the values and checking them against the constraints. For some problems, this will speed them up, for others it will slow them down. It is best to experiment to determine whether to do this or not.

``pre_randomize`` and ``post-randomize``
----------------------------------------

Additional methods are provided to the user as part of ``RandObj``: ``pre_randomize`` and ``post_randomize``. These methods mimic the SystemVerilog ones in that they run at the very beginning and at the very end of ``randomize()``.


..  code-block:: python

    from constrainedrandom import Random, RandObj

    class MyRandObj(RandObj):

        def __init__(self, rand):
            super().__init__(rand)

            self.add_rand_var('a', domain=range(10))

        def pre_randomize():
            print("hello")

        def post_randomize():
            print("goodbye")

    rand = Random(0)
    r = RandObj(rand)
    r.randomize()
    print(r.a)

Output:

.. code-block::

    hello
    goodbye
    6

The methods can be overridden to do anything the user pleases. In the ``RandObj`` class definition they are left empty.


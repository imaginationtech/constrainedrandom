How to use ``constrainedrandom``
================================

The following is a guide on how to use all the features of ``constrainedrandom``.

Code snippets are provided and the user is encouraged to try them out.

The ``RandObj`` class
---------------------

The library provides one main user-facing class, ``RandObj``.

This class can be instanced or inherited from to create randomization problems.

Here is an example of creating an instance of the class:

..  code-block:: python

    from constrainedrandom import RandObj

    # Create a problem where two random numbers
    # between 0 and 9 must have a sum greater than 5.
    randobj = RandObj()
    randobj.add_rand_var("a", domain=range(10))
    randobj.add_rand_var("b", domain=range(10))
    def sum_gt_5(a, b):
        return a + b > 5
    randobj.add_constraint(sum_gt_5, ('a', 'b'))

    randobj.randomize()
    print("a", randobj.a, "b", randobj.b)

Here is the same example implemented by inheriting from the class:

..  code-block:: python

    from constrainedrandom import RandObj

    # Create a problem where two random numbers
    # between 0 and 9 must have a sum greater than 5.
    class SumGTFive(RandObj):

        def __init__(self):
            super().__init__()
            self.add_rand_var("a", domain=range(10))
            self.add_rand_var("b", domain=range(10))
            def sum_gt_5(a, b):
                return a + b > 5
            self.add_constraint(sum_gt_5, ('a', 'b'))

    randobj = SumGTFive()
    randobj.randomize()
    print("a", randobj.a, "b", randobj.b)


Repeatability
-------------

The ``RandObj`` class uses the standard Python ``random`` package under the hood. ``random`` provides repeatable randomization when given the same seed.

There are two ways to seed the ``random`` package, either globally or using an instance of the ``random.Random`` class.

Global seeding
______________

The easiest way to ensure repeatability of a program with a given seed is to use global seeding of the ``random`` pacakage at the beginning of your program.

Here is an example of ensuring repeatability using global seeding:

..  code-block:: python

    import random

    # Use seed 0.
    random.seed(0)
    for _ in range(5):
        print(random.randrange(10))

    # Use seed 0 again, this will produce the same 5 random values.
    random.seed(0)
    for _ in range(5):
        print(random.randrange(10))


Here is an example how to ensure repeatability of ``RandObj`` behaviour using global seeding:

..  code-block:: python

    import random

    from constrainedrandom import RandObj

    def my_function(seed, name):
        # Seed the random package globally.
        random.seed(seed)
        # Don't pass anything in the constructor to RandObj,
        # rely on random seeding for repeatability.
        randobj1 = RandObj()
        randobj1.add_rand_var("a", domain=range(10))
        randobj2 = RandObj()
        randobj2.add_rand_var("b", bits=4)

        # Create and print some random values.
        values = []
        for _ in range(5):
            randobj1.randomize()
            randobj2.randomize()
            values.append(f"a={randobj1.a}, b={randobj2.b}")
        print(name, values)

    # Using the same seed will produce the same results.
    my_function(0, "first call:")
    my_function(0, "second call:")
    # Using a different seed produces different results.
    my_function(1, "third call:")


Object-based seeding
____________________

You can also manage repeatability by passing around an instance of ``random.Random``.

Here is an example of ensuring repeatability using the ``random.Random`` class:

..  code-block:: python

    from random import Random

    # Use seed 0.
    rand1 = Random(0)
    for _ in range(5):
        print(rand1.randrange(10))

    # Use seed 0 again, this will produce the same 5 random values.
    rand2 = Random(0)
    for _ in range(5):
        print(rand2.randrange(10))

The ``RandObj`` class accepts an instance of the ``random.Random`` class in its constructor. In this usage model, use one ``random.Random`` object per seed in a program, and to pass it to all the ``RandObj`` objects used in the program, to ensure that results are repeatable.

..  code-block:: python

    from random import Random

    from constrainedrandom import RandObj

    def my_function(seed, name):
        # Create an instance of random.Random with the desired seed.
        rand = Random(seed)
        # Create two random objects based on the same shared random generator.
        randobj1 = RandObj(rand)
        randobj1.add_rand_var("a", domain=range(10))
        randobj2 = RandObj(rand)
        randobj2.add_rand_var("b", bits=4)

        # Create and print some random values.
        values = []
        for _ in range(5):
            randobj1.randomize()
            randobj2.randomize()
            values.append(f"a={randobj1.a}, b={randobj2.b}")
        print(name, values)

    # Using the same seed will produce the same results.
    my_function(0, "first call:")
    my_function(0, "second call:")
    # Using a different seed produces different results.
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

    import random

    from constrainedrandom import RandObj

    # Ensure repeatability.
    random.seed(0)

    # Create an instance of RandObj.
    r = RandObj()
    # Add a random variable called 'fred', which is 8 bits wide.
    r.add_rand_var('fred', bits=8)
    # Add another random variable called 'bob', which is 4 bits wide.
    r.add_rand_var('bob', bits=4)
    # Randomize all variables.
    r.randomize()
    # The values of the randomizable variables are available
    # as attributes of the object.
    print(r.fred)
    print(r.bob)

``domain``
__________

A "domain" denotes the possible values of the variable. A domain is one of:
 - a ``range`` of possible values
 - a ``list`` or ``tuple`` of possible values
 - a ``dict`` specifying a weighted distribution of possible values (which may itself contain a ``range`` of possible values)
 - an ``Enum`` or ``IntEnum`` class.

..  code-block:: python

    import random
    from enum import Enum

    from constrainedrandom import RandObj

    # Ensure repeatability.
    random.seed(0)

    # Create an instance of RandObj.
    r = RandObj()
    # Add a random variable called 'foo',
    # whose value is greater than or equal to 4 and less than 42.
    r.add_rand_var('foo', domain=range(4, 42))
    # Add a random variable called 'bar',
    # whose value is one of the first 5 prime numbers.
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
    # Add a random variable called 'my_enum', with a domain
    # corresponding to the values of an Enum class.
    # Values SomeEnum.SOME (0), SomeEnum.VALUES (1) and
    # SomeEnum.HERE (10) will be chosen at random with equal weights.
    class SomeEnum(Enum):
        SOME = 0
        VALUES = 1
        HERE = 10
    r.add_rand_var('my_enum', domain=SomeEnum)
    r.randomize()

``fn``
______

A custom function can be provided to dertermine the value of a random variable. Such a custom function is provided via the ``fn`` argument.

It is optional whether the function requires arguments. If it does, these can also be specified as a ``tuple`` and passed via the ``args`` argument.

The custom function will be called to determine the value of the random variable. If arguments are provided via the ``args`` argument, these will be passed to the function when it is called.

..  code-block:: python

    import random
    import time

    from constrainedrandom import RandObj


    # Ensure repeatability.
    random.seed(0)

    # Create an instance of RandObj.
    r = RandObj()
    # Add a random variable called 'time',
    # whose value is determined by calling the function time.time
    r.add_rand_var('time', fn=time.time)
    # Add a random variable called 'time_plus_one',
    # whose value is determined by calling our custom function 'my_func'
    # with argument 1.
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
    In order to maintain repeatability, if using the :ref:`Object-based seeding` approach, the function should not perform randomization independent from the same instance of ``Random`` used to control the ``RandObj``'s seeding.

The following is OK because we are using global seeding:

..  code-block:: python

    import random

    from constrainedrandom import RandObj


    random.seed(0)

    r = RandObj()

    # Add a random variable called 'multiple_of_4',
    # whose value is determined by calling the function rand_mul_by_4.

    def rand_mul_by_4():
        val = random.randrange(1,10)
        return val * 4

    r.add_rand_var('multiple_of_4', fn=rand_mul_by_4)
    r.randomize()

The following is OK because the function uses the same random seeding object as the ``RandObj`` instance that it is added to:

..  code-block:: python

    from random import Random

    from constrainedrandom import RandObj

    rand = Random(0)
    r = RandObj(rand)

    # Add a random variable called 'multiple_of_4',
    # whose value is determined by calling the function rand_mul_by_4.

    def rand_mul_by_4():
        val = rand.randrange(1,10)
        return val * 4

    r.add_rand_var('multiple_of_4', fn=rand_mul_by_4)
    r.randomize()

However, the following is *not* OK because the ``rand_mul_by_4`` function is not seeded by the same object as the ``RandObj`` instance. This will give unrepeatable results because ``rand_mul_by_4`` is using the base Python ``random`` package instead:

..  code-block:: python

    import random

    from constrainedrandom import RandObj

    rand = random.Random(0)
    r = RandObj(rand)

    # Add a random variable called 'multiple_of_4',
    # whose value is determined by calling the function rand_mul_by_4.

    def rand_mul_by_4():
        val = random.randrange(1,10)
        return val * 4

    r.add_rand_var('multiple_of_4', fn=rand_mul_by_4)
    r.randomize()


Random list variables
_____________________

Sometimes, we might want to produce a list of randomized values. ``constrainedrandom`` supports this. You can turn a random variable into a list by supplying the ``length`` argument. ``length=0`` is the default behaviour, i.e. a scalar value. ``length=1`` means a list of one randomized value, similarly ``length=N`` means a list of N randomized values.

Here is an example of a randomized list variable.

..  code-block:: python

    import random

    from constrainedrandom import RandObj

    rand = random.Random(0)
    r = RandObj(rand)
    # Add a variable which is a list of 10 random values between 0 and 99
    r.add_rand_var('listvar', domain=range(100), length=10)
    r.randomize()

See the section below on :ref:`List Constraints` to see how adding constraints to this kind of variable works.

Initial values
______________

An initial value for a variable can be provided. This value is assigned to the variable before randomization takes place. By default, an un-randomized variable in a ``RandObj`` instance has the initial value ``None``.

..  code-block:: python

    import random

    from constrainedrandom import RandObj

    random.seed(0)
    r = RandObj()

    # No initial value supplied.
    r.add_rand_var('a', bits=10)
    # This will print `None`.
    print(r.a)
    # Initial value supplied.
    r.add_rand_var('b', domain=range(100), initial='not defined')
    # This will print `not defined`.
    print(r.b)

    # This will give the variables random values.
    # After this, the initial value is no longer captured.
    r.randomize()
    print("a", r.a, "b", r.b)


Constraints
-----------

Constraints restrict the possible values of one or more of the random variables.

There are two types of constraints:

**Single-variable constraints**
    affect one variable only.

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

The ``add_constraint`` function is used to add constraints to a ``RandObj``. The variables that a constraint affects must have already been added to the problem before ``add_constraint`` is called.

In general, constraints should be used as sparingly as possible, as they are the main source of complexity when it comes to solving these problems.

Single-variable constraints
___________________________

Single-variable constraints constrain one variable only. They are not as much of a burden as multi-variable constraints because they don't introduce dependencies between variables.

They can be added when adding the variable with ``add_rand_var``, or afterwards with ``add_constraint``. For best performance, they should be added to a variable when ``add_rand_var`` is called.

..  code-block:: python

    import random

    from constrainedrandom import RandObj


    random.seed(0)
    r = RandObj()

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

The above simply restricts the values of ``address`` never to be ``0xdeadbeef`` or ``0xcafef00d``, without otherwise affecting the distribution of values.

While it is recommended to add constraints to individual variables as they are added with ``add_rand_var``, it is also possible to add constraints to single variables with ``add_constraint``. This is especially useful when using inheritance patterns.

..  code-block:: python

    import random

    from constrainedrandom import RandObj

    random.seed(0)

    # Create a problem that gives a random number
    # between 0 and 99 which is not divisible by 3.
    class NotDivisibleByThree(RandObj):

        def __init__(self):
            super().__init__()
            def not_div_by_three(x):
                return x % 3 != 0
            self.add_rand_var("a", domain=range(100), constraints=[not_div_by_three])

    randobj = NotDivisibleByThree()
    randobj.randomize()
    print("a", randobj.a)

    # Create a problem with the same constraints as above,
    # but also where the number must not be a multiple of 5.
    class DivisibleByFive(NotDivisibleByThree):
        def __init__(self):
            super().__init__()
            def div_by_five(x):
                return x % 5 == 0
            self.add_constraint(div_by_five, ('a',))

    randobj = DivisibleByFive()
    randobj.randomize()
    print("a", randobj.a)

Multi-variable constraints
__________________________

Usually the most useful part of declarative-style constrained random testing is adding constraints that affect the value of multiple variables. Unfortunately, it is also the biggest single source of complexity when solving problems. The ``add_constraint`` function can be called on a ``RandObj`` to add another constraint to a problem.

In ``constrainedrandom``, multi-variable constraints are added to a ``RandObj`` instance *after* from the variables they affect have already been added.

..  code-block:: python

    import random

    from constrainedrandom import RandObj


    random.seed(0)
    r = RandObj()
    # Add two random variables whose sum should not overflow 16 bits.
    r.add_rand_var('op0', bits=16)
    r.add_rand_var('op1', bits=16)
    # Define a function to describe the constraint that the sum
    # should not overflow 16 bits.
    def not_overflow_16(x, y):
        return (x + y) < (1 << 16)
    r.add_constraint(not_overflow_16, ('op0', 'op1'))
    r.randomize()


List Constraints
________________

When creating a random list variable, we can specify two types of constraints - regular (or scalar) constraints which affect the scalar value in each element of the list, and list constraints wich affect the values of the list relative to each other. The ``list_constraints`` argument is used to supply constraints on the whole list.

Here is an example of using mixed scalar and list constraints for a list variable. We also make use of the provided ``unique`` method which ensures there are no repeated elements.

..  code-block:: python

    import random

    from constrainedrandom import RandObj
    from constrainedrandom.utils import unique

    rand = random.Random(0)
    r = RandObj(rand)
    # Add a variable which is a list of 10 random values between 0 and 99.
    # Each value should be a multiple of 2 or 3.
    # The list shouldn't have any repeated elements.
    # The total sum of the elements shouldn't be below 50.
    def multiple_of_2_or_3(val):
        return (val % 2 == 0) or (val % 3 == 0)
    def sum_gt_50(list_of_vals):
        total = 0
        for val in list_of_vals:
            total += val
        return total >= 50
    r.add_rand_var(
        'listvar',
        domain=range(100),
        length=10,
        constraints=(multiple_of_2_or_3,),
        list_constraints=(sum_gt_50, unique,)
    )
    r.randomize()

If any multi-variable constraints are added that affect a list variable, its type should be treated as a list. E.g.:

..  code-block:: python

    import random

    from constrainedrandom import RandObj
    from constrainedrandom.utils import unique

    rand = random.Random(0)
    r = RandObj(rand)
    # Add a variable which is a list of 10 random values between 0 and 99.
    r.add_rand_var('listvar', domain=range(100), length=10)
    # Add another variable
    r.add_rand_var('a', domain=range(10))
    # Add a multi-variable constraint, treating listvar's type as a list.
    # Ensure 'a' does not appear in the list.
    def not_in_list(a, listvar):
        return not (a in listvar)
    r.add_constraint(not_in_list, ('a', 'listvar'))
    r.randomize()

Temporary constraints
_____________________

Sometimes, we want to apply an extra constraint for one randomization attempt, without permanently modifying the underlying problem. In this case, we can apply one or more temporary constraints.

To achieve this, we use the ``with_constraints`` argument to ``randomize``:

..  code-block:: python

    import random

    from constrainedrandom import RandObj


    random.seed(0)
    r = RandObj()
    # Add two random variables whose sum should not overflow 16 bits.
    r.add_rand_var('op0', bits=16)
    r.add_rand_var('op1', bits=16)
    # Define a function to describe the constraint that the sum
    # should not overflow 16 bits.
    def not_overflow_16(x, y):
        return (x + y) < (1 << 16)
    r.add_constraint(not_overflow_16, ('op0', 'op1'))
    r.randomize()
    print(r.op0, r.op1)

    # On this occasion, we need op0 to be an even number.
    # Add a temporary constraint.
    def is_even(x):
        return x % 2 == 0
    r.randomize(with_constraints=[(is_even, ('op0',))])
    print(r.op0, r.op1)

    # Go back to a randomization just with the original constraints.
    r.randomize()
    print(r.op0, r.op1)

Temporary constraints can also apply to multiple variables:

..  code-block:: python

    # On this occasion, we need op0 + op1 to be an even number.
    # Add a temporary constraint.
    def is_even(x):
        return x % 2 == 0
    def sum_even(x, y):
        return is_even(x + y)
    r.randomize(with_constraints=[(sum_even, ('op0', 'op1'))])
    print(r.op0, r.op1)

.. note::
    Temporary constraints make solving the constraint problem even harder than regular constraints, so please try to use them sparingly for best peformance.

Temporary values
________________

Sometimes, for one randomization attempt, we want to specify a concrete value for a particular variable. In this case, we can randomize with values specified for one or more variable in the problem. This skips randomization for that variable and assigns it the value given. Other variables must still satisfy their constraints with respect to any variables with concrete values.

To achieve this, we use the ``with_values`` argument to ``randomize``:

..  code-block:: python

    import random

    from constrainedrandom import RandObj


    random.seed(0)
    r = RandObj()
    # Add two random variables whose sum should not overflow 16 bits.
    r.add_rand_var('op0', bits=16)
    r.add_rand_var('op1', bits=16)
    # Define a function to describe the constraint that the sum
    # should not overflow 16 bits.
    def not_overflow_16(x, y):
        return (x + y) < (1 << 16)
    r.add_constraint(not_overflow_16, ('op0', 'op1'))
    r.randomize()
    print(r.op0, r.op1)

    # On this occasion, we want op0 to be equal to 42.
    # The randomization will still ensure that 42 + op1 does not
    # overflow 16 bits, as per the above constraint.
    r.randomize(with_values={'op0': 42})
    print(r.op0, r.op1)

    # Randomization just with the original constraints.
    r.randomize()
    print(r.op0, r.op1)

We can mix temporary values with temporary constraints:

..  code-block:: python

    # On this occasion, we want op0 to be equal to 42
    # and op1 to be even.
    # Again the original overflow constraint will still
    # be satisfied.
    def is_even(val):
        return val % 2 == 0
    r.randomize(with_constraints=[(is_even, ('op1',))], with_values={'op0': 42})
    print(r.op0, r.op1)


``pre_randomize`` and ``post-randomize``
----------------------------------------

Additional methods are provided to the user as part of ``RandObj``: ``pre_randomize`` and ``post_randomize``. These methods mimic the SystemVerilog ones in that they run at the very beginning and at the very end of ``randomize()``.


..  code-block:: python

    import random

    from constrainedrandom import RandObj


    class MyRandObj(RandObj):

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.add_rand_var('a', domain=range(10))

        def pre_randomize(self):
            print("hello, value of 'a' is", self.a)

        def post_randomize(self):
            print("randomization is done, value of 'a' is", self.a)
            self.a = self.a + 1
            print("goodbye, value of 'a' is", self.a)

    random.seed(0)
    r = MyRandObj()
    r.randomize()
    print(r.a)

Output:

.. code-block::

    hello, value of 'a' is None
    randomization is done, value of 'a' is 6
    goodbye, value of 'a' is 7
    7

The methods can be overridden to do anything the user pleases. In the ``RandObj`` class definition they are left empty.

Optimization
------------

This section deals with how to optimize ``constrainedrandom`` for a given problem.

Ordering hints
______________

Sometimes, a randomization problem is much easier to solve if the variables are considered in a specific order.

Consider this example:

..  code-block:: python

    import random

    from constrainedrandom import RandObj


    random.seed(0)
    r = RandObj()
    r.add_rand_var("x", range(100))
    r.add_rand_var("y", range(100))
    def plus_one(x, y):
        return y == x + 1
    r.add_constraint(plus_one, ("x", "y"))
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


Constraint solving algorithms
_____________________________

``constrainedrandom`` employs three approaches to solving constraints, in order:

1. Naive solver

The default, low-effort way to solve the problem is to randomize the variables and check the concrete values against the constraints. This is called the naive solver. After a certain number of failed attempts, the solver gives up the low-effort/naive approach.

2. Sparse solver

A graph-based exploration of the state space. A constraint problem is constructed with variables in a given order. A random subset of possible solutions is kept at each depth of the graph in order to reduce the state space. The algorithm begins with a depth-first search, and then goes wider. It gives up after a maximum number of attempts at a maximum width.

3. Thorough solver

Construct a full constraint solution problem. Fully solve the CSP, finding all possible valid solutions, randomly choosing one solution. Slow, but likely to converge. There is still a restriction on the maximum domain size of the problem in order to avoid state space explosion and the program hanging. So this method might still fail.


Setting which solvers to use
____________________________

Some problems may be better suited to certain solvers. The ``set_solver_mode`` function allows the user to turn each solver on or off. The order that the solvers run in as described above cannot be changed.

The example given above in `Ordering hints`_ is very hard to solve by just randomizing and checking. We can force the solver to skip the step where it randomizes and checks the constraints by disabling naive constraint solution:

..  code-block:: python

    r.set_solver_mode(naive=False)

This means we will skip the naive solver and move on immediately to the sparse solver. For some problems, this will speed them up, for others it will slow them down. It is best to experiment to determine whether to do this or not.

The user can turn the other solvers on/off in the same manner. If a solver is not specified in the arguments, its state will not be changed. E.g. the below will turn the sparse solver off, the thorough solver on, and not affect the state of the naive solver:

..  code-block:: python

    r.set_solver_mode(sparse=False, thorough=True)

Tweaking parameters
___________________

``constrainedrandom`` has two main parameters that affect constraint solution, which can be set when constructing a ``RandObj``.

``max_iterations`` determines how many iterations are completed before a solver gives up. It is interpreted slightly differently between the different solvers, but broadly speaking does the same thing in each.

The higher the value of ``max_iterations``, the more likely it is for a solver to converge. However, if a solver has no chance to converge, this makes it take longer overall for the problem to be solved, because the solver will persist for longer before giving up.

``max_domain_size`` determines the maximum state space size that will be used with the ``constraint`` library. Because ``constraint`` is a full CSP solver, it gives all possible solutions to a CSP. The state space of a CSP can easily explode. E.g. two 32 bit variables have a state space of 2^64 when considered together. The ``max_domain_size`` sets an upper limit on this, so as not to overload ``constraint``.

Tweaking ``max_domain_size`` is harder than ``max_iterations``. A higher value may save time if a full constraint problem is faster than randomizing and checking, and is likely to increase the probability of convergence. However, a lower value may be much faster, to avoid computing all possibilites for easier variables.

The only real way to tell is to experiment with specific problems. To alter these properties for a given ``RandObj`` instance, use the arguments in the constructor, e.g.:

..  code-block:: python

    randobj = RandObj(max_iterations=1000, max_domain_size=10000)

Or when inheriting from ``RandObj``:

..  code-block:: python

    class MyRandObj(RandObj):

        def __init__(self):
            super().__init__(max_iterations=1000, max_domain_size=10000)

Bit slices
----------

Bit slicing is commonly required in verification activities, and is supported at a language level by HDLs like SystemVerilog. All bit slice operations can be achieved in Python by using masks, shifts and bitwise operations without any need to build it into the syntax of the language.

For user convenience, ``constrainedrandom`` provides common bitwise operations in the ``constrainedrandom.bits`` package.

``get_bitslice`` returns the required bitslice of the input value. E.g. the following in Python:

.. code-block:: python

    foo = get_bitslice(val, hi, lo)

is equivalent to the following in SystemVerilog:

.. code-block:: SystemVerilog

    foo = val[hi:lo];

``set_bitslice`` sets the bitslice of the input value with a new value and returns it. E.g. the following in Python:

.. code-block:: python

    val = set_bitslice(val, hi, lo, new_val)

is equivalent to the following in SystemVerilog:

.. code-block:: SystemVerilog

    val[hi: lo] = new_val;

Note that ``set_bitslice`` returns the result rather than directly modifying the input ``val``.

Debugging
---------

If the randomization problem described by a ``RandObj`` is unsolvable (at least within a certain effort limit), calling ``randomize()`` will fail. It will throw a ``RandomizationError`` exception, containing an instance of the ``RandomizationDebugInfo`` class. The latter will contain debug info on the most recent set of variables that failed to randomize and meet the constraints.

If ``debug=True`` is passed to ``randomize()``, this will slow execution down a lot, but will result in the ``RandomizationDebugInfo`` instance containing all the debug information for every failed randomization attempt during the call to ``randomize()``. This is a lot of information but might be helpful in spotting repeated patterns of constraints that cannot be solved.

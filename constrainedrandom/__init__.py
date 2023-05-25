# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

from __future__ import annotations
from collections import defaultdict
from functools import partial
from typing import Any, Callable, Iterable, Optional, Union

import constraint
import random


# The maximum iterations before giving up on any randomization
MAX_ITERATIONS = 100
# The largest domain size to use with the constraint library
CONSTRAINT_MAX_DOMAIN_SIZE = 1 << 10

# Distribution type
Dist = dict[Any, int]


class Random(random.Random):
    '''
    Seeded, repeatable, deterministic random generator object.
    Subclass of :class:`random.Random`, enhanced with some quality-of-life features.
    Ideally one of these should be used per seeded random activity, e.g.
    in :class:`constrainedrandom.RandVar`.

    :param seed: Fixed seed for randomization.

    :example:

    .. code-block:: python

        # Create a random generator with seed 0.
        r1 = Random(seed=0)
        # Output five random 32-bit integers.
        for i in range(5):
            print(r1.randbits(32))

        # Create a second random generator with seed 0.
        r2 = Random(seed=0)
        # These five values will be the same as output by r1.
        for i in range(5):
            print(r2.randbits(32))

        # Create a third random generator with seed 1.
        r3 = Random(seed=1)
        # These five values will be different to the previous values.
        for i in range(5):
            print(r3.randbits(32))
    '''

    def __init__(self, seed: int) -> None:
        super().__init__(x=seed)

    def weighted_choice(self, choices_dict: Dist) -> Any:
        '''
        Wrapper around ``random.choices``, allowing the user to specify weights in a dictionary.

        :param choices_dict: A dict containing the possible values as keys and relative
            weights as values.
        :return: One of the keys of ``choices_dict`` chosen at random, based on weighting.
        :example:

        .. code-block:: python

            r = Random(seed=0)
            # 0 will be chosen 25% of the time, 1 25% of the time and 'foo' 50% of the time
            value = r.weighted_choice({0: 25, 1: 25, 'foo': 50})
        '''
        return self.choices(tuple(choices_dict.keys()), weights=tuple(choices_dict.values()))

    def dist(self, dist_dict: Dist) -> Any:
        '''
        Random distribution. As :func:`weighted_choice`, but allows ``range`` to be used as
        a key to the dictionary, which if chosen is then evaluated as a random range.

        :param dist_dict: A dict containing the possible values as keys and relative
            weights as values. If a range is supplied as a key, it will be evaluated
            as a random range.
        :return: One of the keys of ``dist_dict`` chosen at random, based on weighting.
            If the key is a range, evaluate the range as a random range before returning.
        :example:

        .. code-block:: python

            r = Random(seed=0)
            # 0 will be chosen 25% of the time, a value in the range 1 to 9 25% of the time
            # and 'foo' 50% of the time
            value = r.dist({0: 25, range(1, 10): 25, 'foo': 50})
        '''
        answer = self.weighted_choice(choices_dict=dist_dict)[0]
        if isinstance(answer, range):
            return self.randrange(answer.start, answer.stop)
        return answer


# Domain type
Domain = Union[Iterable[Any], range, Dist]
# Constraint type
Constraint = Callable[..., bool]

class RandVar:
    '''
    Randomizable variable. For internal use with RandObj.

    :param parent: The :class:`RandObj` instance that owns this instance.
    :param name: The name of this random variable.
    :param order: The solution order for this variable with respect to other variables.
    :param domain: The possible values for this random variable, expressed either
        as a ``range``, or as an iterable (e.g. ``list``, ``tuple``) of possible values.
        Mutually exclusive with ``bits`` and ``fn``.
    :param bits: Specifies the possible values of this variable in terms of a width
        in bits. E.g. ``bits=32`` signifies this variable can be ``0 <= x < 1 << 32``.
        Mutually exclusive with ``domain`` and ``fn``.
    :param fn: Specifies a function to call that will provide the value of this random
        variable.
        Mutually exclusive with ``domain`` and ``bits``.
    :param args: Arguments to pass to the function specified in ``fn``.
        If ``fn`` is not used, ``args`` must not be used.
    :param constraints: List or tuple of constraints that apply to this random variable.
    :param max_iterations: The maximum number of failed attempts to solve the randomization
        problem before giving up.
    '''

    def __init__(self,
        parent: RandObj,
        name: str,
        order: int,
        *,
        domain: Optional[Domain]=None,
        bits: Optional[int]=None,
        fn: Optional[Callable]=None,
        args: Optional[tuple]=None,
        constraints: Optional[Iterable[Constraint]]=None,
        max_iterations: int=MAX_ITERATIONS,
    ) -> None:
        self.parent = parent
        self.random = self.parent._random
        self.name = name
        self.order = order
        self.max_iterations = max_iterations
        assert  ((domain is not None) != (fn is not None)) != (bits is not None), "Must specify exactly one of fn, domain or bits"
        if fn is None:
            assert args is None, "args has no effect without fn"
        self.domain = domain
        self.bits = bits
        self.fn = fn
        self.args = args
        self.constraints = constraints if constraints is not None else []
        if not (isinstance(self.constraints, tuple) or isinstance(self.constraints, list)):
            self.constraints = (self.constraints,)
        # Default strategy is to randomize and check the constraints.
        self.check_constraints = len(self.constraints) > 0
        # Create a function, self.randomizer, that returns the appropriate random value
        if self.fn is not None:
            if self.args is not None:
                self.randomizer = partial(self.fn, *self.args)
            else:
                self.randomizer = self.fn
        elif self.bits is not None:
            self.randomizer = partial(self.random.getrandbits, self.bits)
            self.domain = range(0, 1 << self.bits)
        else:
            # If we are provided a sufficiently small domain and we have constraints, simply construct a
            # constraint solution problem instead.
            is_range = isinstance(self.domain, range)
            is_list = isinstance(self.domain, list) or isinstance(self.domain, tuple)
            is_dict = isinstance(self.domain, dict)
            if self.check_constraints and len(self.domain) < CONSTRAINT_MAX_DOMAIN_SIZE and (is_range or is_list):
                problem = constraint.Problem()
                problem.addVariable(self.name, self.domain)
                for con in self.constraints:
                    problem.addConstraint(con, (self.name,))
                # Produces a list of dictionaries
                solutions = problem.getSolutions()
                def solution_picker(solns):
                    return self.random.choice(solns)[self.name]
                self.randomizer = partial(solution_picker, solutions)
                self.check_constraints = False
            elif is_range:
                self.randomizer = partial(self.random.randrange, self.domain.start, self.domain.stop)
            elif is_list:
                self.randomizer = partial(self.random.choice, self.domain)
            elif is_dict:
                self.randomizer = partial(self.random.dist, self.domain)
            else:
                raise TypeError(f'RandVar was passed a domain of a bad type - {self.domain}. Domain should be a range, list, tuple or dictionary.')

    def randomize(self) -> Any:
        '''
        Returns a random value based on the definition of this random variable.
        Does not modify the state of the :class:`RandVar` instance.

        :return: A randomly generated value, conforming to the definition of
            this random variable, its constraints, etc.
        :raises RuntimeError: When the problem cannot be solved in fewer than
            the allowed number of iterations.
        '''
        value = self.randomizer()
        value_valid = not self.check_constraints
        iterations = 0
        while not value_valid:
            if iterations == self.max_iterations:
                raise RuntimeError("Too many iterations, can't solve problem")
            problem = constraint.Problem()
            problem.addVariable(self.name, (value,))
            for con in self.constraints:
                problem.addConstraint(con, (self.name,))
            value_valid = problem.getSolution() is not None
            if not value_valid:
                value = self.randomizer()
            iterations += 1
        return value


class MultiVarProblem:
    '''
    Multi-variable problem. Used internally by RandObj.
    Represents one problem concerning multiple random variables,
    where those variables all share dependencies on one another.

    :param parent: The :class:`RandObj` instance that owns this instance.
    :param vars: The dictionary of names and :class:`RandVar` instances this problem consists of.
    :param constraints: The list or tuple of constraints associated with
        the random variables.
    :param max_iterations: The maximum number of failed attempts to solve the randomization
        problem before giving up.
    '''

    def __init__(
        self,
        parent: RandObj,
        vars: dict[str, RandVar],
        constraints: Iterable[Constraint],
        max_iterations: int=MAX_ITERATIONS
    ) -> None:
        self.parent = parent
        self.random = self.parent._random
        self.vars = vars
        self.constraints = constraints
        self.max_iterations = max_iterations

    def determine_order(self) -> list[list[RandVar]]:
        '''
        Chooses an order in which to resolve the values of the variables.
        Used internally.

        :return: A list of lists denoting the order in which to solve the problem.
            Each inner list is a group of variables that can be solved at the same
            time. Each inner list will be considered separately.
        '''
        # Aim to build a list of lists, each inner list denoting a group of variables
        # to solve at the same time.
        # The best case is to simply solve them all at once, if possible, however it is
        # likely that the domain will be too large.

        # Use order hints first, remaining variables can be placed anywhere the domain
        # isn't too large.
        sorted_vars = sorted(self.vars.values(), key=lambda x: x.order)

        # Currently this is just a flat list. Group into as large groups as possible.
        result = [[sorted_vars[0]]]
        index = 0
        domain_size = len(sorted_vars[0].domain) if sorted_vars[0].domain is not None else 1
        for var in sorted_vars[1:]:
            if var.domain is not None:
                domain_size = domain_size * len(var.domain)
            if var.order == result[index][0].order and domain_size < CONSTRAINT_MAX_DOMAIN_SIZE:
                # Put it in the same group as the previous one, carry on
                result[index].append(var)
            else:
                # Make a new group
                index += 1
                domain_size = len(var.domain) if var.domain is not None else 1
                result.append([var])

        return result

    def _solve(self, groups: list[list[RandVar]], max_iterations:int, solutions_per_group: Optional[int]=None) -> Union[dict[str, Any], None]:
        '''
        Constraint solving algorithm (internally used by :class:`MultiVarProblem`).

        :param groups: The list of lists denoting the order in which to resolve the random variables.
            See :func:`determine_order`.
        :param max_iterations: The maximum number of failed attempts to solve the randomization
            problem before giving up.
        :param solutions_per_group: If ``solutions_per_group`` is not ``None``,
            solve each constraint group problem 'sparsely',
            i.e. maintain only a subset of potential solutions between groups.
            Fast but prone to failure.

            ``solutions_per_group = 1`` is effectively a depth-first search through the state space
            and comes with greater benefits of considering each multi-variable constraint at
            most once.

            If ``solutions_per_group`` is ``None``, Solve constraint problem 'thoroughly',
            i.e. keep all possible results between iterations.
            Slow, but will usually converge.
        :returns: A valid solution to the problem, in the form of a dictionary with the
            names of the random variables as keys and the valid solution as the values.
            Returns ``None`` if no solution is found within the allotted ``max_iterations``.
        '''
        constraints = self.constraints
        sparse_solver = solutions_per_group is not None

        if sparse_solver:
            solved_vars = defaultdict(set)
        else:
            solved_vars = []
            problem = constraint.Problem()

        for idx, group in enumerate(groups):
            # Construct a constraint problem where possible. A variable must have a domain
            # in order to be part of the problem. If it doesn't have one, it must just be
            # randomized.
            if sparse_solver:
                # Construct one problem per iteration, add solved variables from previous groups
                problem = constraint.Problem()
                for name, values in solved_vars.items():
                    problem.addVariable(name, list(values))
            group_vars = []
            rand_vars = []
            for var in group:
                group_vars.append(var.name)
                if var.domain is not None and not isinstance(var.domain, dict):
                    problem.addVariable(var.name, var.domain)
                    # If variable has its own constraints, these must be added to the problem,
                    # regardless of whether var.check_constraints is true, as the var's value will
                    # depend on the value of the other constrained variables in the problem.
                    for con in var.constraints:
                        problem.addConstraint(con, (var.name,))
                else:
                    rand_vars.append(var)
            # Add all pertinent constraints
            skipped_constraints = []
            for (con, vars) in constraints:
                skip = False
                for var in vars:
                    if var not in group_vars and var not in solved_vars:
                        # Skip this constraint
                        skip = True
                        break
                if skip:
                    skipped_constraints.append((con, vars))
                    continue
                problem.addConstraint(con, vars)
            # Problem is ready to solve, apart from any new random variables
            solutions = []
            attempts = 0
            while True:
                if attempts >= max_iterations:
                    # We have failed, give up
                    return None
                for var in rand_vars:
                    # Add random variables in with a concrete value
                    if solutions_per_group > 1:
                        var_domain = set()
                        for _ in range(solutions_per_group):
                            var_domain.add(var.randomize())
                        problem.addVariable(var.name, list(var_domain))
                    else:
                        problem.addVariable(var.name, (var.randomize(),))
                solutions = problem.getSolutions()
                if len(solutions) > 0:
                    break
                else:
                    attempts += 1
                    for var in rand_vars:
                        # Remove from problem, they will be re-added with different concrete values
                        del problem._variables[var.name]
            # This group is solved, move on to the next group.
            if sparse_solver:
                if idx != len(groups) - 1:
                    # Store a small number of concrete solutions to avoid bloating the state space.
                    if solutions_per_group < len(solutions):
                        solution_subset = self.random.choices(solutions, k=solutions_per_group)
                    else:
                        solution_subset = solutions
                    solved_vars = defaultdict(set)
                    for soln in solution_subset:
                        for name, value in soln.items():
                            solved_vars[name].add(value)
                if solutions_per_group == 1:
                    # This means we have exactly one solution for the variables considered so far,
                    # meaning we don't need to re-apply solved constraints for future groups.
                    constraints = skipped_constraints
            else:
                solved_vars += group_vars

        return self.random.choice(solutions)

    def solve(self) -> Union[dict[str, Any], None]:
        '''
        Attempt to solve the variables with respect to the constraints.

        :return: One valid solution for the randomization problem, represented as
            a dictionary with keys referring to the named variables.
        :raises RuntimeError: When the problem cannot be solved in fewer than
            the allowed number of iterations.
        '''
        groups = self.determine_order()

        solution = None

        # Try to solve sparsely first
        sparsities = [1, 10, 100, 1000]
        for sparsity in sparsities:
            for _ in range(self.max_iterations // 10):
                solution = self._solve(groups, self.max_iterations // 10, sparsity)
                if solution is not None and len(solution) > 0:
                    return solution

        # Try 'thorough' method - no backup plan if this fails
        solution = self._solve(groups)
        if solution is None:
            raise RuntimeError("Could not solve problem.")
        return solution


class RandObj:
    '''
    Randomizable object. User-facing class.
    Contains any number of random variables and constraints.
    Randomizes to produce a valid solution for those variables and constraints.

    :param random: An instance of :class:`Random`, which controls the
        seeding and random generation for this class.
    :param max_iterations: The maximum number of failed attempts to solve the randomization
        problem before giving up.

    :example:

    .. code-block:: python

        # Create a random object based on a random generator
        rand_generator = Random(seed=0)
        rand_obj = RandObj(rand_generator)

        # Add some random variables
        rand_obj.add_rand_var('one_to_nine', domain=range(10))
        rand_obj.add_rand_var('eight_bits', bits=8, constraints=(lambda x : x != 0))

        # Add a multi-variable constraint
        rand_obj.add_multi_var_constraint(lambda x, y : x != y, ('one_to_nine', 'eight_bits'))

        # Produce one valid solution
        rand_obj.randomize()

        # Random variables are now accessible as member variables
        print(rand_obj.one_to_nine)
        print(rand_obj.eight_bits)
    '''

    def __init__(self, random: Random, *, max_iterations: int=MAX_ITERATIONS) -> None:
        # Prefix 'internal use' variables with '_', as randomized results are populated to the class
        self._random = random
        self._random_vars = {}
        self._constraints = []
        self._constrained_vars = set()
        self._max_iterations = max_iterations
        self._naive_solve = True

    def set_naive_solve(self, naive: bool) -> None:
        '''
        Disable/enable naive solving step, i.e. randomizing and checking constraints.
        For some problems, it is more expedient to skip this step and go straight to
        a MultiVarProblem.

        :param naive: ``True`` if naive solve should be used, ``False`` otherwise.
        :return: ``None``
        '''
        self._naive_solve = naive

    def add_rand_var(
        self,
        name: str,
        *,
        domain: Optional[Domain]=None,
        bits: Optional[int]=None,
        fn: Optional[Callable]=None,
        args: Optional[tuple]=None,
        constraints: Optional[Iterable[Constraint]]=None,
        max_iterations: int=MAX_ITERATIONS,
        order: int =0,
    ) -> None:
        '''
        Add a random variable to the object.
        Exactly one of ``domain``, ``bits``, or ``fn`` (optionally with ``args``) must be provided
        to determine how to randomize.

        :param name: The name of this random variable.
        :param order: The solution order for this variable with respect to other variables.
        :param domain: The possible values for this random variable, expressed either
            as a ``range``, or as an iterable (e.g. ``list``, ``tuple``) of possible values.
            Mutually exclusive with ``bits`` and ``fn``.
        :param bits: Specifies the possible values of this variable in terms of a width
            in bits. E.g. ``bits=32`` signifies this variable can be ``0 <= x < 1 << 32``.
            Mutually exclusive with ``domain`` and ``fn``.
        :param fn: Specifies a function to call that will provide the value of this random
            variable.
            Mutually exclusive with ``domain`` and ``bits``.
        :param args: Arguments to pass to the function specified in ``fn``.
            If ``fn`` is not used, ``args`` must not be used.
        :param constraints: List or tuple of constraints that apply to this random variable.
        :return: ``None``
        :raise AssertionError: If inputs are not valid.

        :example:

        .. code-block:: python

            # Create a random object based on a random generator
            rand_generator = Random(seed=0)
            rand_obj = RandObj(rand_generator)

            # Add a variable which can be 1, 3, 5, 7 or 11
            rand_obj.add_rand_var('prime', domain=(1, 3, 5, 7, 11))

            # Add a variable which can be any number between 3 and 13, except 7
            rand_obj.add_rand_var('not_7', domain=range(3, 14), constraints=(lambda x: x != 7,))

            # Add a variable which is 12 bits wide and can't be zero
            rand_obj.add_rand_var('twelve_bits', bits=12, constraints=(lambda x: x != 0,))

            # Add a variable whose value is generated by calling a function
            def my_fn():
                return rand_generator.randrange(10)
            rand_obj.add_rand_var('fn_based', fn=my_fn)

            # Add a variable whose value is generated by calling a function that takes arguments
            def my_fn(factor):
                return factor * rand_generator.randrange(10)
            rand_obj.add_rand_var('fn_based_with_args', fn=my_fn, args=(2,))
        '''
        # Check this is a valid name
        assert name not in self.__dict__, f"random variable name {name} is not valid, already exists in object"
        assert name not in self._random_vars, f"random variable name {name} is not valid, already exists in random variables"
        self._random_vars[name] = RandVar(parent=self, name=name, domain=domain, bits=bits, fn=fn, args=args, constraints=constraints, order=order)

    def add_multi_var_constraint(self, multi_var_constraint: Constraint, variables: Iterable[str]):
        '''
        Add an aribtrary constraint that applies to more than one variable.

        :param multi_var_constraint: A function (or callable) that accepts the random variables listed in ``variables``
            as argument(s) and returns either ``True`` or ``False``.
            If the function returns ``True`` when passed the variables, the constraint is satisfied.
        :param variables: A tuple/list of variables affected by this constraint. The order matters,
            this order will be preserved when passing variables into the constraint.
        :return: ``None``
        :raises AssertionError: If any member of ``variables`` is not a valid random variable.

        :example:

        .. code-block:: python

            # Assume we have a RandObj called 'randobj', with random variables a, b and c
            # Add a constraint that a, b and c must be different values
            def not_equal(x, y, z):
                return (x != y) and (y != z) and (x != z)
            randobj.add_multi_var_constraint(not_equal, ('a', 'b', 'c'))

            # Add a constraint that a is less than b
            randobj.add_multi_var_constraint(lambda x, y: x < y, ('a', 'b'))

            # Add a constraint that c must be more than double a but less than double b
            randobj.multi_var_constraint(lambda a, b, c: (a * 2) < c < (b * 2), ('a', 'b', 'c'))
        '''
        for var in variables:
            assert var in self._random_vars, f"Variable {var} was not in the set of random variables!"
            self._constrained_vars.add(var)
        self._constraints.append((multi_var_constraint, variables))

    def pre_randomize(self) -> None:
        '''
        Called by :func:`randomize` before randomizing variables. Can be overridden to do something.

        :return: ``None``
        '''

    def randomize(self) -> None:
        '''
        Randomizes all random variables, applying all constraints provided.
        After calling this for the firs time, random variables are
        accessible as member variables.

        :return: None
        :raises RuntimeError: If no solution is found within defined limits.
        '''
        self.pre_randomize()

        result = {}

        for name, random_var in self._random_vars.items():
            result[name] = random_var.randomize()

        # If there are constraints, first try just to solve naively by randomizing the values.
        # This will be faster than constructing a MultiVarProblem if the constraints turn out
        # to be trivial. Only try this a few times so as not to waste time.
        constraints_satisfied = len(self._constraints) == 0
        if self._naive_solve:
            attempts = 0
            max = self._max_iterations
            while not constraints_satisfied:
                if attempts == max:
                    break
                problem = constraint.Problem()
                for var in self._constrained_vars:
                    problem.addVariable(var, (result[var],))
                for _constraint, variables in self._constraints:
                    problem.addConstraint(_constraint, variables)
                solutions = problem.getSolutions()
                if len(solutions) > 0:
                    # At least one solution was found, all is well
                    constraints_satisfied = True
                    solution = self._random.choice(solutions)
                    result.update(solution)
                else:
                    # No solution found, re-randomize and try again
                    for var in self._constrained_vars:
                        result[var] = self._random_vars[var].randomize()
                    attempts += 1

        # If constraints are still not satisfied by this point, construct a multi-variable
        # problem and solve them properly
        if not constraints_satisfied:
            multi_var_problem = MultiVarProblem(self, {name: var for name, var in self._random_vars.items() if name in self._constrained_vars}, self._constraints)
            result.update(multi_var_problem.solve())

        # Update this object such that the results of randomization are available as member variables
        self.__dict__.update(result)

        self.post_randomize()

    def post_randomize(self) -> None:
        '''
        Called by :func:`randomize` after randomizing variables. Can be overridden to do something.

        :return: ``None``
        '''

    def get_results(self) -> dict[str, Any]:
        '''
        Returns a dictionary of the results from the most recent randomization.
        This is mainly provided for testing purposes.

        Note that individual variables can be accessed as member variables of
        a RandObj instance once randomized, e.g.

        .. code-block:: python

            rand = Random(0)
            randobj = RandObj(rand)
            randobj.add_rand_var('a', domain=range(10))
            randobj.randomize()
            print(randobj.a)

        :return: dictionary of the results from the most recent randomization.
        :raises RuntimeError: if :func:`randomize` hasn't been called first.
        '''
        try:
            # Return a new dict object rather than a reference to this object's __dict__
            return {k: self.__dict__[k] for k in self._random_vars.keys()}
        except KeyError as e:
            raise RuntimeError("Can't call .get_results() until .randomize() has been called at least once.")

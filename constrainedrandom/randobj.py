# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

import constraint
import random
from collections import defaultdict
from typing import Any, Callable, Dict, Iterable, List, Optional

from . import utils
from .internal.multivar import MultiVarProblem
from .internal.randvar import RandVar


class RandObj:
    '''
    Randomizable object. User-facing class.
    Contains any number of random variables and constraints.
    Randomizes to produce a valid solution for those variables and constraints.

    :param _random: An instance of ``random.Random``, which controls the
        seeding and random generation for this class. If passed none, use the global
        Python random package.
    :param max_iterations: The maximum number of failed attempts to solve the randomization
        problem before giving up.
    :param max_domain_size: The maximum size of domain that a constraint satisfaction problem
        may take. This is used to avoid poor performance. When a problem exceeds this domain
        size, we don't use the ``constraint`` package, but just use ``random`` instead.

    :example:

    .. code-block:: python

        import random
        from constrainedrandom import RandObj

        # Create a random object based on a random generator with seed 0
        rand_generator = random.Random(0)
        rand_obj = RandObj(rand_generator)

        # Add some random variables
        rand_obj.add_rand_var('one_to_nine', domain=range(1, 10))
        rand_obj.add_rand_var('eight_bits', bits=8, constraints=(lambda x : x != 0))

        # Add a multi-variable constraint
        rand_obj.add_constraint(lambda x, y : x != y, ('one_to_nine', 'eight_bits'))

        # Produce one valid solution
        rand_obj.randomize()

        # Random variables are now accessible as member variables
        print(rand_obj.one_to_nine)
        print(rand_obj.eight_bits)
    '''

    def __init__(
        self,
        _random: Optional[random.Random]=None,
        max_iterations: int=utils.MAX_ITERATIONS,
        max_domain_size: int=utils.CONSTRAINT_MAX_DOMAIN_SIZE,
    ) -> None:
        # Prefix 'internal use' variables with '_', as randomized results are populated to the class
        self._random = _random
        self._random_vars = {}
        self._rand_list_lengths = defaultdict(list)
        self._constraints : List[utils.ConstraintAndVars] = []
        self._constrained_vars = set()
        self._max_iterations = max_iterations
        self._max_domain_size = max_domain_size
        self._naive_solve = True
        self._sparse_solve = True
        self._thorough_solve = True
        self._problem_changed = False

    def _get_random(self) -> random.Random:
        '''
        Internal function to get the appropriate randomization object.

        We can't store the package ``random`` in a member variable as this
        prevents pickling.

        :return: The appropriate random generator.
        '''
        if self._random is None:
            return random
        return self._random

    def set_solver_mode(self,
        naive: Optional[bool]=None,
        sparse: Optional[bool]=None,
        thorough: Optional[bool]=None,
    ) -> None:
        '''
        Disable/enable different solving steps.

        Solvers are used in the following order:
        1. Naive solve - randomizing and checking constraints.
        For some problems, it is more expedient to skip this
        step and go straight to a MultiVarProblem.
        2. Sparse solve - graph-based exporation of state space.
        Start with depth-first search, move to wider subsets
        of each level of state space until valid solution
        found.
        3. Thorough solve - use constraint solver to get
        all solutions and pick a random one.

        If a solver step is enabled it will run, if disabled
        it won't run.

        :param naive: ``True`` if naive solver should be used,
            ``False`` otherwise. Setting not changed if argument
            not provided.
        :param sparse: ``True`` if sparse solver should be used,
            ``False`` otherwise. Setting not changed if argument
            not provided.
        :param thorough: ``True`` if thorough solver should be used,
            ``False`` otherwise. Setting not changed if argument
            not provided.
        :return: ``None``
        '''
        if naive is not None:
            self._naive_solve = naive
        if sparse is not None:
            self._sparse_solve = sparse
        if thorough is not None:
            self._thorough_solve = thorough

    def add_rand_var(
        self,
        name: str,
        *,
        domain: Optional[utils.Domain]=None,
        bits: Optional[int]=None,
        fn: Optional[Callable]=None,
        args: Optional[tuple]=None,
        constraints: Optional[Iterable[utils.Constraint]]=None,
        list_constraints: Optional[Iterable[utils.Constraint]]=None,
        length: Optional[int]=None,
        rand_length: Optional[str]=None,
        order: Optional[int]=None,
        initial: Any=None,
        disable_naive_list_solver: bool=False,
    ) -> None:
        '''
        Add a random variable to the object.
        Exactly one of ``domain``, ``bits``, or ``fn`` (optionally with ``args``) must be provided
        to determine how to randomize.

        :param name: The name of this random variable.
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
            Each of these apply only to the individual values in the list, if a length is
            specified.
        :param constraints: List or tuple of constraints that apply to this random variable.
            Each of these apply across the values in the list, if a length is specified.
        :param length: Specify a length >= 0 to turn this variable into a list of random
            values. A value >= 0 means a list of that length. A zero-length list is just
            an empty list. A value of ``None`` (default) means a scalar value.
            Mutually exclusive with ``rand_length``.
        :param rand_length: Specify the name of a random variable that defines the length
            of this variable. The variable must have already been added to this instance.
            Mutually exclusive with ``length``.
        :param order: The solution order for this variable with respect to other variables.
        :param initial: Initial value to assign to the variable prior to randomizing.
        :param disable_naive_list_solver: Attempt to use a faster algorithm for solving
            list problems. May be faster, but may negatively impact quality of results.
        :return: ``None``
        :raises ValueError: If inputs are not valid.
        :raises RuntimeError: If mutually-exclusive inputs are specified together.

        :example:

        .. code-block:: python

            # Create a random object based on a random generator with seed 0
            rand_generator = random.Random(0)
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
        if name in self.__dict__:
            raise ValueError(f"random variable name '{name}' is not valid, already exists in object")
        if name in self._random_vars:
            raise ValueError(f"random variable name '{name}' is not valid, already exists in random variables")
        # rand_length and length are mutually-exclusive.
        if (length is not None) and (rand_length is not None):
            raise RuntimeError("'length' and 'rand_length' are mutually-exclusive, but both were specified")
        if length is not None and length < 0:
            raise ValueError("length was negative, must be zero or positive.")
        if rand_length is not None:
            # Indicates the length of the RandVar depends on another random variable.
            if rand_length not in self._random_vars:
                raise ValueError(f"random variable length '{name}' is not valid," \
                    " it must be the name of an existing random variable.")
            if self._random_vars[rand_length].length is not None:
                raise ValueError(f"random length '{name}' must be a scalar random" \
                " variable, but is itself a random list.")
            # Track that this variable depends on another for its length.
            self._rand_list_lengths[rand_length].append(name)
            # Ensure the order used for this variable is greater than
            # the one we depend on.
            # Ignore the user if they're wrong rather than raising an error.
            if order is None or order <= self._random_vars[rand_length].order:
                order = self._random_vars[rand_length].order + 1
        order = 0 if order is None else order
        self._random_vars[name] = RandVar(
            name=name,
            _random=self._random,
            order=order,
            domain=domain,
            bits=bits,
            fn=fn,
            args=args,
            constraints=constraints,
            list_constraints=list_constraints,
            length=length,
            rand_length=rand_length,
            max_iterations=self._max_iterations,
            max_domain_size=self._max_domain_size,
            disable_naive_list_solver=disable_naive_list_solver,
        )
        if rand_length is not None:
            # If rand_length is constrained by other vars,
            # so must the variable whose length it controls.
            if rand_length in self._constrained_vars:
                self._constrained_vars.add(name)
        self._problem_changed = True
        self.__dict__[name] = initial

    def add_constraint(self, constr: utils.Constraint, variables: Iterable[str]):
        '''
        Add an aribtrary constraint that applies to one or more variable(s).

        :param constr: A function (or callable) that accepts the random variables listed in
            ``variables`` as argument(s) and returns either ``True`` or ``False``.
            If the function returns ``True`` when passed the variables, the constraint is satisfied.
        :param variables: A tuple/list of variables affected by this constraint.
            The order matters, this order will be preserved when passing variables into the constraint.
        :return: ``None``
        :raises KeyError: If any member of ``variables`` is not a valid random variable.
        :raises TypeError: If type of ``variables`` is not str, list or tuple.

        :example:

        .. code-block:: python

            # Assume we have a RandObj called 'randobj', with random variables a, b and c
            # Add a constraint that a, b and c must be different values
            def not_equal(x, y, z):
                return (x != y) and (y != z) and (x != z)
            randobj.add_constraint(not_equal, ('a', 'b', 'c'))

            # Add a constraint that a is less than b
            randobj.add_constraint(lambda x, y: x < y, ('a', 'b'))

            # Add a constraint that c must be more than double a but less than double b
            randobj.constr(lambda a, b, c: (a * 2) < c < (b * 2), ('a', 'b', 'c'))
        '''
        if isinstance(variables, str):
            # Single-variable constraint
            self._random_vars[variables].add_constraint(constr)
        elif isinstance(variables, list) or isinstance(variables, tuple):
            if len(variables) == 1:
                # Single-variable constraint
                self._random_vars[variables[0]].add_constraint(constr)
            else:
                # Multi-variable constraint
                self._constraints.append((constr, variables))
                for var in variables:
                    if var not in self._random_vars:
                        raise KeyError(f"Variable '{var}' was not in the set of random variables!")
                    self._constrained_vars.add(var)
                    # If var constrains other variables' lengths,
                    # those other variables must also be considered
                    # as constrained.
                    if var in self._rand_list_lengths:
                        for list_var in self._rand_list_lengths[var]:
                            self._constrained_vars.add(list_var)
        else:
            raise TypeError(f"{variables=} must be of type str, tuple or list")
        self._problem_changed = True

    def pre_randomize(self) -> None:
        '''
        Called by :func:`randomize` before randomizing variables. Can be overridden to do something.

        :return: ``None``
        '''
        pass

    def randomize(
        self,
        *,
        with_values: Optional[Dict[str, Any]]=None,
        with_constraints: Optional[Iterable[utils.ConstraintAndVars]]=None,
        debug: bool=False,
    ) -> None:
        '''
        Randomizes all random variables, applying all constraints provided.
        After calling this for the first time, random variables are
        accessible as member variables.

        :return: None
        :param with_constraints: Temporary constraints for this randomization only.
            List of tuples, consisting of a constraint function and an iterable
            containing the variables it applies to.
        :param debug: ``True`` to run in debug mode. Slower, but collects
            all debug info along the way and not just the final failure.
        :raises RandomizationError: If no solution is found
            that satisfies the defined constraints.
        :raises TypeError: If types are incorrect.
        :raises ValueError: If no variables are supplied for a given constraint.
        '''
        self.pre_randomize()

        result = {}

        # Copy always-on constraints, ready to add any temporary ones
        constraints = list(self._constraints)
        constrained_vars = set(self._constrained_vars)

        # Process temporary constraints
        tmp_single_var_constraints = defaultdict(list)
        # Set to True if the problem is different from the base problem
        problem_changed = False
        if with_constraints is not None:
            for constr, vars in with_constraints:
                if not isinstance(vars, Iterable):
                    raise TypeError("with_constraints should specify a list of tuples of (constraint, Iterable[variables])")
                if not len(vars) > 0:
                    raise ValueError("Cannot add a constraint that applies to no variables")
                if len(vars) == 1:
                    # Single-variable constraint
                    tmp_single_var_constraints[vars[0]].append(constr)
                    problem_changed = True
                else:
                    # Multi-variable constraint
                    constraints.append((constr, vars))
                    for var in vars:
                        constrained_vars.add(var)
                    problem_changed = True
            # If a variable becomes constrained due to temporary multi-variable
            # constraints, we must respect single var temporary constraints too.
            for var, constrs in sorted(tmp_single_var_constraints.items()):
                if var in constrained_vars:
                    for constr in constrs:
                        constraints.append((constr, (var,)))

        # Don't allow non-determinism when iterating over a set
        constrained_vars = sorted(constrained_vars)
        # Don't allow non-determinism when iterating over a dict
        random_var_names = sorted(self._random_vars.keys())
        list_length_names = sorted(self._rand_list_lengths.keys())

        # Process concrete values - use these preferentially
        with_values = with_values if with_values is not None else {}

        # Randomize list length vars first
        for list_length_name in list_length_names:
            if list_length_name in with_values:
                length_result = with_values[list_length_name]
            else:
                tmp_constraints = tmp_single_var_constraints.get(list_length_name, [])
                length_result = self._random_vars[list_length_name].randomize(tmp_constraints, debug)
            result[list_length_name] = length_result
            for dependent_var_name in self._rand_list_lengths[list_length_name]:
                self._random_vars[dependent_var_name].set_rand_length(length_result)

        # Randomize all remaining variables once
        for name in random_var_names:
            if name in self._rand_list_lengths:
                continue
            if name in with_values:
                result[name] = with_values[name]
            else:
                tmp_constraints = tmp_single_var_constraints.get(name, [])
                result[name] = self._random_vars[name].randomize(tmp_constraints, debug)

        # If there are constraints, first try just to solve naively by randomizing the values.
        # This will be faster than constructing a MultiVarProblem if the constraints turn out
        # to be trivial. Only try this a few times so as not to waste time.
        constraints_satisfied = len(constraints) == 0
        if self._naive_solve:
            attempts = 0
            max = self._max_iterations
            while not constraints_satisfied:
                if attempts == max:
                    break
                problem = constraint.Problem()
                for var in constrained_vars:
                    problem.addVariable(var, (result[var],))
                for _constraint, variables in constraints:
                    problem.addConstraint(_constraint, variables)
                solutions = problem.getSolutions()
                if len(solutions) > 0:
                    # At least one solution was found, all is well
                    constraints_satisfied = True
                    solution = self._get_random().choice(solutions)
                    result.update(solution)
                else:
                    # No solution found, re-randomize and try again
                    # List length variables first
                    for list_length_name in list_length_names:
                        # If the length-defining variable is constrained,
                        # re-randomize it and all its dependent vars.
                        if list_length_name not in with_values and list_length_name in constrained_vars:
                            tmp_constraints = tmp_single_var_constraints.get(list_length_name, [])
                            length_result = self._random_vars[list_length_name].randomize(tmp_constraints, debug)
                            result[list_length_name] = length_result
                            # Need to re-randomize all dependent vars as their
                            # length has changed.
                            for dependent_var_name in self._rand_list_lengths[list_length_name]:
                                self._random_vars[dependent_var_name].set_rand_length(length_result)
                                tmp_constraints = tmp_single_var_constraints.get(dependent_var_name, [])
                                result[dependent_var_name] = self._random_vars[dependent_var_name].randomize(tmp_constraints, debug)
                    for var in constrained_vars:
                        # Don't re-randomize if we've specified a concrete value
                        if var in with_values:
                            continue
                        # Don't re-randomize list-length vars, those have been dealt with.
                        if var in self._rand_list_lengths:
                            continue
                        # Don't re-randomize list vars which have been re-randomized once already.
                        rand_length = self._random_vars[var].rand_length
                        if rand_length is not None and rand_length in constrained_vars:
                            continue
                        tmp_constraints = tmp_single_var_constraints.get(var, [])
                        result[var] = self._random_vars[var].randomize(tmp_constraints, debug)
                    attempts += 1

        # If constraints are still not satisfied by this point, construct a multi-variable
        # problem and solve them properly
        if not constraints_satisfied:
            if not (self._sparse_solve or self._thorough_solve):
                raise utils.RandomizationError(
                    'Naive solve failed, and sparse solve and thorough solve disabled.' \
                    ' There is no way to solve the problem.'
                )
            if problem_changed or self._problem_changed or self._multi_var_problem is None:
                multi_var_problem = MultiVarProblem(
                    self,
                    [self._random_vars[var_name] for var_name in constrained_vars],
                    constraints,
                    max_iterations=self._max_iterations,
                    max_domain_size=self._max_domain_size,
                )
                # Only 'cache' the problem if it's the base problem with no extra constraints
                if not problem_changed:
                    self._multi_var_problem = multi_var_problem
                    self._problem_changed = False
            else:
                multi_var_problem = self._multi_var_problem
            result.update(
                multi_var_problem.solve(
                    sparse=self._sparse_solve,
                    thorough=self._thorough_solve,
                    with_values=with_values,
                    debug=debug,
                )
            )

        # Update this object such that the results of randomization are available as member variables
        self.__dict__.update(result)

        self.post_randomize()

    def post_randomize(self) -> None:
        '''
        Called by :func:`randomize` after randomizing variables. Can be overridden to do something.

        :return: ``None``
        '''
        pass

    def get_results(self) -> Dict[str, Any]:
        '''
        Returns a dictionary of the results from the most recent randomization.
        This is mainly provided for testing purposes.

        Note that individual variables can be accessed as member variables of
        a RandObj instance, e.g.

        .. code-block:: python

            randobj = RandObj()
            randobj.add_rand_var('a', domain=range(10))
            randobj.randomize()
            print(randobj.a)

        :return: dictionary of the results from the most recent randomization.
        '''
        # Return a new dict object rather than a reference to this object's __dict__
        return {k: self.__dict__[k] for k in self._random_vars.keys()}

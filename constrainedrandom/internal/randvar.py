# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

import constraint
from functools import partial
from itertools import product
from typing import Any, Callable, Iterable, List, Optional
import random

from .. import utils
from ..debug import RandomizationDebugInfo, RandomizationFail
from ..random import dist


def get_and_call(getter: Callable, member_fn: str, *args: List[Any]):
    '''
    This is a very strange workaround for a very strange issue.
    ``copy.deepcopy`` can handle a ``partial`` for all other members
    of ``random.Random``, but not ``getrandbits``. I.e. it correctly
    copies the other functions and their instance of ``random.Random``,
    but not ``getrandbits``. The reason for this is unknown.

    This function therefore exists to work around that issue
    by getting ``getrandbits`` and calling it. I tried many
    other approaches, but this was the only one that worked.

    :param getter: Getter to call, returning an object that
        has a member function with name ``member_fn``.
    :param member_fn: Member function of the the object returned
        by ``getter``.
    :param args: Arguments to supply to ``member_fn``.
    '''
    callable_obj = getter()
    fn = getattr(callable_obj, member_fn)
    return fn(*args)


class RandVar:
    '''
    Randomizable variable. For internal use with :class:`RandObj`.

    :param name: The name of this random variable.
    :param _random: Provides the random generator object this instance will use to
        create random values. Either provide an existing instance of a :class:`Random`,
        or leave as ``None`` to use the global Python `random` package.
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
        Each of these apply only to the individual values in the list, if a length is
        specified.
    :param constraints: List or tuple of constraints that apply to this random variable.
        Each of these apply across the values in the list, if a length is specified.
    :param length: Specify a length >= 0 to turn this variable into a list of random
        values. A value >= 0 means a list of that length. A zero-length list is just
        an empty list. A value of ``None`` (default) means a scalar value.
    :param rand_length: Specify the name of a random variable that defines the length
        of this variable. The variable must have already been added to this instance.
    :param max_iterations: The maximum number of failed attempts to solve the randomization
        problem before giving up.
    :param max_domain_size: The maximum size of domain that a constraint satisfaction problem
        may take. This is used to avoid poor performance. When a problem exceeds this domain
        size, we don't use the ``constraint`` package, but just use ``random`` instead.
    :param disable_naive_list_solver: Attempt to use a faster algorithm for solving
        list problems. May be faster, but may negatively impact quality of results.
    :raises RuntimeError: If mutually-excliusive args are used together.
    :raises TypeError: If wrong types are used.
    '''

    def __init__(self,
        name: str,
        *,
        _random: Optional[random.Random]=None,
        order: int=0,
        domain: Optional[utils.Domain]=None,
        bits: Optional[int]=None,
        fn: Optional[Callable]=None,
        args: Optional[tuple]=None,
        constraints: Optional[Iterable[utils.Constraint]]=None,
        list_constraints: Optional[Iterable[utils.Constraint]]=None,
        length: Optional[int]=None,
        rand_length: Optional[str]=None,
        max_iterations: int,
        max_domain_size: int,
        disable_naive_list_solver: bool,
    ) -> None:
        self._random = _random
        self.name = name
        self.order = order
        self.length = length
        self.rand_length = rand_length
        self.rand_length_val = None
        if (length is not None) and (rand_length is not None):
            raise RuntimeError("'length' and 'rand_length' are mutually-exclusive, but both were specified.")
        self.max_iterations = max_iterations
        self.max_domain_size = max_domain_size
        if not (((domain is not None) != (fn is not None)) != (bits is not None)):
            raise RuntimeError("The user must specify exactly one of 'fn', 'domain' or 'bits', but more than one was specified.")
        if fn is None:
            if args is not None:
                raise RuntimeError("'args' has no effect without 'fn', but was provided without 'fn'")
        self.domain = domain
        self.bits = bits
        self.fn = fn
        self.args = args
        self.constraints = constraints if constraints is not None else []
        if not (isinstance(self.constraints, list) or isinstance(self.constraints, tuple)):
            raise TypeError("constraints was bad type, should be list or tuple")
        if not isinstance(self.constraints, list):
            self.constraints = list(self.constraints)
        self.list_constraints = list_constraints if list_constraints is not None else []
        if not (isinstance(self.list_constraints, list) or isinstance(self.list_constraints, tuple)):
            raise TypeError("list_constraints was bad type, should be list or tuple")
        if not isinstance(self.list_constraints, list):
            self.list_constraints = list(self.list_constraints)
        # Default strategy is to randomize and check the constraints.
        # List constraints are always checked.
        self.check_constraints = len(self.constraints) > 0
        self.randomizer = self.create_randomizer()
        self.disable_naive_list_solver = disable_naive_list_solver

    def create_randomizer(self) -> Callable:
        '''
        Creates a randomizer function that returns an appropriate
        random value for a single instance of the variable, i.e. a single
        element of a list or a simple scalar variable.
        We do this to create a more optimal randomizer than the user might
        have specified that is functionally equivalent.

        We always return a ``partial`` because these work with
        ``copy.deepcopy``, whereas locally-defined functions and
        lambdas can only ever have one instance.

        :return: a function as described.
        :raises TypeError: if the domain is of a bad type.
        '''
        # self.fn, self.bits and self.domain should already be guaranteed
        # to be mutually exclusive - only one should be non-None.
        if self.fn is not None:
            if self.args is not None:
                return partial(self.fn, *self.args)
            else:
                return self.fn
        if self.bits is not None:
            # Convert this to a range-based domain.
            self.domain = range(0, 1 << self.bits)
            # If sufficiently small, let this fall through to the general case,
            # to optimize randomization w.r.t. constraints.
            # The maximum size of range that Python can handle (in CPython)
            # when using size_tis 62 bits, as it uses signed 64-bit integers
            # and the top of the range is expressed as 1 << bits, i.e.
            # requiring one extra bit to store.
            if self.bits >= 63:
                # Ideally here we would use:
                # return partial(self._get_random().getrandbits, self.bits)
                # as it seems that getrandbits is 10x faster than randrange.
                # However, there is a very strange interaction between deepcopy
                # and random that prevents this. See get_and_call for details.
                # This solution is still faster than a partial with randrange.
                return partial(get_and_call, self._get_random, 'getrandbits', self.bits)
        # Handle possible types of domain.
        is_range = isinstance(self.domain, range)
        is_list_or_tuple = isinstance(self.domain, list) or isinstance(self.domain, tuple)
        is_dict = isinstance(self.domain, dict)
        # Range, list and tuple are handled nicely by the constraint package.
        # Other Iterables may not be, e.g. enum.Enum isn't, despite being an Iterable.
        is_iterable = isinstance(self.domain, Iterable)
        if is_iterable and not (is_range or is_list_or_tuple or is_dict):
            # Convert non-dict iterables to a tuple as we don't expect them to need to be mutable,
            # and tuple ought to be slightly more performant than list.
            try:
                self.domain = tuple(self.domain)
            except TypeError:
                raise TypeError(f'RandVar was passed a domain of bad type - {self.domain}. '
                                'This was an Iterable but could not be converted to tuple.')
            is_list_or_tuple = True

        # If we are provided a sufficiently small domain and we have constraints,
        # simply construct a constraint solution problem and choose randomly from the
        # possible solutions.
        if self.check_constraints and (is_range or is_list_or_tuple) and len(self.domain) < self.max_domain_size:
            problem = constraint.Problem()
            problem.addVariable(self.name, self.domain)
            for con in self.constraints:
                problem.addConstraint(con, (self.name,))

            # This call to getSolutions may fail, as we are running it sooner
            # than the user knows. The user expects the constraint only to be
            # called during randomization, but this function will be called
            # when adding new constraints.
            # Allow for it failing, and move on to the other ways to generate
            # a randomizer if it does.
            try:
                solutions = problem.getSolutions()
            except:
                solutions = None

            if solutions is not None:
                # If we can't get any solutions, it's an intractable problem.
                if len(solutions) == 0:
                    debug_fail = RandomizationFail([self.name],
                        [(c, (self.name,)) for c in self.constraints])
                    debug_info = RandomizationDebugInfo()
                    debug_info.add_failure(debug_fail)
                    raise utils.RandomizationError("Variable was unsolvable. Check constraints.", debug_info)
                # getSolutions produces a list of dictionaries - index it
                # up front for very marginal performance gains
                solution_list = [s[self.name] for s in solutions]
                self.check_constraints = False
                return partial(self._get_random().choice, solution_list)

        # Fall through to a standard randomizer which randomizes and checks.
        if self.bits is not None:
            # Ideally here we would use:
            # return partial(self._get_random().getrandbits, self.bits)
            # as it seems that getrandbits is 10x faster than randrange.
            # However, there is a very strange interaction between deepcopy
            # and random that prevents this. See get_and_call for details.
            # This solution is still faster than a partial with randrange.
            return partial(get_and_call, self._get_random, 'getrandbits', self.bits)
        elif is_range:
            return partial(self._get_random().randrange, self.domain.start, self.domain.stop)
        elif is_list_or_tuple:
            return partial(self._get_random().choice, self.domain)
        elif is_dict:
            rand = self._get_random()
            if rand is random:
                # Don't store a module in a partial as this can't be copied.
                # dist defaults to using the global random module.
                return partial(dist, self.domain)
            return partial(dist, self.domain, rand)
        else:
            raise TypeError(f'RandVar was passed a domain of a bad type - {self.domain}. '
                            'Domain should be a range, list, tuple, dictionary or other Iterable.')

    def add_constraint(self, constr: utils.Constraint) -> None:
        '''
        Add a single constraint to this variable.

        :param constr: Constraint to add.
        '''
        length = self.get_length()
        if length is not None:
            # Treat all additional constraints as list constraints,
            # although this is a little less performant.
            self.list_constraints.append(constr)
        else:
            # For adding scalar constraints, reevalute whether we can
            # still use a CSP - recreate the randomizer.
            self.constraints.append(constr)
            self.check_constraints = True
            self.randomizer = self.create_randomizer()

    def get_length(self) -> int:
        '''
        Function to get the length of the random list.

        :return: The length of the list.
        '''
        if self.rand_length is None:
            return self.length
        if self.rand_length_val is None:
            raise RuntimeError("RandVar was marked as having a random length," \
                " but none was given when get_length was called.")
        return self.rand_length_val

    def is_list(self) -> bool:
        '''
        Returns ``True`` if this is a list variable.

        :return: ``True`` if this is a list variable, otherwise ``False``.
        '''
        return self.length is not None or self.rand_length is not None

    def set_rand_length(self, length: int) -> None:
        '''
        Function to set the random length.

        Should only be used when this ``RandVar``
        instance is indicated to have a random length
        that depends on another variable.

        :raises RuntimeError: If this variable instance is not
            marked as one with a random length.
        :raises ValueError: If random length is negative.
        '''
        if self.rand_length is None:
            raise RuntimeError("RandVar was not marked as having a random length," \
                " but set_rand_length was called.")
        if length < 0:
            raise ValueError(f"Random list length was negative for variable '{self.name}'.")
        self.rand_length_val = length

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

    def get_domain_size(self, possible_lengths: Optional[List[int]]=None) -> int:
        '''
        Return total domain size, accounting for length of this random variable.

        :param possible_lengths: Optional, when there is more than one possiblity
            for the value of the random length, specifies a list of the
            possibilities.
        :return: domain size, integer.
        '''
        if self.domain is None:
            # If there's no domain, it means we can't estimate the complexity
            # of this variable. Return 1.
            return 1
        else:
            # possible_lengths is used when the variable has a random
            # length and that length is not yet fully determined.
            if possible_lengths is None:
                # Normal, fixed length of some description.
                length = self.get_length()
                if length is None:
                    # length is None implies a scalar variable.
                    return len(self.domain)
                elif length == 0:
                    # This is a zero-length list, adding no complexity.
                    return 1
                elif length == 1:
                    return len(self.domain)
                else:
                    # In this case it is effectively cartesian product, i.e.
                    # n ** k, where n is the size of the domain and k is the length
                    # of the list.
                    return len(self.domain) ** length
            else:
                # Random length which could be one of a number of values.
                assert self.rand_length is not None, "Cannot use possible_lengths " \
                    "for a variable with non-random length."
                # For each possible length, the domain is the cartesian
                # product as above, but added together.
                total = 0
                for poss_len in possible_lengths:
                    total += len(self.domain) ** poss_len
                return total

    def can_use_with_constraint(self) -> bool:
        '''
        Check whether this random variable can be used in a
        ``constraint.Problem`` or not.
        Note this isn't depenedent on the domain size, just
        purely whether it will work.

        :return: bool, True if it can be used with ``constraint.Problem``.
        '''
        # constraint can handle the variable as long as it has a domain
        # and the domain isn't a dictionary.
        return self.domain is not None and not isinstance(self.domain, dict)

    def get_constraint_domain(self, possible_lengths: Optional[List[int]]=None) -> utils.Domain:
        '''
        Get a ``constraint`` package friendly version of the domain
        of this random variable.

        :param possible_lengths: Optional, when there is more than one possiblity
            for the value of the random length, specifies a list of the
            possibilities.
        :return: the variable's domain in a format that will work
            with the ``constraint`` package.
        '''
        if possible_lengths is None:
            length = self.get_length()
            if length is None:
                # Straightforward, scalar
                return self.domain
            elif length == 0:
                # List of length zero - an empty list is only correct choice.
                return [[]]
            elif length == 1:
                # List of length one
                return [[x] for x in self.domain]
            else:
                # List of greater length, cartesian product.
                # Beware that this may be an extremely large domain.
                # Ensure each element is of type list, which is what
                # we want to return.
                return [list(x) for x in product(self.domain, repeat=length)]
        else:
            # For each possible length, return the possible domains.
            # This can get extremely large, even more so than
            # the regular product.
            result = []
            for poss_len in possible_lengths:
                result += [list(x) for x in product(self.domain, repeat=poss_len)]
            return result

    def randomize_once(self, constraints: Iterable[utils.Constraint], check_constraints: bool, debug: bool) -> Any:
        '''
        Get one random value that satisfies the constraints.

        :param constraints: The constraints that apply to this randomization.
        :param check_constraints: Whether constraints need to be checked.
        :param debug: ``True`` to run in debug mode. Slower, but collects
            all debug info along the way and not just the final failure.
        :return: A random value for the variable, respecting the constraints.
        :raises RandomizationError: When the problem cannot be solved in fewer than
            the allowed number of iterations.
        '''
        value = self.randomizer()
        if not check_constraints:
            return value
        value_valid = False
        iterations = 0
        if debug:
            # Collect failures as we go along
            debug_fail = RandomizationFail([self.name],
                [(c, (self.name,)) for c in constraints])
        while not value_valid:
            if iterations == self.max_iterations:
                if not debug:
                    # Just capture the most recent value
                    debug_fail = RandomizationFail([self.name],
                        [(c, (self.name,)) for c in constraints])
                debug_fail.add_values(iterations, {self.name: value})
                debug_info = RandomizationDebugInfo()
                debug_info.add_failure(debug_fail)
                raise utils.RandomizationError("Too many iterations, can't solve problem", debug_fail)
            problem = constraint.Problem()
            problem.addVariable(self.name, (value,))
            for con in constraints:
                problem.addConstraint(con, (self.name,))
            value_valid = problem.getSolution() is not None
            if not value_valid:
                if debug:
                    # Capture all failing values as we go
                    debug_fail.add_values(iterations, {self.name: value})
                value = self.randomizer()
            iterations += 1
        return value

    def randomize_list_csp(
        self,
        constraints: Iterable[utils.Constraint],
        list_constraints: Iterable[utils.Constraint],
    ):
        '''
        Use a CSP to get a full set of soltuons for the random list,
        fulfilling the constraints. Selects and returns one randomization.
        Should only be used when the domain is suitably small.

        :param constraints: The constraints that apply to this randomization.
            These are scalar constraints, i.e. on each individual element of
            the list.
        :param list_constraints: The constraints that apply to the entire list.
        :return: A random list of values for the variable, respecting
            the constraints.
        '''
        problem = constraint.Problem()
        possible_values = self.get_constraint_domain()
        # Prune possibilities according to scalar constraints.
        possible_values = [x for x in possible_values \
            if all(constr(val) for val in x for constr in constraints)]
        problem.addVariable(self.name, possible_values)
        for con in list_constraints:
            problem.addConstraint(con, (self.name,))
        solutions = problem.getSolutions()
        if len(solutions) == 0:
            debug_fail = RandomizationFail([self.name],
                [(con, (self.name,)) for con in list_constraints])
            debug_info = RandomizationDebugInfo()
            debug_info.add_failure(debug_fail)
            raise utils.RandomizationError("Problem was unsolvable.", debug_info)
        values = self._get_random().choice(solutions)[self.name]
        return values

    def randomize_list_naive(
        self,
        constraints: Iterable[utils.Constraint],
        check_constraints: bool,
        list_constraints: Iterable[utils.Constraint],
        debug: bool,
        debug_fail: Optional[RandomizationFail],
    ):
        '''
        Naive algorithm to randomize a random list of values, and check
        it against the constraints. Faster than CSP as long as it's a simple
        problem. Prone to failure.

        :param constraints: The constraints that apply to this randomization.
            These are scalar constraints, i.e. on each individual element of
            the list.
        :param check_constraints: Whether constraints need to be checked.
        :param list_constraints: The constraints that apply to the entire list.
        :param debug: ``True`` to run in debug mode. Slower, but collects
            all debug info along the way and not just the final failure.
        :param debug_fail: :class:`RandomizationFail` containing debug info,
            if in debug mode, else ``None``.

        :return: A random list of values for the variable, respecting
            the constraints.
        '''
        length = self.get_length()
        values = [self.randomize_once(constraints, check_constraints, debug) \
            for _ in range(length)]
        values_valid = len(list_constraints) == 0
        iterations = 0
        max_iterations = self.max_iterations
        while not values_valid:
            if iterations >= max_iterations:
                # This method has failed.
                return None
            problem = constraint.Problem()
            problem.addVariable(self.name, (values,))
            for con in list_constraints:
                problem.addConstraint(con, (self.name,))
            values_valid = problem.getSolution() is not None
            if not values_valid:
                if debug:
                    # Capture all failing values as we go
                    debug_fail.add_values(iterations, {self.name: values})
                iterations += 1
                values = [self.randomize_once(constraints, check_constraints, debug) \
                    for _ in range(length)]
        return values

    def randomize_list_subset(
        self,
        constraints: Iterable[utils.Constraint],
        check_constraints: bool,
        list_constraints: Iterable[utils.Constraint],
        debug : bool,
        debug_fail: Optional[RandomizationFail],
    ):
        '''
        Algorithm that attempts to ensure forward progress when randomizing
        a random list. Over-constrains the problem slightly. Aims to converage
        quickly while still giving good quality of results.

        :param constraints: The constraints that apply to this randomization.
            These are scalar constraints, i.e. on each individual element of
            the list.
        :param check_constraints: Whether constraints need to be checked.
        :param list_constraints: The constraints that apply to the entire list.
        :param debug: ``True`` to run in debug mode. Slower, but collects
            all debug info along the way and not just the final failure.
        :param debug_fail: :class:`RandomizationFail` containing debug info,
            if in debug mode, else ``None``.
        :return: A random list of values for the variable, respecting
            the constraints.
        :raises RandomizationError: When the problem cannot be solved in fewer than
            the allowed number of iterations.
        '''
        length = self.get_length()
        values = [self.randomize_once(constraints, check_constraints, debug) \
            for _ in range(length)]
        values_valid = len(list_constraints) == 0
        iterations = 0
        # Allow more attempts at a list, as it may be computationally hard.
        # Assume it's linearly harder.
        max_iterations = self.max_iterations * length
        checked = []
        while not values_valid:
            iterations += 1
            if iterations >= max_iterations:
                if not debug:
                    # Create the debug info 'late', only capturing the final
                    # set of values.
                    debug_fail = RandomizationFail([self.name],
                        [(c, (self.name,)) for c in list_constraints])
                debug_fail.add_values(iterations, {self.name: values})
                debug_info = RandomizationDebugInfo()
                debug_info.add_failure(debug_fail)
                raise utils.RandomizationError("Too many iterations, can't solve problem", debug_info)
            # Keep a subset of the answer, to try to ensure forward progress.
            min_group_size = len(checked) + 1
            for idx in range(min_group_size, length):
                tmp_values = values[:idx]
                problem = constraint.Problem()
                problem.addVariable(self.name, (tmp_values,))
                for con in list_constraints:
                    problem.addConstraint(con, (self.name,))
                # This may fail if the user is relying on the
                # list being fully-sized in their constraint.
                try:
                    tmp_values_valid = problem.getSolution() is not None
                except Exception:
                    tmp_values_valid = False
                if tmp_values_valid:
                    # Use these values and continue this loop,
                    # adding to the checked values if more
                    # values satisfy the constraints.
                    # Check the entire list to ensure maximum
                    # degrees of freedom.
                    checked = tmp_values
            values = checked + [self.randomize_once(constraints, check_constraints, debug) \
                for _ in range(length - len(checked))]
            problem = constraint.Problem()
            problem.addVariable(self.name, (values,))
            for con in list_constraints:
                problem.addConstraint(con, (self.name,))
            values_valid = problem.getSolution() is not None
            if debug and not values_valid:
                # Capture failure info as we go along
                debug_fail.add_values(iterations, {self.name: values})
        return values

    def randomize(
        self,
        temp_constraints: Optional[Iterable[utils.Constraint]]=None,
        debug: bool=False,
    ) -> Any:
        '''
        Returns a random value based on the definition of this random variable.
        Does not modify the state of the :class:`RandVar` instance.

        :param temp_constraints: Temporary constraints to apply only for
            this randomization.
        :return: A randomly generated value, conforming to the definition of
            this random variable, its constraints, etc.
        :raises RandomizationError: When the problem cannot be solved in fewer than
            the allowed number of iterations.
        '''
        check_constraints = self.check_constraints
        # Handle temporary constraints. Start with copy of existing constraints,
        # adding any temporary ones in.
        constraints = list(self.constraints)
        using_temp_constraints = temp_constraints is not None and len(temp_constraints) > 0
        length = self.get_length()
        if length is None:
            # Interpret temporary constraints as scalar constraints
            if using_temp_constraints:
                check_constraints = True
                constraints += temp_constraints
            return self.randomize_once(constraints, check_constraints, debug)
        else:
            list_constraints = list(self.list_constraints)
            # Interpret temporary constraints as list constraints
            if using_temp_constraints:
                list_constraints += temp_constraints
            # Create list of values and check after that list constraints
            # are followed.
            # We can't check as we go along as this artificially limits
            # the values that can be selected. E.g. if you have a constraint
            # that says the values sum to zero, you would only ever
            # end up with an all-zero list if you enforced the constraint
            # at each iteration.
            # Try to construct a constraint solution problem, if possible.
            check_list_constraints = len(list_constraints) > 0
            use_csp = check_list_constraints and self.can_use_with_constraint() \
                    and self.get_domain_size() <= self.max_domain_size
            if use_csp:
                return self.randomize_list_csp(constraints, list_constraints)
            else:
                # Otherwise, just randomize and check.
                if debug:
                    # Collect failures as we go along
                    debug_fail = RandomizationFail([self.name],
                        [(c, (self.name,)) for c in list_constraints])
                else:
                    debug_fail = None
                # Start by purely randomizing and checking, unless
                # naive mode disabled.
                if not self.disable_naive_list_solver:
                    values = self.randomize_list_naive(constraints, \
                        check_constraints, list_constraints, debug, debug_fail)
                    if values is not None:
                        return values
                # If the above fails, use a slightly smarter algorithm,
                # which is more likely to make forward progress, but
                # might also restrict value selection.
                # No fallback if this fails.
                return self.randomize_list_subset(constraints, \
                    check_constraints, list_constraints, debug, debug_fail)

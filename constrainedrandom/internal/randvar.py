# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

import constraint
from functools import partial
from typing import Any, Callable, Iterable, Optional, Union
import random

from .. import utils
from ..random import dist


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
    :param max_iterations: The maximum number of failed attempts to solve the randomization
        problem before giving up.
    :param max_domain_size: The maximum size of domain that a constraint satisfaction problem
        may take. This is used to avoid poor performance. When a problem exceeds this domain
        size, we don't use the ``constraint`` package, but just use ``random`` instead.
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
        max_iterations: int,
        max_domain_size:int,
    ) -> None:
        self._random = _random
        self.name = name
        self.order = order
        self.max_iterations = max_iterations
        self.max_domain_size = max_domain_size
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
            self.randomizer = partial(self._get_random().getrandbits, self.bits)
            self.domain = range(0, 1 << self.bits)
        else:
            # Handle possible types.
            is_range = isinstance(self.domain, range)
            is_list_or_tuple = isinstance(self.domain, list) or isinstance(self.domain, tuple)
            is_dict = isinstance(self.domain, dict)
            # Range, list and tuple are handled nicely by constraint. Other Iterables may not be,
            # e.g. enum.Enum isn't, despite being an Iterable.
            is_iterable = isinstance(self.domain, Iterable)
            if is_iterable and not (is_range or is_list_or_tuple or is_dict):
                # Convert non-dict iterables to a tuple as we don't expect them to need to be mutable,
                # and tuple ought to be slightly more performant than list.
                try:
                    self.domain = tuple(self.domain)
                except TypeError:
                    raise TypeError(f'RandVar was passed a domain of bad type - {domain}. This was an Iterable but could not be converted to tuple.')
                is_list_or_tuple = True
            if self.check_constraints and (is_range or is_list_or_tuple) and len(self.domain) < self.max_domain_size:
                # If we are provided a sufficiently small domain and we have constraints, simply construct a
                # constraint solution problem instead.
                problem = constraint.Problem()
                problem.addVariable(self.name, self.domain)
                for con in self.constraints:
                    problem.addConstraint(con, (self.name,))
                # Produces a list of dictionaries
                solutions = problem.getSolutions()
                def solution_picker(solns):
                    return self._get_random().choice(solns)[self.name]
                self.randomizer = partial(solution_picker, solutions)
                self.check_constraints = False
            elif is_range:
                self.randomizer = partial(self._get_random().randrange, self.domain.start, self.domain.stop)
            elif is_list_or_tuple:
                self.randomizer = partial(self._get_random().choice, self.domain)
            elif is_dict:
                self.randomizer = partial(dist, self.domain, self._get_random())
            else:
                raise TypeError(f'RandVar was passed a domain of a bad type - {self.domain}. Domain should be a range, list, tuple, dictionary or other Iterable.')

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

    def randomize(self, temp_constraints:Union[Iterable[utils.Constraint], None]=None) -> Any:
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
        value = self.randomizer()
        check_constraints = self.check_constraints
        # Handle temporary constraints. Start with copy of existing constraints,
        # adding any temporary ones in.
        constraints = list(self.constraints)
        if temp_constraints is not None and len(temp_constraints) > 0:
            check_constraints = True
            constraints += temp_constraints
        value_valid = not check_constraints
        iterations = 0
        while not value_valid:
            if iterations == self.max_iterations:
                raise utils.RandomizationError("Too many iterations, can't solve problem")
            problem = constraint.Problem()
            problem.addVariable(self.name, (value,))
            for con in constraints:
                problem.addConstraint(con, (self.name,))
            value_valid = problem.getSolution() is not None
            if not value_valid:
                value = self.randomizer()
            iterations += 1
        return value

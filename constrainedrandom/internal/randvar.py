# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

import constraint
from functools import partial
from typing import Any, Callable, Iterable, Optional, TYPE_CHECKING

from constrainedrandom import types

if TYPE_CHECKING:
    from constrainedrandom.randobj import RandObj


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
    :param max_domain_size: The maximum size of domain that a constraint satisfaction problem
        may take. This is used to avoid poor performance. When a problem exceeds this domain
        size, we don't use the ``constraint`` package, but just use ``random`` instead.
    '''

    def __init__(self,
        parent: 'RandObj',
        name: str,
        order: int,
        *,
        domain: Optional[types.Domain]=None,
        bits: Optional[int]=None,
        fn: Optional[Callable]=None,
        args: Optional[tuple]=None,
        constraints: Optional[Iterable[types.Constraint]]=None,
        max_iterations: int,
        max_domain_size:int,
    ) -> None:
        self.parent = parent
        self.random = self.parent._random
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
            self.randomizer = partial(self.random.getrandbits, self.bits)
            self.domain = range(0, 1 << self.bits)
        else:
            # If we are provided a sufficiently small domain and we have constraints, simply construct a
            # constraint solution problem instead.
            is_range = isinstance(self.domain, range)
            is_list = isinstance(self.domain, list) or isinstance(self.domain, tuple)
            is_dict = isinstance(self.domain, dict)
            if self.check_constraints and len(self.domain) < self.max_domain_size and (is_range or is_list):
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
# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

import constraint
from functools import cached_property
from typing import Any, Dict, List, Tuple, TYPE_CHECKING, Union

from .. import utils
from ..debug import RandomizationDebugInfo, RandomizationFail

if TYPE_CHECKING:
    from ..internal.randvar import RandVar


class VarGroup:
    '''
    Represents a group of random variables to be solved together.

    Determines which variables in the group can be solved via a
    constraint problem and which ones must be randomized and checked.
    (Used internally by :class:`MultiVarProblem`).

    :param group: List of random variables in this group.
    :param solved vars: List of variable names that are already solved.
    :param problem: Constraint problem to add variables and constraints to.
        Note that the instance will be modified by this function.
    :param constraints: Constraints that still apply at this stage of
        solving the problem.
    :param max_domain_size: The maximum size of domain that a constraint satisfaction problem
        may take. This is used to avoid poor performance. When a problem exceeds this domain
        size, we don't use the ``constraint`` package, but just use ``random`` instead.
    :param debug: ``True`` to run in debug mode. Slower, but collects
        all debug info along the way and not just the final failure.
    :return: A tuple of 1) a list the names of the variables in the group,
        2) a list of variables that must be randomized rather than solved
        via a constraint problem,
        3) a list of constraints and variables that won't be applied for this group.
    '''

    def __init__(
        self,
        group: List['RandVar'],
        solved_vars: List[str],
        problem: constraint.Problem,
        constraints: List[utils.ConstraintAndVars],
        max_domain_size: int,
        debug: bool,
    ) -> None:
        self.group_vars: List[str] = []
        self.rand_vars: List['RandVar'] = []
        self.raw_constraints: List[utils.ConstraintAndVars] = []
        self.problem = problem
        self.max_domain_size = max_domain_size
        self.debug = debug

        # Construct a constraint problem where possible. A variable must have a domain
        # in order to be part of the problem. If it doesn't have one, it must just be
        # randomized. Also take care not to exceed tha maximum domain size for an
        # individual variable.
        for var in group:
            self.group_vars.append(var.name)
            if var.can_use_with_constraint() and var.get_domain_size() < self.max_domain_size:
                self.problem.addVariable(var.name, var.get_constraint_domain())
                # If variable has its own constraints, these must be added to the problem,
                # regardless of whether var.check_constraints is true, as the var's value will
                # depend on the value of the other constrained variables in the problem.
                for con in var.constraints:
                    self.problem.addConstraint(con, (var.name,))
                    self.raw_constraints.append((con, (var.name,)))
            else:
                self.rand_vars.append(var)

        # Add all pertinent constraints
        self.skipped_constraints = []
        for (con, vars) in constraints:
            skip = False
            for var in vars:
                if var not in self.group_vars and var not in solved_vars:
                    # Skip this constraint
                    skip = True
                    break
            if skip:
                self.skipped_constraints.append((con, vars))
                continue
            self.problem.addConstraint(con, vars)
            self.raw_constraints.append((con, vars))

    @cached_property
    def debug_fail(self):
        '''
        Cached property, instance of ``RandomizationFail`` that
        corresponds to this problem.
        '''
        failing_constraints = list(self.raw_constraints)
        for var in self.rand_vars:
            failing_constraints += [(constr, (var.name,)) for constr in var.constraints]
        return RandomizationFail(list(self.group_vars), failing_constraints)

    def can_retry(self):
        '''
        Call this to determine whether or not retrying ``solve``
        can have a different outcome.

        :return: ``True`` if calling ``solve`` again might yield
            a different result (assuming it has already been called.)
            ``False`` otherwise.
        '''
        return len(self.rand_vars) > 0

    def solve(
        self,
        max_iterations: int,
        solutions_per_group: int,
        debug_info: RandomizationDebugInfo,
    ) -> Union[List[Dict[str, Any]], None]:
        '''
        Attempts to solve one group of variables. Preferentially uses a constraint
        satisfaction problem, but may need to randomize variables that can't be
        added to a constraint satisfaction problem.
        (Used internally by :class:`MultiVarProblem`).

        :param max_iterations: Maximum number of attempts to solve the problem
            before giving up.
        :solutions_per_group: How many random values to produce before attempting
            to solve the constraint satisfaction problem. A lower value will run
            quicker but has less chance to succeed.
        :param debug_info: :class:`RandomizationDebugInfo`` instance to collect
            any debug info.
        :return: A list of all possible solutions for the group, or ``None`` if
            it can't be solved within ``max_iterations`` attempts.
        '''
        # Problem is ready to solve, apart from random variables
        solutions = []
        attempts = 0
        if len(self.rand_vars) > 0:
            # If we have additional random variables, randomize and check
            while True:
                for var in self.rand_vars:
                    # Add random variables in with a concrete value
                    if solutions_per_group == 1:
                        self.problem.addVariable(var.name, (var.randomize(),))
                    else:
                        iterations = self.max_domain_size if solutions_per_group is None else solutions_per_group
                        var_domain = set()
                        for _ in range(iterations):
                            var_domain.add(var.randomize())
                        self.problem.addVariable(var.name, sorted(var_domain))
                solutions = self.problem.getSolutions()
                if len(solutions) > 0:
                    break
                else:
                    attempts += 1
                    # Always output debug info on the last attempt.
                    failed = attempts >= max_iterations
                    debug = self.debug or (solutions_per_group is None and failed)
                    for var in self.rand_vars:
                        # Remove from problem, they will be re-added with different concrete values
                        del self.problem._variables[var.name]
                    if debug:
                        self.debug_fail.add_values(attempts, dict(self.problem._variables))
                    if failed:
                        # We have failed, give up
                        debug_info.add_failure(self.debug_fail)
                        return None

        else:
            # Otherwise, just get the solutions, no randomization required.
            solutions = self.problem.getSolutions()
            if len(solutions) == 0:
                # Failed
                debug_info.add_failure(self.debug_fail)
                return None

        return solutions

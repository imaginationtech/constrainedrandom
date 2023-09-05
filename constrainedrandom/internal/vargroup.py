# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

import constraint
from functools import cached_property
from typing import Any, Dict, List, TYPE_CHECKING, Union

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
    :param solution_space: Dictionary of possible values for each
        solved variable in the problem. Solved variables as dict keys,
        lists of possible values as dict values.
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
        solution_space: Dict[str, List[Any]],
        constraints: List[utils.ConstraintAndVars],
        max_domain_size: int,
        debug: bool,
    ) -> None:
        self.solution_space = solution_space
        self.group_vars: List[str] = []
        self.rand_vars: List['RandVar'] = []
        self.raw_constraints: List[utils.ConstraintAndVars] = []
        self.problem = constraint.Problem()
        self.max_domain_size = max_domain_size
        self.debug = debug

        # Respect already-solved values when solving the constraint problem.
        for var_name, values in self.solution_space.items():
            self.problem.addVariable(var_name, values)

        # Construct a constraint problem where possible. A variable must have a domain
        # in order to be part of the problem. If it doesn't have one, it must just be
        # randomized. Also take care not to exceed tha maximum domain size for an
        # individual variable.
        for var in group:
            self.group_vars.append(var.name)

            # Consider whether this variable has random length.
            possible_lengths = None
            if var.rand_length is not None:
                # Variable has a random length.
                # We guarantee that the random length variable will be solved
                # before this one, if it is even part of the problem.
                # If it's not in solution_space, we've already chosen the value
                # for it and set the random length based on it.
                if var.rand_length in self.solution_space:
                    # Deal with potential values.
                    possible_lengths = self.solution_space[var.rand_length]
                    # Create a constraint that the length must be defined
                    # by the other variable.
                    len_constr = lambda listvar, length : len(listvar) == length
                    self.problem.addConstraint(len_constr, (var.name, var.rand_length))
                    self.raw_constraints.append((len_constr, (var.name, var.rand_length)))

            # Either add to constraint problem with full domain,
            # or treat it as a variable to be randomized.
            if (var.can_use_with_constraint() and
                var.get_domain_size(possible_lengths) < self.max_domain_size):
                self.problem.addVariable(var.name, var.get_constraint_domain(possible_lengths))
                # If variable has its own constraints, these must be added to the problem,
                # regardless of whether var.check_constraints is true, as the var's value will
                # depend on the value of the other constrained variables in the problem.
                if var.is_list():
                    # Add list constraints, and add wrapped scalar constraints.
                    for list_con in var.list_constraints:
                        self.problem.addConstraint(list_con, (var.name,))
                        self.raw_constraints.append((list_con, (var.name,)))
                    for con in var.constraints:
                        wrapped_con = lambda listvar, _con=con : all([_con(x) for x in listvar])
                        self.problem.addConstraint(wrapped_con, (var.name,))
                        self.raw_constraints.append((wrapped_con, (var.name,)))
                else:
                    # Just add regular constraints.
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
                if var not in self.group_vars and var not in solution_space:
                    # Skip this constraint
                    skip = True
                    break
            if skip:
                self.skipped_constraints.append((con, vars))
                continue
            self.problem.addConstraint(con, vars)
            self.raw_constraints.append((con, vars))

    @cached_property
    def debug_fail(self) -> RandomizationFail:
        '''
        Cached property, instance of ``RandomizationFail`` that
        corresponds to this problem.
        '''
        failing_constraints = list(self.raw_constraints)
        for var in self.rand_vars:
            failing_constraints += [(constr, (var.name,)) for constr in var.constraints]
        return RandomizationFail(list(self.group_vars), failing_constraints)

    def can_retry(self) -> bool:
        '''
        Call this to determine whether or not retrying ``solve``
        can have a different outcome.

        :return: ``True`` if calling ``solve`` again might yield
            a different result (assuming it has already been called.)
            ``False`` otherwise.
        '''
        return len(self.rand_vars) > 0

    def concretize_rand_length(
        self,
        rand_list_var: 'RandVar',
        concrete_values: Dict[str, Any],
    ) -> None:
        '''
        Concretize the random length of a list.

        This is necessary for a random-length list that needs
        to be randomized. The value of the variable that
        determines the list length must be concrete before
        the list can be randomized.

        :param rand_list_var: Random list variable.
        :param concrete_values: Dict of current concrete values.
        '''
        # Only need to do anything if the variable has a random length.
        if rand_list_var.rand_length is not None:
            # Use existing concrete value if it exists.
            rand_length_val = None
            if rand_list_var.rand_length in concrete_values:
                rand_length_val = concrete_values[rand_list_var.rand_length]
            # Otherwise pick a value and save it.
            if rand_list_var.rand_length in self.solution_space:
                options = self.solution_space[rand_list_var.rand_length]
                rand_length_val = rand_list_var._get_random().choice(options)
                concrete_values[rand_list_var.rand_length] = rand_length_val
            # Either set the length, or ensure it's already set.
            if rand_length_val is not None:
                rand_list_var.set_rand_length(rand_length_val)
            else:
                # If we haven't got a value for the random var
                # in this problem, it must have already been set.
                assert rand_list_var.rand_length_val is not None, \
                    "Rand length must be concretized, but wasn't"

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
                # Reset concrete values on each attempt.
                concrete_values : Dict[str, Any] = {}
                for var in self.rand_vars:
                    if var.name in self.problem._variables:
                        # Remove from problem, it will be re-added with different concrete values
                        del self.problem._variables[var.name]
                    # Deal with random-length lists
                    if var.is_list():
                        self.concretize_rand_length(var, concrete_values)
                    # Add random variables in with a concrete value
                    if solutions_per_group == 1:
                        self.problem.addVariable(var.name, (var.randomize(),))
                    else:
                        iterations = self.max_domain_size if solutions_per_group is None else solutions_per_group
                        var_domain = []
                        for _ in range(iterations):
                            val = var.randomize()
                            # List is ~2x slower than set for 'in',
                            # but variables might be non-hashable.
                            if val not in var_domain:
                                var_domain.append(val)
                        self.problem.addVariable(var.name, var_domain)
                solutions = self.problem.getSolutions()
                if len(solutions) > 0:
                    break
                else:
                    attempts += 1
                    # Always output debug info on the last attempt.
                    failed = attempts >= max_iterations
                    debug = self.debug or (solutions_per_group is None and failed)
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

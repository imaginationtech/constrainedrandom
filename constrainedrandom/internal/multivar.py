# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

import random
from collections import defaultdict
from typing import Any, Callable, Dict, Iterable, List, Optional, TYPE_CHECKING, Union

from .vargroup import VarGroup

from .. import debug
from .. import utils

if TYPE_CHECKING:
    from ..internal.randvar import RandVar


class MultiVarProblem:
    '''
    Multi-variable problem. Used internally by RandObj.
    Represents one problem concerning multiple random variables,
    where those variables all share dependencies on one another.

    :param random_getter: A callable returning the random instance to use within this instance.
    :param vars: The dictionary of names and :class:`RandVar` instances this problem consists of.
    :param constraints: An iterable of tuples of (constraint, (variables,...)) denoting
        the constraints and the variables they apply to.
    :param max_iterations: The maximum number of failed attempts to solve the randomization
        problem before giving up.
    :param max_domain_size: The maximum size of domain that a constraint satisfaction problem
        may take. This is used to avoid poor performance. When a problem exceeds this domain
        size, we don't use the ``constraint`` package, but just use ``random`` instead.
        For :class:`MultiVarProblem`, we also use this to determine the maximum size of a
        solution group.
    '''

    def __init__(
        self,
        *,
        random_getter: Callable[[], random.Random],
        vars: List['RandVar'],
        constraints: Iterable[utils.ConstraintAndVars],
        max_iterations: int,
        max_domain_size: int,
    ) -> None:
        self.random_getter = random_getter
        self.vars = vars
        self.constraints = constraints
        self.max_iterations = max_iterations
        self.max_domain_size = max_domain_size
        self.order: Optional[List[List['RandVar']]] = None
        self.debug_info = Optional[debug.RandomizationDebugInfo]

    def determine_order(self, with_values: Dict[str, Any]) -> List[List['RandVar']]:
        '''
        Chooses an order in which to resolve the values of the variables.
        Used internally.

        :param with_values: Dictionary of variables with set values for this
            randomization.
        :return: A list of lists denoting the order in which to solve the problem.
            Each inner list is a group of variables that can be solved at the same
            time. Each inner list will be considered separately.
        '''
        # Use 'cached' version if no concrete values are specified
        problem_changed = len(with_values) != 0
        if not problem_changed and self.order is not None:
            return self.order

        # Aim to build a list of lists, each inner list denoting a group of variables
        # to solve at the same time.
        # The best case is to simply solve them all at once, if possible, however it is
        # likely that the domain will be too large.
        # If values are provided, simply don't add those variables to the ordering problem.
        if problem_changed:
            vars = []
            for var in self.vars:
                if var.name not in with_values:
                    vars.append(var)
        else:
            vars = list(self.vars)

        # Use order hints first, remaining variables can be placed anywhere the domain
        # isn't too large.
        sorted_vars = sorted(vars, key=lambda x: x.order)

        # Currently this is just a flat list. Group into as large groups as possible.
        result = [[sorted_vars[0]]]
        index = 0
        domain_size = sorted_vars[0].get_domain_size()
        for var in sorted_vars[1:]:
            domain_size = domain_size * var.get_domain_size()
            if var.order == result[index][0].order and domain_size < self.max_domain_size:
                # Put it in the same group as the previous one, carry on
                result[index].append(var)
            else:
                # Make a new group
                index += 1
                domain_size = var.get_domain_size()
                result.append([var])

        if not problem_changed:
            self.order = result

        return result

    def solve_groups(
        self,
        groups: List[List['RandVar']],
        with_values: Dict[str, Any],
        max_iterations: int,
        solutions_per_group: Optional[int]=None,
        debug: bool=False,
    ) -> Union[Dict[str, Any], None]:
        '''
        Constraint solving algorithm. (Used internally by :class:`MultiVarProblem`)

        :param groups: The list of lists denoting the order in which to resolve the random variables.
            See :func:`determine_order`.
        :param with_values: Dictionary of variables with set values for this
            randomization.
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
        :param debug: ``True`` to run in debug mode. Slower, but collects
            all debug info along the way and not just the final failure.
        :returns: A valid solution to the problem, in the form of a dictionary with the
            names of the random variables as keys and the valid solution as the values.
            Returns ``None`` if no solution is found within the allotted ``max_iterations``.
        '''
        constraints = self.constraints
        sparse_solver = solutions_per_group is not None
        solutions : List[Dict[str, Any]] = []
        solved_vars : List[str] = []

        # Respect assigned temporary values.
        if len(with_values) > 0:
            for var_name in with_values.keys():
                solved_vars.append(var_name)
            solutions.append(with_values)

        # For each group, construct a problem and solve it.
        for group in groups:
            group_solutions = None
            group_problem: VarGroup = None
            attempts = 0
            while group_solutions is None or len(group_solutions) == 0:
                # Early loop exit cases
                if attempts >= max_iterations:
                    # We have failed, give up.
                    # Update with latest debug info.
                    self.debug_info = group_problem.debug_info
                    return None
                if attempts > 0 and not group_problem.can_retry():
                    # Not worth retrying - the same result will be obtained.
                    # Update with latest debug info.
                    self.debug_info = group_problem.debug_info
                    return None

                # Determine what the starting state space for this group
                # should be.
                if sparse_solver and len(solutions) > 0:
                    # Respect a proportion of the solution space, determined
                    # by the sparsity/solutions_per_group.
                        # Start by choosing a subset of the possible solutions.
                        if solutions_per_group >= len(solutions):
                            solution_subset = list(solutions)
                        else:
                            solution_subset = self.random_getter().choices(
                                solutions,
                                k=solutions_per_group
                            )
                else:
                    # If not sparse, maintain the entire list of possible solutions.
                    solution_subset = list(solutions)

                # Translate this subset into a dictionary of the
                # possible values for each variable.
                solution_space = defaultdict(list)
                for soln in solution_subset:
                    for var_name, value in soln.items():
                        # List is ~2x slower than set for 'in',
                        # but variables might be non-hashable.
                        if value not in solution_space[var_name]:
                            solution_space[var_name].append(value)

                # Construct the appropriate group variable problem.
                # Must be done after selecting the solution space.
                group_problem = VarGroup(
                    group,
                    solution_space,
                    constraints,
                    self.max_domain_size,
                )

                # Attempt to solve the group
                group_solutions = group_problem.solve(
                    max_iterations,
                    solutions_per_group,
                    debug,
                )
                attempts += 1

            # This group is solved, move on to the next group.
            if solutions_per_group == 1:
                # This means we have exactly one solution for the variables considered so far,
                # meaning we don't need to re-apply solved constraints for future groups.
                constraints = group_problem.get_remaining_constraints()
            solved_vars += group_problem.group_vars
            solutions = group_solutions

        return self.random_getter().choice(solutions)

    def solve(
        self,
        sparse: bool,
        sparsities: List[int],
        thorough: bool,
        with_values: Optional[Dict[str, Any]]=None,
        debug: bool=False,
    ) -> Union[Dict[str, Any], None]:
        '''
        Attempt to solve the variables with respect to the constraints.

        :param with_values: Dictionary of variables with set values for this
            randomization.
        :return: One valid solution for the randomization problem, represented as
            a dictionary with keys referring to the named variables.
        :param debug: ``True`` to run in debug mode. Slower, but collects
            all debug info along the way and not just the final failure.
        :raises RandomizationError: When the problem cannot be solved in fewer than
            the allowed number of iterations.
        '''
        with_values = {} if with_values is None else with_values
        groups = self.determine_order(with_values)
        solution = None

        # Try to solve sparsely first
        if sparse:
            # The worst-case value of the number of iterations for one sparsity level is:
            # iterations_per_sparsity * iterations_per_attempt
            # because of the call to solve_groups hitting iterations_per_attempt.
            # Failing individual solution attempts speeds up some problems greatly,
            # this can be thought of as pruning explorations of the state tree.
            # So, reduce iterations_per_attempt by an order of magnitude.
            iterations_per_sparsity = self.max_iterations
            # Ensure it's non-zero
            iterations_per_attempt = (self.max_iterations // 10) + 1
            for sparsity in sparsities:
                for _ in range(iterations_per_sparsity):
                    solution = self.solve_groups(
                        groups=groups,
                        with_values=with_values,
                        max_iterations=iterations_per_attempt,
                        solutions_per_group=sparsity,
                        debug=debug,
                    )
                    if solution is not None and len(solution) > 0:
                        return solution

        if thorough:
            # Try 'thorough' method - no backup plan if this fails.
            solution = self.solve_groups(
                groups=groups,
                with_values=with_values,
                max_iterations=self.max_iterations,
                solutions_per_group=None,
                debug=debug,
            )
        if solution is None:
            raise utils.RandomizationError(
                "Could not solve multi-variable constraint problem.",
                str(self.debug_info),
            )
        return solution

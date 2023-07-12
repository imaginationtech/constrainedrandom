# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

import constraint
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, TYPE_CHECKING, Tuple, Union

from .. import utils
from ..debug import RandomizationDebugInfo, RandomizationFail

if TYPE_CHECKING:
    from ..randobj import RandObj
    from ..internal.randvar import RandVar


class MultiVarProblem:
    '''
    Multi-variable problem. Used internally by RandObj.
    Represents one problem concerning multiple random variables,
    where those variables all share dependencies on one another.

    :param parent: The :class:`RandObj` instance that owns this instance.
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
        parent: 'RandObj',
        vars: Dict[str, 'RandVar'],
        constraints: Iterable[utils.ConstraintAndVars],
        max_iterations: int,
        max_domain_size: int,
    ) -> None:
        self.parent = parent
        self.vars = vars
        self.constraints = constraints
        self.max_iterations = max_iterations
        self.max_domain_size = max_domain_size
        self.order = None

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
        vars = []

        # If values are provided, simply don't add those variables to the ordering problem.
        if problem_changed:
            for name, var in self.vars.items():
                if name not in with_values:
                    vars.append(var)
        else:
            vars = list(self.vars.values())

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

    def process_group(
        self,
        group: List['RandVar'],
        solved_vars: List[str],
        problem: constraint.Problem,
        constraints: List[utils.ConstraintAndVars],
    ) -> Tuple[List[str], List['RandVar'], List[utils.ConstraintAndVars]]:
        '''
        Determines which variables in the group can be solved via a
        constraint problem and which ones must be randomized and checked.
        (Used internally by :class:`MultiVarProblem`).

        :param group: List of random variables in this group.
        :param solved vars: List of variable names that are already solved.
        :param problem: Constraint problem to add variables and constraints to.
            Note that the instance will be modified by this function.
        :param constraints: Constraints that still apply at this stage of
            solving the problem.
        :return: A tuple of 1) a list the names of the variables in the group,
            2) a list of variables that must be randomized rather than solved
            via a constraint problem,
            3) a list of constraints and variables that won't be applied for this group.
        '''
        # Construct a constraint problem where possible. A variable must have a domain
        # in order to be part of the problem. If it doesn't have one, it must just be
        # randomized. Also take care not to exceed tha maximum domain size for an
        # individual variable.
        group_vars = []
        rand_vars = []
        for var in group:
            group_vars.append(var.name)
            if var.can_use_with_constraint() and var.get_domain_size() < self.max_domain_size:
                problem.addVariable(var.name, var.get_constraint_domain())
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

        return group_vars, rand_vars, skipped_constraints

    def solve_group(
        self,
        rand_vars: List['RandVar'],
        problem: constraint.Problem,
        max_iterations: int,
        solutions_per_group: int,
        debug_info: RandomizationDebugInfo,
        debug: bool,
    ) -> Union[List[Dict[str, Any]], None]:
        '''
        Attempts to solve one group of variables. Preferentially uses a constraint
        satisfaction problem, but may need to randomize variables that can't be
        added to a constraint satisfaction problem.
        (Used internally by :class:`MultiVarProblem`).

        :param rand_vars: List of random variables in the group (which can't be
            added to a constraint satisfaction problem).
        :param problem: Constraint satisfaction problem.
        :param max_iterations: Maximum number of attempts to solve the problem
            before giving up.
        :solutions_per_group: How many random values to produce before attempting
            to solve the constraint satisfaction problem. A lower value will run
            quicker but has less chance to succeed.
        :param debug_info: :class:`RandomizationDebugInfo`` instance to collect
            any debug info.
        :param debug: ``True`` to run in debug mode. Slower, but collects
            all debug info along the way and not just the final failure.
        :return: A list of all possible solutions for the group, or ``None`` if
            it can't be solved within ``max_iterations`` attempts.
        '''
        # Problem is ready to solve, apart from random variables
        solutions = []
        attempts = 0
        if debug:
            debug_fail = RandomizationFail([var.name for var in rand_vars], list(problem._constraints))
        if len(rand_vars) > 0:
            # If we have additional random variables, randomize and check
            while True:
                if attempts >= max_iterations:
                    # We have failed, give up
                    if not debug:
                        debug_fail = RandomizationFail([var.name for var in rand_vars],
                            list(problem._constraints))
                    debug_fail.add_values(dict(problem._variables))
                    debug_info.add_failure(debug_fail)
                    return None
                for var in rand_vars:
                    # Add random variables in with a concrete value
                    if solutions_per_group > 1:
                        var_domain = set()
                        for _ in range(solutions_per_group):
                            var_domain.add(var.randomize())
                        problem.addVariable(var.name, sorted(var_domain))
                    else:
                        problem.addVariable(var.name, (var.randomize(),))
                solutions = problem.getSolutions()
                if len(solutions) > 0:
                    break
                else:
                    attempts += 1
                    if debug:
                        # Add all randomization failures to failure for debugging
                        debug_fail.add_values(dict(problem._variables))
                    for var in rand_vars:
                        # Remove from problem, they will be re-added with different concrete values
                        del problem._variables[var.name]
        else:
            # Otherwise, just get the solutions, no randomization required.
            solutions = problem.getSolutions()
            if len(solutions) == 0:
                # Failed
                if not debug:
                    debug_fail = RandomizationFail([var.name for var in rand_vars],
                        list(problem._constraints))
                debug_info.add_failure(debug_fail)
                return None

        return solutions

    def solve_groups(
        self,
        groups: List[List['RandVar']],
        with_values: Dict[str, Any],
        max_iterations: int,
        debug_info: RandomizationDebugInfo,
        debug: bool,
        solutions_per_group: Optional[int]=None,
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
        :param debug_info: :class:`RandomizationDebugInfo`` instance to collect
            any debug info.
        :param debug: ``True`` to run in debug mode. Slower, but collects
            all debug info along the way and not just the final failure.
        :returns: A valid solution to the problem, in the form of a dictionary with the
            names of the random variables as keys and the valid solution as the values.
            Returns ``None`` if no solution is found within the allotted ``max_iterations``.
        '''
        constraints = self.constraints
        sparse_solver = solutions_per_group is not None
        solutions = []
        solved_vars = []

        # Respect assigned temporary values
        if len(with_values) > 0:
            for var_name in with_values.keys():
                solved_vars.append(var_name)
            solutions.append(with_values)

        # If solving sparsely, we'll create a new problem for each group.
        # If not solving sparsely, just create one big problem that we add to
        # as we go along.
        if not sparse_solver:
            problem = constraint.Problem()
            for var_name, value in with_values.items():
                problem.addVariable(var_name, (value,))

        for group in groups:
            if sparse_solver:
                # Construct one problem per group, add solved variables from previous groups.
                problem = constraint.Problem()
            # Construct the appropriate problem
            group_vars, rand_vars, skipped_constraints = self.process_group(
                group,
                solved_vars,
                problem,
                constraints,
            )

            group_solutions = None
            attempts = 0
            while group_solutions is None or len(group_solutions) == 0:
                if sparse_solver:
                    if len(solutions) > 0:
                        # Respect a proportion of the solution space, determined
                        # by the sparsity/solutions_per_group.
                        if solutions_per_group >= len(solutions):
                            solution_subset = solutions
                        else:
                            solution_subset = self.parent._get_random().choices(
                                solutions,
                                k=solutions_per_group
                            )
                        if solutions_per_group == 1:
                            for var_name, value in solution_subset[0].items():
                                if var_name in problem._variables:
                                    del problem._variables[var_name]
                                problem.addVariable(var_name, (value,))
                        else:
                            solution_space = defaultdict(set)
                            for soln in solution_subset:
                                for var_name, value in soln.items():
                                    solution_space[var_name].add(value)
                            for var_name, values in solution_space.items():
                                if var_name in problem._variables:
                                    del problem._variables[var_name]
                                problem.addVariable(var_name, list(values))

                # Attempt to solve the group
                group_solutions = self.solve_group(
                    rand_vars,
                    problem,
                    max_iterations,
                    solutions_per_group,
                    debug_info,
                    debug,
                )

                attempts += 1
                if attempts > max_iterations:
                    # We have failed, give up
                    return None

            # This group is solved, move on to the next group.
            if solutions_per_group == 1:
                # This means we have exactly one solution for the variables considered so far,
                # meaning we don't need to re-apply solved constraints for future groups.
                constraints = skipped_constraints
            solved_vars += group_vars
            solutions = group_solutions

        return self.parent._get_random().choice(solutions)

    def solve(
        self,
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
        sparsities = [1, 10, 100, 1000]
        # The worst-case value of the number of iterations for one sparsity level is:
        # iterations_per_sparsity * iterations_per_attempt
        # because of the call to solve_groups hitting iterations_per_attempt.
        # Failing individual solution attempts speeds up some problems greatly,
        # this can be thought of as pruning explorations of the state tree.
        # So, reduce iterations_per_attempt by an order of magnitude.
        iterations_per_sparsity = self.max_iterations
        iterations_per_attempt = self.max_iterations // 10
        # Create debug info in case of failure
        debug_info = RandomizationDebugInfo()
        for sparsity in sparsities:
            for _ in range(iterations_per_sparsity):
                solution = self.solve_groups(
                    groups,
                    with_values,
                    iterations_per_attempt,
                    debug_info,
                    debug,
                    sparsity,
                )
                if solution is not None and len(solution) > 0:
                    return solution

        # Try 'thorough' method - no backup plan if this fails
        solution = self.solve_groups(groups, with_values, debug_info, debug, self.max_iterations)
        if solution is None:
            raise utils.RandomizationError("Could not solve problem.", debug_info)
        return solution

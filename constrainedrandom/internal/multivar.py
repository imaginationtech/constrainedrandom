# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

import constraint
from collections import defaultdict
from typing import Any, Dict, Iterable, Optional, TYPE_CHECKING, Union

from constrainedrandom import utils

if TYPE_CHECKING:
    from constrainedrandom.randobj import RandObj
    from constrainedrandom.internal.randvar import RandVar


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
        constraints: Iterable[utils.Constraint],
        max_iterations: int,
        max_domain_size: int,
    ) -> None:
        self.parent = parent
        self.random = self.parent._random
        self.vars = vars
        self.constraints = constraints
        self.max_iterations = max_iterations
        self.max_domain_size = max_domain_size

    def determine_order(self) -> list[list['RandVar']]:
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
            if var.order == result[index][0].order and domain_size < self.max_domain_size:
                # Put it in the same group as the previous one, carry on
                result[index].append(var)
            else:
                # Make a new group
                index += 1
                domain_size = len(var.domain) if var.domain is not None else 1
                result.append([var])

        return result

    def solve_groups(
        self,
        groups: list[list['RandVar']],
        max_iterations:int,
        solutions_per_group: Optional[int]=None,
    ) -> Union[Dict[str, Any], None]:
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

    def solve(self) -> Union[Dict[str, Any], None]:
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
                solution = self.solve_groups(groups, self.max_iterations // 10, sparsity)
                if solution is not None and len(solution) > 0:
                    return solution

        # Try 'thorough' method - no backup plan if this fails
        solution = self.solve_groups(groups)
        if solution is None:
            raise RuntimeError("Could not solve problem.")
        return solution


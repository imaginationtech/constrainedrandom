# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

from typing import Any, Dict, Iterable, List

from .utils import Constraint, ConstraintAndVars


def debug_constraints(
        constraints: Iterable[ConstraintAndVars],
        values: Dict[str, Any]
    ) -> List[Constraint]:
    '''
    Call this to debug constraints. Gives feedback on which constraints
    are not satisfied by the current set of values.

    :param constraints: the list of constraints and the variables
        they apply to.
    :param values: dictionary of values.
    :return: List of failing constraints.
    '''
    unsatisfied = []
    for constr, var_names in constraints:
        args = []
        for var_name in var_names:
            args.append(values[var_name])
        satisfied = constr(*args)
        if not satisfied:
            unsatisfied.append((constr, var_names))
    return unsatisfied


class RandomizationFail:
    '''
    Represents one failure to randomize a problem.

    :param variables: List of variables that were randomized.
    :param constraints: List of tuples, giving constraints that
        were applied and the variables they apply to.
    '''

    def __init__(self, variables: Iterable[str], constraints: Iterable[ConstraintAndVars]) -> None:
        self.variables = variables
        self.constraints = constraints
        self.values = []
        self.failing_constraints = []

    def add_values(self, attempt: int, values: Dict[str, Any]) -> None:
        '''
        Adds values to the failed randomization. These values did
        not satisfy one or more constraints.

        :param attempt: Number of attempts up until this failure.
        :param values: Dictionary where keys are names of variables,
            values are the failed values.
        '''
        self.values.append((attempt, values))
        # Try to work out the constraints that are failing.
        # This may not be possible, depending on the problem we are being passed.
        try:
            failing_constraints = debug_constraints(self.constraints, values)
            self.failing_constraints.append(failing_constraints)
        except Exception:
            self.failing_constraints.append('could not compute failing constraints')

    def __str__(self):
        s = f"variables: {self.variables}"
        s += f"\nconstraints: {self.constraints}"
        if len(self.values) > 0:
            s += f"\nvalues and failing constraints:"
        for (attempt, value_dict), failing_constraints in zip(self.values, self.failing_constraints):
            s += f"\n  attempt: {attempt}  values: {value_dict}"
            s += f" failing constraints: {failing_constraints}"
        return s

    def __repr__(self) -> str:
        return self.__str__()


class RandomizationDebugInfo:
    '''
    Contains information about a failing randomization problem.

    Returned as part of a ``RandomizationError``.
    '''

    def __init__(self) -> None:
        self.failures = []

    def __str__(self) -> str:
        s = "Randomization failure:"
        for fail in self.failures:
            s += "\n" + (str(fail))
        return s

    def __repr__(self) -> str:
        return self.__str__()

    def add_failure(self, failure: RandomizationFail):
        '''
        Adds a failure object, representing a single
        randomization failure along the way.

        :param failure: One ``RandomizationFail`` instance
            to add to the debug info.
        '''
        self.failures.append(failure)

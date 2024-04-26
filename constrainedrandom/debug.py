# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

from typing import Any, Dict, Iterable, List, Optional, TYPE_CHECKING

from .utils import Constraint, ConstraintAndVars

if TYPE_CHECKING:
    from .internal.randvar import RandVar


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

    Describes the values of the failed randomization.
    These values did not satisfy one or more constraints.

    :param attempt: Number of attempts up until this failure.
    :param values: Dictionary where keys are names of variables,
        values are the failed values.
    :param constraints: List of tuples, giving constraints that
        were applied and the variables they apply to.
    '''

    def __init__(
        self,
        *,
        attempt: Optional[int],
        values: Dict[str, Any],
        constraints: Iterable[ConstraintAndVars],
        other_variables: Optional[Dict[str, Any]],
    ) -> None:
        self.attempt = attempt
        self.values = values
        self.other_variables = other_variables
        self.failing_constraints = []
        # Try to work out the constraints that are failing.
        # This may not be possible, depending on the problem we are being passed.
        try:
            failing_constraints = debug_constraints(constraints, values)
            self.failing_constraints += failing_constraints
        except Exception:
            self.failing_constraints.append('could not compute failing constraints')

    def __str__(self):
        s = "RandomizationFail("
        if self.attempt is not None:
            s += f"attempt={self.attempt}, "
        s += f"values={self.values}, "
        s += f"failing_constraints={self.failing_constraints}"
        if self.other_variables is not None:
            s += f", other_variables={self.other_variables}"
        s += ")"
        return s


class RandomizationDebugInfo:
    '''
    Contains information about a failing randomization problem.

    Returned as part of a ``RandomizationError`` exception.

    :param variables: List of variables that were randomized.
    :param constraints: List of tuples, giving constraints that
        were applied and the variables they apply to.
    '''

    def __init__(
        self,
        variables: List['RandVar'],
        constraints: Iterable[ConstraintAndVars],
    ) -> None:
        self.variables = variables
        self.constraints = constraints
        self.failures: List[RandomizationFail] = []

    def __str__(self) -> str:
        s = "RandomizationDebugInfo("
        s += f"variables=["
        for idx, variable in enumerate(self.variables):
            s += f"{str(variable)}"
            if idx < len(self.variables) - 1:
                s += ", "
        s += f"], "
        s += f"constraints={self.constraints}"
        if len(self.failures) > 0:
            s += ", failures=["
            for idx, fail in enumerate(self.failures):
                s += str(fail)
                if idx < len(self.failures) - 1:
                    s += ", "
            s += "]"
        s += ")"
        return s

    def clear(self) -> None:
        '''
        Clear current debug information.
        '''
        self.failures.clear()

    def add_failure(
        self,
        *,
        values: Dict[str, Any],
        constraints: Optional[Iterable[ConstraintAndVars]]=None,
        attempt: int=None,
        other_variables: Optional[Dict[str, Any]]=None,
    ):
        '''
        Adds a failure object, representing a single
        randomization failure along the way.

        :param attempt: Number of attempts up until this failure.
        :param values: Dictionary where keys are names of variables,
            values are the failed values.
        :param constraints: List of tuples, giving constraints that
            were applied and the variables they apply to. If ``None``
            supplied, just use existing constraints.
        :param other_variables: Dictionary of other variable names
            and possible values at this point in the problem.
        '''
        if constraints is None:
            constraints = self.constraints
        failure = RandomizationFail(
            attempt=attempt,
            values=values,
            constraints=constraints,
            other_variables=other_variables,
        )
        self.failures.append(failure)

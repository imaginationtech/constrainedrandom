# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

'''
Miscellaneous utilities for the constrainedrandom package.
'''

from inspect import getclosurevars
from typing import Any, Callable, Dict, Iterable, List, Tuple, Union


# Distribution type
Dist = Dict[Any, int]

# Domain type
Domain = Union[Iterable[Any], range, Dist]

# Constraint type
Constraint = Callable[..., bool]

# Constraint and the variables it applies to
ConstraintAndVars = Tuple[Constraint, Iterable[str]]

# The default maximum iterations before giving up on any randomization problem.
# A larger number means convergence is more likely, but runtime may be higher.
MAX_ITERATIONS = 100

# The default largest domain size to use with the constraint library.
# A large number may improve convergence, but hurt performance.
# A lower number may improve performance, but make convergence less likely.
CONSTRAINT_MAX_DOMAIN_SIZE = 1 << 10

class RandomizationError(Exception):
    '''
    Denotes that a randomization attempt has failed.
    '''

def unique(list_variable: Iterable[Any]) -> bool:
    '''
    Optimal function for testing uniqueness of values in a list.
    Useful constraint on a list.
    O(N) time complexity where N is list length, but also
    O(N) worst-case space complexity.
    Usually what you want rather than O(N**2) time compexity
    and O(1) space.

    :param list_variable: A list (or any iterable).
    :return: True if every element in the list is unique,
        False otherwise.
    '''
    seen = set()
    for i in list_variable:
        if i in seen:
            return False
        seen.add(i)
    return True


def is_pure(function: Callable) -> bool:
    '''
    Determine whether a function is "pure", i.e. its return value
    is only influenced by its arguments when it is called and by
    nothing else..

    :param function: Callable to determine whether it is pure.
    :return: ``True`` if "pure", ``False`` otherwise,
    '''
    # A function with __self__ attribute is bound to a class instance,
    # and is therefore not pure.
    if hasattr(function, '__self__'):
        return False
    # A function that has closure variables that are nonlocal or global
    # is impure. We count functions that use builtins as pure, assuming
    # those builtins themselves are pure.
    closure = getclosurevars(function)
    if len(closure.nonlocals) > 0 or len(closure.globals) > 0:
        return False
    # Look at default argument values. If they point to mutable objects,
    # this is not a pure function.
    if function.__defaults__ is not None:
        for default_val in function.__defaults__:
            if type(default_val) not in (str, int, bool, float, tuple, complex, bytes):
                return False
    return True

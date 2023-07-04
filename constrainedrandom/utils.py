# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

from typing import Any, Callable, Dict, Iterable, List, Tuple, Union


# Distribution type
Dist = Dict[Any, int]

# Domain type
Domain = Union[Iterable[Any], range, Dist]

# Constraint type
Constraint = Callable[..., bool]

# Constraint and the variables it applies to
ConstraintAndVars = Tuple[Constraint, Iterable[str]]

# The default maximum iterations before giving up on any randomization problem
MAX_ITERATIONS = 100

# The default largest domain size to use with the constraint library
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

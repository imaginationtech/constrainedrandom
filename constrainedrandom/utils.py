# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

from typing import Any, Callable, Dict, Iterable, Union


# Distribution type
Dist = Dict[Any, int]

# Domain type
Domain = Union[Iterable[Any], range, Dist]

# Constraint type
Constraint = Callable[..., bool]

# The default maximum iterations before giving up on any randomization problem
MAX_ITERATIONS = 100

# The default largest domain size to use with the constraint library
CONSTRAINT_MAX_DOMAIN_SIZE = 1 << 10

class RandomizationError(Exception):
    '''
    Denotes that a randomization attempt has failed.
    '''

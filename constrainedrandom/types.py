# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

from typing import Any, Callable, Dict, Iterable, Union


# Distribution type
Dist = Dict[Any, int]

# Domain type
Domain = Union[Iterable[Any], range, Dist]

# Constraint type
Constraint = Callable[..., bool]

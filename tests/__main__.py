# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

'''
Test all supported features.

Test for determinism within one thread, record performance.
'''

from .main import main

# Import all tests for unittest to run
from .bits import *
from .determinism import *
from .is_pure import *
from .features.basic import *
from .features.classes import *
from .features.errors import *
from .features.rand_list import *
from .features.temp import *
from .features.user import *


if __name__ == "__main__":
    main()

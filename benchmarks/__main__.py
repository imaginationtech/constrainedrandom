# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

'''
Benchmark against pyvsc library for equivalent testcases.
'''


from tests.main import main

from benchmarks.pyvsc.basic import VSCBasic
from benchmarks.pyvsc.in_keyword import VSCIn
from benchmarks.pyvsc.ldinstr import VSCInstr
from benchmarks.pyvsc.randlist import VSCRandListSumZero
from benchmarks.pyvsc.randlist import VSCRandListUnique


if __name__ == "__main__":
    main()

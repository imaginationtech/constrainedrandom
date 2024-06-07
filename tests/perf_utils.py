# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Imagination Technologies Ltd. All Rights Reserved

''' Reusable definitions for testing performance. '''

import json
from collections import defaultdict
from datetime import datetime
from time import time
from typing import Dict, List, Optional, Union


# Maintain performance results at module level for easy retrieval
PERF_DICT = Dict[str, Union[float, int]]
PERF_RESULTS: Dict[str, List[PERF_DICT]] = defaultdict(list)


def add_perf_result(
    name: str,
    perf_result: PERF_DICT,
) -> None:
    '''
    Adds a performance result.

    name:        Identifier for the result.
    perf_result: Dict of performance results.
    '''
    PERF_RESULTS[name].append(perf_result)


def get_perf_result(name: str) -> PERF_DICT:
    '''
    Retrieves a performance result.

    name: Identifier for the result.
    '''
    return PERF_RESULTS[name]


def dump_perf_data(perf_results_file: Optional[str], perf_results_tag: Optional[str]):
    '''
    Dump performance data to a JSON file.

    perf_results_file: File path to write to.
    perf_results_tag:  Tag to add to JSON data.
    '''
    timestamp = datetime.fromtimestamp(time()).strftime('%Y-%m-%d-%H%M%S')
    if perf_results_file is None:
        if perf_results_tag is not None:
            perf_results_file = f"perf-results-{perf_results_tag}.json"
        else:
            perf_results_file = f"perf-results-{timestamp}.json"
    if perf_results_tag is None:
        perf_results_tag = timestamp
    perf_results_final = {}
    for test_name, result_list in PERF_RESULTS.items():
        perf_results_final[test_name] = defaultdict(list)
        perf_results_final[test_name][perf_results_tag] += result_list
    print(f"Writing performance results to '{perf_results_file}' with tag '{perf_results_tag}'")
    with open(perf_results_file, "wt") as json_file:
        json_file.write(json.dumps(perf_results_final))

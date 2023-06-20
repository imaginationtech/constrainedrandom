# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

import random

from typing import Any, Optional

from . import utils


def weighted_choice(choices_dict: utils.Dist, _random: Optional[random.Random]=random) -> Any:
    '''
    Wrapper around ``random.choices``, allowing the user to specify weights in a dictionary.

    :param choices_dict: A dict containing the possible values as keys and relative
        weights as values.
    :param _random: Instance of random generator object to use. If not supplied, use
        global Python ``random`` module.
    :return: One of the keys of ``choices_dict`` chosen at random, based on weighting.
    :example:

    .. code-block:: python

        # 0 will be chosen 25% of the time, 1 25% of the time and 'foo' 50% of the time
        value = weighted_choice({0: 25, 1: 25, 'foo': 50})
    '''
    return _random.choices(tuple(choices_dict.keys()), weights=tuple(choices_dict.values()))

def dist(dist_dict: utils.Dist, _random: Optional[random.Random]=random) -> Any:
    '''
    Random distribution. As :func:`weighted_choice`, but allows ``range`` to be used as
    a key to the dictionary, which if chosen is then evaluated as a random range.

    :param dist_dict: A dict containing the possible values as keys and relative
        weights as values. If a range is supplied as a key, it will be evaluated
        as a random range.
    :param _random: Instance of random generator object to use. If not supplied, use
        global Python ``random`` module.
    :return: One of the keys of ``dist_dict`` chosen at random, based on weighting.
        If the key is a range, evaluate the range as a random range before returning.
    :example:

    .. code-block:: python

        # 0 will be chosen 25% of the time, a value in the range 1 to 9 25% of the time
        # and 'foo' 50% of the time
        value = dist({0: 25, range(1, 10): 25, 'foo': 50})
    '''
    answer = weighted_choice(choices_dict=dist_dict, _random=_random)[0]
    if isinstance(answer, range):
        return _random.randrange(answer.start, answer.stop)
    return answer

# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

import random

from typing import Any

from constrainedrandom import types


class Random(random.Random):
    '''
    Seeded, repeatable, deterministic random generator object.
    Subclass of :class:`random.Random`, enhanced with some quality-of-life features.
    Ideally one of these should be used per seeded random activity, e.g.
    in :class:`constrainedrandom.RandVar`.

    :param seed: Fixed seed for randomization.

    :example:

    .. code-block:: python

        # Create a random generator with seed 0.
        r1 = Random(seed=0)
        # Output five random 32-bit integers.
        for i in range(5):
            print(r1.randbits(32))

        # Create a second random generator with seed 0.
        r2 = Random(seed=0)
        # These five values will be the same as output by r1.
        for i in range(5):
            print(r2.randbits(32))

        # Create a third random generator with seed 1.
        r3 = Random(seed=1)
        # These five values will be different to the previous values.
        for i in range(5):
            print(r3.randbits(32))
    '''

    def __init__(self, seed: int) -> None:
        super().__init__(x=seed)

    def weighted_choice(self, choices_dict: types.Dist) -> Any:
        '''
        Wrapper around ``random.choices``, allowing the user to specify weights in a dictionary.

        :param choices_dict: A dict containing the possible values as keys and relative
            weights as values.
        :return: One of the keys of ``choices_dict`` chosen at random, based on weighting.
        :example:

        .. code-block:: python

            r = Random(seed=0)
            # 0 will be chosen 25% of the time, 1 25% of the time and 'foo' 50% of the time
            value = r.weighted_choice({0: 25, 1: 25, 'foo': 50})
        '''
        return self.choices(tuple(choices_dict.keys()), weights=tuple(choices_dict.values()))

    def dist(self, dist_dict: types.Dist) -> Any:
        '''
        Random distribution. As :func:`weighted_choice`, but allows ``range`` to be used as
        a key to the dictionary, which if chosen is then evaluated as a random range.

        :param dist_dict: A dict containing the possible values as keys and relative
            weights as values. If a range is supplied as a key, it will be evaluated
            as a random range.
        :return: One of the keys of ``dist_dict`` chosen at random, based on weighting.
            If the key is a range, evaluate the range as a random range before returning.
        :example:

        .. code-block:: python

            r = Random(seed=0)
            # 0 will be chosen 25% of the time, a value in the range 1 to 9 25% of the time
            # and 'foo' 50% of the time
            value = r.dist({0: 25, range(1, 10): 25, 'foo': 50})
        '''
        answer = self.weighted_choice(choices_dict=dist_dict)[0]
        if isinstance(answer, range):
            return self.randrange(answer.start, answer.stop)
        return answer
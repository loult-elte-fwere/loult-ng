from os import listdir, path
from asyncio import create_subprocess_shell
from asyncio.subprocess import PIPE
from typing import List

import numpy
from numpy import pad
from scipy.io.wavfile import read

from tools.tools import cached_loader

BASE_SAMPLING_RATE = 16000

def mix_tracks(track1, track2, offset=None, align=None):
    """Function that mixes two tracks of unequal lengths(represented by numpy arrays) together,
    using an 'align' or an offset. Zero padding is added to the smallest track as to make it fit.

    if offset is defined:
    longest track :  [=============================]
    smallest track : [0000000][================][00]
                      offset
    or
    longest track :  [=============================][00]
    smallest track : [000000000000000][================]
                          offset

    if align is defined:
    left:
    longest track :  [=============================]
    smallest track : [=====================][000000]

    right:
    longest track :  [=============================]
    smallest track : [000000][=====================]

    center:
    longest track :  [=============================]
    smallest track : [000][===================][000]
    """
    short_t, long_t = (track1, track2) if len(track1) < len(track2) else (track2, track1)
    diff = len(long_t) - len(short_t)

    if offset is not None:
        if len(long_t) - (len(short_t) + offset) >= 0:
            padded_short_t = pad(short_t, (offset, diff - offset), "constant", constant_values=0.0)
        else: # if offset + short > long, we have to padd the end of the long one
            padded_short_t = pad(short_t, (offset, 0), "constant", constant_values=0.0)
            long_t = pad(long_t, (0, offset - diff), "constant", constant_values=0.0)

    elif align is not None and align in ["left", "right", "center"]:
        if align == "right":
            padded_short_t = pad(short_t, (diff, 0), "constant", constant_values=0.0)
        elif align == "left":
            padded_short_t = pad(short_t, (0, diff), "constant", constant_values=0.0)
        elif align == "center":
            left = diff // 2
            right = left if diff % 2 == 0 else left + 1
            padded_short_t = pad(short_t, (left, right), "constant", constant_values=0.0)
    else:
        from tools.tools import ToolsError
        raise ToolsError()

    # the result vector's elements are c_i = a_i + b_i
    return padded_short_t + long_t


def get_sounds(dir: str) -> List[numpy.ndarray]:
    sounds = []
    for filename in listdir(dir):
        realpath = path.join(dir, filename)
        rate, data = cached_loader.load_wav(realpath)
        sounds.append(data)
    return sounds


async def resample(wave_data : numpy.ndarray, sample_in, sample_out=BASE_SAMPLING_RATE):
    """Uses sox to resample the wave data array"""
    cmd = "sox -N -V1 -t f32 -r %s -c 1 - -t f32 -r %s -c 1 -" % (sample_in, sample_out)
    process = await create_subprocess_shell(cmd, stdin=PIPE, stdout=PIPE)
    output, err = await process.communicate(input=wave_data.tobytes(order="f"))
    return numpy.fromstring(output, dtype=numpy.float32)


"""This is where effects go to die"""
import random
from os import path, listdir

import numpy
from scipy.io.wavfile import read
from voxpopuli import PhonemeList

from tools.audio_tools import mix_tracks
from tools.effects import PhonemicEffect, AudioEffect


class PhonemicShuffleEffect(PhonemicEffect):
    NAME = "interprète kiglon"
    TIMEOUT = 120

    def process(self, phonems : PhonemeList):
        random.shuffle(phonems)
        return phonems


class ReversedEffect(AudioEffect):
    """?sdef vlop sdaganliup uirt vlad"""
    NAME = "inversion"
    TIMEOUT = 120

    def process(self, wave_data: numpy.ndarray):
        return wave_data[::-1]


class AmbianceEffect(AudioEffect):
    """Adds a random mood to the audio"""
    NAME = "ambiance"
    TIMEOUT = 180
    effects_mapping = {
        "starwars_mood": ("lasèw", 0.1),
        # "bonfire_mood" : ("les feux de l'amouw", 0.6),
        "seastorm_mood": ("bretagne", 0.08),
        "war_mood": ("wesh yé ou ryan ce pd", 0.2),
    }
    data_folder = path.join(path.dirname(path.realpath(__file__)), "data/ambiance/")

    def __init__(self):
        super().__init__()
        filename = random.choice(list(self.effects_mapping.keys()))
        self._name, self.gain = self.effects_mapping[filename]
        with open(path.join(self.data_folder, filename + ".wav"), "rb") as sndfile:
            self.rate, self.track_data = read(sndfile)

    @property
    def name(self):
        return self._name

    def process(self, wave_data: numpy.ndarray):
        padding_time = self.rate * 2
        rnd_pos = random.randint(0, len(self.track_data) - len(wave_data) - padding_time)
        return mix_tracks(self.track_data[rnd_pos:rnd_pos + len(wave_data) + padding_time] * self.gain,
                          wave_data,
                          align="center")


class BeatsEffect(AudioEffect):
    main_dir = path.join(path.dirname(path.realpath(__file__)), "data/beats/")
    NAME = "JR"
    TIMEOUT = 150

    _directories = {"posay" : ["other"],
                    "tape ton para": ["ez3kiel", "outrun", "serbian_film"],
                    "JR" : ["jr"]}

    def __init__(self):
        super().__init__()
        self._name, directories = random.choice(list(self._directories.items()))
        dir = random.choice(directories)
        beat_filename = random.choice(listdir(path.join(self.main_dir, dir)))
        with open(path.join(self.main_dir, dir, beat_filename), "rb") as sndfile:
            self.rate, self.track = read(sndfile)

    @property
    def name(self):
        return self._name

    def process(self, wave_data: numpy.ndarray):
        if len(self.track) < len(wave_data):
            beat_track = numpy.tile(self.track, (len(wave_data) // len(self.track)) + 1)
            return mix_tracks(beat_track * 0.4, wave_data, align="center")
        else:
            return wave_data
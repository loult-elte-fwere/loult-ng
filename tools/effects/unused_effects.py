
"""This is where effects go to die"""
import random
from os import path, listdir

import numpy
from scipy.io.wavfile import read

from tools.effects import EffectGroup
from tools.phonems import PhonemList
from tools.effects import PhonemicEffect, AudioEffect, ExplicitTextEffect
from tools.audio_tools import get_sounds, mix_tracks


class PhonemicShuffleEffect(PhonemicEffect):
    NAME = "interprète kiglon"
    TIMEOUT = 120

    def process(self, phonems : PhonemList):
        random.shuffle(phonems)
        return phonems


class ReversedEffect(AudioEffect):
    """?sdef vlop sdaganliup uirt vlad"""
    NAME = "inversion"
    TIMEOUT = 120

    def process(self, wave_data: numpy.ndarray):
        return wave_data[::-1]


class IssouEffect(AudioEffect):
    # TODO : refactor plus compact des fonctions sur les deux dossiers différents
    """el famoso"""
    main_dir = path.join(path.dirname(path.realpath(__file__)), "data/issou")
    issou_dir = path.join(main_dir, "issou")
    other_dir = path.join(main_dir, "other")
    NAME = "el famoso"
    TIMEOUT = 120

    def __init__(self):
        super().__init__()

        self.issou_sounds = get_sounds(self.issou_dir)
        self.other_sounds = get_sounds(self.other_dir)
        self.pending_issou, self.pending_other = [], []
        self._create_pattern()

    def _create_pattern(self):
        random.shuffle(self.issou_sounds)
        random.shuffle(self.other_sounds)
        self.pending_other = self.other_sounds[:random.randint(1,3)]
        self.pending_issou = self.issou_sounds[:random.randint(2,4)]

    def process(self, wave_data: numpy.ndarray):
        if random.randint(0,3) == 1:
            if self.pending_other:
                return self.pending_other.pop()
            elif self.pending_issou:
                return self.pending_issou.pop()
            else:
                self._create_pattern()
                return self.process(wave_data)
        else:
            return wave_data


class SitcomEffect(AudioEffect):
    main_dir = path.join(path.dirname(path.realpath(__file__)), "data/sitcom")
    _subfolders = ["laugh_track", "boo", "applaud"]
    NAME = "sitcom"
    TIMEOUT = 150

    def __init__(self):
        super().__init__()
        self.tracks = dict()
        for subfolder in self._subfolders:
            self.tracks[subfolder] = get_sounds(path.join(self.main_dir, subfolder))
            # sorting by length
            self.tracks[subfolder].sort(key = lambda s: len(s))

    def find_nearest(self, track_list, value):
        nearest_bigger_index = next((i for i, x in enumerate(track_list) if len(x) > value), None)
        return nearest_bigger_index - 1 if nearest_bigger_index > 0 else 0

    def process(self, wave_data: numpy.ndarray):
        if random.randint(0,1):
            randoum = random.randint(1, 3)
            if randoum == 1:
                wave_data = numpy.concatenate((wave_data, random.choice(self.tracks["laugh_track"])))
            elif randoum == 2:
                wave_data = numpy.concatenate((wave_data, random.choice(self.tracks["applaud"])))
            elif randoum == 3:
                boo_track_id = self.find_nearest(self.tracks["boo"], len(wave_data))
                wave_data = mix_tracks(wave_data, self.tracks["boo"][boo_track_id], align="right")

        return wave_data


class TurfuEffect(EffectGroup):
    TIMEOUT = 150
    NAME = "du turfu"

    @property
    def effects(self):
        from .effects import TurboHangoul, CrapweEffect
        hangoul, crapw = TurboHangoul(4), CrapweEffect(4)
        hangoul._timeout = 150
        crapw._timeout = 150
        return [hangoul, crapw]


class VenerEffect(EffectGroup):
    TIMEOUT = 120
    NAME = "YÉ CHAUD"
    _sound_file = path.join(path.dirname(path.realpath(__file__)),
                            "data/vener/stinkhole_shave_me_extract.wav")

    class UPPERCASEEffect(ExplicitTextEffect):
        TIMEOUT = 120

        def process(self, text : str):
            return text.upper()

    @property
    def effects(self):
        monkey_patched = AmbianceEffect()
        monkey_patched._timeout = 120
        monkey_patched.gain = 0.2
        with open(self._sound_file, "rb") as sndfile:
            monkey_patched.rate, monkey_patched.track_data = read(sndfile)
        return [self.UPPERCASEEffect(), monkey_patched]

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
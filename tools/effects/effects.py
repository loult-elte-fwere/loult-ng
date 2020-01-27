import json
import random
from copy import deepcopy
from datetime import datetime
from functools import partial
from itertools import cycle
from os import path
from pathlib import Path
from typing import List
from statistics import mean
import re

import numpy as np
from pysndfx import AudioEffectsChain
from scipy.io.wavfile import read

import tools
from tools.audio_tools import mix_tracks, get_sounds, BASE_SAMPLING_RATE
from tools.tools import cached_loader
from tools.effects.tree import Node, Leaf
from voxpopuli import PhonemeList, FrenchPhonemes
from voxpopuli.phonemes import Phoneme
from tools.users import VoiceParameters
from .melody import chord_progressions, get_harmonies


DATA_FOLDER = Path(__file__).absolute().parent / Path("data")


# TODO : effet théatre, effet speech random
# guitar raggea + maitre de l'élocution
# effet javanais


class Effect:
    NAME = ""
    TIMEOUT = 0

    def __init__(self):
        self.creation = datetime.now()
        self._timeout = None
        self._name = None

    @property
    def timeout(self):
        return self.TIMEOUT if self._timeout is None else self._timeout

    @property
    def name(self):
        return self.NAME if self._name is None else self._name  # using a property, in case it gets more fancy than just a class constant

    def is_expired(self):
        return (datetime.now() - self.creation).seconds > self.timeout

    def process(self, **kwargs):
        pass


class EffectGroup(Effect):
    """An effect group is basically a 'meta-effect'. It returns, through the property 'effects' a
    list of already instanciated effect objects, which are all going to be added the a user's effects
    lists. In practice, it's a simple way to have effects that are both on sound, phonems and text.

    Before returning the list of effects, one has to make sure that the tools returned by the 'effects' property
    all have the same timeout time as the effect group that returns them. This can be done by setting the optional
    _timeout instance attribute (*NOT* the TIMEOUT class attribute) of an Effect object"""

    _sub_effects = []

    @property
    def effects(self) -> List[Effect]:
        return [effect_cls() for effect_cls in self._sub_effects]


class TextEffect(Effect):

    def process(self, text: str) -> str:
        """This function takes text and applies (or not, it's up the dev) alterations to that text"""
        pass


class ExplicitTextEffect(TextEffect):
    """Effect that modifies the text that is rendered AND sent to mbrola"""
    pass


class HiddenTextEffect(TextEffect):
    """Effect that modifies the text before it is sent to mbrola, but the end user doesn't see it"""
    pass


class PhonemicEffect(Effect):
    """Effect that modifies Phonems before they're sent to mbrola"""

    def process(self, phonems: PhonemeList) -> PhonemeList:
        """"""


class VoiceEffect(Effect):
    """Affects the voice before the audio rendering"""

    def process(self, voice_params: VoiceParameters) -> VoiceParameters:
        pass


class AudioEffect(Effect):
    """Modifies the audio file, after the mbrola rendering"""

    def process(self, wave_data: np.ndarray) -> np.ndarray:
        pass


class VisualEffect(Effect):
    """Doesn't do anything, just here to notify the client"""


#### Here are the text effects ####

class SnebwewEffect(ExplicitTextEffect):
    """Finds, using a simple heuristic, random nouns and changes them to snèbwèw"""
    NAME = "snèbwèw"
    TIMEOUT = 240
    pronouns = ["le", "la", "un", "une", "du", "son", "sa", "mon", "ce", "ma", "cette", "au", "les", "aux", "à",
                "tu", "je", "a"]

    def process(self, text: str):
        splitted = text.split()  # fak ye baudrive
        reconstructed = ''
        it = iter(splitted)
        endswith_sneb = False
        for word in it:
            if word:
                reconstructed += word + ' '
                if word.lower() in self.pronouns and random.randint(1, 2) == 1:
                    reconstructed += "SNÈBWÈW" + ' '
                    endswith_sneb = True
                    try:
                        next(it)
                    except StopIteration:
                        break
                else:
                    endswith_sneb = False
        if endswith_sneb:
            reconstructed = reconstructed[:-1] + "ENNW"

        return reconstructed


class FlowerEffect(ExplicitTextEffect):
    """Insert flower emojis between words"""
    NAME = "fleuwiw"
    TIMEOUT = 800

    flowers = ["\U0001f337", "\U0001f338", "\U0001f339", "\U0001f33a", "\U0001f33b", "\U0001f33c"]

    def process(self, text: str) -> str:
        # We'll try to have neither too few nor too many flowers.
        probability = random.uniform(0.3, 0.6)
        result = []
        # The empty string accounts for the possibility to insert an emoji at the end.
        for token in text.split() + ['']:
            if probability <= random.uniform(0, 1):
                result.append(random.choice(self.flowers))
            result.append(token)
        return " ".join(result[:-1])  # slice to avoid trailing whitespace


class ContradictorEffect(ExplicitTextEffect):
    NAME = "contradicteur"
    TIMEOUT = 600
    # TODO : test if verb tree is actually useful
    TREE_FILEPATH = DATA_FOLDER / Path("contradicteur/verbs_tree.pckl")

    def __init__(self):
        super().__init__()
        self.verb_tree = cached_loader.load_pickle(self.TREE_FILEPATH)

    def process(self, text: str):
        if random.randint(1, 2) == 1:
            splitted = text.split()
            reconstructed = ''
            previous_was_negation = False
            for word in splitted:
                if word.lower() in ["pas", "pa", "aps"]:
                    previous_was_negation = True
                else:
                    reconstructed += word + " "
                    if previous_was_negation and self.verb_tree.has_leaf(Leaf(word)):  # testing if it's a verb
                        reconstructed += 'pas'
                        previous_was_negation = False

            return reconstructed
        else:
            return text


class CaptainHaddockEffect(ExplicitTextEffect):
    NAME = "mille million de milles sabords"
    TIMEOUT = 200
    INSULTS_FILEPATH = DATA_FOLDER / Path("insults.txt")

    def __init__(self):
        super().__init__()
        with open(self.INSULTS_FILEPATH) as insults_file:
            self.insults = insults_file.read().split("\n")

    def process(self, text: str) -> str:
        insult = random.choice(self.insults)
        if insult[0] in {"a", "e", "é", "è", "y", "o", "u", "h", "ê", "i"}:
            article = "d'"
        else:
            article = "de "
        swear = random.choice(['bande', 'espèce', 'satanés', 'bougre', 'mille million'])
        return f"{text.strip('!,.:?')}, {swear} {article}{insult}!"


class TouretteEffect(HiddenTextEffect):
    """Randomly inserts insults in between words"""
    NAME = "syndrome de tourette"
    TIMEOUT = 120
    available_words = {
        "tourette": ["pute", "salope", "chier", "kk", "chienne", "merde", "cul", "bite", "chatte", "suce"],
        "bibwe": ["jtm", "t miw miw", "onw", "jvm", "biswe bidwe", "plein d'amouw", "bibwe", "t chwe"]}

    def __init__(self, disease: str = None):
        super().__init__()
        if disease is None:
            disease = random.choice(["tourette", "bibwe"])

        if disease == "tourette":
            self.NAME = "syndrome de tourette"
        elif disease == "bibwe":
            self.NAME = "bibwe du loult"
        else:
            raise ValueError()
        self.words = self.available_words[disease]

    def process(self, text: str):
        # the variable is called splitted because it pisses off this australian cunt that mboevink is
        space_splitted = [word for word in text.split(" ") if word != ""]
        reconstructed = ""
        for word in space_splitted:
            reconstructed += " " + word + " "
            if random.randint(1, 6) == 1:
                reconstructed += " ".join([random.choice(self.words)
                                           for i in range(random.randint(1, 4))])
        return reconstructed


class CensorshipEffect(ExplicitTextEffect):
    """Censors randomly parts of the input text"""
    NAME = "censure d'état"
    TIMEOUT = 150

    @staticmethod
    def random_repl(match):
        if random.randint(0, 5) != 0:
            return match.group()
        else:
            return "**%s**" % match.group()

    def process(self, text: str) -> str:
        # maybe use a sub instead of iterating like an idiot
        return re.sub(r"[\w]+", self.random_repl, text)


class SpeechMasterEffect(HiddenTextEffect):
    """Increases your speech abilities by 76%"""
    NAME = "maître de l'élocution"
    TIMEOUT = 120
    available_punctuation = "?,!.:'"

    def process(self, text: str):
        space_splitted = [word for word in text.split(" ") if word != ""]
        reconstructed = " ".join([word + random.choice(self.available_punctuation)
                                  for word in space_splitted])
        return reconstructed


class SkyblogEffect(ExplicitTextEffect):
    """Increases your style by 64%"""
    NAME = "skyblog"
    TIMEOUT = 120
    available_punctuation = "?,!.:'"

    def process(self, text: str):
        reconstructed = ""
        for char in text:
            reconstructed += char.upper() if random.randint(1, 3) == 1 else char

        return reconstructed


#### Here are the phonemic effects ####

class PhonemicNwwoiwwEffect(PhonemicEffect):
    NAME = "nwwoiww"
    TIMEOUT = 150

    def process(self, phonems: PhonemeList):
        w_phonem = Phoneme("w", 103, [])
        for i, phoneme in enumerate(phonems):
            if phoneme.name == "R":
                phoneme.name = "w"
                if random.randint(0, 1) == 0:
                    for j in range(2):
                        phonems.insert(i, w_phonem)
                else:
                    phoneme.duration = 206
        return phonems


class PhonemicFofoteEffect(PhonemicEffect):
    NAME = "fofotage"
    TIMEOUT = 150

    def process(self, phonems: PhonemeList):
        for phoneme in phonems:
            if phoneme.name in ["s", "v", "z", "S", "Z"]:
                phoneme.name = "f"
        return phonems


class AccentAllemandEffect(PhonemicEffect):
    NAME = "accent shleu"
    TIMEOUT = 150
    _tranlation_table = {"Z": "S",  # je -> che
                         "v": "f",  # vous -> fous
                         "b": "p",  # boule -> poule
                         "g": "k"}  # gant -> kan

    def process(self, phonems: PhonemeList):
        for phoneme in phonems:
            if phoneme.name in self._tranlation_table:
                phoneme.name = self._tranlation_table[phoneme.name]
            elif phoneme.name in FrenchPhonemes.ORALS and random.randint(1, 3) == 1:
                phoneme.duration *= 2
            elif phoneme.name == "d" and random.randint(1, 2) == 1:
                phoneme.name = "t"
        return phonems


class AccentMarseillaisEffect(PhonemicEffect):
    NAME = "du vieux port"
    TIMEOUT = 150

    def process(self, phonems: PhonemeList):
        reconstructed = PhonemeList([])
        ng_phonem = Phoneme("N", 100)
        euh_phonem = Phoneme("2", 79)
        phonems.append(Phoneme("_", 10))  # end-silence-padding, just to be safe
        for i, phoneme in enumerate(phonems):
            if phoneme.name in FrenchPhonemes.NASAL_WOVELS:
                reconstructed += [phoneme, ng_phonem]
            elif phoneme.name in FrenchPhonemes.CONSONANTS - {"w"} and phonems[i + 1].name not in FrenchPhonemes.VOWELS:
                reconstructed += [phoneme, euh_phonem]
            elif phoneme.name == "o":
                phoneme.name = "O"
                reconstructed.append(phoneme)
            else:
                reconstructed.append(phoneme)
        return reconstructed


class StutterEffect(PhonemicEffect):
    TIMEOUT = 150
    NAME = "be be te"

    def process(self, phonems: PhonemeList):
        silence = Phoneme("_", 61)
        reconstructed = PhonemeList([])
        for i, phoneme in enumerate(phonems):
            if phonems[i].name in FrenchPhonemes.CONSONANTS \
                    and phonems[i + 1].name in FrenchPhonemes.VOWELS \
                    and random.randint(1, 3) == 1:
                reconstructed += [phonems[i], phonems[i + 1]] * 2
            elif phoneme.name in FrenchPhonemes.VOWELS and random.randint(1, 3) == 1:
                reconstructed += [phoneme, silence, phoneme]
            else:
                reconstructed.append(phoneme)
        return reconstructed


class VocalDyslexia(PhonemicEffect):
    NAME = "dysclesie vocael"
    TIMEOUT = 150

    def process(self, phonems: PhonemeList):

        def permutation(i, j, input_list):
            input_list[i], input_list[j] = input_list[j], input_list[i]

        def double_permutation(i, input_list):
            input_list[i - 1], input_list[i], input_list[i + 1], input_list[i + 2] = \
                input_list[i + 1], input_list[i + 2], input_list[i - 1], input_list[i]

        if len(phonems) > 5:
            permut_count = random.randint(1, len(phonems) // 5)  # approx 1 permut/10 phonems
            permut_points = [random.randint(1, len(phonems) - 3) for i in range(permut_count)]
            for point in permut_points:
                permutation(point, point + 1, phonems)

        return phonems


class AutotuneEffect(PhonemicEffect):
    pitch_file = DATA_FOLDER / Path("pitches.json")
    NAME = "lou a du talent"
    TIMEOUT = 150

    def __init__(self):
        super().__init__()
        with open(self.pitch_file) as pitch_file:
            self.pitches = json.load(pitch_file)
        self.progression = random.choice(chord_progressions)
        self.octave = 3

    def _get_note(self):
        for chord in cycle(self.progression):
            if chord.endswith("m"):
                note, chord_type = chord.strip("m"), "minor"
            else:
                note, chord_type = chord, "major"

            harmonies_ptich = get_harmonies(self.pitches[note + str(self.octave)], chord_type)
            for _ in range(4):
                yield random.choice(harmonies_ptich)

    def process(self, phonems: PhonemeList):
        notes = self._get_note()
        for pho in phonems:
            if pho.name in FrenchPhonemes.VOWELS:
                pitch = next(notes)
                pho.set_from_pitches_list([pitch] * 2)
                pho.duration *= 2

        return phonems


class RythmicEffect(PhonemicEffect):
    NAME = "JR"
    TIMEOUT = 200
    BEAT_TIME = 80  #  in milliseconds

    def __init__(self):
        super().__init__()
        self.durations = [0.5, 0.5, 0.5, 0.5, 1, 1, 2, 2]
        random.shuffle(self.durations)

    def process(self, phonems: PhonemeList):
        beat_iterator = cycle(self.durations)
        for phoneme in phonems:
            if phoneme.name in FrenchPhonemes.VOWELS:
                beat = next(beat_iterator)
                phoneme.duration = int(beat * self.BEAT_TIME)
        return phonems


class CrapweEffect(PhonemicEffect):
    """Dilates random vowels and modifies the pitch to go up and down"""
    NAME = "crapwe force"
    TIMEOUT = 150

    def __init__(self, intensity=None):
        super().__init__()
        self.intensity = random.randint(1, 4) if intensity is None else intensity
        self._name = self.NAME + " " + str(self.intensity)

    @property
    def name(self):
        return self._name

    def process(self, phonems: PhonemeList):
        for phoneme in phonems:
            if phoneme.name in FrenchPhonemes.VOWELS and random.randint(1, 4) >= self.intensity:
                phoneme.duration *= 8
                if phoneme.pitch_modifiers:
                    orgnl_pitch_avg = mean([pitch for pos, pitch in phoneme.pitch_modifiers])
                else:
                    orgnl_pitch_avg = 150
                phoneme.set_from_pitches_list([orgnl_pitch_avg + ((-1) ** i * 30) for i in range(4)])

        return phonems


class TurboHangoul(PhonemicEffect):
    NAME = "turbo hangoul force"
    TIMEOUT = 150

    def __init__(self, intensity=None):
        super().__init__()
        self.intensity = random.randint(1, 4) if intensity is None else intensity
        self._name = self.NAME + " " + str(self.intensity)

    @property
    def name(self):
        return self._name

    def process(self, phonems: PhonemeList):
        for phoneme in phonems:
            if phoneme.name in FrenchPhonemes.VOWELS and random.randint(1, 4) <= self.intensity:
                phoneme.duration *= 8
                phoneme.set_from_pitches_list([364 - 10, 364])

        return phonems


class GrandSpeechMasterEffect(PhonemicEffect):
    NAME = "grand maître de l'élocution"
    TIMEOUT = 150

    def process(self, phonems: PhonemeList):
        for phoneme in phonems:
            if phoneme.name in FrenchPhonemes._all:
                phoneme.duration = int(phoneme.duration * (random.random() * 4 + 0.7))

        return phonems


class VowelExchangeEffect(PhonemicEffect):
    NAME = "hein quoi?"
    TIMEOUT = 200

    def process(self, phonems: PhonemeList):
        vowels_list = list(FrenchPhonemes.ORALS | FrenchPhonemes.NASAL_WOVELS)
        for phoneme in phonems:
            if phoneme.name in FrenchPhonemes.ORALS | FrenchPhonemes.NASAL_WOVELS and random.randint(1, 5) == 1:
                phoneme.name = random.choice(vowels_list)
        return phonems


class PitchRandomizerEffect(PhonemicEffect):
    TIMEOUT = 150
    NAME = "problèmes de gorge"
    _multiplier_range = 0.6
    _delimiters_per_phonems = 5

    def process(self, phonems: PhonemeList):
        delimiters = list({random.randint(1, len(phonems))
                           for _ in range(len(phonems) // self._delimiters_per_phonems)})
        delimiters.sort()
        delim_idx = 0
        current_multiplier = 1
        for i, phoneme in enumerate(phonems):
            if delim_idx < len(delimiters) and i == delimiters[delim_idx]:
                delim_idx += 1
                current_multiplier = random.random() * self._multiplier_range * (1 if random.randint(0, 1) else -1) + 1
            phoneme.pitch_modifiers = [(duration, int(pitch * current_multiplier))
                                       for duration, pitch in phoneme.pitch_modifiers]
        return phonems


class PubertyEffect(PhonemicEffect):
    NAME = "puberté"
    TIMEOUT = 180

    def process(self, phonems: PhonemeList):
        for phoneme in phonems:
            if phoneme.name in FrenchPhonemes.VOWELS and random.randint(1, 2) == 1:
                phoneme.duration *= 2
                factor = random.uniform(0.3, 2)
                phoneme.pitch_modifiers = [(pos, int(pitch * factor)) for pos, pitch in phoneme.pitch_modifiers]
        return phonems


#### Here are the voice effets ####


class VoiceSpeedupEffect(VoiceEffect):
    TIMEOUT = 200
    NAME = "en stress"

    def __init__(self, factor: float = None):
        super().__init__()
        self.factor = random.uniform(1.5, 2.4) if factor is None else factor

    def process(self, voice_params: VoiceParameters):
        voice_params = deepcopy(voice_params)
        voice_params.speed = int(self.factor * voice_params.speed)
        return voice_params


class VoiceCloneEffect(VoiceEffect):
    TIMEOUT = 600
    NAME = "clone de voiw"

    def __init__(self, voice_params: VoiceParameters):
        super().__init__()
        self.params = voice_params

    def process(self, voice_params: VoiceParameters):
        return self.params


#### Here are the audio effects ####


class ReverbManEffect(AudioEffect):
    """Adds a pretty heavy reverb effect"""
    NAME = "reverbman"
    TIMEOUT = 180

    def __init__(self):
        super().__init__()
        self._name = random.choice(["ouévèwbèw", self.NAME, "lou monastèw"])

    @property
    def name(self):
        return self._name

    def process(self, wave_data: np.ndarray):
        wave_data = np.concatenate([wave_data, np.zeros(BASE_SAMPLING_RATE, wave_data.dtype)])
        apply_audio_effects = AudioEffectsChain().reverb(reverberance=100, hf_damping=100)
        return apply_audio_effects(wave_data, sample_in=BASE_SAMPLING_RATE, sample_out=BASE_SAMPLING_RATE)


class GhostEffect(AudioEffect):
    """Adds a ghostly effect"""
    NAME = "stalker"
    TIMEOUT = 120

    def process(self, wave_data: np.ndarray):
        reverb = ReverbManEffect()
        return reverb.process(wave_data[::-1])[::-1]


class RobotVoiceEffect(AudioEffect):
    NAME = "Gladwse"
    TIMEOUT = 150

    def process(self, wave_data: np.ndarray):
        apply_audio_effects = AudioEffectsChain().pitch(200).tremolo(500).delay(0.6, 0.8, [33], [0.9])
        return apply_audio_effects(wave_data, sample_in=BASE_SAMPLING_RATE, sample_out=BASE_SAMPLING_RATE)


class AngryRobotVoiceEffect(AudioEffect):
    """Adds pitch-shifted versions of the track to itself to create a scary effect
    """
    NAME = "13-NRV"
    TIMEOUT = 150

    def process(self, wave_data: np.ndarray):
        # making a partial for each pitch change
        effects_partials = [partial(AudioEffectsChain().pitch(pitch),
                                    sample_in=BASE_SAMPLING_RATE, sample_out=BASE_SAMPLING_RATE)
                            for pitch in [200, 100, -100, -200]]
        # preparing a reverb effect chain
        reverb = AudioEffectsChain().reverb(reverberance=50, hf_damping=100).gain(-5)
        # sometimes, the pitch_shifted output arrays are slightly different from one another,
        # thus, to sum them we need to find the minimal length
        repitched_arrays = [effect(wave_data) for effect in effects_partials]
        min_len = min(map(len, repitched_arrays))

        return reverb(sum([audio_array[:min_len] for audio_array in repitched_arrays]),
                      sample_in=BASE_SAMPLING_RATE, sample_out=BASE_SAMPLING_RATE)


class PitchShiftEffect(AudioEffect):
    NAME = "pitch shift"
    TIMEOUT = 150

    def __init__(self):
        super().__init__()
        if random.randint(0, 1):
            self._name, self.pitch_shift = "pascal le grand frère", -700
        else:
            self._name, self.pitch_shift = "castration", 700

    def process(self, wave_data: np.ndarray):
        pitch_shift = AudioEffectsChain().pitch(self.pitch_shift)
        return pitch_shift(wave_data, sample_in=BASE_SAMPLING_RATE, sample_out=BASE_SAMPLING_RATE)


class WpseEffect(AudioEffect):
    """Adds or inserts funny sounds to the input sound, at random places"""
    main_dir = DATA_FOLDER /  Path("maturity")
    subfolders = ["burps", "prout"]
    NAME = "c pas moi lol"
    TIMEOUT = 130

    def __init__(self):
        super().__init__()
        self.type_folder = random.choice(self.subfolders)
        self.samples = get_sounds(self.main_dir / Path(self.type_folder))

    def process(self, wave_data: np.ndarray):
        if random.randint(1, 2) == 1:
            sample = random.choice(self.samples) * 0.3
            if self.type_folder == "burps":
                wave_data = np.insert(wave_data, random.randint(1, len(wave_data)), sample)
            else:
                wave_data = mix_tracks(wave_data, sample, offset=random.randint(1, len(wave_data)))

        return wave_data


class BadCellphoneEffect(AudioEffect):
    NAME = "mauvais réseau"
    TIMEOUT = 200

    _params_table = {1: (700, "3k", 30, -9),
                     2: (400, "3.5k", 25, -6),
                     3: (320, "3.8k", 22, -6)}
    _interference_filepath = DATA_FOLDER / Path("interference.wav")

    def __init__(self, signal_strength: int = None):
        super().__init__()
        self.signal = signal_strength if signal_strength is not None else random.randint(1, 3)
        self._name = "%i barres de rézo" % self.signal
        self.hpfreq, self.lpfreq, self.overdrive, self.gain = self._params_table[self.signal]
        rate, self.interf_fx = cached_loader.load_wav(str(self._interference_filepath))

    @property
    def name(self):
        return self._name

    def _apply_interference(self, wave_data, amount):
        cuts_lengths = (np.abs(np.random.normal(1.8, 0.5, amount)) * BASE_SAMPLING_RATE).astype("int32")
        for cut_length in cuts_lengths:
            # taking a random slice of the interference sound fx
            slice_start = random.randint(0, len(self.interf_fx) - cut_length)
            fx_slice = self.interf_fx[slice_start:slice_start + cut_length]
            start_frame = random.randint(0, len(wave_data) - cut_length)
            wave_data[start_frame:start_frame + cut_length] = fx_slice
        return wave_data

    def _apply_cuts(self, wave_data, amount):
        #  making cuts in the sound, of around 0.3 sec
        cuts_lengths = (np.abs(np.random.normal(0.3, 0.09, amount)) * BASE_SAMPLING_RATE).astype("int32")
        for cut_length in cuts_lengths:
            zeros = np.zeros(cut_length)
            start_frame = random.randint(0, len(wave_data) - cut_length)
            wave_data[start_frame:start_frame + cut_length] = zeros
        return wave_data

    def process(self, wave_data: np.ndarray):
        # first, giving the
        chain = AudioEffectsChain() \
            .sinc(high_pass_frequency=self.hpfreq, low_pass_frequency=self.lpfreq) \
            .overdrive(self.overdrive) \
            .gain(self.gain)
        phone_pass = chain(wave_data, sample_in=BASE_SAMPLING_RATE, sample_out=BASE_SAMPLING_RATE)
        # now we just need to add some interference to the signal

        seconds = len(phone_pass) / BASE_SAMPLING_RATE
        if len(phone_pass) > 2 * BASE_SAMPLING_RATE:  # adding cuts only if it's longer than 2 seconds
            if self.signal < 3:
                phone_pass = self._apply_cuts(phone_pass, int(seconds * 0.7))
            else:
                phone_pass = self._apply_cuts(phone_pass, int(seconds * 0.5))

        if self.signal == 1 and len(
                phone_pass) > 3 * BASE_SAMPLING_RATE:  # adding cuts only if it's longer than 3 seconds
            phone_pass = self._apply_interference(phone_pass, int(seconds / 3))  # approx 1 interf/ 3 sec
        return phone_pass


class FapEffect(AudioEffect):
    TIMEOUT = 180
    FAP_FX = DATA_FOLDER / Path("fpefpefpe.wav")

    def __init__(self):
        super().__init__()
        self.rate, self.fx_wave_array = cached_loader.load_wav(str(self.FAP_FX))

    def process(self, wave_data: np.ndarray) -> np.ndarray:
        padding_time = self.rate * 1.5
        rnd_pos = random.randint(0, len(self.fx_wave_array) - len(wave_data) - padding_time)
        return mix_tracks(self.fx_wave_array[rnd_pos:rnd_pos + len(wave_data) + int(padding_time)] * 1.3,
                          wave_data,
                          align="center")

#### Here are the effects groups ####


class VieuxPortEffect(EffectGroup):
    TIMEOUT = 150
    NAME = "du vieux port"

    class VieuxPortInterjections(HiddenTextEffect):
        """Kinda like a tourette effect, but but just a couple of southern interjections"""
        TIMEOUT = 150
        available_words = ["putain", "con", "bonne mère", "t'es fada", "peuchère"]

        def process(self, text: str):
            # the variable is called splitted because it pisses off this australian cunt that mboevink is
            space_splitted = [word for word in text.split(" ") if word != ""]
            reconstructed = ""
            for word in space_splitted:
                reconstructed += " " + word + " "
                if random.randint(1, 6) == 1:
                    reconstructed += ", %s ," % random.choice(self.available_words)
            if random.randint(1, 3) == 1:
                reconstructed += ", %s" % random.choice(self.available_words)
            return reconstructed

    @property
    def effects(self):
        southern_accent = AccentMarseillaisEffect()
        southern_accent._timeout = 150
        return [southern_accent, self.VieuxPortInterjections()]


class MwfeEffect(EffectGroup):
    NAME = "YE LA"
    TIMEOUT = 150

    class TextMwfeEffect(ExplicitTextEffect):
        TIMEOUT = 150

        _mwfe_punchlines = ["CHU LA", "OK BEN NIK TA MER", "JGO CHIER", "JGO FL", "PUTT 1 1 1 1 1 1 COUZ 1 1 1 1 1 1",
                            "A GERBER WALLAH", "YE OU JR", "YA QUOI", "OUÉVÈWB?", "PK LA VIE"]

        def process(self, text: str):
            if random.randint(0, 3) != 0:
                text = text.upper()
                if random.randint(0, 4) == 0:
                    text = random.choice(["MDR ", "WESH "]) + text
            else:
                text = random.choice(self._mwfe_punchlines)
            return text

    class VoiceMwfeEffect(VoiceEffect):
        TIMEOUT = 150

        def process(self, voice_params: VoiceParameters):
            return VoiceParameters(speed=110, pitch=60, voice_id=7)

    _sub_effects = [TextMwfeEffect, VoiceMwfeEffect]


class GodSpeakingEffect(EffectGroup):
    TIMEOUT = 120
    NAME = "gode mode"

    class BackgroundEffect(AudioEffect):
        """Adds a mood to the audio"""
        NAME = "ambiance"
        TIMEOUT = 120
        _sound_file = DATA_FOLDER / Path("godspeaking.wav")
        _gain = 0.4

        def __init__(self):
            super().__init__()
            self.rate, self.track_data = cached_loader.load_wav(str(self._sound_file))

        def process(self, wave_data: np.ndarray):
            padding_time = self.rate * 2
            rnd_pos = random.randint(0, len(self.track_data) - len(wave_data) - padding_time)
            return mix_tracks(self.track_data[rnd_pos:rnd_pos + len(wave_data) + padding_time] * self._gain,
                              wave_data,
                              align="center")

    @property
    def effects(self):
        return [ReverbManEffect(), self.BackgroundEffect()]


class VenerEffect(EffectGroup):
    TIMEOUT = 120
    NAME = "YÉ CHAUD"

    class UPPERCASEEffect(ExplicitTextEffect):
        TIMEOUT = 120

        def process(self, text: str):
            return text.upper()

    class AmbianceEffect(AudioEffect):
        """Adds a random mood to the audio"""
        NAME = "ambiance"
        TIMEOUT = 120
        sound_file = DATA_FOLDER / Path("stinkhole_shave_me_extract.wav")
        gain = 0.3

        def __init__(self):
            super().__init__()
            self.rate, self.track_data = cached_loader.load_wav(str(self.sound_file))

        @property
        def name(self):
            return self._name

        def process(self, wave_data: np.ndarray):
            padding_time = self.rate * 2
            rnd_pos = random.randint(0, len(self.track_data) - len(wave_data) - padding_time)
            return mix_tracks(self.track_data[rnd_pos:rnd_pos + len(wave_data) + padding_time] * self.gain,
                              wave_data * 1.2,
                              align="center")

    @property
    def effects(self):
        return [self.UPPERCASEEffect(), self.AmbianceEffect()]
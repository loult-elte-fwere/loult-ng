import json
import logging
import pickle
import re
from asyncio import create_subprocess_shell
from asyncio.subprocess import PIPE
from collections import OrderedDict
from datetime import datetime
from functools import lru_cache
from io import BytesIO
from itertools import chain
from os import path
from re import sub
from shlex import quote
from struct import pack
from typing import Union, Dict

import numpy
from resampy import resample
from scipy.io import wavfile
from voxpopuli import PhonemeList, Phoneme

logger = logging.getLogger('tools')


INVISIBLE_UNICODE_POINTS = chain(range(0x2060, 0x2070), range(0x2028, 0x2030),
                                 range(0x200b, 0x2010), [0xfeff])


INVISIBLE_CHARS = "[%s]" % "".join(chr(i) for i in INVISIBLE_UNICODE_POINTS)


class ToolsError(Exception):
    pass


class AudioRenderer:
    lang_voices_mapping = {"fr": ("fr", (1, 2, 3, 4, 5, 6, 7)),
                           "en": ("us", (1, 2, 3)),
                           "es": ("es", (1, 2)),
                           "de": ("de", (4, 5, 6, 7))}

    volumes_presets = {'fr1': 1.17138, 'fr2': 1.60851, 'fr3': 1.01283, 'fr4': 1.0964, 'fr5': 2.64384, 'fr6': 1.35412,
                       'fr7': 1.96092, 'us1': 1.658, 'us2': 1.7486, 'us3': 3.48104, 'es1': 3.26885, 'es2': 1.84053}

    def _get_additional_params(self, lang, voice_params : 'VoiceParameters'):
        """Uses the msg's lang field to figure out the voice, sex, and volume of the synth"""
        lang, voices = self.lang_voices_mapping.get(lang, self.lang_voices_mapping["fr"])
        voice = voices[voice_params.voice_id % len(voices)]

        if lang != 'fr':
            sex = voice
        else:
            sex = 4 if voice in (2, 4) else 1

        volume = 1
        if lang != 'de':
            volume = self.volumes_presets['%s%d' % (lang, voice)] * 0.5

        return lang, voice, sex, volume

    def _wav_format(self, wav : bytes):
        """Since the wav returned by Mbrola has an incomplete header (size of the wav isn't set), this
        function sets the wav's RIFF header to their actual values"""
        return wav[:4] + pack('<I', len(wav) - 8) + wav[8:40] + pack('<I', len(wav) - 44) + wav[44:]

    async def string_to_audio(self, text : str, lang : str, voice_params : 'VoiceParameters') -> bytes:
        """Renders directly a string to audio using an espeak -> mbrola pipeline
        (output is a wav bytes object)"""
        lang, voice, sex, volume = self._get_additional_params(lang, voice_params)
        synth_string = 'MALLOC_CHECK_=0 espeak -s %d -p %d --pho -q -v mb/mb-%s%d %s ' \
                       '| MALLOC_CHECK_=0 mbrola -v %g -e /usr/share/mbrola/%s%d/%s%d - -.wav' \
                       % (voice_params.speed, voice_params.pitch, lang, sex, text,
                          volume, lang, voice, lang, voice)
        logger.debug("Running synth command %s" % synth_string)
        process = await create_subprocess_shell(synth_string, stderr=PIPE, stdout=PIPE)
        wav, err = await process.communicate()
        return self._wav_format(wav)

    async def phonemes_to_audio(self, phonemes : PhonemeList, lang : str, voice_params : 'VoiceParameters') -> bytes:
        """Renders a phonemlist object to audio using mbrola"""
        lang, voice, sex, volume = self._get_additional_params(lang, voice_params)
        audio_synth_string = 'MALLOC_CHECK_=0 mbrola -v %g -e /usr/share/mbrola/%s%d/%s%d - -.wav' \
                             % (volume, lang, voice, lang, voice)
        logger.debug("Running mbrola command %s" % audio_synth_string)
        process = await create_subprocess_shell(audio_synth_string, stdout=PIPE,
                                                stdin=PIPE, stderr=PIPE)
        wav, err = await process.communicate(input=str(phonemes).encode('utf-8'))
        return self._wav_format(wav)

    async def string_to_phonemes(self, text : str, lang : str, voice_params : 'VoiceParameters') -> PhonemeList:
        """Renders an input string to a phonemlist object using espeak"""
        lang, voice, sex, volume = self._get_additional_params(lang, voice_params)
        phonem_synth_string = 'MALLOC_CHECK_=0 espeak -s %d -p %d --pho -q -v mb/mb-%s%d %s ' \
                              % (voice_params.speed, voice_params.pitch, lang, sex, text)
        logger.debug("Running espeak command %s" % phonem_synth_string)
        process = await create_subprocess_shell(phonem_synth_string,
                                                stdout=PIPE, stderr=PIPE)
        phonems, err = await process.communicate()
        return PhonemeList(phonems.decode('utf-8').strip())

    @staticmethod
    async def to_f32_16k(wav : bytes) -> numpy.ndarray:
        from .audio_tools import BASE_SAMPLING_RATE
        # converting the wav to ndarray, which is much easier to use for DSP
        rate, data = wavfile.read(BytesIO(wav))
        # casting the data array to the right format (float32, for usage by pysndfx)
        data = (data / (2. ** 15)).astype('float32')
        if rate != BASE_SAMPLING_RATE:
            data = resample(data, rate, BASE_SAMPLING_RATE)

        return BASE_SAMPLING_RATE, data

    @staticmethod
    def to_wav_bytes(data : numpy.ndarray, rate : int) -> bytes:
        # casting it back to int16
        data = (data * (2. ** 15)).astype("int16")
        # then, converting it back to binary data
        bytes_obj = bytes()
        bytes_buff = BytesIO(bytes_obj)
        wavfile.write(bytes_buff, rate, data)
        return bytes_buff.read()


class UtilitaryEffect:
    pass


class SpoilerBipEffect(UtilitaryEffect):
    """If there are ** phonems markers in the text, replaces their phonemic render by
    an equally long beep. If not, just returns the text"""
    _tags_phonems = {
        "en" : ("k_hIN", "dZINk"),
        "fr" : ("kiN", "ZiNk"),
        "de" : ("kIN", "gINk"),
        "es" : ("kin", "xink"),
    }

    def __init__(self, renderer : AudioRenderer, voice_params : 'VoiceParameters'):
        super().__init__()
        self.renderer = renderer
        self.voice_params = voice_params

    def _gen_beep(self, duration : int, lang : str):
        i_phonem = "i:" if lang == "de" else "i" # "i" phonem is not the same i german. Damn krauts
        return PhonemeList(PhonemeList([Phoneme("b", 103),
                                      Phoneme(i_phonem, duration, [(0, 103 * 3), (80, 103 * 3), (100, 103 * 3)]),
                                      Phoneme("p", 228)]))

    async def process(self, text: str, lang : str) -> Union[str, PhonemeList]:
        """Beeps out parts of the text that are tagged with double asterisks.
        It basicaly replaces the opening and closing asterisk with two opening and closing 'stop words'
        then finds the phonemic form of these two and replaces the phonems inside with an equivalently long beep"""
        occ_list = re.findall(r"\*\*.+?\*\*", text)
        if occ_list:
            # replace the "**text**" by "king text gink"
            tagged_occ_list = [" king %s gink " % occ.strip("*") for occ in occ_list]
            for occ, tagged_occ in zip(occ_list, tagged_occ_list):
                text = text.replace(occ, tagged_occ)
            # getting the phonemic form of the text
            phonems = await self.renderer.string_to_phonemes(text, lang, self.voice_params)
            # then using a simple state machine (in_beep is the state), replaces the phonems between
            # the right phonemic occurence with the phonems of a beep
            in_beep = False
            output, buffer = PhonemeList([]), PhonemeList([])
            while phonems:
                if PhonemeList(phonems[:3]).phonemes_str == self._tags_phonems[lang][0] and not in_beep:
                    in_beep, buffer = True, PhonemeList([])
                    phonems = PhonemeList(phonems[3:])
                elif PhonemeList(phonems[:4]).phonemes_str == self._tags_phonems[lang][1] and in_beep:
                    in_beep = False
                    # creating a beep of the buffer's duration
                    if buffer:
                        output += self._gen_beep(sum([pho.duration for pho in buffer]), lang)
                    phonems = phonems[4:]
                elif not in_beep:
                    output.append(phonems.pop(0))
                elif in_beep:
                    buffer.append(phonems.pop(0))
            return output
        else:
            return text


links_translation = {'fr': 'cliquez mes petits chatons',
                     'de': 'Klick drauf!',
                     'es': 'Clico JAJAJA',
                     'en': "Click it mate"}


def prepare_text_for_tts(text : str, lang : str) -> str:
    text = sub('(https?://[^ ]*[^.,?! :])', links_translation[lang], text)
    text = text.replace('#', 'hashtag ')
    return quote(text.strip(' -"\'`$();:.'))


def encode_json(data):
    return json.dumps(data, ensure_ascii=False).encode('utf-8')


@lru_cache()
def open_sound_file(relative_path):
    """Opens a wav file from a path relative to the current directory."""
    full_path = path.join(path.dirname(path.realpath(__file__)), relative_path)
    with open(full_path, "rb") as sound_file:
        return sound_file.read()


class OrderedDequeDict(OrderedDict):

    def __init__(self, size=100, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.size = size

    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        elif len(self) == self.size:
            self.popitem(last=False)

        OrderedDict.__setitem__(self, key, value)


class CachedOpener:

    FILE_EXPIRY_TIME = 15 * 60 # in seconds

    def __init__(self):
        self.files = {} # type: Dict[str,Union[str,byte]]
        self.last_hit = {} # type: Dict[str,datetime]

    def check_files_expiry(self):
        now = datetime.now()
        for filepath, last_hit in list(self.last_hit.items()):
            if (now - last_hit).seconds > self.FILE_EXPIRY_TIME:
                del self.files[filepath]
                del self.last_hit[filepath]

    def load_byte(self, filepath, read_func=None):
        if filepath not in self.files:
            with open(filepath, "rb") as bytefile:
                if read_func is None:
                    self.files[filepath] = bytefile.read()
                else:
                    self.files[filepath] = read_func(bytefile)

        self.last_hit[filepath] = datetime.now()
        self.check_files_expiry()
        return self.files[filepath]

    def load_pickle(self, filepath):
        return self.load_byte(filepath, pickle.load)

    def load_wav(self, filepath):
        return self.load_byte(filepath, wavfile.read)


cached_loader = CachedOpener()

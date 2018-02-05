import io
import logging
import random
import wave
from asyncio import get_event_loop
from hashlib import md5

import numpy as np
import pyaudio
from pysndfx import AudioEffectsChain
from scipy.io.wavfile import read

from salt import SALT
from tools import AudioEffect, PhonemicEffect
from tools.audio_tools import mix_tracks
from tools.effects.effects import BadCellphoneEffect
from tools.phonems import PhonemList, FrenchPhonems
from tools.users import User

logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("pysndfx").setLevel(logging.DEBUG)


class AudioFile:
    """A sound player"""
    chunk = 1024

    def __init__(self, file):
        """ Init audio stream """
        self.wf = wave.open(file, 'rb')
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format = self.p.get_format_from_width(self.wf.getsampwidth()),
            channels = self.wf.getnchannels(),
            rate = self.wf.getframerate(),
            output = True
        )

    def play(self):
        """ Play entire file """
        data = self.wf.readframes(self.chunk)
        while data != b'':
            self.stream.write(data)
            data = self.wf.readframes(self.chunk)

    def close(self):
        """ Graceful shutdown """
        self.stream.close()
        self.p.terminate()


class TestEffect(AudioEffect):
    NAME = "test"
    TIMEOUT = 30

    def process(self, wave_data: np.ndarray):
        low_shelf = AudioEffectsChain().bandreject(80, q=10.0)
        high_shelf = AudioEffectsChain().pitch(700)
        return high_shelf(wave_data, sample_in=16000, sample_out=16000)


class ConvertINT16PCM(AudioEffect):
    NAME = "convert"
    TIMEOUT = 30

    def process(self, wave_data: np.ndarray):
        return (wave_data * (2. ** 15)).astype("int16")


class AddTrackEffect(AudioEffect):
    NAME = "convert"
    TIMEOUT = 30

    def process(self, wave_data: np.ndarray):
        with open("tools/data/ambiance/war_mood.wav", "rb") as sndfile:
            rate, track_data = read(sndfile)
        # rnd_pos = random.randint(0,len(track_data) - len(wave_data))
        print(len(track_data))
        return mix_tracks(track_data[rate*3:len(wave_data) + rate*5] * 0.4, wave_data, align="center")


class SpeechDeformation(PhonemicEffect):
    NAME = "puberté"
    TIMEOUT = 30

    def process(self, phonems : PhonemList):
        for phonem in phonems:
            if phonem.name in FrenchPhonems.VOWELS and random.randint(1,2) == 1:
                phonem.duration *= 2
                factor = random.uniform(0.3, 2)
                phonem.pitch_modifiers = [(pos, int(pitch * factor)) for pos, pitch in phonem.pitch_modifiers]
        return phonems


fake_cookie = md5(("622545609233193a39466" + SALT).encode('utf8')).digest()
user = User(fake_cookie, "wesh", None)
for effect in []:
    print("Applying effect %s" % effect.name)
    user.state.add_effect(effect)

msg = """Non mais là les mecs faut se détendre si vous voulez sortir moi jme
ferais un plaisir de putain de sortir des pédales comme vous parce que putain jreconnais les gars comme vous genre
ils sla pètent ouais moi jsais chier debout et tout mais mon gars les mecs qui chient debout arrivent pas
a pisser assis et ceux qui pissent assis mon gars c'est des connards qui votent pour daesh aux élections
 régionales ça c'est avéré jai vécu des trucs dans ma life mon gars tsais meme pas ou ta sexualité se situe"""

loop = get_event_loop()
text, wav = loop.run_until_complete(user.render_message(msg, "fr"))

print("Text : ", text)

with open("/tmp/effect.wav", "wb") as wavfile:
    wavfile.write(wav)
a = AudioFile(io.BytesIO(wav))
a.play()
a.close()


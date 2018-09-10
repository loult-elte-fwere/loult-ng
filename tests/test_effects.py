import unittest
from tools.effects import AVAILABLE_EFFECTS
from tools.effects.effects import TextEffect, PhonemicEffect, AudioEffect, VoiceEffect
from voxpopuli import Voice
from tools.tools import AudioRenderer
from tools.users import VoiceParameters
from hashlib import md5
from asyncio import get_event_loop


class TestEffects(unittest.TestCase):

    text = "Les écoute pas ces sheitane c  moi le vrai crysw"

    def setUp(self):
        self.effects = {eff_class : set()
                        for eff_class in (PhonemicEffect, TextEffect, AudioEffect, VoiceEffect)}
        for effect_cls in set(AVAILABLE_EFFECTS):
            effect = effect_cls()
            for cls in self.effects.keys():
                if isinstance(effect, cls):
                    self.effects[cls].add(effect)
        self.voice = Voice(lang="fr")

    def test_text_effects(self):
        for effect in self.effects[TextEffect]:
            self.assertIsNotNone(effect.process(self.text))

    def test_phonemic_effects(self):
        pho = self.voice.to_phonemes(self.text)
        for effect in self.effects[PhonemicEffect]:
            self.assertIsNotNone(effect.process(pho))

    def test_audio_effects(self):
        wav = self.voice.to_audio(self.text)
        _, wav_array = get_event_loop().run_until_complete(AudioRenderer.to_f32_16k(wav))
        for effect in self.effects[AudioEffect]:
            self.assertIsNotNone(effect.process(wav_array))

    def test_voice_effects(self):
        cookie_hash = md5(("parce que nous we").encode('utf8')).digest()
        voice_params = VoiceParameters.from_cookie_hash(cookie_hash)
        for effect in self.effects[VoiceEffect]:
            self.assertIsNotNone(effect.process(voice_params))
import logging
import random
from asyncio import get_event_loop
from colorsys import hsv_to_rgb
from datetime import timedelta, datetime
from re import compile as regex
from struct import pack
from typing import Tuple, List
from os import path
import json

from config import FLOOD_DETECTION_WINDOW, BANNED_WORDS, FLOOD_WARNING_TIMEOUT, FLOOD_DETECTION_MSG_PER_SEC, \
    ATTACK_RESTING_TIME
from tools import pokemons

from tools.tools import AudioRenderer, SpoilerBipEffect, prepare_text_for_tts
from voxpopuli import PhonemeList

DATA_FILES_FOLDER = path.join(path.dirname(path.realpath(__file__)), "data/")

with open(path.join(DATA_FILES_FOLDER, "adjectifs.txt")) as file:
    adjectives = file.read().splitlines()

with open(path.join(DATA_FILES_FOLDER, "metiers.txt")) as file:
    jobs = file.read().splitlines()

with open(path.join(DATA_FILES_FOLDER, "villes.json")) as file:
    cities = json.load(file)

with open(path.join(DATA_FILES_FOLDER, "sexualite.txt")) as file:
    sexual_orient = file.read().splitlines()


class VoiceParameters:

    def __init__(self, speed : int, pitch : int, voice_id : int):
        self.speed = speed
        self.pitch = pitch
        self.voice_id = voice_id

    @classmethod
    def from_cookie_hash(cls, cookie_hash):
        return cls((cookie_hash[5] % 80) + 90, # speed
                   cookie_hash[0] % 100, # pitch
                   cookie_hash[1]) # voice_id


class PokeParameters:

    def __init__(self, color, poke_id, adj_id):
        self.color = color
        self.poke_id = poke_id
        self.pokename = pokemons.pokemon[self.poke_id]
        self.poke_adj = adjectives[adj_id]

    @classmethod
    def from_cookie_hash(cls, cookie_hash):
        color_rgb = hsv_to_rgb(cookie_hash[4] / 255, 0.8, 0.9)
        return cls('#' + pack('3B', *(int(255 * i) for i in color_rgb)).hex(), # color
                   (cookie_hash[2] | (cookie_hash[3] << 8)) % len(pokemons.pokemon) + 1,
                   (cookie_hash[5] | (cookie_hash[6] << 13)) % len(adjectives) + 1)


class PokeProfile:

    def __init__(self, job_id, age, city_id, sex_orient_id):
        self.job = jobs[job_id]
        self.age = age
        self.city, self.departement = cities[city_id]
        self.sex_orient = sexual_orient[sex_orient_id]

    def to_dict(self):
        return {"job": self.job,
                "age": self.age,
                "city": self.city,
                "departement": self.departement,
                "orientation": self.sex_orient}

    @classmethod
    def from_cookie_hash(cls, cookie_hash):
        return cls((cookie_hash[4] | (cookie_hash[2] << 7)) % len(jobs), # job
                   (cookie_hash[3] | (cookie_hash[5] << 6)) % 62 + 18, # age
                   ((cookie_hash[6] * cookie_hash[4] << 17)) % len(cities), # city
                   (cookie_hash[2] | (cookie_hash[3] << 4)) % len(sexual_orient)) # sexual orientation


class UserState:

    detection_window = timedelta(seconds=FLOOD_DETECTION_WINDOW)

    def __init__(self, banned_words=BANNED_WORDS):
        from tools.effects import AudioEffect, HiddenTextEffect, ExplicitTextEffect, PhonemicEffect, \
            VoiceEffect

        self.effects = {cls: [] for cls in
                        (AudioEffect, HiddenTextEffect, ExplicitTextEffect, PhonemicEffect, VoiceEffect)}
        self.connection_time = datetime.now()
        self.last_attack = datetime.now()  # any user has to wait some time before attacking, after entering the chan
        self.last_message = datetime.now()
        self.timestamps = list()
        self.has_been_warned = False # User has been warned he shouldn't flood
        self._banned_words = [regex(word) for word in banned_words]
        self.is_shadowbanned = False # User has been shadowbanned

    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)
        if name == "has_been_warned" and value:
            # it's safe since the whole application only
            # uses the default loop
            loop = get_event_loop()
            loop.call_later(FLOOD_WARNING_TIMEOUT, self._reset_warning)

    def add_effect(self, effect):
        """Adds an effect to one of the active tools list (depending on the effect type)"""
        from .effects.effects import EffectGroup, AudioEffect, HiddenTextEffect, ExplicitTextEffect, PhonemicEffect, \
            VoiceEffect

        if isinstance(effect, EffectGroup):  # if the effect is a meta-effect (a group of several effects)
            added_effects = effect.effects
        else:
            added_effects = [effect]

        for efct in added_effects:
            for cls in (AudioEffect, HiddenTextEffect, ExplicitTextEffect, PhonemicEffect, VoiceEffect):
                if isinstance(efct, cls):
                    if len(self.effects[cls]) == 5:  # only 5 effects of one type allowed at a time
                        self.effects[cls].pop(0)
                    self.effects[cls].append(efct)
                    break

    def reset_flood_detection(self):
        self.timestamps = list()

    def check_flood(self, msg):
        self._add_timestamp()
        threshold = FLOOD_DETECTION_MSG_PER_SEC * FLOOD_DETECTION_WINDOW
        return len(self.timestamps) > threshold or self.censor(msg)

    def _add_timestamp(self):
        """Add a timestamp for a user's message, and clears timestamps which are too old"""
        # removing msg timestamps that are out of the detection window
        now = datetime.now()
        self.last_message = now
        self._refresh_timestamps(now)
        self.timestamps.append(now)

    def censor(self, msg):
        return any(regex_word.fullmatch(msg) for regex_word in self._banned_words)

    def _reset_warning(self):
        """
        Helper with a better debug representation than
        a lambda for use as a callback in the event loop.
        """
        self.has_been_warned = False

    def _refresh_timestamps(self, now=None):
        # now has to be a possible argument else there might me slight
        # time differences between the current time of the calling function
        # and this one's current time.
        now = now if now else datetime.now()
        # removing msg timestamps that are out of the detection window
        updated = [timestamp for timestamp in self.timestamps
                   if timestamp + self.detection_window > now]
        self.timestamps = updated


class User:
    """Stores a user's state and parameters, which are also used to render the user's audio messages"""

    def __init__(self, cookie_hash, channel, client):
        """Initiating a user using its cookie md5 hash"""
        self.audio_renderer = AudioRenderer()
        self.voice_params = VoiceParameters.from_cookie_hash(cookie_hash)
        self.poke_params = PokeParameters.from_cookie_hash(cookie_hash)
        self.poke_profile = PokeProfile.from_cookie_hash(cookie_hash)
        self.user_id = cookie_hash.hex()[-16:]
        self.cookie_hash = cookie_hash

        self.channel = channel
        self.clients = [client]
        self.state = UserState()
        self._info = None

    def reload_params_from_cookie(self):
        self._info = None
        self.voice_params = VoiceParameters.from_cookie_hash(self.cookie_hash)
        self.poke_params = PokeParameters.from_cookie_hash(self.cookie_hash)
        self.poke_profile = PokeProfile.from_cookie_hash(self.cookie_hash)

    def __hash__(self):
        return self.user_id.__hash__()

    def __eq__(self, other):
        return self.user_id == other.user_id

    def throw_dice(self, type="attack") -> Tuple[int, int]:
        bonus = (datetime.now() - self.state.last_attack).seconds // ATTACK_RESTING_TIME if type == "attack" else 0
        return random.randint(1, 100), bonus

    @property
    def info(self):
        if self._info is None:
            self._info = {
                'userid': self.user_id,
                'params': {
                    'name': self.poke_params.pokename,
                    'img': str(self.poke_params.poke_id).zfill(3),
                    'color': self.poke_params.color,
                    'adjective': self.poke_params.poke_adj
                },
                'profile': self.poke_profile.to_dict()

            }
        return self._info

    @staticmethod
    def apply_effects(input_obj, effect_list: List['Effect']):
        if effect_list:
            for effect in effect_list:
                if effect.is_expired():
                    effect_list.remove(effect)  # if the effect has expired, remove it
                else:
                    try:
                        input_obj = effect.process(input_obj)
                    except Exception as e:
                        logging.warning("Error while applying effect %s, error: \n %s"
                                        % (effect.__class__.__name__, str(e)))

        return input_obj

    async def _vocode(self, text: str, lang: str) -> bytes:
        """Renders a text and a language to a wav bytes object using espeak + mbrola"""
        # if there are voice effects, apply them to the voice renderer's voice and give them to the renderer
        from tools.effects import VoiceEffect, PhonemicEffect
        if self.state.effects[VoiceEffect]:
            voice_params = self.apply_effects(self.voice_params, self.state.effects[VoiceEffect])
        else:
            voice_params = self.voice_params

        # apply the beep effect for spoilers
        beeped = await SpoilerBipEffect(self.audio_renderer, voice_params).process(text, lang)

        if isinstance(beeped, PhonemeList) or self.state.effects[PhonemicEffect]:

            modified_phonems = None
            if isinstance(beeped, PhonemeList) and self.state.effects[PhonemicEffect]:
                # if it's already a phonem list, we apply the effect diretcly
                modified_phonems = self.apply_effects(beeped, self.state.effects[PhonemicEffect])
            elif isinstance(beeped, PhonemeList):
                # no effects, only the beeped phonem list
                modified_phonems = beeped
            elif self.state.effects[PhonemicEffect]:
                # first running the text-to-phonems conversion, then applying the phonemic tools
                phonems = await self.audio_renderer.string_to_phonemes(text, lang, voice_params)
                modified_phonems = self.apply_effects(phonems, self.state.effects[PhonemicEffect])

            #rendering audio using the phonemlist
            return await self.audio_renderer.phonemes_to_audio(modified_phonems, lang, voice_params)
        else:
            # regular render
            return await self.audio_renderer.string_to_audio(text, lang, voice_params)

    async def render_message(self, text: str, lang: str):
        from tools.effects import ExplicitTextEffect, HiddenTextEffect, AudioEffect

        cleaned_text = text[:500]
        # applying "explicit" effects (visible to the users)
        displayed_text = self.apply_effects(cleaned_text, self.state.effects[ExplicitTextEffect])
        # applying "hidden" texts effects (invisible on the chat, only heard in the audio)
        rendered_text = self.apply_effects(displayed_text, self.state.effects[HiddenTextEffect])
        rendered_text = prepare_text_for_tts(rendered_text, lang)

        # rendering the audio from the text
        wav = await self._vocode(rendered_text, lang)

        # if there are effets in the audio_effect list, we run it
        if self.state.effects[AudioEffect]:
            # converting to f32 (more standard) and resampling to 16k if needed, and converting to a ndarray
            rate , data = await self.audio_renderer.to_f32_16k(wav)
            # applying the effects pipeline to the sound
            data = self.apply_effects(data, self.state.effects[AudioEffect])
            # converting the sound's ndarray back to bytes
            wav = self.audio_renderer.to_wav_bytes(data, rate)

        return displayed_text, wav

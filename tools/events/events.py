import random
from datetime import datetime, timedelta, time
from time import time as timestamp
from typing import List
from os import path
from .base import next_occ

import yaml

from tools.effects.effects import AutotuneEffect, ReverbManEffect, RobotVoiceEffect, \
    AngryRobotVoiceEffect, PitchShiftEffect, GrandSpeechMasterEffect, VisualEffect, VoiceCloneEffect, \
    VoiceSpeedupEffect, BadCellphoneEffect, RythmicEffect
from tools.events.base import PeriodicEvent, PseudoPeriodicEvent, ChannelModEvent
from tools.users import User


class SayHi(PeriodicEvent):

    async def trigger(self, loultstate):
        for channel in loultstate.chans.values():
            user = next(iter(channel.users.values()))
            channel.broadcast(type='msg', userid=user.user_id,
                              msg="WESH WESH", date=timestamp() * 1000)


class BienDowmiwEvent(PeriodicEvent):

    PERIOD = timedelta(days=1)
    FIRST_OCC = next_occ(datetime.day, time(hour=0, minute=0))

    class BienDowmiwEffect(VisualEffect):
        TIMEOUT = 10
        NAME = "fnre du biendowmiw"
        TAG = "biendowmiw"

    async def trigger(self, loultstate):
        for channel in loultstate.chans.values():
            for user in channel.users.values():
                if random.randint(1,10) == 1:
                    effect = self.BienDowmiwEffect()
                    channel.broadcast(type='attack', date=timestamp() * 1000,
                                      event='effect',
                                      tag=effect.TAG,
                                      target_id=user.user_id,
                                      effect=effect.name,
                                      timeout=effect.timeout)


class EffectEvent(PeriodicEvent):

    def _select_random_users(self, user_list: List[User]) -> List[User]:
        #filtering out users who haven't talked in the last 20 minutes
        now = datetime.now()
        users = [user for user in user_list if (now - user.state.last_message).seconds < 20 * 60]
        # selecting 3 random users
        selected_users = []
        while users and len(selected_users) < 3:
            rnd_user = users.pop(random.randint(0,len(users) - 1))
            selected_users.append(rnd_user)
        return selected_users


class BienChantewEvent(EffectEvent):
    PERIOD = timedelta(days=1)
    FIRST_OCC = next_occ(datetime.day, time(hour=22, minute=0))

    async def trigger(self, loultstate):
        for channel in loultstate.chans.values():
            selected_users = self._select_random_users(channel.users.values())
            for user in selected_users:
                autotune = AutotuneEffect()
                ouevewb = ReverbManEffect()
                autotune._timeout = 7200 # 2 hours
                ouevewb._timeout = 7200 # 2 hours
                user.state.add_effect(autotune)
                user.state.add_effect(ouevewb)
                channel.broadcast(type="notification",
                                  event_type="autotune",
                                  date=timestamp() * 1000,
                                  msg="%s a été visité par le Qwil du bon ouévèwb!" % user.poke_params.pokename)


class MaledictionEvent(EffectEvent):
    PERIOD = timedelta(days=1)
    FIRST_OCC = next_occ(datetime.day, time(hour=4, minute=0))

    async def trigger(self, loultstate):
        for channel in loultstate.chans.values():
            selected_users = self._select_random_users(channel.users.values())
            for user in selected_users:
                effects = [GrandSpeechMasterEffect(), RobotVoiceEffect(), AngryRobotVoiceEffect(), PitchShiftEffect()]
                for effect in effects:
                    effect._timeout = 7200
                    user.state.add_effect(effect)
                channel.broadcast(type="notification",
                                  event_type="curse",
                                  date=timestamp() * 1000,
                                  msg="%s a été touché par la malédictionw!" % user.poke_params.pokename)


class UsersVoicesShuffleEvent(PseudoPeriodicEvent):
    PSEUDO_PERIOD = timedelta(hours=4)
    VARIANCE = timedelta(hours=0.5)

    async def trigger(self, loultstate):
        for channel in loultstate.chans.values():
            users_lists = list(channel.users.values())
            random.shuffle(users_lists)
            for user_receiver, user_giver in zip(channel.users.values(), users_lists):
                user_receiver.state.add_effect(VoiceCloneEffect(user_giver.voice_params))
            channel.broadcast(type="notification",
                              event_type="voice_shuffle",
                              date=timestamp() * 1000,
                              msg="Les voix des pokémons ont été mélangées!")


class AmphetamineEvent(PseudoPeriodicEvent):

    async def trigger(self, loultstate):
        for channel in loultstate.chans.values():
            for user in channel.users.values():
                effect = VoiceSpeedupEffect(factor=2.4)
                effect._timeout = 600
                user.state.add_effect(effect)
            channel.broadcast(type="notification",
                              event_type="amphetamine",
                              date=timestamp() * 1000,
                              msg="LE LOULT EST SOUS AMPHETAMINE!")


class TunnelEvent(PseudoPeriodicEvent):
    PSEUDO_PERIOD = timedelta(hours=2)
    VARIANCE = timedelta(hours=0.5)

    async def trigger(self, loultstate):
        for channel in loultstate.chans.values():
            for user in channel.users.values():
                effect = BadCellphoneEffect(signal_strength=random.randint(1,2))
                effect._timeout = 300
                user.state.add_effect(effect)
            channel.broadcast(type="notification",
                              event_type="tunnel",
                              date=timestamp() * 1000,
                              msg="Le loult passe sous un tunnel!")


class MusicalEvent(PseudoPeriodicEvent):
    """Adds several effects that make everyone a real good singer"""
    PSEUDO_PERIOD = timedelta(hours=2.5)
    VARIANCE = timedelta(hours=0.5)

    async def trigger(self, loultstate):
        for channel in loultstate.chans.values():
            for user in channel.users.values():
                effects = [RythmicEffect(), AutotuneEffect(), ReverbManEffect()]
                for effect in effects:
                    effect._timeout = 400
                    user.state.add_effect(effect)
            channel.broadcast(type="notification",
                              event_type="musical",
                              date=timestamp() * 1000,
                              msg="Le loult est une comédie musicale!")


class UsersMixupEvent(ChannelModEvent):

    EVENT_TYPE = "users_mixup"
    PSEUDO_PERIOD = timedelta(hours=5)
    VARIANCE = timedelta(hours=0.7)
    DURATION = timedelta(minutes=10)

    def __init__(self):
        super().__init__()
        self.with_voices = None # set when the fuckup is called

    @property
    def event_message(self):
        msg =  "Les pokémons se sont tous mélangés!"
        if self.with_voices:
            msg += " (et même les voix!)"
        return msg

    def _fuckup_channel_users(self, channel):
        self.with_voices = random.randint(0,1) == 0
        users_params = [(user.poke_params, user.poke_profile, user.voice_params)
                        for user in channel.users.values()]
        random.shuffle(users_params)
        for user, (params, profile, voice) in zip(channel.users.values(), users_params):
            user._info = None
            user.poke_params = params
            user.poke_profile = profile
            if self.with_voices:
                user.voice_params = voice


class CloneArmyEvent(ChannelModEvent):

    EVENT_TYPE = "clone_army"
    PSEUDO_PERIOD = timedelta(hours=5)
    VARIANCE = timedelta(hours=0.7)
    DURATION = timedelta(minutes=10)

    def __init__(self):
        super().__init__()
        self.picked_user = None # defined when the fuckup function is called

    @property
    def event_message(self):
        return "Le loult est une armée de clones de %s!" % self.picked_user

    def _fuckup_channel_users(self, channel):
        picked_usr = random.choice(list(channel.users.values()))
        self.picked_user = picked_usr.poke_params.pokename + " " + picked_usr.poke_params.poke_adj
        params, profile, voice = picked_usr.poke_params, picked_usr.poke_profile, picked_usr.voice_params
        for user in channel.users.values():
            user._info = None
            user.poke_params = params
            user.poke_profile = profile
            user.voice_params = voice


class ThemeRenameEvent(ChannelModEvent):

    EVENT_TYPE = "theme_rename"
    THEMES_FILE = path.join(path.dirname(path.realpath(__file__)), "data/themes.yml")
    PSEUDO_PERIOD = timedelta(hours=5)
    VARIANCE = timedelta(hours=0.7)
    DURATION = timedelta(minutes=10)

    def __init__(self):
        super().__init__()
        with open(self.THEMES_FILE) as themesfile:
            self.themes = yaml.load(themesfile)
        self.theme_descr = None # defined when the fuckup function is called

    @property
    def event_message(self):
        return "Le loult est devenu %s!" % self.theme_descr

    def _fuckup_channel_users(self, channel):
        picked_theme = random.choice(self.themes)
        self.theme_descr = picked_theme["description"]
        for user in channel.users.values():
            user._info = None
            user.poke_params.pokename = random.choice(picked_theme["names"])
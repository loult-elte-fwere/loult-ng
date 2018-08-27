import random
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime
from time import time as timestamp
from typing import List

from tools.effects.effects import AutotuneEffect, ReverbManEffect, RobotVoiceEffect, \
    AngryRobotVoiceEffect, PitchShiftEffect, GrandSpeechMasterEffect, VisualEffect, VoiceCloneEffect, \
    VoiceSpeedupEffect, BadCellphoneEffect, RythmicEffect
from tools.events.base import PeriodicEvent, PseudoPeriodicEvent, FiniteDurationEventMixin
from tools.users import User


class SayHi(PeriodicEvent):

    async def happen(self, loultstate):
        for channel in loultstate.chans.values():
            user = next(iter(channel.users.values()))
            channel.broadcast(type='msg', userid=user.user_id,
                              msg="WESH WESH", date=timestamp() * 1000)


class BienDowmiwEvent(PeriodicEvent):

    class BienDowmiwEffect(VisualEffect):
        TIMEOUT = 10
        NAME = "fnre du biendowmiw"
        TAG = "biendowmiw"

    async def happen(self, loultstate):
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

    async def happen(self, loultstate):
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

    async def happen(self, loultstate):
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
                                  msg="%s a été touché par la maledictionw!" % user.poke_params.pokename)


class UsersVoicesShuffleEvent(PseudoPeriodicEvent):

    async def happen(self, loultstate):
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

    async def happen(self, loultstate):
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

    async def happen(self, loultstate):
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

    async def happen(self, loultstate):
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


class UserListModEvent(PseudoPeriodicEvent, FiniteDurationEventMixin):

    EVENT_TYPE = ""

    @property
    def event_message(self):
        return "Gros bazar sur le loult"

    def _fuckup_userlist(self, users_list) -> OrderedDict:
        pass

    def happen(self, loultstate):
        for channel in loultstate.chans.values():
            users_list = OrderedDict([(user_id, deepcopy(user.info))
                                     for user_id, user in channel.users.items()])
            channel.update_userlist(self._fuckup_userlist(users_list))
            channel.broadcast(type="notification",
                              event_type=self.EVENT_TYPE,
                              date=timestamp() * 1000,
                              msg=self.event_message)
        super().happen(loultstate)

    def finish(self, loultstate):
        """Reseting the userlist to real value for each user in each channel"""
        for channel in loultstate.chans.values():
            users_list = OrderedDict([(user_id, deepcopy(user.info))
                                     for user_id, user in channel.users.items()])
            channel.update_userlist(users_list)
        super().finish(loultstate)



import random
from datetime import datetime, timedelta, time
from pathlib import Path
from time import time as timestamp
from typing import List

import yaml

from .base import PeriodicEvent, PseudoPeriodicEvent, ChannelModEvent
from .base import next_occ
from ..effects.effects import AutotuneEffect, ReverbManEffect, RobotVoiceEffect, AngryRobotVoiceEffect, \
    PitchShiftEffect, GrandSpeechMasterEffect, VisualEffect, VoiceCloneEffect, VoiceSpeedupEffect, BadCellphoneEffect, \
    RythmicEffect, VenerEffect
from ..objects import get_random_object, Quiver, C4, Detonator, SantasSack
from ..objects.objects import DiseaseObject, BaseballBat, AlcoholBottle
from ..objects.weapons import RobinHoodsBow
from ..tools import load_bytes
from ..users import User

DATA_PATH = Path(__file__).absolute().parent / Path("data")


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
                if random.randint(1, 10) == 1:
                    effect = self.BienDowmiwEffect()
                    channel.broadcast(type='attack', date=timestamp() * 1000,
                                      event='effect',
                                      tag=effect.TAG,
                                      target_id=user.user_id,
                                      effect=effect.name,
                                      timeout=effect.timeout)


class EffectEvent(PeriodicEvent):

    def _select_random_users(self, user_list: List[User]) -> List[User]:
        # filtering out users who haven't talked in the last 20 minutes
        now = datetime.now()
        users = [user for user in user_list if (now - user.state.last_message).seconds < 20 * 60]
        # selecting 3 random users
        selected_users = []
        while users and len(selected_users) < 3:
            rnd_user = users.pop(random.randint(0, len(users) - 1))
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
                autotune._timeout = 7200  #  2 hours
                ouevewb._timeout = 7200  #  2 hours
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
                effect = BadCellphoneEffect(signal_strength=random.randint(1, 2))
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


class TreizeNRV(PseudoPeriodicEvent):
    """Everyone's very, very angry now"""
    PSEUDO_PERIOD = timedelta(hours=3.5)
    VARIANCE = timedelta(hours=0.5)

    async def trigger(self, loultstate):
        for channel in loultstate.chans.values():
            for user in channel.users.values():
                user.state.add_effect(VenerEffect())
            channel.broadcast(type="notification",
                              event_type="13NRV",
                              date=timestamp() * 1000,
                              msg="TOUT LE MONDE EST 13NRV PUTT 1 1 1 1 1 1")


class UsersMixupEvent(ChannelModEvent):
    """All the users's profiles are mixed up, sometimes including their voices"""

    EVENT_TYPE = "users_mixup"
    PSEUDO_PERIOD = timedelta(hours=5)
    VARIANCE = timedelta(hours=0.7)
    DURATION = timedelta(minutes=10)

    def __init__(self):
        super().__init__()
        self.with_voices = None  # set when the fuckup is called

    @property
    def event_message(self):
        msg = "Les pokémons se sont tous mélangés!"
        if self.with_voices:
            msg += " (et même les voix!)"
        return msg

    def _fuckup_channel_users(self, channel):
        self.with_voices = random.randint(0, 1) == 0
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
    """Everyone's a clone of someone"""

    EVENT_TYPE = "clone_army"
    PSEUDO_PERIOD = timedelta(hours=5)
    VARIANCE = timedelta(hours=0.7)
    DURATION = timedelta(minutes=10)

    def __init__(self):
        super().__init__()
        self.picked_user = None  # defined when the fuckup function is called

    @property
    def event_message(self):
        return f"Le loult est une armée de clones de {self.picked_user}!"

    def _fuckup_channel_users(self, channel):
        if not channel.users:
            return

        picked_usr = random.choice(list(channel.users.values()))
        self.picked_user = picked_usr.poke_params.pokename + " " + picked_usr.poke_params.poke_adj
        params, profile, voice = picked_usr.poke_params, picked_usr.poke_profile, picked_usr.voice_params
        for user in channel.users.values():
            user._info = None
            user.poke_params = params
            user.poke_profile = profile
            user.voice_params = voice


class ThemeRenameEvent(ChannelModEvent):
    """Everyone gets a new name based on a theme"""

    EVENT_TYPE = "theme_rename"
    THEMES_FILE = DATA_PATH / Path("themes.yml")
    PSEUDO_PERIOD = timedelta(hours=3)
    VARIANCE = timedelta(hours=0.4)
    DURATION = timedelta(minutes=10)

    def __init__(self):
        super().__init__()
        with open(self.THEMES_FILE) as themesfile:
            self.themes = yaml.safe_load(themesfile)
        self.theme_descr = None  # defined when the fuckup function is called

    @property
    def event_message(self):
        return "Le loult est devenu %s!" % self.theme_descr

    def _fuckup_channel_users(self, channel):
        picked_theme = random.choice(self.themes)
        self.theme_descr = picked_theme["description"]
        for user in channel.users.values():
            user._info = None
            user.poke_params.pokename = random.choice(picked_theme["names"])


class ObjectDropEvent(PseudoPeriodicEvent):
    """Drops an object on a random connected user"""
    PSEUDO_PERIOD = timedelta(minutes=60)
    VARIANCE = timedelta(hours=0.1)

    async def trigger(self, loultstate):
        for channel in loultstate.chans.values():
            if not channel.users:
                continue

            user = random.choice(list(channel.users.values()))
            user.state.inventory.add(get_random_object())
            for client in user.clients:
                client.send_json(type="notification",
                                 msg="Vous avez reçu un objet, regardez votre inventaire!")


class InfectionEvent(PseudoPeriodicEvent):
    """Gives an infectuous disease to a random connected user"""
    PSEUDO_PERIOD = timedelta(hours=6)
    VARIANCE = timedelta(hours=0.2)

    async def trigger(self, loultstate):
        for channel in loultstate.chans.values():
            if not channel.users:
                continue

            user = random.choice(list(channel.users.values()))
            user.state.inventory.add(DiseaseObject(user.poke_params.fullname))
            channel.broadcast(type="notification",
                              msg="%s a été infecté!" % user.poke_params.fullname)


class LynchingEvent(PseudoPeriodicEvent):
    """Everyone gets a baseball bat, except for one"""
    PSEUDO_PERIOD = timedelta(hours=8)
    VARIANCE = timedelta(hours=0.4)

    async def trigger(self, loultstate):
        for channel in loultstate.chans.values():
            if not channel.users:
                continue

            usr_list = list(channel.users.values())
            lynched_usr = usr_list.pop(random.randint(0, len(usr_list) - 1))
            for usr in usr_list:
                usr.state.inventory.add(BaseballBat(lynched_usr.user_id, lynched_usr.poke_params.fullname))
            channel.broadcast(type="notification",
                              msg="%s va passer un sale quart d'heure!" % lynched_usr.poke_params.fullname)


class PubBrawlEvent(PseudoPeriodicEvent):
    """Everyone gets a drink"""
    PSEUDO_PERIOD = timedelta(hours=6)
    VARIANCE = timedelta(hours=0.4)

    async def trigger(self, loultstate):
        for channel in loultstate.chans.values():
            for usr in channel.users.values():
                usr.state.inventory.add(AlcoholBottle())
            channel.broadcast(type="notification",
                              msg="Tournée générale dans le Loult Saloon!")


class FireworksEvent(PseudoPeriodicEvent):
    """Drops ammo in the common inventory"""
    PSEUDO_PERIOD = timedelta(hours=2.5)
    VARIANCE = timedelta(hours=0.2)

    async def trigger(self, loultstate):
        for channel in loultstate.chans.values():
            usr_list = list(channel.users.values())
            detonator_usr = usr_list.pop(random.randint(0, len(usr_list) - 1))
            # if the user is alone in the channel, it's "aborted"
            if not usr_list:
                continue

            detonator_usr.state.inventory.add(Detonator())
            for _ in range(0, 5):
                rnd_usr = random.choice(usr_list)
                rnd_usr.state.inventory.add(C4())
            for client in detonator_usr.clients:
                client.send_json(type="notification",
                                 msg="Vous avez reçu un détonateur. Utilisez-le pour déclencher un beau feu d'artifice")


class RobinHoodEvent(PseudoPeriodicEvent):
    """Someone becomes robin hood, savior of the poor"""
    PSEUDO_PERIOD = timedelta(hours=6)
    VARIANCE = timedelta(hours=0.4)

    async def trigger(self, loultstate):
        for channel in loultstate.chans.values():
            user = random.choice(list(channel.users.values()))
            channel.broadcast(type="notification",
                              msg=f"{user.poke_params.fullname} est robin du Loult!")
            user.state.inventory.add(RobinHoodsBow())
            user.state.inventory.add(Quiver(arrows=5))
            user.poke_params.pokename = "Robin"
            user.poke_params.poke_adj = "du Loult"
            user._info = None
            channel.update_userlist()


class SantaEvent(PseudoPeriodicEvent):
    """Someone becomes santa"""
    PSEUDO_PERIOD = timedelta(hours=4)
    VARIANCE = timedelta(hours=0.1)

    async def trigger(self, loultstate):
        for channel in loultstate.chans.values():
            user = random.choice(list(channel.users.values()))
            channel.broadcast(type="notification",
                              msg=f"{user.poke_params.fullname} est le père noël!",
                              binary_payload=load_bytes(DATA_PATH / Path("christmas_bells.mp3")))
            user.state.inventory.add(SantasSack(presents=10))
            user.poke_params.pokename = "Pawpaw"
            user.poke_params.poke_adj = "Nowel"
            user._info = None
            channel.update_userlist()

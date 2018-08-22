from datetime import timedelta, datetime, time, date
from typing import List, Tuple
import asyncio
from time import time as timestamp
import random

from tools.state import LoultServerState
from tools.effects.effects import AutotuneEffect, ReverbManEffect, SkyblogEffect, RobotVoiceEffect, \
    AngryRobotVoiceEffect, PitchShiftEffect, GrandSpeechMasterEffect, VisualEffect, VoiceCloneEffect, \
    VoiceSpeedupEffect, BadCellphoneEffect, RythmicEffect
from tools.users import User


def next_occ(period, occ_time: time):
    now = datetime.now()
    today = date.today()
    if period is datetime.day:
        if now > datetime.combine(today, occ_time):
            return datetime.combine(today + timedelta(days=1), occ_time)
        else:
            return datetime.combine(today, occ_time)

    elif period is datetime.hour:
        if now.minute > occ_time.minute:
            return datetime.combine(today, time(hour=now.hour + 1, minute=occ_time.minute))
        else:
            return datetime.combine(today, time(hour=now.hour, minute=occ_time.minute))


class Event:

    def __init__(self):
        self.next_occurence = None

    def update_next_occ(self, now):
        pass

    async def happen(self, loultstate):
        pass


class PeriodicEvent(Event):

    def __init__(self, period: timedelta, first_occ: datetime=None):
        super().__init__()
        self.period = period
        self.next_occurence = first_occ if first_occ is not None else datetime.now()

    def update_next_occ(self, now):
        self.next_occurence += self.period


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


class PseudoPeriodicEvent(Event):

    def __init__(self, pseudo_period: timedelta, variance: timedelta, first_occ: datetime=None, ):
        super().__init__()
        self.pseudo_period = pseudo_period
        self.variance = variance
        if first_occ is None:
            self.next_occurence = datetime.now()
            self.update_next_occ(None)
        else:
            self.next_occurence = first_occ

    def update_next_occ(self, now):
        new_period_secs = random.gauss(self.pseudo_period.total_seconds(), self.variance.total_seconds())
        new_period_timedelta = timedelta(seconds=new_period_secs)
        self.next_occurence += new_period_timedelta


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

class EventScheduler:

    def __init__(self, loultstate, events: List[Event]):
        self.loultstate = loultstate
        self.events = events
        self.schedule = []  # type:List[Tuple[datetime, Event]]

    def _order_schedule(self):
        self.schedule.sort(key=lambda x: x[0])

    def _build_scheduler(self):
        now = datetime.now()
        for event in self.events:
            if event.next_occurence < now:
                event.update_next_occ(now)
            self.schedule.append((event.next_occurence, event))
        self._order_schedule()

    async def start(self):
        self._build_scheduler()
        while self.schedule:
            now = datetime.now()
            event_time, event = self.schedule.pop(0)
            event.update_next_occ(now)
            self.schedule.append((event.next_occurence, event))
            if (event_time - now).total_seconds() > 0: # if we're "late" then the event happens right away
                await asyncio.sleep((event_time - now).total_seconds())
            await event.happen(self.loultstate)
            self._order_schedule()
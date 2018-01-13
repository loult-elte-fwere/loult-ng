from datetime import timedelta, datetime, time, date
from typing import List, Tuple
import asyncio
from time import time as timestamp

from poke import LoultServerState


def compute_next_occ(period, occ_time: time):
    now = datetime.now()
    today = date.today()
    if period is datetime.day:
        if now > datetime.combine(today, occ_time):
            return datetime.combine(today + timedelta(days=1), occ_time)
        else:
            return datetime.combine(today, occ_time)

    elif period is datetime.hour:
        if now.minute > occ_time.minute:
            return datetime.combine(today, time(hour=now.hour + 1, minute=occ_minute))
        else:
            return datetime.combine(today, time(hour=now.hour, minute=occ_minute))

class Event:

    def __init__(self, loultstate: LoultServerState):
        self.loultstate = loultstate
        self.next_occurence = None

    def update_next_occ(self, now):
        pass

    async def happen(self):
        pass


class PeriodicEvent(Event):

    def __init__(self, loultstate, period: timedelta, first_occ=None):
        super().__init__(loultstate)
        self.period = period
        self.next_occurence = first_occ if first_occ is not None else datetime.now()

    def update_next_occ(self, now):
        self.next_occurence = self.next_occurence + self.period


class SayHi(PeriodicEvent):

    async def happen(self):
        for channel in self.loultstate.chans.values():
            user = next(iter(channel.users.values()))
            client = next(iter(channel.clients))
            client._broadcast_to_channel(type='msg', userid=user.user_id,
                                         msg="WESH WESH", date=timestamp() * 1000)



class EventScheduler:

    def __init__(self, events: List[Event]):
        self.events = events
        self.schedule = [] # type:List[Tuple[datetime, Event]]

    def _build_scheduler(self):
        now = datetime.now()
        for event in self.events:
            if event.next_occurence < now:
                event.update_next_occ(now)
            self.schedule.append((event.next_occurence, event))
        self.schedule.sort(key=lambda x: x[0])

    async def __call__(self):
        self._build_scheduler()
        while self.schedule:
            now = datetime.now()
            event_time, event = self.schedule.pop(0)
            event.update_next_occ(now)
            await asyncio.sleep((event_time - now).seconds)
            await event.happen()
            self.schedule.append((event.next_occurence, event))
            self.schedule.sort(key=lambda x: x[0])
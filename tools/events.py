from datetime import timedelta, datetime
from typing import List, Tuple
import asyncio

def compute_next_occ(period, occ_time):
    now = datetime.now()
    if period is datetime.day:
        return if now.hour >
    elif period is datetime.hour:
        pass

class Event:

    def __init__(self, loultserv):
        self.loultserv = loultserv
        self.next_occurence = None

    def update_next_occ(self, now):
        pass

    async def happen(self):
        pass


class PeriodicEvent(Event):

    def __init__(self, loultserv, period: timedelta, first_occ=None):
        super().__init__(loultserv)
        self.period = period
        self.next_occurence = first_occ if first_occ is not None else datetime.now()

    def update_next_occ(self, now):
        self.next_occurence = self.next_occurence + self.period


class


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
            next_event_time, next_event = self.schedule.pop(0)
            await asyncio.sleep((next_event_time - now).seconds)
            next_event.happen()
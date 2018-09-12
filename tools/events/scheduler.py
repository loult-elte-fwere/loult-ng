import asyncio
from datetime import datetime
from typing import List

from tools.events.base import Event, FiniteDurationEventMixin


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

            # sleeping until the current event happens
            if (event_time - now).total_seconds() > 0: # if we're "late" then the event happens right away
                await asyncio.sleep((event_time - now).total_seconds())

            # triggering the event!
            await event.trigger(self.loultstate)

            # scheduling the next occurence of the event the next occurence of the event
            now = datetime.now()
            event.update_next_occ(now)
            self.schedule.append((event.next_occurence, event))
            self._order_schedule()
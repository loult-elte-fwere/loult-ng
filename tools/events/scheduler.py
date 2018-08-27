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

            # before sleeping until the event triggers, let's schedule the next occurence of the event
            if isinstance(event, FiniteDurationEventMixin) and not event.is_happening:
                self.schedule.append((event.get_finish_time(now), event))
            else:
                event.update_next_occ(now)
                self.schedule.append((event.next_occurence, event))

            # sleeping until the current event happens
            if (event_time - now).total_seconds() > 0: # if we're "late" then the event happens right away
                await asyncio.sleep((event_time - now).total_seconds())

            # triggering the event!
            if isinstance(event, FiniteDurationEventMixin) and event.is_happening:
                await event.finish(self.loultstate)
            else:
                await event.happen(self.loultstate)

            self._order_schedule()
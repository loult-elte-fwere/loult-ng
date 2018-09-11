import random
from collections import OrderedDict
from copy import deepcopy
from datetime import time, datetime, date, timedelta
from time import time as timestamp


def next_occ(period, occ_time: time):
    """Using the period: a day or an hour, figures out when the next occurence of the event
    is going it to be (depending on if it's daily or hourly)"""
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
    """Base class for an event. Basically it has a triggeer (`happen` method) and
    a getter to tell the scheduler when is the next occurence"""

    def __init__(self):
        self.next_occurence = None

    def update_next_occ(self, now):
        pass

    async def trigger(self, loultstate):
        pass


class PeriodicEvent(Event):
    """Event that happens periodically, with a fixed period"""

    PERIOD = None  # type:timedelta
    FIRST_OCC = None  # type:datetime

    def __init__(self):
        super().__init__()
        self.next_occurence = self.FIRST_OCC if self.FIRST_OCC is not None else datetime.now()

    def update_next_occ(self, now):
        self.next_occurence += self.PERIOD


class PseudoPeriodicEvent(Event):
    """Event that happens pseudo-periodically: the period is randomly generated after
    each occurrence, from a gaussian distribution"""

    PSEUDO_PERIOD = None  # type:timedelta
    VARIANCE = None  # type:timedelta
    FIRST_OCC = None  # type:datetime

    def __init__(self):
        super().__init__()
        if self.FIRST_OCC is None:
            self.next_occurence = datetime.now()
            self.update_next_occ(None)
        else:
            self.next_occurence = self.FIRST_OCC

    def update_next_occ(self, now):
        new_period_secs = random.gauss(self.PSEUDO_PERIOD.total_seconds(), self.VARIANCE.total_seconds())
        new_period_timedelta = timedelta(seconds=new_period_secs)
        self.next_occurence += new_period_timedelta


class FiniteDurationEventMixin(Event):
    """Mixin class for events that have a termination trigger"""

    DURATION = None  # type:timedelta

    def __init__(self):
        self.is_happening = False
        super().__init__()

    def update_next_occ(self, now):
        if self.is_happening:
            self.next_occurence = now + self.DURATION
        else:
            super().update_next_occ(now)

    async def start(self, loultstate):
        pass

    async def finish(self, loultstate):
        pass

    async def trigger(self, loultstate):
        if self.is_happening:
            await self.finish(loultstate)
            self.is_happening = False
        else:
            await self.start(loultstate)
            self.is_happening = True


class ChannelModEvent(FiniteDurationEventMixin, PseudoPeriodicEvent):

    EVENT_TYPE = ""

    @property
    def event_message(self):
        return "Gros bazar sur le loult"

    def _fuckup_channel_users(self, channel):
        pass

    async def start(self, loultstate):
        for channel in loultstate.chans.values():
            self._fuckup_channel_users(channel)
            channel.update_userlist()
            channel.broadcast(type="notification",
                              event_type=self.EVENT_TYPE,
                              date=timestamp() * 1000,
                              msg=self.event_message)
            print("Starting event at %s" % str(datetime.now()))

    async def finish(self, loultstate):
        """Reseting the userlist to real value for each user in each channel"""
        for channel in loultstate.chans.values():
            for user in channel.users.values():
                user.reload_params_from_cookie()
            print("Ending event at %s" % str(datetime.now()))
            channel.update_userlist()


import random
from datetime import time, datetime, date, timedelta


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

    async def happen(self, loultstate):
        pass


class PeriodicEvent(Event):
    """Event that happens periodically, with a fixed period"""

    def __init__(self, period: timedelta, first_occ: datetime=None):
        super().__init__()
        self.period = period
        self.next_occurence = first_occ if first_occ is not None else datetime.now()

    def update_next_occ(self, now):
        self.next_occurence += self.period


class PseudoPeriodicEvent(Event):
    """Event that happens pseudo-periodically: the period is randomly generated after
    each occurrence, from a gaussian distribution"""

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


class FiniteDurationEventMixin(Event):
    """Mixin class for events that have a termination trigger"""

    def __init__(self, *args, duration: timedelta):
        super().__init__(*args)
        self.duration = duration
        self.is_happening = False

    def get_finish_time(self, now: datetime):
        return now + self.duration

    async def finish(self, loultstate):
        self.is_happening = False

    async def happen(self, loultstate):
        self.is_happening = True
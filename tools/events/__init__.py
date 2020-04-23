from typing import List, Type

from .events import (BienChantewEvent, BienDowmiwEvent, MaledictionEvent, MusicalEvent, TunnelEvent,
                     UsersVoicesShuffleEvent, UsersMixupEvent, CloneArmyEvent, ThemeRenameEvent,
                     ObjectDropEvent, InfectionEvent, LynchingEvent, PubBrawlEvent, FireworksEvent,
                     RobinHoodEvent, TreizeNRV, SantaEvent)
from .base import Event
from .scheduler import EventScheduler

AVAILABLE_EVENTS: List[Type[Event]] = [
    BienChantewEvent, MaledictionEvent,
    UsersVoicesShuffleEvent, MusicalEvent,
    ThemeRenameEvent, InfectionEvent,
    LynchingEvent, PubBrawlEvent, FireworksEvent, RobinHoodEvent,
    SantaEvent
]


def events_factory() -> List[Event]:
    return [event_type() for event_type in AVAILABLE_EVENTS]

import random
from typing import Type

from .base import LoultObject
from .objects import (ScrollOfQurk,
                      Crown, Scolopamine, AlcoholBottle, Microphone, C4, Detonator, SuicideJacket, Flower,
                      Costume, WealthDetector, RectalExam, Cigarettes, Lighter,
                      MollyChute, CaptainHaddockPipe, Cacapulte, LaxativeBox,
                      PandorasBox, EffectsStealer, Transmutator, SantasSack)
from .unused_objects import SimpleInstrument, PolynectarPotion, Cocaine, Revolver, RevolverCartridges, SniperRifle, \
    SniperBullets, RPG, RPGRocket, Grenade
from tools.objects.weapons import Quiver

# objects which can be given to users and are not specifically linked to any events
AVAILABLE_OBJECTS = [Crown, Scolopamine,
                     AlcoholBottle, Microphone, C4,
                     Detonator, SuicideJacket, Flower, Quiver,
                     RectalExam, Costume, Cigarettes, Lighter, MollyChute,
                     CaptainHaddockPipe, ScrollOfQurk, EffectsStealer,
                     PandorasBox, LaxativeBox, Cacapulte, Transmutator,
                     SantasSack
                     ]


def get_random_object() -> LoultObject:
    obj_class: Type[LoultObject] = random.choice(AVAILABLE_OBJECTS)
    return obj_class()

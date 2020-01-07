import random
from .base import LoultObject
from .objects import (ScrollOfQurk,
                      Crown, Scolopamine, AlcoholBottle, Microphone, C4, Detonator, SuicideJacket, Flower,
                      Costume, WealthDetector, RectalExam, Cigarettes, Lighter,
                      MollyChute, CaptainHaddockPipe)
from .unused_objects import SimpleInstrument, PolynectarPotion, Cocaine, Revolver, RevolverCartridges, SniperRifle, \
    SniperBullets, RPG, RPGRocket, Grenade
from tools.objects.weapons import Quiver

# objects which can be given to users and are not specifically linked to any events
AVAILABLE_OBJECTS = [Crown, Scolopamine,
                     AlcoholBottle, Microphone, C4,
                     Detonator, SuicideJacket, Flower, Quiver,
                     RectalExam, Costume, Cigarettes, Lighter, MollyChute,
                     CaptainHaddockPipe,
                     ]


def get_random_object() -> LoultObject:
    return random.choice(AVAILABLE_OBJECTS)()
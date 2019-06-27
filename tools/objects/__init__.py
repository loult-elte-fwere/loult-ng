import random
from .base import LoultObject
from .objects import (MagicWand,
                      Crown, SimpleInstrument, Scolopamine, AlcoholBottle, PolynectarPotion,
                      Microphone, C4, Detonator, SuicideJacket, Flower,
                      Costume, WealthDetector, RectalExam, Cigarettes, Lighter,
                      MollyChute, CaptainHaddockPipe)
from tools.objects.weapons import Revolver, RevolverCartridges, SniperRifle, \
    SniperBullets, RPG, RPGRocket, Grenade, Quiver

# objects which can be given to users and are not specifically linked to any events
AVAILABLE_OBJECTS = [MagicWand, Crown, SimpleInstrument, Scolopamine,
                     AlcoholBottle, PolynectarPotion, Microphone, C4,
                     Detonator, SuicideJacket, Flower, Quiver, WealthDetector,
                     RectalExam, Costume, Cigarettes, Lighter, MollyChute, CaptainHaddockPipe]


def get_random_object() -> LoultObject:
    return random.choice(AVAILABLE_OBJECTS)()
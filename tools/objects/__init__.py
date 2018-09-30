import random
from .base import LoultObject
from .objects import (Grenade, SniperRifle, Revolver, RevolverCartridges, SniperBullets, MagicWand,
                      Crown, SimpleInstrument, Scolopamine, WhiskyBottle, PolynectarPotion,
                      RPG, RPGRocket, Microphone, C4, Detonator, SuicideJacket, Flower,
                      Costume, Quiver, WealthDetector, RectalExam, Cigarettes, Lighter,
                      MollyChute)

# objects which can be given to users and are not specifically linked to any events
AVAILABLE_OBJECTS = [Grenade, SniperBullets, SniperRifle, Revolver, RevolverCartridges, MagicWand,
                     Crown, SimpleInstrument, Scolopamine, WhiskyBottle, PolynectarPotion, RPG,
                     RPGRocket, Microphone, C4, Detonator, SuicideJacket, Flower, Quiver,
                     WealthDetector, RectalExam, Costume, Cigarettes, Lighter, MollyChute]


def get_random_object() -> LoultObject:
    return MollyChute()
    return random.choice(AVAILABLE_OBJECTS)()
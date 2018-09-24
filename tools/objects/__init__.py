import random
from .base import LoultObject
from .objects import (Grenade, SniperRifle, Revolver, RevolverCartridges, SniperBullets, MagicWand,
                      Crown, SimpleInstrument, Scolopamine, WhiskyBottle, PolynectarPotion,
                      RPG, RPGRocket, Microphone)

# objects which can be given to users and are not specifically linked to any events
AVAILABLE_OBJECTS = [Grenade, SniperBullets, SniperRifle, Revolver, RevolverCartridges, MagicWand,
                     Crown, SimpleInstrument, Scolopamine, WhiskyBottle, PolynectarPotion, RPG,
                     RPGRocket, Microphone]


def get_random_object() -> LoultObject:
    return random.choice(AVAILABLE_OBJECTS)()
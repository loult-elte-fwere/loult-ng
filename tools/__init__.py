import random

from .effects.effects import PhonemicEffect, VoiceEffect, AudioEffect, ExplicitTextEffect, HiddenTextEffect
from .effects.effects import (
    Effect, SnebwewEffect, ReverbManEffect, TouretteEffect,
    RobotVoiceEffect, GhostEffect, SpeechMasterEffect, PoiloEffect,
    PitchRandomizerEffect, PhonemicNwwoiwwEffect, PhonemicFofoteEffect,
    AccentMarseillaisEffect, AngryRobotVoiceEffect, VocalDyslexia,
    AccentAllemandEffect, CrapweEffect, TurboHangoul, MwfeEffect,
    VieuxPortEffect, GodSpeakingEffect, WpseEffect,
    AutotuneEffect, VoiceSpeedupEffect, StutterEffect,
    GrandSpeechMasterEffect, VowelExchangeEffect, SkyblogEffect,
    PitchShiftEffect, ContradictorEffect, CyborgEffect
)

# the multiplier for each tools list sets the "probability" of the effect
AVAILABLE_EFFECTS = 1 * [GodSpeakingEffect, SnebwewEffect, VoiceSpeedupEffect,
                         PhonemicFofoteEffect, VieuxPortEffect, MwfeEffect,
                         TurboHangoul, GhostEffect, TurboHangoul,
                         SkyblogEffect, PoiloEffect, AccentAllemandEffect] + \
                    3 * [WpseEffect, SpeechMasterEffect, CrapweEffect,
                         VocalDyslexia, ReverbManEffect, PhonemicNwwoiwwEffect,
                         StutterEffect, GrandSpeechMasterEffect, TouretteEffect,
                         VowelExchangeEffect, PitchShiftEffect,
                         ContradictorEffect, CyborgEffect] + \
                    6 * [AutotuneEffect, PitchRandomizerEffect,
                         RobotVoiceEffect, AngryRobotVoiceEffect]
#AVAILABLE_EFFECTS = [ContradictorEffect] # single tools list used when testing


def get_random_effect() -> Effect:
    return random.choice(AVAILABLE_EFFECTS)()

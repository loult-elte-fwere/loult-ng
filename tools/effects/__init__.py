import random
from .effects import AudioEffect, HiddenTextEffect, ExplicitTextEffect, PhonemicEffect, VoiceEffect

from .effects import (GodSpeakingEffect, VoiceSpeedupEffect, PhonemicFofoteEffect, VieuxPortEffect, MwfeEffect,
                   TurboHangoul, GhostEffect, SkyblogEffect, AccentAllemandEffect,
                   RobotVoiceEffect,
                   AngryRobotVoiceEffect, WpseEffect, SpeechMasterEffect, CrapweEffect, VocalDyslexia,
                   ReverbManEffect,
                   PhonemicNwwoiwwEffect, StutterEffect, VowelExchangeEffect, PitchShiftEffect,
                   ContradictorEffect, PubertyEffect,
                   PitchRandomizerEffect, SnebwewEffect, AutotuneEffect, GrandSpeechMasterEffect, TouretteEffect,
                   BadCellphoneEffect, CaptainHaddockEffect,
                   Effect)

AVAILABLE_EFFECTS = 1 * [GodSpeakingEffect, VoiceSpeedupEffect,
                         VieuxPortEffect, MwfeEffect,
                         TurboHangoul, GhostEffect, TurboHangoul,
                         SkyblogEffect, AccentAllemandEffect,
                         RobotVoiceEffect, AngryRobotVoiceEffect, BadCellphoneEffect] + \
                    3 * [WpseEffect, SpeechMasterEffect, CrapweEffect,
                         VocalDyslexia, ReverbManEffect, PhonemicNwwoiwwEffect,
                         StutterEffect, VowelExchangeEffect, PitchShiftEffect,
                         ContradictorEffect, PubertyEffect, PitchRandomizerEffect,
                         SnebwewEffect, CaptainHaddockEffect] + \
                    6 * [AutotuneEffect, GrandSpeechMasterEffect, TouretteEffect,
                         PhonemicFofoteEffect]


def get_random_effect() -> Effect:
    return random.choice(AVAILABLE_EFFECTS)()
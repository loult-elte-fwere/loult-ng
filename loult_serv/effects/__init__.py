import random

from .effects import AudioEffect, HiddenTextEffect, ExplicitTextEffect, PhonemicEffect, VoiceEffect
from .effects import (GodSpeakingEffect, VoiceSpeedupEffect, PhonemicFofoteEffect, VieuxPortEffect, MwfeEffect,
                      TurboHangoul, GhostEffect, SkyblogEffect, AccentAllemandEffect,
                      RobotVoiceEffect,
                      AngryRobotVoiceEffect, WpseEffect, SpeechMasterEffect,
                      CrapweEffect, VocalDyslexia,
                      ReverbManEffect,
                      PhonemicNwwoiwwEffect, StutterEffect, VowelExchangeEffect,
                      PitchShiftEffect,
                      PubertyEffect,
                      PitchRandomizerEffect, SnebwewEffect, AutotuneEffect, GrandSpeechMasterEffect, TouretteEffect,
                      BadCellphoneEffect, CaptainHaddockEffect,
                      Effect, CensorshipEffect, FapEffect)

AVAILABLE_EFFECTS = 1 * [GodSpeakingEffect, VoiceSpeedupEffect,
                         VieuxPortEffect, MwfeEffect,
                         TurboHangoul, GhostEffect, TurboHangoul,
                         SkyblogEffect, AccentAllemandEffect,
                         RobotVoiceEffect, AngryRobotVoiceEffect, BadCellphoneEffect,
                         CensorshipEffect, CaptainHaddockEffect] + \
                    3 * [SpeechMasterEffect, CrapweEffect,
                         VocalDyslexia, ReverbManEffect, PhonemicNwwoiwwEffect,
                         StutterEffect, VowelExchangeEffect, PitchShiftEffect,
                         PubertyEffect, PitchRandomizerEffect,
                         SnebwewEffect, FapEffect] + \
                    6 * [AutotuneEffect, GrandSpeechMasterEffect, TouretteEffect,
                         PhonemicFofoteEffect, WpseEffect]


def get_random_effect() -> Effect:
    return random.choice(AVAILABLE_EFFECTS)()

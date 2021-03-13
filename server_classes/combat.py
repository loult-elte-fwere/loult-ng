from typing import Tuple
import random

from server_classes.effects import get_random_effect
from server_classes.effects.effects import (TouretteEffect, CrapweEffect, TurboHangoul, MwfeEffect, WpseEffect,
                           GrandSpeechMasterEffect, AngryRobotVoiceEffect, FapEffect)


class CombatSimulator:

    _global_effects = [TouretteEffect, CrapweEffect, TurboHangoul, MwfeEffect, WpseEffect,
                       GrandSpeechMasterEffect, AngryRobotVoiceEffect, FapEffect]

    def __init__(self):
        self._affected_users = []
        self.atk_dice, self.atk_bonus, self.def_dice, self.def_bonus= None, None, None, None

    def _fumble(self, user):
        for effect in [get_random_effect() for i in range(4)]:
            user.state.add_effect(effect)
            self._affected_users.append((user, effect))

    def run_attack(self, attacker, defender, channel):
        self.atk_dice, self.atk_bonus = attacker.throw_dice("attack")# type:Tuple[int,int]
        self.def_dice, self.def_bonus = defender.throw_dice("defend")# type:Tuple[int,int]

        if self.atk_dice == 100: # global effect
            effect_type = random.choice(self._global_effects)
            for userid, user in channel.users.items():
                if userid != attacker.user_id:
                    effect_obj = effect_type()
                    user.state.add_effect(effect_obj)
                    self._affected_users.append((user,effect_obj))

        elif self.atk_dice == 1 or self.def_dice == 100: # attack fumble
            self._fumble(attacker)

        elif self.def_dice == 1: # def fumble
            self._fumble(defender)

        elif self.atk_dice + self.atk_bonus < self.def_dice + self.def_bonus: # rebound or bounceback
            randoum = random.randint(1,3)
            effect = get_random_effect()
            if randoum == 1: # bounceback
                attacker.state.add_effect(effect)
                self._affected_users = [(attacker, effect)]
            elif randoum == 2:
                random_other_user = random.choice(list(channel.users.values()))
                random_other_user.state.add_effect(effect)
                self._affected_users = [(random_other_user, effect)]

        elif self.atk_dice + self.atk_bonus > self.def_dice + self.def_bonus:# regular atck pass
            effect = get_random_effect()
            defender.state.add_effect(effect)
            self._affected_users = [(defender, effect)]
            if self.atk_dice + self.atk_bonus > 100: # adding an effect for every slice of 50 above 100
                for i in range((self.atk_dice + self.atk_bonus - 100) // 50):
                    effect = get_random_effect()
                    defender.state.add_effect(effect)
                    self._affected_users.append((defender, effect))

    @property
    def affected_users(self):
        return self._affected_users
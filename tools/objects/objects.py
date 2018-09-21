from datetime import datetime, timedelta
import random
import re
from os import path, listdir
from time import time as timestamp

from tools.effects.effects import ExplicitTextEffect
from tools.objects.base import ClonableObject, InertObject, UsableObject, DestructibleObject, TargetedObject
from tools.tools import cached_loader


class SicknessObject(ClonableObject, InertObject):

    def __init__(self, sickness, patient_zero):
        self.sickness = sickness
        self.patient_zero = patient_zero

    @property
    def name(self):
        return "la %s de %s" % self.sickness, self.patient_zero


class SimpleInstrument(UsableObject):
    pass


class Revolver(UsableObject):
    pass


class Sniper(UsableObject, TargetedObject):
    SNIPER_FX = path.join(path.dirname(path.realpath(__file__)), "data/sniper_fx.mp3")
    NAME = "Fusil de précision"

    def __init__(self):
        self.empty = False

    @property
    def name(self):
        if self.empty:
            return self.NAME + " (vide)"
        else:
            return self.NAME
    
    def use(self, loult_state, server, obj_params):
        if self.empty:
            return server.send_json(type="notification",
                             msg="Plus de munitions!")

        adversary_id, adversary = self._acquire_target(server, obj_params)
        if adversary is None:
            return

        with open(self.SNIPER_FX, "rb") as fx_file:
            sniper_fx = fx_file.read()
        server.channel_obj.broadcast(type="notification",
                                     msg="%s tire au fusil sniper sur %s",
                                     binary_payload=sniper_fx)
        server.channel_obj.broadcast(type='antiflood', event='banned',
                                     flooder_id=adversary_id,
                                     date=timestamp() * 1000)
        loult_state.ban_cookie(server.cookie)
        server.sendClose(code=4006, reason='reconnect later')
        self.empty = True
        

class Grenade(UsableObject, DestructibleObject):
    UNPIN_FX = path.join(path.dirname(path.realpath(__file__)), "data/grenade_unpin.mp3")
    EXPLOSION_FX = path.join(path.dirname(path.realpath(__file__)), "data/grenade_explosion.mp3")
    NAME = "Grenade"

    def use(self, loult_state, server, obj_params):
        with open(self.UNPIN_FX, "rb") as fx_file:
            unpin_fx = fx_file.read()

        server.channel_obj.broadcast(type="notification",
                                     msg="%s a lancé une grenade!" % server.user.poke_params.fullname,
                                     binary_payload=unpin_fx)
        # selecting 5 random users and making them disconnect
        users = list(server.channel_obj.users.values())
        hit_users = []
        while users and len(hit_users) < 5:
            rnd_user = users.pop(random.randint(0, len(users) - 1))
            hit_users.append(rnd_user)
        for usr in hit_users:
            for client in usr.clients:
                client.sendClose(code=4006, reason="Reconnect please")

        # throwing in an explosion sound
        with open(self.EXPLOSION_FX, "rb") as fx_file:
            explosion_fx = fx_file.read()
        server.channel_obj.broadcast(binary_payload=explosion_fx)
        self.should_be_destroyed = True


class BaseballBat(UsableObject, DestructibleObject):
    FIGHTING_FX_DIR = path.join(path.dirname(path.realpath(__file__)), "fighting/")

    def __init__(self, target_userid, target_username):
        super().__init__()
        self.target_name = target_username
        self.target_userid = target_userid
        self.remaining_hits = random.randint(5, 15)
        self.sounds = []
        for filename in listdir(self.FIGHTING_FX_DIR):
            realpath = path.join(self.FIGHTING_FX_DIR, filename)
            self.sounds.append(cached_loader.load_byte(realpath))
    
    @property
    def name(self):
        return "Batte pour frapper %s" % self.target_name

    def use(self, loult_state, server, obj_params):
        # checking if target user is present, sending a notif and a sound
        if self.target_userid in server.channel_obj.users:
            server.channel_obj.broadcast(type="notification",
                                         msg="%s donne un coup de batte à %s"
                                             % (server.user.poke_params.fullname, self.target_name),
                                         binary_payload=random.choice(self.sounds))
            self.remaining_hits -= 1
        else:
            server.channel_obj.broadcast(type="notification",
                                         msg="Cette batte ne sert qu'à taper %s" % self.target_name)

        # if it's the last hit, notifying and destroying the object
        if self.remaining_hits <= 0:
            self.should_be_destroyed = True
            server.channel_obj.broadcast(type="notification",
                                         msg="%s a cassé sa batte sur %s"
                                             % (server.user.poke_params.fullname, self.target_name))


class Crown(UsableObject, DestructibleObject):
    NAME = "Couronne du loult"

    class ServantEffect(ExplicitTextEffect):
        TIMEOUT = 300
        SUFFIXES = ["seigneur %s", "maître %s", "mon roi", "mon bon %s", "ô grand %s", "sire %s"]

        def __init__(self, pokename):
            super().__init__()
            self.suffixes = [suff % pokename if "%s" in suff else suff for suff in self.SUFFIXES]

        def process(self, text: str):
            return text.strip("!,.:?") + ", " + random.choice(self.suffixes)

    def use(self, loult_state, server, obj_params):
        for user in server.channel_obj.users.values():
            if user is not server.user:
                user.state.add_effect(self.ServantEffect(server.user.poke_params.pokename))
        server.channel_obj.broadcast(type="notification",
                                     msg="%s est maintenant le roi du loult" % server.user.poke_params.fullname)


class MagicWand(UsableObject, TargetedObject):
    NAME = "Baguette Magique"
    COOLDOWN = 15 * 60 # in seconds

    class DuckEffect(ExplicitTextEffect):
        TIMEOUT = 300

        def process(self, text : str):
            return re.sub(r"[\w]+","qurk", text)

    def __init__(self):
        self.last_used = datetime.now()

    def use(self, loult_state, server, obj_params):
        if (datetime.now() - self.last_used).seconds < self.COOLDOWN:
            return server.send_json(type="notification",
                                    msg="Plus de mana!")

        adversary_id, adversary = self._acquire_target(server, obj_params)
        if adversary is None:
            return

        adversary.state.add_effect(self.DuckEffect())
        server.broadcast(type="notification",
                         msg="%s s'est fait changer en canard" % adversary.poke_params.fullname)
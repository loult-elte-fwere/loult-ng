from datetime import datetime
import random
import re
from os import path, listdir
from time import time as timestamp

from tools.effects.effects import ExplicitTextEffect
from tools.objects.base import ClonableObject, InertObject, UsableObject, DestructibleObject, TargetedObject, \
    userlist_dist
from tools.tools import cached_loader


class DiseaseObject(ClonableObject, InertObject):

    DISEASES = ["syphilis", "diarrhée", "chaude-pisse", "gripe aviaire"]

    def __init__(self, patient_zero, disease=None):
        if disease is None:
            self.disease = random.choice(self.DISEASES)
        self.patient_zero = patient_zero

    @property
    def name(self):
        return "la %s de %s" % (self.disease, self.patient_zero)


class SimpleInstrument(UsableObject):
    SND_DIR = path.join(path.dirname(path.realpath(__file__)), "data/instruments/")
    INSTRUMENTS_MAPPING = {"gong": "gong.mp3"}
    COOLDOWN = 30 # in seconds

    def __init__(self, instrument=None):
        if instrument is None:
            instrument = random.choice(list(self.INSTRUMENTS_MAPPING.keys()))

        self.instrument_name = instrument.capitalize()
        self.fx_filepath = path.join(self.SND_DIR, self.INSTRUMENTS_MAPPING[instrument])
        self.last_used = datetime(1972, 1 ,1)

    @property
    def name(self):
        return self.instrument_name

    def use(self, loult_state, server, obj_params):
        if (datetime.now() - self.last_used).seconds < self.COOLDOWN:
            return

        server.channel_obj.broadcast(binary_payload=self._load_byte(self.fx_filepath))
        self.last_used = datetime.now()


class Revolver(UsableObject, TargetedObject):
    GUNSHOT_FX = path.join(path.dirname(path.realpath(__file__)), "data/gun/gunshot.mp3")
    EMPTY_FX = path.join(path.dirname(path.realpath(__file__)), "data/gun/empty_mag.mp3")
    NAME = "Walther PKK"

    def __init__(self, bullets=5):
        self.remaining_bullets = bullets

    @property
    def name(self):
        if self.remaining_bullets:
            return self.NAME + " (%i)" % self.remaining_bullets
        else:
            return self.NAME + " (vide)"

    def use(self, loult_state, server, obj_params):
        if self.remaining_bullets <= 0:
            server.send_json(type="notification",
                             msg="Plus de munitions!")
            server.send_binary(self._load_byte(self.EMPTY_FX))
            return

        adversary_id, adversary = self._acquire_target(server, obj_params)
        if adversary is None:
            return

        target_dist = userlist_dist(server.channel_obj, server.user.user_id, adversary_id)
        if target_dist > 1:
            return server.send_json(type="notification",
                                    msg="Trop loin pour tirer!")

        server.channel_obj.broadcast(type="notification",
                                     msg="%s tire au Colt sur %s"
                                         % (server.user.poke_params.fullname, adversary.poke_params.fullname),
                                     binary_payload=self._load_byte(self.GUNSHOT_FX))
        for client in adversary.clients:
            client.sendClose(code=4006, reason='Reconnect please')
        self.remaining_bullets -= 1


class RevolverCartridges(UsableObject, DestructibleObject):
    NAME = "Chargeur de pistolet"
    RELOADING_FX = path.join(path.dirname(path.realpath(__file__)), "data/gun/reloading.mp3")

    def use(self, loult_state, server, obj_params):
        # searching in the user's inventory for the emptiest gun to be used on
        users_guns = server.user.state.inventory.search_by_class(Revolver)
        users_guns = [gun for gun in users_guns if gun.remaining_bullets < 6]
        if not users_guns:
            return server.send_json(type="notification",
                                    msg="Pas de pistolet à recharger dans votre inventaire")

        users_guns.sort(key=lambda x: x.remaining_bullets, reverse=False)
        emptiest_gun = users_guns[0]
        emptiest_gun.remaining_bullets = 5
        server.send_json(type="notification", msg="Pistolet chargé!")
        server.send_binary(self._load_byte(self.RELOADING_FX))
        self.should_be_destroyed = True


class SniperRifle(UsableObject, TargetedObject):
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
                                     msg="%s tire au fusil sniper sur %s"
                                         % (server.user.poke_params.fullname, adversary.poke_params.fullname),
                                     binary_payload=sniper_fx)
        server.channel_obj.broadcast(type='antiflood', event='banned',
                                     flooder_id=adversary_id,
                                     date=timestamp() * 1000)
        loult_state.ban_cookie(adversary.cookie_hash)
        for client in adversary.clients:
            client.sendClose(code=4006, reason='reconnect later')
        self.empty = True


class SniperBullets(UsableObject, DestructibleObject):
    NAME = "Balles de sniper"
    RELOADING_FX = path.join(path.dirname(path.realpath(__file__)), "data/gun/bolt_reloading.mp3")

    def __init__(self, bullets=3):
        super().__init__()
        self.remaining_bullets = bullets

    @property
    def name(self):
        return self.NAME + "(%i)" % self.remaining_bullets

    def use(self, loult_state, server, obj_params):
        # searching in the user's inventory for an empty sniper rifle
        users_guns = server.user.state.inventory.search_by_class(SniperRifle)
        users_guns = [gun for gun in users_guns if gun.empty]
        if not users_guns:
            return server.send_json(type="notification",
                                    msg="Pas de fusil sniper à recharger dans votre inventaire")

        emptiest_gun = users_guns[0]
        emptiest_gun.empty = False
        server.send_json(type="notification", msg="Fusil sniper chargé!")
        server.send_binary(self._load_byte(self.RELOADING_FX))
        self.remaining_bullets -= 1
        if self.remaining_bullets <= 0:
            self.should_be_destroyed = True


class RPG(UsableObject, TargetedObject):
    NAME = "lance-roquette"
    RPG_FX = path.join(path.dirname(path.realpath(__file__)), "data/rpg_rocket.mp3")

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

        server.channel_obj.broadcast(type="notification",
                                     msg="")
        hit_usrs = [usr for usr in server.channel_obj.users.values()
                    if userlist_dist(server.channel_obj, adversary_id, usr.user_id) < 2]
        for user in hit_usrs:
            for client in user.clients:
                client.sendClose(code=4006, reason="Reconnect please")

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
        server.channel_obj.broadcast(binary_payload=self._load_byte(self.EXPLOSION_FX))
        self.should_be_destroyed = True


class BaseballBat(UsableObject, DestructibleObject):
    FIGHTING_FX_DIR = path.join(path.dirname(path.realpath(__file__)), "data/fighting/")

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
        self.should_be_destroyed = True


class MagicWand(UsableObject, TargetedObject):
    NAME = "Baguette Magique"
    COOLDOWN = 15 * 60 # in seconds

    class DuckEffect(ExplicitTextEffect):
        TIMEOUT = 300

        def process(self, text : str):
            return re.sub(r"[\w]+","qurk", text)

    def __init__(self):
        self.last_used = datetime(1972, 1, 1)

    def use(self, loult_state, server, obj_params):
        if (datetime.now() - self.last_used).seconds < self.COOLDOWN:
            return server.send_json(type="notification",
                                    msg="Plus de mana!")

        adversary_id, adversary = self._acquire_target(server, obj_params)
        if adversary is None:
            return

        adversary.state.add_effect(self.DuckEffect())
        server.channel_obj.broadcast(type="notification",
                                     msg="%s s'est fait changer en canard" % adversary.poke_params.fullname)
        self.last_used = datetime.now()


class Scolopamine(UsableObject, DestructibleObject, TargetedObject):
    NAME = "Scolopamine"

    def use(self, loult_state, server, obj_params):
        adversary_id, adversary = self._acquire_target(server, obj_params)
        if adversary is None:
            return

        server.user.state.inventory.objects += adversary.state.inventory.objects
        adversary.state.inventory.objects = []

        server.channel_obj.broadcast(type="notification",
                                     msg="%s a drogué %s et puis a piqué tout son inventaire!"
                                         % (server.user.poke_params.fullname, adversary.poke_params.fullname))
        self.should_be_destroyed = True


class WhiskyBottle(UsableObject, DestructibleObject):
    NAME = "Bouteille de whisky"


class PolynectarPotion(UsableObject, DestructibleObject, TargetedObject):
    pass

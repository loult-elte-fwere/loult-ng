from datetime import datetime
import random
import re
from itertools import cycle
from os import path, listdir
from time import time as timestamp

from tools.effects.effects import ExplicitTextEffect, GrandSpeechMasterEffect, StutterEffect, VocalDyslexia, \
    VowelExchangeEffect
from tools.objects.base import ClonableObject, InertObject, UsableObject, DestructibleObject, TargetedObject, \
    userlist_dist, MilitiaWeapon
from tools.tools import cached_loader

DATA_PATH = path.join(path.dirname(path.realpath(__file__)), "data")


class DiseaseObject(ClonableObject, InertObject):

    DISEASES = ["syphilis", "diarrhée", "chaude-pisse", "gripe aviaire"]

    def __init__(self, patient_zero, disease=None):
        if disease is None:
            self.disease = random.choice(self.DISEASES)
        self.patient_zero = patient_zero

    @property
    def name(self):
        return "la %s de %s" % (self.disease, self.patient_zero)


class Flower(InertObject):
    FLOWERS = ["rose", "lys blanc", "iris", "chrysanthème", "oeillet", "jonquille", "muguet",
               "tulipe", "orchidée"]

    def __init__(self):
        self.flower_name = random.choice(self.FLOWERS)

    @property
    def name(self):
        return self.flower_name


class SimpleInstrument(UsableObject):
    SND_DIR = path.join(DATA_PATH, "instruments/")
    INSTRUMENTS_MAPPING = {"gong": "gong.mp3"}
    COOLDOWN = 30 # in seconds

    def __init__(self, instrument=None):
        if instrument is None:
            instrument = random.choice(list(self.INSTRUMENTS_MAPPING.keys()))

        self.instrument_name = instrument.capitalize()
        self.fx_filepath = path.join(self.SND_DIR, self.INSTRUMENTS_MAPPING[instrument])
        self.last_used = datetime(1972, 1, 1)

    @property
    def name(self):
        return self.instrument_name

    def use(self, loult_state, server, obj_params):
        if (datetime.now() - self.last_used).seconds < self.COOLDOWN:
            return

        server.channel_obj.broadcast(binary_payload=self._load_byte(self.fx_filepath))
        self.last_used = datetime.now()


class Revolver(UsableObject, TargetedObject):
    GUNSHOT_FX = path.join(DATA_PATH, "gun/gunshot.mp3")
    EMPTY_FX = path.join(DATA_PATH, "gun/empty_mag.mp3")
    NAME = "Walther PKK"

    def __init__(self, bullets=5):
        self.remaining_bullets = bullets

    @property
    def name(self):
        if self.remaining_bullets:
            return self.NAME + " (%s)" % ("▮" * self.remaining_bullets)
        else:
            return self.NAME + " (vide)"

    def use(self, loult_state, server, obj_params):
        if self.remaining_bullets <= 0:
            server.send_json(type="notification",
                             msg="Plus de munitions!")
            server.send_binary(self._load_byte(self.EMPTY_FX))
            return

        target_id, target = self._acquire_target(server, obj_params)
        if target is None:
            return

        target_dist = userlist_dist(server.channel_obj, server.user.user_id, target_id)
        if target_dist > 2:
            return server.send_json(type="notification",
                                    msg="Trop loin pour tirer!")

        server.channel_obj.broadcast(type="notification",
                                     msg="%s tire au pistolet sur %s"
                                         % (server.user.poke_params.fullname, target.poke_params.fullname),
                                     binary_payload=self._load_byte(self.GUNSHOT_FX))
        for client in target.clients:
            client.sendClose(code=4006, reason='Reconnect please')
        self.remaining_bullets -= 1


class RevolverCartridges(UsableObject, DestructibleObject):
    NAME = "Chargeur de pistolet"
    RELOADING_FX = path.join(DATA_PATH, "gun/reloading.mp3")

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
    SNIPER_FX = path.join(DATA_PATH, "sniper_fx.mp3")
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

        target_id, target = self._acquire_target(server, obj_params)
        if target is None:
            return

        server.channel_obj.broadcast(type="notification",
                                     msg="%s tire au fusil sniper sur %s"
                                         % (server.user.poke_params.fullname, target.poke_params.fullname),
                                     binary_payload=self._load_byte(self.SNIPER_FX))
        for client in target.clients:
            client.sendClose(code=4006, reason='reconnect later')
        self.empty = True


class SniperBullets(UsableObject, DestructibleObject):
    NAME = "Balles de sniper"
    RELOADING_FX = path.join(DATA_PATH, "gun/bolt_reloading.mp3")

    def __init__(self, bullets=3):
        super().__init__()
        self.remaining_bullets = bullets

    @property
    def name(self):
        return self.NAME + " (%s)" % ("▮" * self.remaining_bullets)

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
    RPG_FX = path.join(DATA_PATH, "rpg_rocket.mp3")

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

        target_id, target = self._acquire_target(server, obj_params)
        if target is None:
            return

        server.channel_obj.broadcast(type="notification",
                                     msg="%s tire au bazooka sur %s"
                                         % (server.user.poke_params.fullname, target.poke_params.fullname),
                                     binary_payload=self._load_byte(self.RPG_FX))
        hit_usrs = [usr for usr in server.channel_obj.users.values()
                    if userlist_dist(server.channel_obj, target_id, usr.user_id) < 2]
        for user in hit_usrs:
            for client in user.clients:
                client.sendClose(code=4006, reason="Reconnect please")

        self.empty = True


class RPGRocket(UsableObject, DestructibleObject):
    NAME = "Roquette pour RPG"
    RELOADING_FX = path.join(DATA_PATH, "rpg_reload.mp3")

    def use(self, loult_state, server, obj_params):
        users_rpg = server.user.state.inventory.search_by_class(RPG)
        users_rpg = [gun for gun in users_rpg if gun.empty]
        if not users_rpg:
            return server.send_json(type="notification",
                                    msg="Pas de RPG sniper à recharger dans votre inventaire")

        empty_rpg = users_rpg[0]
        empty_rpg.empty = False
        server.send_json(type="notification", msg="RPG chargé!")
        server.send_binary(self._load_byte(self.RELOADING_FX))
        self.should_be_destroyed = True
        

class Grenade(UsableObject, DestructibleObject):
    UNPIN_FX = path.join(DATA_PATH, "grenade_unpin.mp3")
    EXPLOSION_FX = path.join(DATA_PATH, "grenade_explosion.mp3")
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
    FIGHTING_FX_DIR = path.join(DATA_PATH, "fighting/")

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
            server.send_json(type="notification",
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
                                    msg="Plus de mana dans la baguette, il faut attendre!")

        target_id, target = self._acquire_target(server, obj_params)
        if target is None:
            return

        target.state.add_effect(self.DuckEffect())
        server.channel_obj.broadcast(type="notification",
                                     msg="%s s'est fait changer en canard" % target.poke_params.fullname)
        self.last_used = datetime.now()


class Scolopamine(UsableObject, DestructibleObject, TargetedObject):
    NAME = "Scolopamine"

    def use(self, loult_state, server, obj_params):
        target_id, target = self._acquire_target(server, obj_params)
        if target is None:
            return

        server.user.state.inventory.objects += target.state.inventory.objects
        target.state.inventory.objects = []
        target.state.add_effect(GrandSpeechMasterEffect())

        server.channel_obj.broadcast(type="notification",
                                     msg="%s a drogué %s et puis a piqué tout son inventaire!"
                                         % (server.user.poke_params.fullname, target.poke_params.fullname))
        self.should_be_destroyed = True


class WhiskyBottle(UsableObject, DestructibleObject, TargetedObject):
    NAME = "Bouteille de whisky"
    EFFECTS = [GrandSpeechMasterEffect, StutterEffect, VocalDyslexia, VowelExchangeEffect]
    FILLING_MAPPING = {0: "vide", 1: "presque vide", 2: "moitié vide",
                       3: "presque pleine", 4: "pleine"}
    BOTTLE_FX = path.join(DATA_PATH, "broken_bottle.mp3")
    GULP_FX = path.join(DATA_PATH, "gulp.mp3")

    def __init__(self):
        super().__init__()
        self.remaining_use = 4

    @property
    def name(self):
        return self.NAME + " (%s)" % self.FILLING_MAPPING[self.remaining_use]

    def use(self, loult_state, server, obj_params):
        # user decides to use it on someone else, meaning throwing it
        if obj_params:
            target_id, target = self._acquire_target(server, obj_params)
            if target is None:
                return

            target_dist = userlist_dist(server.channel_obj, server.user.user_id, target_id)
            if target_dist > 1:
                return server.send_json(type="notification",
                                        msg="Trop loin pour lancer la bouteille dessus!")

            server.channel_obj.broadcast(type="notification",
                                         msg="%s lance une bouteille de whisky sur %s"
                                             % (server.user.poke_params.fullname, target.poke_params.fullname),
                                         binary_payload=self._load_byte(self.BOTTLE_FX))
            for client in target.clients:
                client.sendClose(code=4006, reason='Reconnect please')
            self.should_be_destroyed = True
        else:
            if self.remaining_use <= 0:
                return server.send_json(type="notification",
                                        msg="La bouteille est vide!")
            server.channel_obj.broadcast(type="notification",
                                         msg="%s se descend du whisky!" % server.user.poke_params.fullname,
                                         binary_payload=self._load_byte(self.GULP_FX))
            for effect_type in self.EFFECTS:
                server.user.state.add_effect(effect_type())
            self.remaining_use -= 1


class PolynectarPotion(UsableObject, DestructibleObject, TargetedObject):
    NAME = "potion polynectar"

    def use(self, loult_state, server, obj_params):
        target_id, target = self._acquire_target(server, obj_params)
        if target is None:
            return

        server.channel_obj.broadcast(type="notification",
                                     msg="%s a pris l'apparence de %s!"
                                         % (server.user.poke_params.fullname, target.poke_params.fullname))
        usr = server.user
        usr.poke_params = target.poke_params
        usr.voice_params = target.voice_params
        usr.poke_profile = target.poke_profile
        usr._info = None
        server.channel_obj.update_userlist()
        self.should_be_destroyed = True


class Microphone(UsableObject):
    MIKEDROP_FX = path.join(DATA_PATH, "mikedrop.mp3")
    NAME = 'micro'

    def use(self, loult_state, server, obj_params):
        server.channel_obj.broadcast(type="notification",
                                     msg="%s drop le mike!" % server.user.poke_params.fullname,
                                     binary_payload=self._load_byte(self.MIKEDROP_FX))
        for client in server.user.clients:
            client.sendClose(code=4006, reason='Mike drop, bitch')


class C4(InertObject):
    NAME = "C4"


class Detonator(UsableObject):
    NAME = "Détonateur"
    EXPLOSION_FX = path.join(DATA_PATH, "explosion.mp3")

    def use(self, loult_state, server, obj_params):
        blown_up_users = []
        for user in server.channel_obj.users.values():
            if user.state.inventory.search_by_class(C4):
                user.state.inventory.remove_by_class(C4)
                for client in user.clients:
                    client.sendClose(code=4006, reason='reconnect later')
                blown_up_users.append(user.poke_params.fullname)
        if blown_up_users:
            server.channel_obj.broadcast(type="notification",
                                         msg="%s a fait sauter %s!"
                                             % (server.user.poke_params.fullname, ", ".join(blown_up_users)),
                                         binary_payload=self._load_byte(self.EXPLOSION_FX))


class SuicideJacket(UsableObject, DestructibleObject):
    NAME = "ceinture d'explosif"
    EXPLOSION_FX = path.join(DATA_PATH, "suicide_bomber.mp3")

    def use(self, loult_state, server, obj_params):
        hit_usrs = [usr for usr in server.channel_obj.users.values()
                    if userlist_dist(server.channel_obj, server.user.user_id, usr.user_id) < 3
                    and usr is not server.user]
        server.channel_obj.broadcast(type="notification",
                                     msg="%s s'est fait sauter, emportant avec lui %s"
                                         % (server.user.poke_params.fullname
                                            , ", ".join([usr.poke_params.fullname for usr in hit_usrs])),
                                     binary_payload=self._load_byte(self.EXPLOSION_FX))
        for user in hit_usrs:
            for client in user.clients:
                client.sendClose(code=4006, reason="Reconnect please")
        server.channel_obj.broadcast(type='antiflood', event='banned',
                                     flooder_id=server.user.user_id,
                                     date=timestamp() * 1000)
        loult_state.ban_cookie(server.user.cookie_hash)
        for client in server.user.clients:
            client.sendClose(code=4006, reason='reconnect later')
        self.should_be_destroyed = True


class Costume(UsableObject):
    NAME = "costume"
    CHARACTERS = ["link", "mario", "wario", "sonic"]

    def __init__(self):
        self.character = random.choice(self.CHARACTERS) # type:str

    @property
    def name(self):
        return self.NAME + " de %s" % self.character.capitalize()

    def use(self, loult_state, server, obj_params):
        if hasattr(server.user, "costume") and server.user.costume == self.character:
            return server.send_json(type="notification",
                                    msg="Vous ne pouvez pas enfiler deux fois d'affilée le costume!")

        server.channel_obj.broadcast(type="notification",
                                     msg="%s enfile un costume de %s"
                                         % (server.user.poke_params.fullname, self.character.capitalize()))
        params = server.user.poke_params
        params.img_id = self.character
        params.pokename = self.character.capitalize()
        server.user._info = None
        server.user.costume = self.character
        server.channel_obj.update_userlist()


class RobinHoodsBow(UsableObject, TargetedObject):
    NAME = "arc de robin des bois"
    BOW_FX = path.join(DATA_PATH, "bow_fire.mp3")

    def use(self, loult_state, server, obj_params):
        target_id, target = self._acquire_target(server, obj_params)
        if target is None:
            return

        if server.user is target:
            return server.send_json(type="notification", msg="Impossible d'utiliser l'arc sur soi-même")

        usrs = list(server.channel_obj.users.values())
        usrs.remove(target)
        usrs.remove(server.user)
        target_objs = list(target.state.inventory.objects)

        quivers = server.user.state.inventory.search_by_class(Quiver)
        if not quivers:
            return server.send_json(type="notification",
                                    msg="Il vous faut un carquois avec des flèches pour pouvoir tirer à l'arc!")
        quiver = quivers[0]
        quiver.arrows -= 1

        if usrs:
            usrs.sort(key=lambda x: len(x.state.inventory.objects), reverse=False)
            for usr in cycle(usrs):
                if target_objs:
                    obj = target_objs.pop()
                    target.state.inventory.remove(obj)
                    usr.state.inventory.add(obj)
                else:
                    break
        else:
            for obj in target_objs:
                target.state.inventory.remove(obj)
                server.channel_obj.inventory.add(obj)
        server.channel_obj.broadcast(type="notification",
                                     msg="%s vole à %s pour donner aux pauvres"
                                         % (server.user.poke_params.fullname, target.poke_params.fullname),
                                     binary_payload=self._load_byte(self.BOW_FX))


class Quiver(InertObject, DestructibleObject):
    NAME = "carquois"

    def __init__(self, arrows=3):
        super().__init__()
        self.arrows = arrows

    @property
    def name(self):
        if self.arrows:
            return self.NAME + " (%s)" % ("➹" * self.arrows)
        else:
            return self.NAME

    @property
    def destroy(self):
        return self.arrows <= 0


class RectalExam(UsableObject, TargetedObject, DestructibleObject):
    NAME = "examen rectal"

    def use(self, loult_state, server, obj_params):
        target_id, target = self._acquire_target(server, obj_params)
        if target is None:
            return

        from ..objects import get_random_object
        rdm_objects = [get_random_object() for _ in range(random.randint(2,4))]
        for obj in rdm_objects:
            server.user.state.inventory.add(obj)
        names_list = ", ".join(obj.name for obj in rdm_objects)

        if target is server.user:
            msg = "%s a sorti %s de son cul!" % (server.user.poke_params.fullname, names_list)
        else:
            msg = "%s fouille dans le cul de %s et trouve %s! " \
                  % (server.user.poke_params.fullname, target.poke_params.fullname, names_list)

        server.channel_obj.broadcast(type="notification", msg=msg)
        self.should_be_destroyed = True


class WealthDetector(UsableObject, TargetedObject):
    NAME = "détecteur de richesse"
    
    def use(self, loult_state, server, obj_params):
        target_id, target = self._acquire_target(server, obj_params)
        if target is None:
            return

        server.channel_obj.broadcast(type="notification",
                                     msg="%s utilise le détecteur de richesse sur %s"
                                         % (server.user.poke_params.fullname, target.poke_params.fullname))
        server.send_json(type="notification",
                         msg="%s a %i objets dans son inventaire"
                             % (target.poke_params.fullname, len(target.state.inventory.objects)))


class MilitiaSniper(UsableObject, TargetedObject, MilitiaWeapon):
    NAME = "PGM Hecate II"
    SNIPER_FX = path.join(DATA_PATH, "sniper_headshot.mp3")

    def __init__(self):
        self.remaining_bullets = 7

    @property
    def name(self):
        if self.remaining_bullets:
            return self.NAME + " (%s)" % ("▮" * self.remaining_bullets)
        else:
            return self.NAME + " (vide)"

    def use(self, loult_state, server, obj_params):
        if not self._check_militia(server):
            return

        try:
            is_aiming = obj_params[0] == "aim"
            if is_aiming:
                obj_params.pop(0)
        except IndexError:
            is_aiming = False

        target_id, target = self._acquire_target(server, obj_params)
        if target is None:
            return

        if is_aiming:
            return server.channel_obj.broadcast(type="notification",
                                                msg="Un point rouge lumineux se ballade sur le front de %s"
                                                    % target.poke_params.fullname)

        if self.remaining_bullets <= 0:
            return server.send_json(type="notification",
                                    msg="Plus de munitions!")
        self.remaining_bullets -= 1
        server.channel_obj.broadcast(type="notification",
                                     msg="%s tire au fusil sniper calibre .50 sur %s"
                                         % (server.user.poke_params.fullname, target.poke_params.fullname),
                                     binary_payload=self._load_byte(self.SNIPER_FX))
        server.channel_obj.broadcast(type='antiflood', event='banned',
                                     flooder_id=target_id,
                                     date=timestamp() * 1000)
        for client in target.clients:
            loult_state.ban_ip(client.ip)
            client.sendClose(code=4006, reason="Reconnect later.")
        splashed_usrs = [usr for usr in server.channel_obj.users.values()
                         if userlist_dist(server.channel_obj, target_id, usr.user_id) < 2
                         and usr is not target]
        splashed_usrs = ", ".join(usr.poke_params.fullname for usr in splashed_usrs)
        server.channel_obj.broadcast(type="notification",
                                     msg="%s se sont faits éclabousser par de sang et de cervelle de %s"
                                         % (splashed_usrs, target.poke_params.fullname))


class MilitiaSniperAmmo(UsableObject, DestructibleObject, MilitiaWeapon):
    NAME = "Chargeur PGM"
    RELOADING_FX = path.join(DATA_PATH, "gun/reloading.mp3")

    def use(self, loult_state, server, obj_params):
        if not self._check_militia(server):
            return

        # searching in the user's inventory for the emptiest gun to be used on
        users_guns = server.user.state.inventory.search_by_class(MilitiaSniper)
        users_guns = [gun for gun in users_guns if gun.remaining_bullets < 7]
        if not users_guns:
            return server.send_json(type="notification",
                                    msg="Pas de PGM à recharger dans votre inventaire")

        users_guns.sort(key=lambda x: x.remaining_bullets, reverse=False)
        emptiest_gun = users_guns[0]
        emptiest_gun.remaining_bullets = 7
        server.send_json(type="notification", msg="PGM Hécate II chargé!")
        server.send_binary(self._load_byte(self.RELOADING_FX))
        self.should_be_destroyed = True


class Cigarettes(UsableObject, DestructibleObject):
    NAME = "cigarettes"
    BRANDS = ["Lucky Loult", "Lucky Loult Menthol", "Mrleboro", "Chesterfnre", "Sheitanes Maïs",
              "Aguloises"]
    CIG_FX = path.join(DATA_PATH, "cigarette_lighting.mp3")

    def __init__(self):
        super().__init__()
        self.brand = random.choice(self.BRANDS)
        self.cigarettes = 20

    @property
    def name(self):
        return self.brand + " (%i)" % self.cigarettes

    @property
    def destroy(self):
        return self.cigarettes <= 0

    def use(self, loult_state, server, obj_params):
        if not server.user.state.inventory.search_by_class(Lighter):
            return server.send_json(type="notification",
                                    msg="Il vous faut un briquet pour pouvoir allumer une clope!")

        self.cigarettes -= 1
        server.channel_obj.broadcast(type="notification",
                                     msg="%s allume une clope et prend un air cool"
                                         % server.user.poke_params.fullname,
                                     binary_payload=self._load_byte(self.CIG_FX))
        if random.randint(1, 10) == 1:
            server.channel_obj.broadcast(type="notification",
                                         msg="%s choppe le cancer et meurt sur le champ!"
                                             % server.user.poke_params.fullname)
            for client in server.user.clients:
                client.sendClose(code=4006, reason="Reconnect please.")


class Lighter(UsableObject):
    NAME = "briquet"
    COOLDOWN = 30 # in seconds
    CIG_FX = path.join(DATA_PATH, "lighter.mp3")

    def __init__(self):
        self.last_use = datetime(1972, 1, 1)

    def use(self, loult_state, server, obj_params):
        if (datetime.now() - self.last_use).seconds < self.COOLDOWN:
            return
        server.channel_obj.broadcast(binary_payload=self._load_byte(self.CIG_FX))
        self.last_use = datetime.now()


class MollyChute(UsableObject, DestructibleObject):
    NAME = "paras de MD"

    class LoveEffect(ExplicitTextEffect):
        NAME = "un paras"
        love_sentence = ["Attendez je vais kiffer le son là",
                         "J'ai envie de vous faire un calin à tous",
                         "Je peux t'embrasser %s?",
                         "Vous êtes tous vraiment trop sympa en fait",
                         "C'est tout doux quand je te caresse les cheveux %s",
                         "Arrêtez de vous dire des trucs méchants moi je vous aime tous",
                         "Franchement le monde est trop beau",
                         "T'es vraiment trop sympa en fait %s",
                         "C'est vraiment la plus belle soirée de ma vie"]
        TIMEOUT = 300

        def __init__(self, users_names):
            super().__init__()
            self.users = users_names

        def process(self, text: str):
            if random.randint(1, 3) == 1:
                sentence = random.choice(self.love_sentence)
                if "%s" in sentence:
                    return sentence % random.choice(self.users)
                else:
                    return sentence
            else:
                return text

    def use(self, loult_state, server, obj_params):
        efct = self.LoveEffect([usr.poke_params.pokename for usr in server.channel_obj.users.values()])
        server.user.state.add_effect(efct)
        server.channel_obj.broadcast(type="notification",
                                     msg="%s prend de la MD!" % server.user.poke_params.fullname)
        self.should_be_destroyed = True

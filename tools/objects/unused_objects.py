import random
from datetime import datetime
from os import path

from tools.effects.effects import VenerEffect
from tools.objects import LoultObject
from tools.objects.base import cooldown, destructible, targeted, userlist_dist
from tools.objects.objects import DATA_FOLDER


@cooldown(30)
class SimpleInstrument(LoultObject):
    ICON = "gong.gif"
    SND_DIR = path.join(DATA_FOLDER, "instruments/")
    INSTRUMENTS_MAPPING = {"gong": "gong.mp3"}

    def __init__(self, instrument=None):
        super().__init__()
        if instrument is None:
            instrument = random.choice(list(self.INSTRUMENTS_MAPPING.keys()))

        self.instrument_name = instrument.capitalize()
        self.fx_filepath = path.join(self.SND_DIR, self.INSTRUMENTS_MAPPING[instrument])
        self.last_used = datetime(1972, 1, 1)

    @property
    def name(self):
        return self.instrument_name

    def use(self, obj_params):
        if (datetime.now() - self.last_used).seconds < self.COOLDOWN:
            return

        self.channel.broadcast(binary_payload=self._load_byte(self.fx_filepath))
        self.last_used = datetime.now()


@destructible
@targeted()
class PolynectarPotion(LoultObject):
    NAME = "potion polynectar"
    ICON = "polynectar.gif"

    def use(self, obj_params):
        self.notify_channel(
            msg=f"{self.user.poke_params.fullname} a pris l'apparence de {self.targeted_user.poke_params.fullname}!")
        usr = self.user
        usr.poke_params = self.targeted_user.poke_params
        usr.voice_params = self.targeted_user.voice_params
        usr.poke_profile = self.targeted_user.poke_profile
        usr._info = None
        self.channel.update_userlist()
        self.should_be_destroyed = True


@destructible
@targeted()
class Cocaine(LoultObject):
    NAME = "poudre de perlinpinpin"
    ICON = "c.png"

    def use(self, obj_params):
        self.notify_channel(msg=f"{self.user_fullname} se fait une trace sur le cul de {self.user_fullname}!")
        self.user.state.add_effect(VenerEffect())
        self.should_be_destroyed = True


@targeted()
class Revolver(LoultObject):
    GUNSHOT_FX = path.join(DATA_FOLDER, "gun/gunshot.mp3")
    EMPTY_FX = path.join(DATA_FOLDER, "gun/empty_mag.mp3")
    NAME = "Walther PKK"

    def __init__(self, bullets=5):
        super().__init__()
        self.remaining_bullets = bullets

    @property
    def name(self):
        if self.remaining_bullets:
            return self.NAME + " (%s)" % ("▮" * self.remaining_bullets)
        else:
            return self.NAME + " (vide)"

    def use(self, obj_params):
        if self.remaining_bullets <= 0:
            server.send_json(type="notification",
                             msg="Plus de munitions!")
            server.send_binary(self._load_byte(self.EMPTY_FX))
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


@destructible
class RevolverCartridges(LoultObject):
    NAME = "Chargeur de pistolet"
    RELOADING_FX = path.join(DATA_FOLDER, "gun/reloading.mp3")

    def use(self, obj_params):
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


@targeted()
class SniperRifle(LoultObject):
    SNIPER_FX = path.join(DATA_FOLDER, "sniper_fx.mp3")
    NAME = "Fusil de précision"

    def __init__(self):
        super().__init__()
        self.empty = False

    @property
    def name(self):
        if self.empty:
            return self.NAME + " (vide)"
        else:
            return self.NAME

    def use(self, obj_params):
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


@destructible
class SniperBullets(LoultObject):
    NAME = "Balles de sniper"
    RELOADING_FX = path.join(DATA_FOLDER, "gun/bolt_reloading.mp3")

    def __init__(self, bullets=3):
        super().__init__()
        self.remaining_bullets = bullets

    @property
    def name(self):
        return self.NAME + " (%s)" % ("▮" * self.remaining_bullets)

    def use(self, obj_params):
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


@targeted()
class RPG(LoultObject):
    NAME = "lance-roquette"
    RPG_FX = path.join(DATA_FOLDER, "rpg_rocket.mp3")

    def __init__(self):
        super().__init__()
        self.empty = False

    @property
    def name(self):
        if self.empty:
            return self.NAME + " (vide)"
        else:
            return self.NAME

    def use(self, obj_params):
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


@destructible
class RPGRocket(LoultObject):
    NAME = "Roquette pour RPG"
    RELOADING_FX = path.join(DATA_FOLDER, "rpg_reload.mp3")

    def use(self, obj_params):
        users_rpg = server.user.state.inventory.search_by_class(RPG)
        users_rpg = [gun for gun in users_rpg if gun.empty]
        if not users_rpg:
            return server.send_json(type="notification",
                                    msg="Pas de RPG à recharger dans votre inventaire")

        empty_rpg = users_rpg[0]
        empty_rpg.empty = False
        server.send_json(type="notification", msg="RPG chargé!")
        server.send_binary(self._load_byte(self.RELOADING_FX))
        self.should_be_destroyed = True


@destructible
class Grenade(LoultObject):
    UNPIN_FX = path.join(DATA_FOLDER, "grenade_unpin.mp3")
    EXPLOSION_FX = path.join(DATA_FOLDER, "grenade_explosion.mp3")
    NAME = "Grenade"

    def use(self, obj_params):
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
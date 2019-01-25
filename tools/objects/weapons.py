import random
from itertools import cycle
from os import path
from time import time as timestamp

from tools.objects.base import UsableObject, TargetedObject, userlist_dist, \
    DestructibleObject, InertObject, MilitiaWeapon
from tools.objects.objects import DATA_PATH


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
                                    msg="Pas de RPG à recharger dans votre inventaire")

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
                                     msg="%s se sont faits éclabousser de sang et de cervelle de %s"
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


class ClientSidePunitiveObject(UsableObject, MilitiaWeapon, TargetedObject):
    EVENT = "none"
    MSG = ""

    def use(self, loult_state, server, obj_params):
        if not self._check_militia(server):
            return
        target_id, target = self._acquire_target(server, obj_params)
        if target is None:
            return

        for client in server.user.clients:
            client.send_json(type="notification", msg=self.MSG
                                                      % target.poke_params.fullname)
        for client in target.clients:
            client.send_json(type="punish", event=self.EVENT)


class Civilisator(ClientSidePunitiveObject):
    NAME = "Civilizator"
    EVENT = "taser"
    MSG = "Civilisation de %s"


class Screamer(ClientSidePunitiveObject):
    NAME = "SCR34-MR"
    EVENT = "cactus"
    MSG = "Redirection vers un site adapté pour %s"
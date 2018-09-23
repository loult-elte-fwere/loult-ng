def userlist_dist(channel_obj, userid_1, userid_2):
    userlist = list(channel_obj.users.keys())
    return abs(userlist.index(userid_1) - userlist.index(userid_2))


class LoultObject:
    NAME = "stuff"

    @property
    def name(self):
        return self.NAME

    def use(self, loult_state, server, obj_params):
        pass

    def _load_byte(self, filepath):
        with open(filepath, "rb") as binfile:
            return binfile.read()

class InertObject(LoultObject):
    """Object that doesn't do anything"""

    def use(self, loult_state, server, obj_params):
        server.send_json(type="notification",
                         msg="Cet objet ne peut être utilisé")


class UsableObject(LoultObject):
    """Object that can be used"""
    pass


class ClonableObject(LoultObject):
    """Object that gets cloned when it's given to someone else"""
    pass


class DestructibleObject(LoultObject):

    def __init__(self):
        self.should_be_destroyed = False

    @property
    def destroy(self):
        return self.should_be_destroyed


class TargetedObject(LoultObject):

    def _acquire_target(self, server, obj_params):
        try:
            target = obj_params[0]
        except KeyError:
            server.send_json(type="notification",
                             msg="Il faut spécifier un nom de pokémon (comme lors d'une attaque),"
                                 "exemple: /use 3 Taupiqueur 2")
            return None, None

        try:
            offset = int(obj_params[1]) - 1
        except Exception:
            offset = 0

        adversary_id, adversary = server.channel_obj.get_user_by_name(target, offset)
        if adversary is None:
            server.send_json(type="notification",
                                    msg="L'utilisateur visé n'existe pas")
            return None, None

        return adversary_id, adversary
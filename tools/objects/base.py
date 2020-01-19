from datetime import datetime
from pathlib import Path
from typing import Type, List

from config import MILITIA_COOKIES


def userlist_dist(channel_obj, userid_1, userid_2):
    userlist = list(channel_obj.users.keys())
    return abs(userlist.index(userid_1) - userlist.index(userid_2))


class LoultObject:
    NAME = "stuff"
    ICON = "question.gif"
    COOLDOWN = None  # in seconds
    DESTRUCTIBLE = False
    TARGETED = False
    TARGET_MANDATORY = False
    INERT = False
    CLONABLE = False
    FOR_MILITIA = False

    def __init__(self):
        from .inventory import UserInventory
        from ..state import Channel, LoultServerState
        from ..client import LoultServerProtocol
        from ..users import User
        self.last_use: datetime = datetime.fromtimestamp(0)
        self.user_inventory: UserInventory = None
        self.user: User = None
        self.server: LoultServerProtocol = None
        self.loult_state: LoultServerState = None
        self.targeted_user: User = None
        self.targeted_userid: str = None
        self.channel: Channel = None
        self.should_be_destroyed = False

    @property
    def name(self):
        return self.NAME

    @property
    def user_fullname(self):
        return self.user.poke_params.fullname

    @property
    def icon(self):
        return self.ICON

    @property
    def destroy(self):
        if self.DESTRUCTIBLE:
            return self.should_be_destroyed
        else:
            return False

    def notify_serv(self, msg: str):
        self.server.send_json(type="notification", msg=msg)

    def notify_channel(self, msg: str, binary_payload: bytes = None):
        self.channel.broadcast(type="notification", msg=msg, binary_payload=binary_payload)

    def _acquire_target(self, obj_params):
        try:
            target = obj_params[0]
        except IndexError:
            if self.TARGET_MANDATORY:
                self.notify_serv(msg="Il faut spécifier un nom de pokémon (comme lors d'une attaque), "
                                     "exemple: /use 3 Taupiqueur 2")
            self.targeted_user, self.targeted_userid = None, None
            return

        try:
            offset = int(obj_params[1]) - 1
        except Exception:
            offset = 0

        self.targeted_userid, self.targeted_user = self.channel.get_user_by_name(target, offset)
        if self.targeted_user is None:
            self.notify_serv(msg="L'utilisateur visé n'existe pas")

    def _check_militia(self):
        if self.server.raw_cookie not in MILITIA_COOKIES:
            self.notify_serv(msg="Ceci est une arme pour militiens, utilisation non autorisée!")
            self.server.sendClose(code=4006, reason="Unauthorized object")
            return False
        return True

    def __call__(self, loult_state, server, obj_params):
        self.server = server
        self.loult_state = loult_state
        self.channel = server.channel_obj
        self.user = server.user
        self.user_inventory = self.user.state.inventory

        if self.FOR_MILITIA:
            if not self._check_militia():
                return

        if self.INERT:
            self.notify_serv(msg="Cet objet ne peut être utilisé")
            return

        if self.COOLDOWN is not None:
            if (datetime.now() - self.last_use).seconds < self.COOLDOWN:
                self.notify_serv(msg="Il faut attendre pour pouvoir utiliser cet objet.")
                return

        if self.TARGETED:
            self._acquire_target(obj_params)
            if self.targeted_user is None and self.TARGET_MANDATORY:
                return

        self.use(obj_params)

        self.last_use = datetime.now()

    def use(self, obj_params: List):
        pass

    def _load_byte(self, filepath: Path):
        with open(str(filepath), "rb") as binfile:
            return binfile.read()


###  all the class decorators that set various properties
def cooldown(value: int):
    """Sets the cooldown (in seconds) for an object"""

    def wrapper(klass: Type[LoultObject]):
        klass.COOLDOWN = value
        return klass

    return wrapper


def destructible(klass: Type[LoultObject]):
    """Sets the object class as destructible"""
    klass.DESTRUCTIBLE = True
    return klass


def targeted(mandatory=True):
    """Sets the cooldown (in seconds) for an object"""

    def wrapper(klass: Type[LoultObject]):
        klass.TARGETED = True
        klass.TARGET_MANDATORY = mandatory
        return klass

    return wrapper


def inert(klass: Type[LoultObject]):
    """Sets the object class as inert (no usage)"""
    klass.INERT = True
    return klass


def clonable(klass: Type[LoultObject]):
    """Sets the object class as inert (no usage)"""
    klass.CLONABLE = True
    return klass


def for_militia(klass: Type[LoultObject]):
    """Sets the object class as inert (no usage)"""
    klass.FOR_MILITIA = True
    return klass

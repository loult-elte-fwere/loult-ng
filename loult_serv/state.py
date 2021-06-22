from asyncio import get_event_loop
from collections import OrderedDict, deque
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from time import time as timestamp
from typing import Tuple, List, Dict, Set, Optional, Deque, TYPE_CHECKING

from autobahn.exception import Disconnected

from config import MAX_COOKIES_PER_IP, BAN_TIME, CHANNEL_SETUP_INVENTORY_COUNT, ENABLE_OBJECTS
from .objects import get_random_object
from .objects.inventory import UserInventory
from .state_users import User
from .tools import encode_json, OrderedDequeDict

if TYPE_CHECKING:
    from .client import LoultServerProtocol


class Channel:

    def __init__(self, channel_name, state):
        self.name = channel_name
        self.loult_state = state
        self.clients: Set['LoultServerProtocol'] = set()
        self.users: Dict[str, User] = OrderedDict()
        self.backlog: List = []
        # this is used to track how many cookies we have per connected IP in that channel
        self.ip_cookies_tracker: Dict[str, Set[bytes]] = dict()
        self.inventory = UserInventory()
        # filling the channel's inventory with some random items
        if ENABLE_OBJECTS:
            from .objects import SantasSack
            for _ in range(3):
                self.inventory.add(SantasSack())
            for _ in range(CHANNEL_SETUP_INVENTORY_COUNT):
                self.inventory.add(get_random_object())

    def _signal_user_connect(self, client, user: User):
        client.send_json(type='connect', date=timestamp() * 1000, **user.info)

    def _signal_user_disconnect(self, client, user: User):
        client.send_json(type='disconnect', date=timestamp() * 1000,
                         userid=user.user_id)

    def broadcast(self, binary_payload=None, **kwargs):
        msg = encode_json(kwargs)
        for client in self.clients:
            try:
                if kwargs:  # in case there is no "text" message to be broadcasted
                    client.sendMessage(msg)
                if binary_payload:
                    client.send_binary(binary_payload)
            except Disconnected:
                client.sendClose(code=4000, reason="Something went wrong, closing connection")

    def get_userlist(self):
        return OrderedDict([(user_id, deepcopy(user.info))
                            for user_id, user in self.users.items()])

    def update_userlist(self):
        userlist = self.get_userlist()
        for user_id in self.users.keys():
            my_userlist = deepcopy(userlist)
            my_userlist[user_id]['params']['you'] = True
            for client in self.users[user_id].clients:
                client.send_json(type='userlist', users=list(my_userlist.values()))

    def channel_leave(self, client, user: User):
        try:
            self.users[user.user_id].clients.remove(client)

            # if the user is not connected anymore, we signal its disconnect to the others
            if len(self.users[user.user_id].clients) < 1:
                self.clients.discard(client)
                del self.users[user.user_id]

                # removing the client/user's cookie from the ip-cookie tracker
                self.ip_cookies_tracker[client.ip].remove(client.cookie)

                for client in self.clients:
                    self._signal_user_disconnect(client, user)

                # if no one's connected, we delete the channel from the register
                if not self.clients:
                    del self.loult_state.chans[self.name]
        except KeyError:
            pass

    def user_connect(self, new_user: User, client):
        if client.ip in self.ip_cookies_tracker:
            if client.cookie not in self.ip_cookies_tracker[client.ip]:
                if len(self.ip_cookies_tracker[client.ip]) >= MAX_COOKIES_PER_IP:
                    from .client import UnauthorizedCookie
                    raise UnauthorizedCookie()
                else:
                    self.ip_cookies_tracker[client.ip].add(client.cookie)
        else:
            self.ip_cookies_tracker[client.ip] = {client.cookie}

        if self.loult_state.is_shadowbanned(cookie=new_user.cookie_hash,
                                            ip=client.ip):
            new_user.state.is_shadowbanned = True

        if new_user.user_id not in self.users:
            for other_client in self.clients:
                if other_client != client:
                    self._signal_user_connect(other_client, new_user)
            self.users[new_user.user_id] = new_user
            return new_user
        else:
            self.users[new_user.user_id].clients.append(client)
            return self.users[new_user.user_id]  # returning an already existing instance of the user

    def log_to_backlog(self, user_id, msg: str, kind='msg'):
        # creating new entry
        info = {
            'user': self.users[user_id].info['params'],
            'msg': msg,
            'userid': user_id,
            'date': timestamp() * 1000,
            'type': kind,
        }

        # adding it to list and removing oldest entry
        self.backlog.append(info)
        self.backlog = self.backlog[-10:]
        return info

    def get_user_by_name(self, pokemon_name: str, order=0) -> (int, User):

        for user_id, user in self.users.items():
            if user.poke_params.pokename.lower() == pokemon_name.lower():
                if order <= 0:
                    return user_id, user
                else:
                    order -= 1

        return None, None

    def disconnect_all_clients(self, user_id=None, ip=None):
        """Either disconnects all clients for a user, or for an ip"""
        if user_id is not None:
            pass

        if ip is not None:
            pass


@dataclass(frozen=True)
class UserIdentity:
    cookie: str = None
    ip: str = None


@dataclass
class IdentitiesTracker:
    cookies: Set[str] = field(default_factory=set)
    ips: Set[str] = field(default_factory=set)

    def __contains__(self, item: UserIdentity):
        if item.cookie is not None:
            if item.cookie in self.cookies:
                return True
        if item.ip is not None:
            if item.ip in self.ips:
                return True
        return False

    def add(self, item: UserIdentity):
        if item.cookie is not None:
            self.cookies.add(item.cookie)
        if item.ip is not None:
            self.ips.add(item.ip)

    def remove(self, item: UserIdentity):
        if item.cookie is not None:
            self.cookies.remove(item.cookie)
        if item.ip is not None:
            self.ips.remove(item.ip)


@dataclass
class ConnectionEvent:
    cookie: str
    ip: str
    channel: str
    time: datetime


class IdentitiesBacklog:

    def __init__(self):
        self.backlog: Deque[ConnectionEvent] = deque(maxlen=1000)
        self.ip_last_login = OrderedDequeDict()

    def log_connection(self, cookie: str, ip: str, channel: str):
        self.backlog.append(ConnectionEvent(cookie=cookie, ip=ip,
                                            channel=channel, time=datetime.now()))
        self.ip_last_login[ip] = datetime.now()

    def get_cookie_ips(self, cookie: str):
        return set(conn.ip for conn in self.backlog if conn.cookie == cookie)

    def get_ip_cookies(self, ip: str):
        return set(conn.cookie for conn in self.backlog if conn.ip == ip)

    def get_cookie_channels(self, cookie: str):
        return set(conn.channel for conn in self.backlog if conn.cookie == cookie)

    def ip_backlog(self):
        return set(conn.ip for conn in self.backlog)


class LoultServerState:

    def __init__(self):
        self.chans: Dict[str, Channel] = {}
        self.id_backlog = IdentitiesBacklog()
        self.banned: IdentitiesTracker = IdentitiesTracker()
        self.shadowbanned: IdentitiesTracker = IdentitiesTracker()
        self.trashed: IdentitiesTracker = IdentitiesTracker()

    def channel_connect(self, client, user_cookie: str, channel_name: str) -> Tuple[Channel, User]:
        # if the channel doesn't exist, we instanciate it and add it to the channel dict
        if channel_name not in self.chans:
            self.chans[channel_name] = Channel(channel_name, self)
        channel_obj = self.chans[channel_name]
        channel_obj.clients.add(client)
        self.id_backlog.log_connection(user_cookie, client.ip, channel_name)
        return channel_obj, channel_obj.user_connect(User(user_cookie, channel_name, client), client)

    def apply_ban(self, cookie: Optional[str] = None, ip: Optional[str] = None,
                  ban_type: str = "ban",  # ban, shadowban or trash
                  duration: int = BAN_TIME * 60  # in seconds
                  ):
        identity = UserIdentity(cookie=cookie, ip=ip)
        if ban_type == "shadowban":
            tracker = self.shadowbanned
        elif ban_type == "trash":
            tracker = self.trashed
        else:
            tracker = self.banned
        if identity in tracker:
            return
        tracker.add(identity)
        loop = get_event_loop()
        loop.call_later(duration, tracker.remove, identity)

    def remove_ban(self, cookie: Optional[str] = None, ip: Optional[str] = None,
                   ban_type: str = "ban",  # ban, shadowban or trash
                   ):
        identity = UserIdentity(cookie=cookie, ip=ip)
        if ban_type == "shadowban":
            tracker = self.shadowbanned
        elif ban_type == "trash":
            tracker = self.trashed
        else:
            tracker = self.banned
        if identity in tracker:
            return
        tracker.remove(identity)

    def is_banned(self, cookie: Optional[str] = None, ip: Optional[str] = None):
        return UserIdentity(cookie=cookie, ip=ip) in self.banned

    def is_shadowbanned(self, cookie: Optional[str] = None, ip: Optional[str] = None):
        return UserIdentity(cookie=cookie, ip=ip) in self.shadowbanned

    def is_trashed(self, cookie: Optional[str] = None, ip: Optional[str] = None):
        return UserIdentity(cookie=cookie, ip=ip) in self.trashed

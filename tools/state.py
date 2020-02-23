from asyncio import get_event_loop
from collections import OrderedDict, deque
from copy import deepcopy
from time import time as timestamp
from typing import Tuple

from config import MAX_COOKIES_PER_IP, BAN_TIME, CHANNEL_SETUP_INVENTORY_COUNT, ENABLE_OBJECTS
from tools.objects.inventory import UserInventory
from tools.tools import encode_json, OrderedDequeDict
from tools.users import User
from .objects import get_random_object


class Channel:

    def __init__(self, channel_name, state):
        self.name = channel_name
        self.loult_state = state
        self.clients = set()  # type:Set[LoultServer]
        self.users = OrderedDict()  # type:OrderedDict[str, User]
        self.backlog = []  # type:List
        # this is used to track how many cookies we have per connected IP in that channel
        self.ip_cookies_tracker = dict()  # type: Dict[str,Set[bytes]]
        self.inventory = UserInventory()
        # filling the channel's inventory with some random items
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
            if kwargs:  # in case there is no "text" message to be broadcasted
                client.sendMessage(msg)
            if binary_payload:
                client.send_binary(binary_payload)

    def get_userlist(self):
        return OrderedDict([(user_id , deepcopy(user.info))
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

    def user_connect(self, new_user : User, client):
        if client.ip in self.ip_cookies_tracker:
            if client.cookie not in self.ip_cookies_tracker[client.ip]:
                if len(self.ip_cookies_tracker[client.ip]) >= MAX_COOKIES_PER_IP:
                    from .client import UnauthorizedCookie
                    raise UnauthorizedCookie()
                else:
                    self.ip_cookies_tracker[client.ip].add(client.cookie)
        else:
            self.ip_cookies_tracker[client.ip] = {client.cookie}

        if new_user.cookie_hash in self.loult_state.shadowbanned_cookies:
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


class LoultServerState:

    def __init__(self):
        self.chans = {} # type:Dict[str,Channel]
        self.banned_cookies = set() #type:Set[str]
        self.banned_ips= set() #type:Set[str]
        self.ip_backlog = deque(maxlen=100) #type: Tuple(str, str)
        self.shadowbanned_cookies = set()
        self.trashed_cookies = set()
        self.ip_last_login = OrderedDequeDict()

    def channel_connect(self, client, user_cookie : str, channel_name : str) -> Tuple[Channel, User]:
        # if the channel doesn't exist, we instanciate it and add it to the channel dict
        if channel_name not in self.chans:
            self.chans[channel_name] = Channel(channel_name, self)
        channel_obj = self.chans[channel_name]
        channel_obj.clients.add(client)

        return channel_obj, channel_obj.user_connect(User(user_cookie, channel_name, client), client)

    def ban_cookie(self, cookie : str):
        if cookie in self.banned_cookies:
            return
        self.banned_cookies.add(cookie)
        loop = get_event_loop()
        loop.call_later(BAN_TIME * 60, self.banned_cookies.remove, cookie)

    def ban_ip(self, ip: str):
        if ip in self.banned_ips:
            return
        self.banned_ips.add(ip)
        loop = get_event_loop()
        loop.call_later(BAN_TIME * 60 * 2, self.banned_ips.remove, ip)
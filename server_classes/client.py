import json
import logging
from asyncio import ensure_future
from collections import OrderedDict
from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from hashlib import md5
from os import urandom
from re import sub
from time import time as timestamp
from typing import List
import re

from autobahn.websocket.types import ConnectionDeny

from config import TIME_BETWEEN_CONNECTIONS, MOD_COOKIES, MILITIA_COOKIES, FILTER_DOMAINS, AUTHORIZED_DOMAINS
from salt import SALT
from .tools import encode_json


class Route:

    def __init__(self, field: str, value: str, handler_class):
        self.field = field
        self.value = value
        self.handler_class = handler_class


class RoutingTable:
    """Takes care of the actual routing"""

    def __init__(self, loult_state, server_protocol, routes, binary_route):
        self.server = server_protocol
        self.routing_dict = defaultdict(dict)
        for route in routes:
            self.routing_dict[route.field][route.value] = route.handler_class(loult_state, server_protocol)
        self.binary_route = binary_route(loult_state, server_protocol)

    async def route_json(self, msg_data: dict):
        for field, values in self.routing_dict.items():
            if field in msg_data:
                if msg_data[field] in values:
                    handler = values[msg_data[field]]
                    return await handler.handle(msg_data)

        self.server.logger.warning("Could not route message")

    async def route_binary(self, payload: bytes):
        return await self.binary_route.handle(payload)


class ClientRouter:
    """Only used for registering routes, which are then passed on to the routing
    table which actually instanciates handlers that process messages"""

    def __init__(self):
        self.routes = [] #type: List[Route]
        self.binary_route = None

    def add_route(self, field : str, value : str, handler_class):
        self.routes.append(Route(field, value, handler_class))

    def set_binary_route(self, handler_class):
        self.binary_route = handler_class

    def get_router(self, loultstate, server_protocol):
        return RoutingTable(loultstate, server_protocol, self.routes, self.binary_route)


class UnauthorizedCookie(Exception):
    pass


class ClientLogAdapter(logging.LoggerAdapter):

    def process(self, msg, kwargs):

        if not (self.extra.ip is None or self.extra.user is None):
            tpl = '{ip}:{user_id}:{msg}'
            msg = tpl.format(user_id=self.extra.user.user_id,
                             ip=self.extra.ip, msg=msg)
        elif self.extra.user is None and self.extra.ip is not None:
            msg = '{ip}:{msg}'.format(ip=self.extra.ip, msg=msg)
        else:
            msg = 'pre-handshake state, no information: {msg}'.format(msg=msg)

        return msg, kwargs


class LoultServerProtocol:
    router = None
    channel_n = None
    channel_obj = None
    client_logger = None
    cnx = False
    cookie = None
    ip = None
    lasttxt = None
    loult_state = None
    sendend = None
    user = None

    def __init__(self):
        if self.client_logger is None or self.loult_state is None:
            raise NotImplementedError('You must override "logger" and "state".')
        self.logger = ClientLogAdapter(self.client_logger, self)
        super().__init__()

    def onConnect(self, request):
        """HTTP-level request, triggered when the client opens the WSS connection"""

        self.ip = request.headers['x-real-ip']

        # checking if this IP's last login isn't too close from this one
        ip_backlog = self.loult_state.id_backlog.ip_last_login
        if self.ip in ip_backlog:
            if (datetime.now() - ip_backlog[self.ip]).seconds < TIME_BETWEEN_CONNECTIONS:
                raise ConnectionDeny(403, 'Wait some time before trying to connect')

        self.logger.debug('attempting a connection')

        # trying to extract the cookie from the request header. Else, creating a new cookie and
        # telling the client to store it with a Set-Cookie header
        retn = {}
        try:
            ck = request.headers['cookie'].split('id=')[1].split(';')[0]
        except (KeyError, IndexError):
            ck = urandom(16).hex()
            retn = {'Set-Cookie': 'id=%s; expires=Tue, 19 Jan 2038 03:14:07 UTC; Path=/' % ck}

        self.raw_cookie = ck
        cookie_hash = md5((ck + SALT).encode('utf8')).digest()

        if self.loult_state.is_banned(cookie=cookie_hash, ip=self.ip):
            raise ConnectionDeny(403, 'temporarily banned.')

        self.cookie = cookie_hash
        #  trashed users are automatically redirected to a "trash" channel
        if self.loult_state.is_trashed(cookie=cookie_hash, ip=self.ip):
            self.channel_n = "cancer"
        else:
            self.channel_n = request.path.lower().split('/', 2)[-1]
            self.channel_n = sub("/.*", "", self.channel_n)

        if FILTER_DOMAINS:
            if request.headers.get('origin') is not None:
                if re.sub(r"http(s)://", "", request.headers["origin"]) not in AUTHORIZED_DOMAINS:
                    self.channel_n = "cancer"
            else:
                self.channel_n = "cancer"

        self.sendend = datetime.now()
        self.lasttxt = datetime.now()

        return None, retn

    def send_json(self, **kwargs):
        self.sendMessage(encode_json(kwargs), isBinary=False)

    def send_binary(self, payload):
        self.sendMessage(payload, isBinary=True)

    def onOpen(self):
        """Triggered once the WSS is opened. Mainly consists of registering the user in the channel, and
        sending the channel's information (connected users and the backlog) to the user"""
        # telling the  connected users'register to register the current user in the current channel
        try:
            self.channel_obj, self.user = self.loult_state.channel_connect(self, self.cookie, self.channel_n)
        except UnauthorizedCookie: # this means the user's cookie was denied
            self.sendClose(code=4005, reason='Too many cookies already connected to your IP')

        # setting up routing table once all objects are functionnal
        self.routing_table = self.router.get_router(self.loult_state, self)

        # copying the channel's userlist info and telling the current JS client which userid is "its own"
        my_userlist = OrderedDict([(user_id , deepcopy(user.info))
                                   for user_id, user in self.channel_obj.users.items()])
        my_userlist[self.user.user_id]['params']['you'] = True  # tells the JS client this is the user's pokemon
        # sending the current user list to the client
        self.send_json(type='userlist', users=list(my_userlist.values()))
        self.send_json(type='backlog', msgs=self.channel_obj.backlog, date=timestamp() * 1000)

        self.cnx = True  # connected!
        self.logger.debug('has fully open a connection')

    def onMessage(self, payload, isBinary):
        """Triggered when a user sends any type of message to the server"""
        async def auto_close(coroutine):
            try:
                return await coroutine
            except OSError:
                exit(1)
            except Exception as err:
                self.sendClose(code=4000, reason=str(err))
                self.logger.error('raised an exception "%s"' % err)
                self.logger.error(err, exc_info=True)

        if isBinary:
            ensure_future(auto_close(self.routing_table.route_binary(payload)))

        else:
            try:
                msg = json.loads(payload.decode('utf-8'))
            except json.JSONDecodeError:
                return self.sendClose(code=4001, reason='Malformed JSON.')
            ensure_future(auto_close(self.routing_table.route_json(msg)))

    def onClose(self, wasClean, code, reason):
        """Triggered when the WS connection closes. Mainly consists of deregistering the user"""
        if self.cnx:
            self.channel_obj.channel_leave(self, self.user)
            # emptying user inventory to the channel's common inventory
            for obj in self.user.state.inventory.objects:
                if not (obj.CLONABLE or obj.FOR_MILITIA): # except for clonable object
                    self.channel_obj.inventory.add(obj)

        msg = 'left with reason "{}"'.format(reason) if reason else 'left'

        self.logger.debug(msg)
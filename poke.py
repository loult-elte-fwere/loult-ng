#!/usr/bin/python3
#-*- encoding: Utf-8 -*-
import json
import logging
import wave
from asyncio import get_event_loop, ensure_future, sleep, gather
from collections import OrderedDict, deque
from copy import deepcopy
from datetime import datetime, timedelta, time
from functools import lru_cache, wraps
from hashlib import md5
from html import escape
from io import BytesIO
from itertools import chain
from os import urandom, path
from re import sub
from time import time as timestamp
from typing import List, Dict, Set, Tuple

from autobahn.websocket.types import ConnectionDeny

from config import ATTACK_RESTING_TIME, BAN_TIME, MOD_COOKIES, SOUND_BROADCASTER_COOKIES, MAX_COOKIES_PER_IP, \
    TIME_BEFORE_TALK, TIME_BETWEEN_CONNECTIONS
from salt import SALT
from tools.ban import Ban, BanFail
from tools.combat import CombatSimulator
from tools.tools import INVISIBLE_CHARS, encode_json, OrderedDequeDict
from tools.users import User


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


def auto_close(method):
    @wraps(method)
    async def wrapped(*args, **kwargs):
        self = args[0]
        try:
            return await method(*args, **kwargs)
        except Exception as err:
            self.sendClose(code=4000, reason=str(err))
            self.logger.error('raised an exception "%s"' % err)
            self.logger.debug(err, exc_info=True)
    return wrapped


class LoultServer:

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
    raw_cookie = None

    def __init__(self):
        if self.client_logger is None or self.loult_state is None:
            raise NotImplementedError('You must override "logger" and "state".')
        self.logger = ClientLogAdapter(self.client_logger, self)
        super().__init__()

    def onConnect(self, request):
        """HTTP-level request, triggered when the client opens the WSS connection"""
       	self.ip = request.headers['x-real-ip']

        # checking if this IP's last login isn't too close from this one
        if self.ip in self.loult_state.ip_last_login:
            if (datetime.now() - self.loult_state.ip_last_login[self.ip]).seconds < TIME_BETWEEN_CONNECTIONS:
                raise ConnectionDeny(403, 'Wait some time before trying to connect')
        self.loult_state.ip_last_login[self.ip] = datetime.now()

        self.logger.info('attempting a connection')

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

        if cookie_hash in self.loult_state.banned_cookies:
            raise ConnectionDeny(403, 'temporarily banned for flooding.')

        self.cookie = cookie_hash
        #  trashed cookies are automatically redirected to a "trash" channel
        if self.cookie in self.loult_state.trashed_cookies:
            self.channel_n = "cancer"
        else:
            self.channel_n = request.path.lower().split('/', 2)[-1]
            self.channel_n = sub("/.*", "", self.channel_n)
        self.sendend = datetime.now()
        self.lasttxt = datetime.now()

        return None, retn

    def onOpen(self):
        """Triggered once the WSS is opened. Mainly consists of registering the user in the channel, and
        sending the channel's information (connected users and the backlog) to the user"""
        # telling the  connected users'register to register the current user in the current channel
        try:
            self.channel_obj, self.user = self.loult_state.channel_connect(self, self.cookie, self.channel_n)
        except UnauthorizedCookie: # this means the user's cookie was denied
            self.sendClose(code=4005, reason='Too many cookies already connected to your IP')

        # copying the channel's userlist info and telling the current JS client which userid is "its own"
        my_userlist = OrderedDict([(user_id , deepcopy(user.info))
                                   for user_id, user in self.channel_obj.users.items()])
        my_userlist[self.user.user_id]['params']['you'] = True  # tells the JS client this is the user's pokemon
        # sending the current user list to the client
        self.send_json(type='userlist', users=list(my_userlist.values()))
        self.send_json(type='backlog', msgs=self.channel_obj.backlog, date=timestamp() * 1000)

        self.cnx = True  # connected!
        self.logger.info('has fully open a connection')

    def send_json(self, **kwargs):
        self.sendMessage(encode_json(kwargs), isBinary=False)

    def send_binary(self, payload):
        self.sendMessage(payload, isBinary=True)

    def _check_flood(self, msg):
        if not self.user.state.check_flood(msg):
            return False

        if self.cookie in self.loult_state.banned_cookies:
            return True

        if self.user.state.has_been_warned: # user has already been warned. Ban him/her and notify everyone
            self.logger.info('has been detected as a flooder')
            self.channel_obj.broadcast(type='antiflood', event='banned',
                                       flooder_id=self.user.user_id,
                                       date=timestamp() * 1000)
            self.loult_state.ban_cookie(self.cookie)
            self.sendClose(code=4004, reason='banned for flooding')
        else:
            # resets the user's msg log, then warns the user
            self.user.state.reset_flood_detection()
            self.user.state.has_been_warned = True
            self.send_json(type='antiflood', event='flood_warning',
                           date=timestamp() * 1000)
            alarm_sound = self._open_sound_file("tools/data/alerts/alarm.wav")
            self.send_binary(alarm_sound)
            self.logger.info('has been warned for flooding')
        return True

    @auto_close
    async def _msg_handler(self, msg_data : Dict):
        now = datetime.now()
        if (now - self.user.state.connection_time).seconds < TIME_BEFORE_TALK:
            return self.send_json(type='wait',date=timestamp()*1000)

        if self._check_flood(msg_data['msg']):
            return
        # user object instance renders both the output sound and output text
        output_msg, wav = await self.user.render_message(msg_data["msg"], msg_data.get("lang", "fr"))
        # estimating the end of the current voice render, to rate limit
        calc_sendend = max(self.sendend, now) + timedelta(seconds=len(wav) * 8 / 6000000)
        synth = calc_sendend < now + timedelta(seconds=2.5)
        if synth:
            self.sendend = calc_sendend

        output_msg = escape(output_msg)

        # send to the backlog
        info = self.channel_obj.log_to_backlog(self.user.user_id, output_msg)
        if not self.user.state.is_shadowbanned:
            if "notext" in msg_data and self.raw_cookie in SOUND_BROADCASTER_COOKIES:
                self.channel_obj.broadcast(type="audio_broadcast", userid=self.user.user_id,
                                           binary_payload=wav if synth else None)
            else:
                # broadcast message and rendered audio to all clients in the channel
                self.channel_obj.broadcast(type='msg', userid=self.user.user_id,
                                           msg=output_msg, date=info['date'],
                                           binary_payload=wav if synth else None)
        else: # we just send the message to the current client
            self.send_json(type='msg', userid=self.user.user_id,
                           msg=output_msg, date=info['date'])
            if synth:
                self.send_binary(wav)

    @auto_close
    async def _pm_handler(self, msg_data: Dict):
        # cleaning up none values in case of fuckups
        msg_data = {key: value for key, value in msg_data.items() if value is not None}
        target = self.channel_obj.users.get(msg_data.get("userid"))
        if target is None:
            self.send_json(type='private_msg', event='invalid')
        for client in self.channel_obj.clients:
            if client.user == target:
                client.send_json(type='private_msg', msg=msg_data["msg"])


    @auto_close
    async def _norender_msg_handler(self, msg_data: Dict):
        """This handler is for messages that are displayed without a sound render, like bot status messages or
        /me commands"""
        msg_type = msg_data['type']
        user_id = self.user.user_id
        output_msg = escape(msg_data['msg'])
        if self._check_flood(output_msg):
            return

        info = self.channel_obj.log_to_backlog(user_id, output_msg, kind=msg_type)
        if not self.user.state.is_shadowbanned:
            self.channel_obj.broadcast(type=msg_type, msg=output_msg,
                                       userid=user_id, date=info['date'])
        else: # user is shadowbanned, so it's only sent to the
            self.send_json(type=msg_type, msg=output_msg,
                           userid=user_id, date=info['date'])

    @lru_cache()
    def _open_sound_file(self, relative_path):
        """Opens a wav file from a path relative to the current directory."""
        full_path = path.join(path.dirname(path.realpath(__file__)), relative_path)
        with open(full_path, "rb") as sound_file:
            return sound_file.read()

    @auto_close
    async def _attack_handler(self, msg_data : Dict):
        # cleaning up none values in case of fuckups
        msg_data = {key: value for key, value in msg_data.items() if value is not None}

        adversary_id, adversary = self.channel_obj.get_user_by_name(msg_data.get("target",
                                                                                 self.user.poke_params.pokename),
                                                                    msg_data.get("order", 1) - 1)
        now = datetime.now()

        # checking if the target user is found, and if the current user has waited long enough to attack
        if adversary is None:
            self.send_json(type='attack', event='invalid')
        elif (now - self.user.state.last_attack < timedelta(seconds=ATTACK_RESTING_TIME)):
            self.send_json(type='attack', event='invalid')
        else:
            self.channel_obj.broadcast(type='attack', date=timestamp() * 1000,
                                       event='attack',
                                       attacker_id=self.user.user_id,
                                       defender_id=adversary_id)

            combat_sim = CombatSimulator()
            combat_sim.run_attack(self.user, adversary, self.channel_obj)
            self.channel_obj.broadcast(type='attack', date=timestamp() * 1000,
                                       event='dice',
                                       attacker_dice=combat_sim.atk_dice,
                                       defender_dice=combat_sim.def_dice,
                                       attacker_bonus=combat_sim.atk_bonus,
                                       defender_bonus=combat_sim.def_bonus,
                                       attacker_id=self.user.user_id,
                                       defender_id=adversary_id)

            if combat_sim.affected_users: # there are users affected by some effects
                for user, effect in combat_sim.affected_users:
                    self.channel_obj.broadcast(type='attack', date=timestamp() * 1000,
                                               event='effect',
                                               tag=effect.TAG if hasattr(effect, "TAG") else None,
                                               target_id=user.user_id,
                                               effect=effect.name,
                                               timeout=effect.timeout)
            else: # list is empty, no one was attacked
                self.channel_obj.broadcast(type='attack', date=timestamp() * 1000,
                                           event='nothing')

            # combat_sim uses the last attack time to compute the bonus,
            # so it must be updated after the running the attack.
            self.user.state.last_attack = now


    @auto_close
    async def _move_handler(self, msg_data : Dict):
        # checking if all the necessary data is here
        if not {"x", "y", "id"}.issubset(set(msg_data.keys())):
            return
        # signalling all users in channel that this user moved
        self.channel_obj.broadcast(type='move',
                                   id=escape(msg_data['id'][:12]),
                                   userid=self.user.user_id,
                                   x=float(msg_data['x']),
                                   y=float(msg_data['y']))

    @auto_close
    async def _ban_handler(self, msg_data : Dict):
        user_id = msg_data['userid']
        ban_type = msg_data['type']
        action = msg_data['action']
        timeout = msg_data.get('timeout', None)
        info = {'type': ban_type, 'userid': user_id}

        if not self.loult_state.can_ban:
            info['state'] = 'ban_system_disabled'
            return self.send_json(**info)

        if self.raw_cookie not in MOD_COOKIES:
            info['state'] = 'unauthorized'
            self.logger.info('unauthorized access to ban tools')
            return self.send_json(**info)

        if "signal_client" in msg_data:
            # before even running the ban, each clients of the concerned user is notified of the ban
            for client in [client for client in self.channel_obj.clients if client.user and client.user.user_id == user_id]:
                client.send_json(type="banned",
                                 msg="ofwere")

        if action == "apply" and ban_type == "ban":
            # and everyone is notified of the ban as to instigate fear in the heart of others
            self.channel_obj.broadcast(type='antiflood', event='banned',
                                       flooder_id=user_id,
                                       date=timestamp() * 1000)

        connected_list = {client.ip for client in self.channel_obj.clients
                          if client.user and client.user.user_id == user_id}
        backlog_list = {ip for userid, ip in self.loult_state.ip_backlog
                        if userid == user_id}
        todo = connected_list | backlog_list

        log_msg = '{type}:{ip}:{userid}:resulted in "{state}"'

        try:
            ban = Ban(ban_type, action, timeout)
            info['state'] = await ban(todo)
            self.logger.info(log_msg.format(**info, ip=todo))
            self.send_json(**info)
        except BanFail as err:
            info['state'] = err.state
            self.logger.info(log_msg.format(**info, ip=todo))
            self.send_json(**info)

    @auto_close
    async def _shadowban_handler(self, msg_data : Dict):
        user_id = msg_data['userid']

        if self.raw_cookie not in MOD_COOKIES:
            self.logger.info('unauthorized access to shadowban tools')
            return self.send_json(type="shadowban", userid=user_id, state="unauthorized")

        shadowbanned_user = self.channel_obj.users[user_id]
        if msg_data["action"] == "apply":
            shadowbanned_user.state.is_shadowbanned = True
            loult_state.shadowbanned_cookies.add(shadowbanned_user.cookie_hash)
            self.send_json(type="shadowban", userid=user_id, state="apply_ok")
        elif msg_data["action"] == "remove":
            shadowbanned_user.state.is_shadowbanned = False
            loult_state.shadowbanned_cookies.remove(shadowbanned_user.cookie_hash)
            self.send_json(type="shadowban", userid=user_id, state="remove_ok")

    @auto_close
    async def _trash_handler(self, msg_data: Dict):
        user_id = msg_data['userid']

        if self.raw_cookie not in MOD_COOKIES:
            self.logger.info('unauthorized access to trash tools')
            return self.send_json(type="shadowban", userid=user_id, state="unauthorized")

        trashed_user = self.channel_obj.users[user_id]
        if msg_data["action"] == "apply":
            loult_state.trashed_cookies.add(trashed_user.cookie_hash)
            self.send_json(type="trash", userid=user_id, state="apply_ok")
            for client in self.channel_obj.clients:
                if client.user is not None and client.user.user_id == user_id:
                    client.sendClose(code=4006,reason="Reconnect please")
        elif msg_data["action"] == "remove":
            loult_state.trashed_cookies.remove(trashed_user.cookie_hash)
            self.send_json(type="trash", userid=user_id, state="remove_ok")

    @auto_close
    async def _binary_handler(self, payload):
        print("%s sending a sound file" % self.raw_cookie)
        if self.raw_cookie in SOUND_BROADCASTER_COOKIES:
            try:
                _ = wave.open(BytesIO(payload)) # testing if it's a proper wav file
                self.channel_obj.broadcast(type="audio_broadcast", userid=self.user.user_id,
                                           binary_payload=payload)
            except wave.Error:
                return self.sendClose(code=4002,
                                      reason='Invalid wav sound file')
        else:
            return self.sendClose(code=4002,
                                  reason='Binary data is not accepted')


    def onMessage(self, payload, isBinary):
        """Triggered when a user sends any type of message to the server"""
        if isBinary:
            ensure_future(self._binary_handler(payload))

        else:
            try:
                msg = json.loads(payload.decode('utf-8'))
            except json.JSONDecodeError:
                return self.sendClose(code=4001, reason='Malformed JSON.')

            if 'msg' in msg:
                msg['msg'] = sub(INVISIBLE_CHARS, '', msg['msg'])

            if msg['type'] == 'msg':
                # when the message is just a simple text message (regular chat)
                ensure_future(self._msg_handler(msg))

            if msg['type'] == 'private_msg':
                # when it's a private message destined to a specific user
                ensure_future(self._pm_handler(msg))

            elif msg["type"] == "attack":
                # when the current client attacks someone else
                ensure_future(self._attack_handler(msg))

            elif msg["type"] == "move":
                # when a user moves
                ensure_future(self._move_handler(msg))

            elif msg["type"] in Ban.ban_types:
                ensure_future(self._ban_handler(msg))

            elif msg["type"] == "shadowban":
                ensure_future(self._shadowban_handler(msg))

            elif msg["type"] == "trash":
                ensure_future(self._trash_handler(msg))

            elif msg['type'] in ('me', 'bot'):
                ensure_future(self._norender_msg_handler(msg))

    def onClose(self, wasClean, code, reason):
        """Triggered when the WS connection closes. Mainly consists of deregistering the user"""
        if self.cnx:
            # This lets moderators ban an user even after their disconnection
            self.loult_state.ip_backlog.append((self.user.user_id, self.ip))
            self.channel_obj.channel_leave(self, self.user)

        msg = 'left with reason "{}"'.format(reason) if reason else 'left'

        self.logger.info(msg)


class Channel:

    def __init__(self, channel_name, state):
        self.name = channel_name
        self.loult_state = state
        self.clients = set()  # type:Set[LoultServer]
        self.users = OrderedDict()  # type:OrderedDict[str, User]
        self.backlog = []  # type:List
        # this is used to track how many cookies we have per connected IP in that channel
        self.ip_cookies_tracker = dict()  # type: Dict[str,Set[bytes]]

    def _signal_user_connect(self, client: LoultServer, user: User):
        client.send_json(type='connect', date=timestamp() * 1000, **user.info)

    def _signal_user_disconnect(self, client: LoultServer, user: User):
        client.send_json(type='disconnect', date=timestamp() * 1000,
                         userid=user.user_id)

    def broadcast(self, binary_payload=None, **kwargs):
        msg = encode_json(kwargs)
        for client in self.clients:
            if kwargs:  # in case there is no "text" message to be broadcasted
                client.sendMessage(msg)
            if binary_payload:
                client.send_binary(binary_payload)

    def channel_leave(self, client: LoultServer, user: User):
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

                # if no one's connected dans the backlog is empty, we delete the channel from the register
                if not self.clients and not self.backlog:
                    del self.loult_state.chans[self.name]
        except KeyError:
            pass

    def user_connect(self, new_user : User, client : LoultServer):
        if client.ip in self.ip_cookies_tracker:
            if client.cookie not in self.ip_cookies_tracker[client.ip]:
                if len(self.ip_cookies_tracker[client.ip]) >= MAX_COOKIES_PER_IP:
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


class LoultServerState:

    def __init__(self):
        self.chans = {} # type:Dict[str,Channel]
        self.banned_cookies = set() #type:Set[str]
        self.ip_backlog = deque(maxlen=100) #type: Tuple(str, str)
        self.shadowbanned_cookies = set()
        self.trashed_cookies = set()
        self.ip_last_login = OrderedDequeDict()

    def channel_connect(self, client : LoultServer, user_cookie : str, channel_name : str) -> Tuple[Channel, User]:
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


async def say_hi():
    while True:
        await sleep(5)
        print("WESH WESH")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger('server')

## uncomment once https://github.com/MagicStack/uvloop/issues/93 is closed
#    try:
#        asyncio_policy = get_event_loop_policy()
#        import uvloop
#        # Make sure to set uvloop as the default before importing anything
#        # from autobahn else it won't use uvloop
#        set_event_loop_policy(uvloop.EventLoopPolicy())
#        logger.info("uvloop's event loop succesfully activated.")
#    except:
#        set_event_loop_policy(asyncio_policy)
#        logger.info("Failed to use uvloop, falling back to asyncio's event loop.")
#    finally:
#        from autobahn.asyncio.websocket import WebSocketServerProtocol, \
#            WebSocketServerFactory
    from autobahn.asyncio.websocket import WebSocketServerProtocol, \
        WebSocketServerFactory

    loop = get_event_loop()
    loult_state = LoultServerState()

    # setting up events
    from tools.events import (EventScheduler, BienChantewEvent, MaledictionEvent, BienDowmiwEvent,
                              UsersVoicesShuffleEvent, AmphetamineEvent, TunnelEvent, next_occ)
    scheduler = EventScheduler(loult_state,
                               [BienChantewEvent(timedelta(days=1), next_occ(datetime.day, time(hour=22, minute=0))),
                                MaledictionEvent(timedelta(days=1), next_occ(datetime.day, time(hour=4, minute=0))),
                                BienDowmiwEvent(timedelta(days=1), next_occ(datetime.day, time(hour=0, minute=0))),
                                UsersVoicesShuffleEvent(timedelta(hours=4), timedelta(hours=0.5)),
                                AmphetamineEvent(timedelta(hours=6), timedelta(hours=1)),
                                TunnelEvent(timedelta(hours=2), timedelta(hours=0.5)),
                                ])

    try:
        loop.run_until_complete(Ban.test_ban())
        loult_state.can_ban = True
    except BanFail:
        loult_state.can_ban = False
        logger.warning("nft command dosen't work; bans are disabled.")


    class AutobahnLoultServer(LoultServer, WebSocketServerProtocol):
        loult_state = loult_state
        client_logger = logging.getLogger('client')


    factory = WebSocketServerFactory(server='Lou.lt/NG') # 'ws://127.0.0.1:9000',
    factory.protocol = AutobahnLoultServer
    # Allow 4KiB max size for messages, in a single frame.
    factory.setProtocolOptions(
            autoPingInterval=60,
            autoPingTimeout=30,
        )

    coro = loop.create_server(factory, '127.0.0.1', 9000)
    scheduler_task = ensure_future(scheduler.start())
    server = loop.run_until_complete(gather(coro, scheduler_task))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info('Shutting down all connections...')
        for client in chain.from_iterable((channel.clients for channel in loult_state.chans.values())):
            client.sendClose(code=1000, reason='Server shutting down.')
        loop.close()
        print('aplse')

#!/usr/bin/python3
#-*- encoding: Utf-8 -*-
import logging
import random
from asyncio import get_event_loop, set_event_loop_policy, \
        get_event_loop_policy, ensure_future
from collections import OrderedDict, deque
from copy import deepcopy
from datetime import datetime, timedelta
from hashlib import md5
from html import escape
import json
from os import urandom, path
from re import sub
from time import time
from functools import lru_cache, wraps
from itertools import chain
from typing import List, Dict, Set, Tuple, Optional

from autobahn.websocket.types import ConnectionDeny

from config import ATTACK_RESTING_TIME, BAN_TIME, BANNED_WORDS, MOD_COOKIES
from salt import SALT
from tools.ban import Ban, BanFail
from tools.combat import CombatSimulator
from tools.effects import Effect, AudioEffect, HiddenTextEffect, ExplicitTextEffect, PhonemicEffect, \
     VoiceEffect
from tools.phonems import PhonemList
from tools.tools import AudioRenderer, SpoilerBipEffect, VoiceParameters, PokeParameters, UserState, \
    prepare_text_for_tts, INVISIBLE_CHARS


def encode_json(data):
    return json.dumps(data, ensure_ascii=False).encode('utf-8')


class User:
    """Stores a user's state and parameters, which are also used to render the user's audio messages"""

    def __init__(self, cookie_hash, channel, client):
        """Initiating a user using its cookie md5 hash"""
        self.audio_renderer = AudioRenderer()
        self.voice_params = VoiceParameters.from_cookie_hash(cookie_hash)
        self.poke_params = PokeParameters.from_cookie_hash(cookie_hash)
        self.user_id = cookie_hash.hex()[-16:]

        self.channel = channel
        self.clients = [client]
        self.state = UserState()
        self._info = None

    def __hash__(self):
        return self.user_id.__hash__()

    def __eq__(self, other):
        return self.user_id == other.user_id

    def throw_dice(self, type="attack") -> Tuple[int, int]:
        bonus = (datetime.now() - self.state.last_attack).seconds // ATTACK_RESTING_TIME if type == "attack" else 0
        return random.randint(1, 100), bonus

    @property
    def info(self):
        if self._info is None:
            self._info = {
                'userid': self.user_id,
                'params': {
                    'name': self.poke_params.pokename,
                    'img': str(self.poke_params.poke_id).zfill(3),
                    'color': self.poke_params.color
                }
            }
        return self._info

    @staticmethod
    def apply_effects(input_obj, effect_list: List[Effect]):
        if effect_list:
            for effect in effect_list:
                if effect.is_expired():
                    effect_list.remove(effect)  # if the effect has expired, remove it
                else:
                    input_obj = effect.process(input_obj)

        return input_obj

    async def _vocode(self, text: str, lang: str) -> bytes:
        """Renders a text and a language to a wav bytes object using espeak + mbrola"""
        # if there are voice effects, apply them to the voice renderer's voice and give them to the renderer
        if self.state.effects[VoiceEffect]:
            voice_params = self.apply_effects(self.voice_params, self.state.effects[VoiceEffect])
        else:
            voice_params = self.voice_params

        # apply the beep effect for spoilers
        beeped = await SpoilerBipEffect(self.audio_renderer, voice_params).process(text, lang)

        if isinstance(beeped, PhonemList) or self.state.effects[PhonemicEffect]:

            modified_phonems = None
            if isinstance(beeped, PhonemList) and self.state.effects[PhonemicEffect]:
                # if it's already a phonem list, we apply the effect diretcly
                modified_phonems = self.apply_effects(beeped, self.state.effects[PhonemicEffect])
            elif isinstance(beeped, PhonemList):
                # no effects, only the beeped phonem list
                modified_phonems = beeped
            elif self.state.effects[PhonemicEffect]:
                # first running the text-to-phonems conversion, then applying the phonemic tools
                phonems = await self.audio_renderer.string_to_phonemes(text, lang, voice_params)
                modified_phonems = self.apply_effects(phonems, self.state.effects[PhonemicEffect])

            #rendering audio using the phonemlist
            return await self.audio_renderer.phonemes_to_audio(modified_phonems, lang, voice_params)
        else:
            # regular render
            return await self.audio_renderer.string_to_audio(text, lang, voice_params)

    async def render_message(self, text: str, lang: str):
        cleaned_text = text[:500]
        # applying "explicit" effects (visible to the users)
        displayed_text = self.apply_effects(cleaned_text, self.state.effects[ExplicitTextEffect])
        # applying "hidden" texts effects (invisible on the chat, only heard in the audio)
        rendered_text = self.apply_effects(displayed_text, self.state.effects[HiddenTextEffect])
        rendered_text = prepare_text_for_tts(rendered_text, lang)

        # rendering the audio from the text
        wav = await self._vocode(rendered_text, lang)

        # if there are effets in the audio_effect list, we run it
        if self.state.effects[AudioEffect]:
            # converting to f32 (more standard) and resampling to 16k if needed, and converting to a ndarray
            rate , data = await self.audio_renderer.to_f32_16k(wav)
            # applying the effects pipeline to the sound
            data = self.apply_effects(data, self.state.effects[AudioEffect])
            # converting the sound's ndarray back to bytes
            wav = self.audio_renderer.to_wav_bytes(data, rate)

        return displayed_text, wav


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
        self.channel_n = request.path.lower().split('/', 2)[-1]
        self.channel_n = sub("/.*", "", self.channel_n)
        self.sendend = datetime.now()
        self.lasttxt = datetime.now()

        return None, retn

    def onOpen(self):
        """Triggered once the WSS is opened. Mainly consists of registering the user in the channel, and
        sending the channel's information (connected users and the backlog) to the user"""
        # telling the  connected users'register to register the current user in the current channel
        self.channel_obj, self.user = self.loult_state.channel_connect(self, self.cookie, self.channel_n)

        # copying the channel's userlist info and telling the current JS client which userid is "its own"
        my_userlist = OrderedDict([(user_id , deepcopy(user.info))
                                   for user_id, user in self.channel_obj.users.items()])
        my_userlist[self.user.user_id]['params']['you'] = True  # tells the JS client this is the user's pokemon
        # sending the current user list to the client
        self.send_json(type='userlist', users=list(my_userlist.values()))
        self.send_json(type='backlog', msgs=self.channel_obj.backlog)

        self.cnx = True  # connected!
        self.logger.info('has fully open a connection')

    def send_json(self, **kwargs):
        self.sendMessage(encode_json(kwargs), isBinary=False)

    def send_binary(self, payload):
        self.sendMessage(payload, isBinary=True)

    def _broadcast_to_channel(self, binary_payload=None, **kwargs):
        msg = encode_json(kwargs)
        for client in self.channel_obj.clients:
            client.sendMessage(msg)
            if binary_payload:
                client.send_binary(binary_payload)

    def _check_flood(self, msg):
        self.user.state.add_to_backlog(msg)
        if not self.user.state.is_flooding:
            return False

        if self.cookie in self.loult_state.banned_cookies:
            return True

        if self.user.state.warned: # user has already been warned. Ban him/her and notify everyone
            self.logger.info('has been detected as a flooder')
            self._broadcast_to_channel(type='antiflood', event='banned',
                                       flooder_id=self.user.user_id,
                                       date=time() * 1000)
            self.loult_state.ban_cookie(self.cookie)
            self.sendClose(code=4004, reason='banned for flooding')
        else:
            # resets the user's msg log, then warns the user
            self.user.state.reset_flood_detection()
            self.user.state.warned = True
            self.send_json(type='antiflood', event='flood_warning',
                           date=time() * 1000)
            alarm_sound = self._open_sound_file("tools/data/alerts/alarm.wav")
            self.send_binary(alarm_sound)
            self.logger.info('has been warned for flooding')
        return True

    @auto_close
    async def _msg_handler(self, msg_data : Dict):
        now = datetime.now()
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

        # broadcast message and rendered audio to all clients in the channel
        self._broadcast_to_channel(type='msg', userid=self.user.user_id,
                                   msg=output_msg, date=info['date'],
                                   binary_payload=wav if synth else None)

    @auto_close
    async def _extra_handler(self, msg_data: Dict):
        msg_type = msg_data['type']
        user_id = self.user.user_id
        output_msg = escape(msg_data['msg'])

        info = self.channel_obj.log_to_backlog(user_id, output_msg, kind=msg_type)
        self._broadcast_to_channel(type=msg_type, msg=output_msg,
                                   userid=user_id, date=info['date'])

    @lru_cache()
    def _open_sound_file(self, relative_path):
        """Sends a wav file from a path relative to the current directory."""
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
            return
        else:
            self._broadcast_to_channel(type='attack', date=time() * 1000,
                                       event='attack',
                                       attacker_id=self.user.user_id,
                                       defender_id=adversary_id)

            combat_sim = CombatSimulator()
            combat_sim.run_attack(self.user, adversary, self.channel_obj)
            self._broadcast_to_channel(type='attack', date=time() * 1000,
                                       event='dice',
                                       attacker_dice=combat_sim.atk_dice,
                                       defender_dice=combat_sim.def_dice,
                                       attacker_bonus=combat_sim.atk_bonus,
                                       defender_bonus=combat_sim.def_bonus,
                                       attacker_id=self.user.user_id,
                                       defender_id=adversary_id)

            if combat_sim.affected_users: # there are users affected by some effects
                for user, effect in combat_sim.affected_users:
                    self._broadcast_to_channel(type='attack', date=time() * 1000,
                                               event='effect',
                                               target_id=user.user_id,
                                               effect=effect.name,
                                               timeout=effect.timeout)
            else: # list is empty, no one was attacked
                self._broadcast_to_channel(type='attack', date=time() * 1000,
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
        self._broadcast_to_channel(type='move',
                                   id=escape(msg_data['id'][:12]),
                                   userid=self.user.user_id,
                                   x=float(msg_data['x']),
                                   y=float(msg_data['y']))

    @auto_close
    async def _ban_handler(self, msg_data : Dict):
        user_id = msg_data['userid']
        ban_type = msg_data['type']
        state = msg_data['state']
        timeout = msg_data.get('timeout', None)
        info = {'type': ban_type, 'userid': user_id}

        if not self.loult_state.can_ban:
            info['state'] = 'ban_system_disabled'
            return self.send_json(**info)

        if self.raw_cookie not in MOD_COOKIES:
            info['state'] = 'unauthorized'
            self.logger.info('unauthorized access to ban tools')
            return self.send_json(**info)

        connected_list = {client.ip for client in self.channel_obj.clients
                          if client.user.user_id == user_id}
        backlog_list = {ip for userid, ip in self.loult_state.ip_backlog
                        if userid == user_id}
        todo = connected_list | backlog_list

        log_msg = '{type}:{ip}:{userid}:resulted in "{state}"'

        try:
            ban = Ban(ban_type, state, timeout)
            info['state'] = await ban(todo)
            self.logger.info(log_msg.format(**info, ip=todo))
            self.send_json(**info)
        except BanFail as err:
            info['state'] = err.state
            self.logger.info(log_msg.format(**info, ip=todo))
            self.send_json(**info)

    def onMessage(self, payload, isBinary):
        """Triggered when a user receives a message"""
        if isBinary:
            return self.sendClose(code=4002,
                                  reason='Binary data is not accepted')

        try:
            msg = json.loads(payload.decode('utf-8'))
        except json.JSONDecodeError:
            return self.sendClose(code=4001, reason='Malformed JSON.')

        if msg['type'] in ('msg', 'me', 'bot'):
            if self._check_flood(msg['msg']):
                return

        if 'msg' in msg:
            msg['msg'] = sub(INVISIBLE_CHARS, '', msg['msg'])

        if msg['type'] == 'msg':
            # when the message is just a simple text message (regular chat)
            ensure_future(self._msg_handler(msg))

        elif msg["type"] == "attack":
            # when the current client attacks someone else
            ensure_future(self._attack_handler(msg))

        elif msg["type"] == "move":
            # when a user moves
            ensure_future(self._move_handler(msg))

        elif msg["type"] in Ban.ban_types:
            ensure_future(self._ban_handler(msg))

        elif msg['type'] in ('me', 'bot'):
            ensure_future(self._extra_handler(msg))

        else:
            return self.sendClose(code=4003,
                                  reason='Unrecognized command type.')

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

    def _signal_user_connect(self, client: LoultServer, user: User):
        client.send_json(type='connect', date=time() * 1000, **user.info)

    def _signal_user_disconnect(self, client: LoultServer, user: User):
        client.send_json(type='disconnect', date=time() * 1000,
                         userid=user.user_id)

    def channel_leave(self, client: LoultServer, user: User):
        try:
            self.users[user.user_id].clients.remove(client)

            # if the user is not connected anymore, we signal its disconnect to the others
            if len(self.users[user.user_id].clients) < 1:
                self.clients.discard(client)
                del self.users[user.user_id]

                for client in self.clients:
                    self._signal_user_disconnect(client, user)

                # if no one's connected dans the backlog is empty, we delete the channel from the register
                if not self.clients and not self.backlog:
                    del self.loult_state.chans[self.name]
        except KeyError:
            pass

    def user_connect(self, new_user : User, client : LoultServer):
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
            'date': time() * 1000,
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
            maxFramePayloadSize=4096,
            maxMessagePayloadSize=4096,
        )

    coro = loop.create_server(factory, '127.0.0.1', 9000)
    server = loop.run_until_complete(coro)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info('Shutting down all connections...')
        for client in chain.from_iterable((channel.clients for channel in loult_state.chans.values())):
            client.sendClose(code=1000, reason='Server shutting down.')
        loop.close()
        print('aplse')

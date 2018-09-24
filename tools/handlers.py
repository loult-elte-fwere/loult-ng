from typing import Dict
from datetime import datetime, timedelta
from time import time as timestamp
from html import escape

from tools.objects.base import ClonableObject, DestructibleObject
from .combat import CombatSimulator
from .ban import Ban, BanFail
from io import BytesIO
from scipy.io import wavfile

from config import ATTACK_RESTING_TIME, BAN_TIME, MOD_COOKIES, SOUND_BROADCASTER_COOKIES, MAX_COOKIES_PER_IP, \
    TIME_BEFORE_TALK, TIME_BETWEEN_CONNECTIONS
from tools.tools import open_sound_file


class BaseHandler:

    def __init__(self, server_state, my_server):
        self.loult_state = server_state
        self.server = my_server
        self.channel_obj = self.server.channel_obj
        self.user = self.server.user

    async def handle(self, *args):
        pass


class MsgBaseHandler(BaseHandler):

    async def handle(self, msg_data: Dict):
        pass


class BinaryHandler(BaseHandler):

    async def handle(self, payload: bytes):
        if self.server.raw_cookie in SOUND_BROADCASTER_COOKIES:
            try:
                _ = wavfile.read(BytesIO(payload)) # testing if it's a proper wav file
                self.channel_obj.broadcast(type="audio_broadcast", userid=self.user.user_id,
                                           binary_payload=payload)
            except:
                return self.server.sendClose(code=4002,
                                             reason='Invalid wav sound file')
        else:
            return self.server.sendClose(code=4002,
                                         reason='Binary data is not accepted')


class FloodCheckerHandler(MsgBaseHandler):

    def _check_flood(self, msg):
        if not self.user.state.check_flood(msg):
            return False

        if self.server.cookie in self.loult_state.banned_cookies:
            return True

        if self.user.state.has_been_warned: # user has already been warned. Ban him/her and notify everyone
            self.server.logger.info('has been detected as a flooder')
            self.channel_obj.broadcast(type='antiflood', event='banned',
                                       flooder_id=self.user.user_id,
                                       date=timestamp() * 1000)
            self.loult_state.ban_cookie(self.server.cookie)
            self.server.sendClose(code=4004, reason='banned for flooding')
        else:
            # resets the user's msg log, then warns the user
            self.user.state.reset_flood_detection()
            self.user.state.has_been_warned = True
            self.server.send_json(type='antiflood', event='flood_warning',
                           date=timestamp() * 1000)
            alarm_sound = open_sound_file("tools/data/alerts/alarm.wav")
            self.server.send_binary(alarm_sound)
            self.server.logger.info('has been warned for flooding')
        return True


class MessageHandler(FloodCheckerHandler):

    async def handle(self, msg_data: Dict):
        now = datetime.now()
        if (now - self.user.state.connection_time).seconds < TIME_BEFORE_TALK:
            return self.server.send_json(type='wait', date=timestamp() * 1000)

        if self._check_flood(msg_data['msg']):
            return
        # user object instance renders both the output sound and output text
        output_msg, wav = await self.user.render_message(msg_data["msg"], msg_data.get("lang", "fr"))
        # estimating the end of the current voice render, to rate limit
        calc_sendend = max(self.server.sendend, now) + timedelta(seconds=len(wav) * 8 / 6000000)
        synth = calc_sendend < now + timedelta(seconds=2.5)
        if synth:
            self.server.sendend = calc_sendend

        output_msg = escape(output_msg)

        # send to the backlog
        info = self.channel_obj.log_to_backlog(self.user.user_id, output_msg)
        if not self.user.state.is_shadowbanned:
            if "notext" in msg_data and self.server.raw_cookie in SOUND_BROADCASTER_COOKIES:
                self.channel_obj.broadcast(type="audio_broadcast", userid=self.user.user_id,
                                           binary_payload=wav if synth else None)
            else:
                # broadcast message and rendered audio to all clients in the channel
                self.channel_obj.broadcast(type='msg', userid=self.user.user_id,
                                           msg=output_msg, date=info['date'],
                                           binary_payload=wav if synth else None)
        else:  # we just send the message to the current client
            self.server.send_json(type='msg', userid=self.user.user_id,
                           msg=output_msg, date=info['date'])
            if synth:
                self.server.send_binary(wav)


class NoRenderMsgHandler(FloodCheckerHandler):
    """This handler is for messages that are displayed without a sound render, like bot status messages or
                    /me commands"""

    async def handle(self, msg_data: Dict):
        msg_type = msg_data['type']
        user_id = self.user.user_id
        output_msg = escape(msg_data['msg'])
        if self._check_flood(output_msg):
            return

        info = self.channel_obj.log_to_backlog(user_id, output_msg, kind=msg_type)
        if not self.user.state.is_shadowbanned:
            self.channel_obj.broadcast(type=msg_type, msg=output_msg,
                                       userid=user_id, date=info['date'])
        else:  # user is shadowbanned, so it's only sent to the
            self.server.send_json(type=msg_type, msg=output_msg,
                           userid=user_id, date=info['date'])


class PrivateMessageHandler(FloodCheckerHandler):

    async def handle(self, msg_data: Dict):
        # cleaning up none values in case of fuckups
        msg_data = {key: value for key, value in msg_data.items() if value is not None}
        target = self.channel_obj.users.get(msg_data.get("userid"))
        output_msg = escape(msg_data['msg'])
        if self._check_flood(output_msg):
            return

        if target is None:
            self.server.send_json(type='private_msg', event='invalid')
        for client in self.channel_obj.clients:
            if client.user == target:
                client.send_json(type='private_msg', msg=msg_data["msg"])


class AttackHandler(MsgBaseHandler):

    async def handle(self, msg_data: Dict):
        # cleaning up none values in case of fuckups
        msg_data = {key: value for key, value in msg_data.items() if value is not None}

        adversary_id, adversary = self.channel_obj.get_user_by_name(msg_data.get("target",
                                                                                 self.user.poke_params.pokename),
                                                                    msg_data.get("order", 1) - 1)
        now = datetime.now()

        # checking if the target user is found, and if the current user has waited long enough to attack
        if adversary is None:
            self.server.send_json(type='attack', event='invalid')
        elif (now - self.user.state.last_attack < timedelta(seconds=ATTACK_RESTING_TIME)):
            self.server.send_json(type='attack', event='invalid')
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

            if combat_sim.affected_users:  # there are users affected by some effects
                for user, effect in combat_sim.affected_users:
                    self.channel_obj.broadcast(type='attack', date=timestamp() * 1000,
                                               event='effect',
                                               tag=effect.TAG if hasattr(effect, "TAG") else None,
                                               target_id=user.user_id,
                                               effect=effect.name,
                                               timeout=effect.timeout)
            else:  # list is empty, no one was attacked
                self.channel_obj.broadcast(type='attack', date=timestamp() * 1000,
                                           event='nothing')

            # combat_sim uses the last attack time to compute the bonus,
            # so it must be updated after the running the attack.
            self.user.state.last_attack = now


class MoveHandler(MsgBaseHandler):

    async def handle(self, msg_data: Dict):
        # checking if all the necessary data is here
        if not {"x", "y", "id"}.issubset(set(msg_data.keys())):
            return
        # signalling all users in channel that this user moved
        self.channel_obj.broadcast(type='move',
                                   id=escape(msg_data['id'][:12]),
                                   userid=self.user.user_id,
                                   x=float(msg_data['x']),
                                   y=float(msg_data['y']))


class BanHandler(MsgBaseHandler):

    async def handle(self, msg_data: Dict):
        user_id = msg_data['userid']
        ban_type = msg_data['type']
        action = msg_data['action']
        timeout = msg_data.get('timeout', None)
        info = {'type': ban_type, 'userid': user_id}

        if not self.loult_state.can_ban:
            info['state'] = 'ban_system_disabled'
            return self.server.send_json(**info)

        if self.server.raw_cookie not in MOD_COOKIES:
            info['state'] = 'unauthorized'
            self.server.logger.info('unauthorized access to ban tools')
            return self.server.send_json(**info)

        if "signal_client" in msg_data:
            # before even running the ban, each clients of the concerned user is notified of the ban
            for client in [client for client in self.channel_obj.clients if
                           client.user and client.user.user_id == user_id]:
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
            self.server.logger.info(log_msg.format(**info, ip=todo))
            self.server.send_json(**info)
        except BanFail as err:
            info['state'] = err.state
            self.server.logger.info(log_msg.format(**info, ip=todo))
            self.server.send_json(**info)


class ShadowbanHandler(MsgBaseHandler):

    async def handle(self, msg_data: Dict):
        user_id = msg_data['userid']

        if self.server.raw_cookie not in MOD_COOKIES:
            self.server.logger.info('unauthorized access to shadowban tools')
            return self.server.send_json(type="shadowban", userid=user_id, state="unauthorized")

        shadowbanned_user = self.channel_obj.users[user_id]
        if msg_data["action"] == "apply":
            shadowbanned_user.state.is_shadowbanned = True
            self.loult_state.shadowbanned_cookies.add(shadowbanned_user.cookie_hash)
            self.server.send_json(type="shadowban", userid=user_id, state="apply_ok")
        elif msg_data["action"] == "remove":
            shadowbanned_user.state.is_shadowbanned = False
            self.loult_state.shadowbanned_cookies.remove(shadowbanned_user.cookie_hash)
            self.server.send_json(type="shadowban", userid=user_id, state="remove_ok")


class TrashHandler(MsgBaseHandler):

    async def handle(self, msg_data: Dict):
        user_id = msg_data['userid']

        if self.server.raw_cookie not in MOD_COOKIES:
            self.server.logger.info('unauthorized access to trash tools')
            return self.server.send_json(type="shadowban", userid=user_id, state="unauthorized")

        trashed_user = self.channel_obj.users[user_id]
        if msg_data["action"] == "apply":
            self.loult_state.trashed_cookies.add(trashed_user.cookie_hash)
            self.server.send_json(type="trash", userid=user_id, state="apply_ok")
            for client in self.channel_obj.clients:
                if client.user is not None and client.user.user_id == user_id:
                    client.sendClose(code=4006, reason="Reconnect please")
        elif msg_data["action"] == "remove":
            self.loult_state.trashed_cookies.remove(trashed_user.cookie_hash)
            self.server.send_json(type="trash", userid=user_id, state="remove_ok")


class InventoryListingHandler(MsgBaseHandler):

    async def handle(self, msg_data: Dict):
        inventory_listing = self.user.state.inventory.get_listing()
        self.server.send_json(type="notification",
                              msg="Votre inventaire contient : %s" % inventory_listing)


class ObjectGiveHandler(MsgBaseHandler):

    async def handle(self, msg_data: Dict):
        try:
            given_obj = self.user.state.inventory.get_object_by_id(int(msg_data.get("object_id")))
        except TypeError:
            return self.server.send_json(type="object", response="invalid_id")
        if given_obj is None:
            return self.server.send_json(type="object", response="invalid_id")

        beneficiary_id, beneficiary = self.channel_obj.get_user_by_name(msg_data.get("target",
                                                                                     self.user.poke_params.pokename),
                                                                        msg_data.get("order", 1) - 1)
        if beneficiary is None:
            return self.server.send_json(type="give", response="invalid_target")

        if not isinstance(given_obj, ClonableObject):
            self.user.state.inventory.remove(given_obj)
        beneficiary.state.inventory.add(given_obj)

        self.channel_obj.broadcast(type="give",
                                   response='exchanged',
                                   sender=self.user.user_id,
                                   receiver=beneficiary_id,
                                   obj_name=given_obj.name,
                                   date=timestamp() * 1000)


class ObjectUseHandler(MsgBaseHandler):

    async def handle(self, msg_data: Dict):
        try:
            selected_obj = self.user.state.inventory.get_object_by_id(int(msg_data.get("object_id")))
        except TypeError:
            return self.server.send_json(type="object", response="invalid_id")

        if selected_obj is None:
            return self.server.send_json(type="object", response="invalid_id")

        selected_obj.use(self.loult_state, self.server, msg_data['params'])
        if isinstance(selected_obj, DestructibleObject) and selected_obj.destroy:
            self.user.state.inventory.remove(selected_obj)


class ObjectTrashHandler(MsgBaseHandler):

    async def handle(self, msg_data: Dict):
        selected_obj = self.user.state.inventory.get_object_by_id(int(msg_data.get("object_id")))
        if selected_obj is None:
            self.server.send_json(type="object", response="invalid_id")
            return

        self.user.state.inventory.remove(selected_obj)
        self.channel_obj.inventory.add(selected_obj)
        self.server.send_json(type="object", response="object_trashed",
                              object_name=selected_obj.name)


class ListChannelInventoryHandler(MsgBaseHandler):

    async def handle(self, msg_data: Dict):
        self.server.send_json(type="notification",
                              msg="L'inventaire commun contient: " + self.channel_obj.inventory.get_listing())


class ObjectTakeHandler(MsgBaseHandler):
    RATE_LIMIT = 5 # in seconds

    def __init__(self, server_state, my_server):
        super().__init__(server_state, my_server)
        self.last_take = datetime(1972, 1, 1)

    async def handle(self, msg_data: Dict):
        try:
            selected_obj = self.channel_obj.inventory.get_object_by_id(int(msg_data.get("object_id")))
        except TypeError:
            return self.server.send_json(type="object", response="invalid_id")

        if selected_obj is None:
            return self.server.send_json(type="object", response="invalid_id")

        if (datetime.now() - self.last_take).seconds > self.RATE_LIMIT:
            self.channel_obj.inventory.remove(selected_obj)
            self.user.state.inventory.add(selected_obj)
            self.server.send_json(type="object", response="object_taken",
                                  object_name=selected_obj.name)
            self.last_take = datetime.now()
        else:
            self.server.send_json(type="notification",
                                  msg="Attendez un peu avant de piller la banque!")
from autobahn.asyncio.websocket import WebSocketServerProtocol

class ClientRouter:

    def __init__(self):
        pass

    def add_route(self, field : str, value : str, handler):
        pass

    def set_binary_route(self, handler):
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


class BaseLoultClient(WebSocketServerProtocol):

    def __init__(self, router: ClientRouter, loult):
        self.router = router
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

    def onMessage(self, payload, isBinary):
        """Triggered when a user sends any type of message to the server"""
        pass
import os, sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from autobahn.asyncio.websocket import WebSocketClientProtocol, \
    WebSocketClientFactory
#from datetime import datetime, timedelta
#from tools.users import UserState
from config import MAX_COOKIES_PER_IP

class ManyClientsProtocol(WebSocketClientProtocol):

    def onConnect(self, response):
        print("Server connected: {0}".format(response.peer))

    def onConnecting(self, transport_details):
        print("Connecting; transport details: {}".format(transport_details))
        return None  # ask for defaults

    def onOpen(self):
        print("WebSocket connection open.")

    def onMessage(self, payload, isBinary):
        if isBinary:
            print("Binary message received: {0} bytes".format(len(payload)))
        else:
            print("Text message received: {0}".format(payload.decode('utf8')))

    def onClose(self, wasClean, code, reason):
        print("WebSocket connection closed: {0}".format(reason))


if __name__ == '__main__':

    try:
        import asyncio
    except ImportError:
        # Trollius >= 0.3 was renamed
        import trollius as asyncio

    factory = WebSocketClientFactory(u"wss://127.0.0.1:80/socket/")
    factory.protocol = ManyClientsProtocol

    loop = asyncio.get_event_loop()
    tasks = []

    for i in range(MAX_COOKIES_PER_IP):
        task = asyncio.ensure_future(loop.create_connection(factory, '127.0.0.1', 80))
        tasks.append(task)

    # coro = loop.create_connection(factory, '127.0.0.1', 80)
    loop.run_until_complete(asyncio.wait(tasks))
    loop.run_forever()
    loop.close()

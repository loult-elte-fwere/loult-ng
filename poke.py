#!/usr/bin/python3
import argparse
import logging
from asyncio import get_event_loop, ensure_future, gather, set_event_loop_policy, get_event_loop_policy
from itertools import chain

from tools.ban import Ban, BanFail
from tools.client import ClientRouter, LoultServerProtocol
from tools.handlers import (MessageHandler, BinaryHandler, TrashHandler, BanHandler, ShadowbanHandler,
                            NoRenderMsgHandler, AttackHandler, PrivateMessageHandler, MoveHandler,
                            InventoryListingHandler, ObjectGiveHandler, ObjectUseHandler, ObjectTrashHandler,
                            ListChannelInventoryHandler, ObjectTakeHandler, WeaponsGrantHandler)
from tools.state import LoultServerState

if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("-d", "--debug", action="store_true")
    args = argparser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('server')

    try:
        asyncio_policy = get_event_loop_policy()
        import uvloop
        # Make sure to set uvloop as the default before importing anything
        # from autobahn else it won't use uvloop
        set_event_loop_policy(uvloop.EventLoopPolicy())
        logger.info("uvloop's event loop succesfully activated.")
    except:
        set_event_loop_policy(asyncio_policy)
        logger.info("Failed to use uvloop, falling back to asyncio's event loop.")
    finally:
        from autobahn.asyncio.websocket import WebSocketServerProtocol, \
            WebSocketServerFactory

    loop = get_event_loop()
    loult_state = LoultServerState()

    # setting up events
    from tools.events import events_factory, EventScheduler
    scheduler = EventScheduler(loult_state, events_factory())

    try:
        loop.run_until_complete(Ban.test_ban())
        loult_state.can_ban = True
    except BanFail:
        loult_state.can_ban = False
        logger.warning("nft command doesn't work; bans are disabled.")

    # setting up routing table
    router = ClientRouter()
    router.set_binary_route(BinaryHandler)
    router.add_route(field="type", value="msg", handler_class=MessageHandler)
    router.add_route(field="type", value="private_msg", handler_class=PrivateMessageHandler)
    router.add_route(field="type", value="attack", handler_class=AttackHandler)
    router.add_route(field="type", value="move", handler_class=MoveHandler)
    router.add_route(field="type", value="me", handler_class=NoRenderMsgHandler)
    router.add_route(field="type", value="bot", handler_class=NoRenderMsgHandler)

    # objects-related handlers
    router.add_route(field="type", value="inventory", handler_class=InventoryListingHandler)
    router.add_route(field="type", value="give", handler_class=ObjectGiveHandler)
    router.add_route(field="type", value="use", handler_class=ObjectUseHandler)
    router.add_route(field="type", value="trash", handler_class=ObjectTrashHandler)
    router.add_route(field="type", value="channel_inventory", handler_class=ListChannelInventoryHandler)
    router.add_route(field="type", value="take", handler_class=ObjectTakeHandler)

    #moderation handlers
    router.add_route(field="mod", value="trash", handler_class=TrashHandler)
    router.add_route(field="mod", value="shadowban", handler_class=ShadowbanHandler)
    for ban_type in Ban.ban_types:
        router.add_route(field="mod", value=ban_type, handler_class=BanHandler)
    router.add_route(field="mod", value="grant", handler_class=WeaponsGrantHandler)


    class AutobahnLoultServerProtocol(LoultServerProtocol, WebSocketServerProtocol):
        loult_state = loult_state
        client_logger = logging.getLogger('client')
        router = router


    factory = WebSocketServerFactory(server='Lou.lt/NG') # 'ws://127.0.0.1:9000',
    factory.protocol = AutobahnLoultServerProtocol
    # Allow 4KiB max size for messages, in a single frame.
    factory.setProtocolOptions(
            autoPingInterval=60,
            autoPingTimeout=30,
        )

    coro = loop.create_server(factory, '127.0.0.1', 9000)
    scheduler_task = ensure_future(scheduler.start())
    server = loop.run_until_complete(gather(coro, scheduler_task))
    # server = loop.run_until_complete(coro)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info('Shutting down all connections...')
        for client in chain.from_iterable((channel.clients for channel in loult_state.chans.values())):
            client.sendClose(code=1000, reason='Server shutting down.')
        loop.close()
        print('wvwoiw')

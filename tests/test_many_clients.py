#!/usr/bin/env python

import os, sys

# t-thanks Python (or am I a dumb fuck?)
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import asyncio
import json
import random
import time
import websockets
from os import urandom
from config import MAX_COOKIES_PER_IP

MESSAGES = ['c le nwe nwe rce ennw?', 'c le nwe nwe rce ennw!', 'we', '&we', 'de']


async def send_message(websocket, message):
    if message is not None:
        data = {"lang": "fr", "msg": message, "type": "msg"}
        await websocket.send(json.dumps(data))


async def reconnect(loop):
    await asyncio.sleep(5, loop)
    await client(loop)


async def client(loop):
    ck = urandom(16).hex()
    async with websockets.connect(u"ws://127.0.0.1:80/socket/") as websocket:
            
        async def echo(loop):

            await send_message(websocket, random.choice(MESSAGES))
            await asyncio.sleep(random.randint(1, 6), loop=loop)
            await asyncio.sleep(5, loop=loop)

        while True:
            try:
                data = await websocket.recv()
                if isinstance(data, str):
                    print("[client {}] Message : {}".format(ck, data))
                #await echo(loop)
            except (websockets.exceptions.ConnectionClosed) as e:
                print(e)
                await reconnect(loop)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    tasks = []

    for i in range(MAX_COOKIES_PER_IP):
        task = asyncio.ensure_future(client(loop))
        tasks.append(task)

    while True:
        loop.run_until_complete(asyncio.wait(tasks))
        #loop.run_forever()
        #loop.close()
    

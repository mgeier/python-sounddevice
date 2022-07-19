#!/usr/bin/env python3

import asyncio
import logging
import queue

import websockets


#logging.basicConfig(format="%(message)s", level=logging.DEBUG)
logging.basicConfig(
    format="%(asctime)s %(message)s",
    level=logging.INFO,
)

#q_in = asyncio.Queue()
message_q = queue.SimpleQueue()
loop = asyncio.get_event_loop()


def callback(indata, frame_count, time_info, status):
    # TODO: check message_q

    # TODO: remove queue if connection was closed

    # TODO: log status

    data = bytes(indata)  # make a copy of the data
    for q in queues:
        loop.call_soon_threadsafe(q_in.put_nowait, data)


#stream = sd.InputStream(callback=callback, channels=1, dtype='int8', **kwargs)
#with stream:
#    while True:
#        indata, status = await q_in.get()
#        yield indata, status


async def handle_connection(websocket):
    # TODO: if stream is not running, start stream
    # TODO: send queue to audio callback

    # TODO: don't receive data, only send?

    #while True:
    #    try:
    #        message = await websocket.recv()
    #    except websockets.ConnectionClosedOK:
    #        # TODO: log message
    #        # TODO: stop stream if there are no other listeners
    #        break
    #    print(message)

    async for message in websocket:
        # TODO: ignore messages?
        print(message)

    # TODO: loop over queue
    #await websocket.send(???)


async def main():
    async with websockets.serve(handle_connection, host='', port=7654):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())

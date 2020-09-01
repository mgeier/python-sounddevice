#!/usr/bin/env python3
import sounddevice as sd


device = None
blocksize = 1024


class PrintBlocks:

    def __init__(self, n):
        self.n = n

    def __await__(self):
        print('start __await__')
        for i in range(self.n):
            outdata, frames, time, status = yield None
            print('block', i, '- frames:', frames)
        # TODO: meaningful return value?
        return self.n

class Voice:

    def __init__(self, note):
        self.note = note

    def __await__(self):
        while True:
            print('calculating note, adding to output')
            yield

class Synth:

    async def play_note(self):
        await ...

    def __await__(self):
        while True:
            self.outdata, self.frames, self.time, self.status = yield


async def audio_coroutine():
    result = await PrintBlocks(10)
    #result = await Voice(10)
    print('result:', result)
    return result


coro = audio_coroutine()
coro.send(None)

def callback(outdata, frames, time, status):
    print('start callback')
    outdata.fill(0)
    try:
        iter_result = coro.send((outdata, frames, time, status))
    except StopIteration as e:
        print('StopIteration:', e)
        # TODO: sd.CallbackAbort?
        raise sd.CallbackStop from e
    print('iter result:', iter_result)


stream = sd.OutputStream(
    device=device,
    blocksize=blocksize,
    channels=1,
    callback=callback,
)
with stream:
    sd.sleep(5_000)
    print('stopping stream')
print('the end')

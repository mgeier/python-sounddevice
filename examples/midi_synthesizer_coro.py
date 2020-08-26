#!/usr/bin/env python3
"""A simple synthesizer for playing MIDI files.

The mido module and NumPy must be installed.

"""


import argparse
import queue

import mido
import numpy as np
import sounddevice as sd



parser = argparse.ArgumentParser(add_help=False)
parser.add_argument(
    '-l', '--list-devices', action='store_true',
    help='show list of audio devices and exit')
args, remaining = parser.parse_known_args()
if args.list_devices:
    print(sd.query_devices())
    parser.exit(0)
parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    parents=[parser])

parser.add_argument(
    'filename', metavar='FILENAME',
    help='MIDI file to be played back')

parser.add_argument(
    '-a', '--amplitude', type=float, default=0.2,
    help='amplitude (default: %(default)s)')


parser.add_argument(
    '-d', '--device',
    help='output device (numeric ID or substring)')
parser.add_argument(
    '-b', '--blocksize', type=int, default=0,
    help='block size (default: %(default)s)')
# TODO: latency?
parser.add_argument(
    '-q', '--queuesize', type=int, default=20,
    help='number of notes queued for playback (default: %(default)s)')


args = parser.parse_args(remaining)



q = queue.Queue(maxsize=args.queuesize)

try:
    midifile = mido.MidiFile(args.filename)
    samplerate = sd.query_devices(args.device, 'output')['default_samplerate']

    async def audio_coroutine(loop):
        print('starting coroutine')
        while True:
            outdata, frames, time, status = await loop
            try:
                msg = q.get_nowait()
            except queue.Empty as e:
                print('waiting for first message')
                continue
            else:
                print('got first message')
                break
        offset = 0
        while True:
            offset += round(msg.time * samplerate)
            while offset >= frames:
                offset -= frames
                outdata, frames, time, status = await loop
            if msg.type == 'note_on':
                print('generating note:', msg.note)
            else:
                # ignored
                pass

            while True:
                try:
                    msg = q.get_nowait()
                except queue.Empty as e:
                    # TODO: end of song?
                    # TODO: or wait for more messages?
                    offset -= frames
                    outdata, frames, time, status = await loop
                else:
                    break

    class Loop:

        def __await__(self):
            yield 42
            return 'data', 1000, 'time', 'status'

    loop = Loop()

    generator = audio_coroutine(loop)
    # NB: coroutine is started in main thread
    generator.send(None)

    def callback(outdata, frames, time, status):

        outdata.fill(0)

        #generator.send((outdata, frames, time, status))
        generator.send(None)

    stream = sd.OutputStream(
        device=args.device,
        blocksize=args.blocksize,
        channels=1,
        callback=callback,
        samplerate=samplerate,
    )
    with stream:
        print('starting stream')

        sd.sleep(100)

        print('starting iteration')

        for message in midifile:
            q.put(message)


        print('done reading midi file')

        sd.sleep(100)

        print('exiting context manager')

except KeyboardInterrupt:
    parser.exit('\nInterrupted by user')
except Exception as e:
    parser.exit(type(e).__name__ + ': ' + str(e))

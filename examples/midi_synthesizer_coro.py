#!/usr/bin/env python3
"""A simple synthesizer for playing MIDI files.

The mido module and NumPy must be installed.

"""


import argparse
import queue

import mido
import numpy as np
import sounddevice as sd

ATTACK = 0.1
DECAY = 0.2
SUSTAIN = 0.7
RELEASE = 0.5


def m2f(note):
    """Convert MIDI note number to frequency in Hertz.

    See https://en.wikipedia.org/wiki/MIDI_Tuning_Standard.

    """
    return 2 ** ((note - 69) / 12) * 440


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

    def generate_signal(note, note_on, velocity, note_off, t):
        note_on /= samplerate
        env = np.ones_like(t)

        peak = args.amplitude * velocity / 127
        vol = SUSTAIN * peak
        env *= vol
        env = np.minimum(
            env,
            -vol * (t - RELEASE - note_off / samplerate) / RELEASE)
        env = np.maximum(
            env,
            peak + (vol - peak) * (t - ATTACK - note_on) / DECAY)
        env = np.minimum(
            env,
            peak * (t - note_on) / ATTACK)
        env = np.maximum(env, 0)

        sine = np.sin(2 * np.pi * m2f(note) * t)
        return env * sine

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
        index = 0
        t = np.arange(frames) / samplerate
        block_end = frames
        # mapping (channel, pitch) -> index, velocity
        voices = {}
        while True:
            index += round(msg.time * samplerate)
            while index >= block_end:

                # Iterating over a copy, because "voices" may be mutated
                for (channel, note) in list(voices):
                    note_on, velocity, note_off = voices[(channel, note)]
                    if note_off is None:
                        note_off = block_end
                    signal = generate_signal(note, note_on, velocity, note_off, t)
                    if signal[-1] != 0:
                        voices[(channel, note)] = note_on, velocity, index
                    else:
                        del voices[(channel, note)]
                    outdata += signal

                outdata, frames, time, status = await loop
                t = np.arange(block_end, block_end + frames) / samplerate
                t.shape = -1, 1
                block_end += frames
            if msg.type == 'note_on':
                print('generating note:', msg.note)
                # TODO: if (channel, note) already exists: insert note_off?
                voices[(msg.channel, msg.note)] = index, msg.velocity, None
            elif msg.type == 'note_off':
                data = voices.get((msg.channel, msg.note))
                if data is None:
                    print('note_off without note_on')
                # TODO: check that note_off is None?
                note_on, velocity, _ = data
                signal = generate_signal(msg.note, note_on, velocity, index, t)
                if signal[-1] != 0:
                    voices[(msg.channel, msg.note)] = note_on, velocity, index
                else:
                    del voices[(msg.channel, msg.note)]
                outdata += signal
            else:
                pass  # ignored

            while True:
                try:
                    msg = q.get_nowait()
                except queue.Empty as e:
                    # TODO: end of song?
                    # TODO: or wait for more messages?

                    # TODO: generate existing voices

                    outdata, frames, time, status = await loop
                    t = np.arange(block_end, block_end + frames) / samplerate
                    block_end += frames
                else:
                    break

    class Loop:

        def __await__(self):
            # TODO: yield some kind of future? append to list of futures?
            #result = yield 42
            result = yield
            #print('__await__ yield result:', result)
            # TODO: return the result of the future?
            #return 'data', 10000, 'time', 'status'
            return result

    loop = Loop()
    

    generator = audio_coroutine(loop)
    generator.send(None)

    def callback(outdata, frames, time, status):

        outdata.fill(0)

        # TODO: update loop, notify all awaiting coroutines?

        generator.send((outdata, frames, time, status))
        #data = generator.send('dummy')
        #print('data from generator.send():', data)

        # TODO: future.set_result() (or .done()?)

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

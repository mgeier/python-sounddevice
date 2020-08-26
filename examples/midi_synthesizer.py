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
    '-d', '--device', type=int_or_str,
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

    note_start = None

    def callback(outdata, frames, time, status):
        nonlocal note_start

        # TODO: update/prune existing voices?

        while True:

            try:
                message = q.get_nowait()
            except queue.Empty as e:
                # TODO: end of song?
                break

            if note_start is None:
                note_start = time.outputBufferDacTime

            note_start += message.time

            if message.type != 'note_on':
                continue

            # TODO: update notes
            message.note
            message.velocity
            message.channel


    stream = sd.OutputStream(
        device=args.device,
        blocksize=args.blocksize,
        channels=1,
        callback=callback,
        samplerate=samplerate,
    )
    with stream:

        # TODO: get current time

        for message in midifile:

except KeyboardInterrupt:
    parser.exit('\nInterrupted by user')
except Exception as e:
    parser.exit(type(e).__name__ + ': ' + str(e))

#!/usr/bin/env python3
import queue
import threading

import mido
import sounddevice as sd


device = 0
blocksize = 1024
filename = 'FurElise.mid'

q = queue.Queue(maxsize=20)

event = threading.Event()

class Synth:

    def __init__(self, queue):
        self.queue = queue
        self.active_voices = {}
        self.released_voices = []

    def voice(self, note, velocity):
        print('starting voice', note, velocity)
        while True:
            end = yield
            print('calculating', self.time.outputBufferDacTime)
            if end is not None:
                # TODO update end
                print('end', end)
            print('playing note', note)
            if end is not None:
                # TODO: check proper end of voice
                return

    def update_audio_block(self):
        for note in self.active_voices.values():
            # NB: There will be no StopIteration here
            note.send(None)

        self.outdata, self.frames, self.time, self.status = yield

        # Iterating in reverse because items may be deleted
        for i in reversed(range(len(self.released_voices))):
            try:
                next(self.released_voices[i])
            except StopIteration:
                del self.released_voices[i]

        # TODO: return something?

    def run(self):

        yield from self.update_audio_block()

        while True:

            try:
                msg = self.queue.get_nowait()
            except queue.Empty:
                print('no message, waiting')
                yield from self.update_audio_block()
                continue

            if msg.type == 'note_on':
                key = msg.channel, msg.note
                if key in self.active_voices:
                    # TODO: do something?
                    print('error: note on without note off')
                voice = self.voice(msg.note, msg.velocity)
                voice.send(None)
                self.active_voices[key] = voice
            elif msg.type == 'note_off':
                try:
                    voice = self.active_voices.pop((msg.channel, msg.note))
                except KeyError:
                    print('note off without note on (ignored)')
                    continue
                try:
                    voice.send('TODO: note off time/index')
                except StopIteration:
                    pass
                else:
                    self.released_voices.append(voice)


synth = Synth(q)

synth_gen = synth.run()
synth_gen.send(None)


def callback(outdata, frames, time, status):
    outdata.fill(0)
    try:
        iter_result = synth_gen.send((outdata, frames, time, status))
    except StopIteration as e:
        print('StopIteration:', e)
        # TODO: sd.CallbackAbort?
        raise sd.CallbackStop from e
    print('iter result:', iter_result)


midifile = mido.MidiFile(filename)

stream = sd.OutputStream(
    device=device,
    blocksize=blocksize,
    channels=1,
    callback=callback,
    finished_callback=event.set,
)
with stream:
    q.put(mido.Message('note_on', channel=1, note=2, velocity=3))
    q.put(mido.Message('note_on', channel=4, note=5, velocity=6))
    q.put(mido.Message('note_on', channel=7, note=8, velocity=9))
    #for message in midifile:
    #    q.put(message)

    sd.sleep(500)

    q.put(mido.Message('note_off', channel=1, note=2, velocity=3))
    q.put(mido.Message('note_off', channel=4, note=5, velocity=6))
    q.put(mido.Message('note_off', channel=7, note=8, velocity=9))

    # TODO: somehow force note_off in all voices?
    event.wait()
    print('stopping stream')
print('the end')

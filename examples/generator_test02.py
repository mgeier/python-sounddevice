#!/usr/bin/env python3
import queue
import threading

import mido
import numpy as np
import sounddevice as sd


device = None
blocksize = 1024
#filename = 'FurElise.mid'
filename = 'Girl-of-Mine.mid'

amplitude = 0.2

ATTACK = 0.005
DECAY = 0.2
SUSTAIN = 0.4
RELEASE = 0.2

q = queue.Queue(maxsize=20)

event = threading.Event()

def m2f(note):
    """Convert MIDI note number to frequency in Hertz.

    See https://en.wikipedia.org/wiki/MIDI_Tuning_Standard.

    """
    return 2 ** ((note - 69) / 12) * 440

class Synth:

    def __init__(self, queue, samplerate):
        self.queue = queue
        self.samplerate = samplerate
        self.voices = {}
        #self.released_voices = []
        self.block_end = 0

    def envelope(self, note_on, velocity):
        note_off = None
        data = yield
        while True:
            if data is None:
                env = np.ones_like(self.t)
                peak = amplitude * velocity / 127
                sus = SUSTAIN * peak
                env *= sus
                if note_off is not None:
                    env = np.minimum(
                        env,
                        #-sus * (self.t - note_off - RELEASE) / RELEASE)
                        #sus - sus * (self.t - note_off - RELEASE) / RELEASE)
                        sus * (1 - (self.t - note_off) / RELEASE))
                env = np.maximum(
                    env,
                    peak + (sus - peak) * (self.t - ATTACK - note_on) / DECAY)
                env = np.minimum(
                    env,
                    peak * (self.t - note_on) / ATTACK)
                env = np.maximum(env, 0)
                data = yield env
                if env[-1] == 0:
                    if note_off is None:
                        print('missing note_off')
                    return
            else:
                assert note_off is None
                note_off = data
                data = yield


    def voice(self, pitch):
        # NB: There can be multiple consecutive note_on events,
        #     each creating a separate envelope.
        envelopes = []
        note_off = None

        while True:
            event = yield
            if event is not None:
                try:
                    note_on, velocity = event
                except (TypeError, ValueError):
                    assert envelopes
                    envelopes[-1].send(event)
                else:
                    if envelopes:
                        # Send note_off time to previous envelope
                        envelopes[-1].send(note_on)
                    new_env = self.envelope(note_on, velocity)
                    new_env.send(None)
                    envelopes.append(new_env)
                continue

            env = 0
            keep = []
            for e in envelopes:
                try:
                    env = env + e.send(None)
                except StopIteration:
                    pass
                else:
                    keep.append(e)
            envelopes = keep
            sine = np.sin(2 * np.pi * m2f(pitch) * self.t)
            self.outdata[:, 0] += env * sine

    def update_audio_block(self):
        # Iterating over a copy because item may be removed
        for k in list(self.voices):
            voice = self.voices[k]
            try:
                voice.send(None)
            except StopIteration:
                del self.voices[k]
        start_idx = self.block_end
        self.outdata, frames = yield
        self.block_end += frames
        self.t = np.arange(start_idx, start_idx + frames) / self.samplerate

        # TODO: return something?

    def run(self):
        yield from self.update_audio_block()
        current_time = None
        while True:
            try:
                msg = self.queue.get_nowait()
            except queue.Empty:
                print('no message, waiting')
                yield from self.update_audio_block()
                continue
            if current_time is None:
                # first MIDI message
                current_time = self.t[0]
            current_time += msg.time
            while current_time >= self.block_end / self.samplerate:
                yield from self.update_audio_block()
            if msg.type == 'note_on':
                key = msg.channel, msg.note
                voice = self.voices.get(key)
                if voice is None:
                    voice = self.voice(msg.note)
                    voice.send(None)
                    self.voices[key] = voice
                voice.send((current_time, msg.velocity))
            elif msg.type == 'note_off':
                voice = self.voices.get(key)
                if voice is None:
                    print('note off without note on (ignored)')
                else:
                    # NB: no StopIteration here
                    voice.send(current_time)

samplerate = sd.query_devices(device, 'output')['default_samplerate']

synth = Synth(q, samplerate)

synth_gen = synth.run()
synth_gen.send(None)


def callback(outdata, frames, time, status):
    if status:
        print(status)
    outdata.fill(0)
    try:
        iter_result = synth_gen.send((outdata, frames))
    except StopIteration as e:
        print('StopIteration:', e)
        # TODO: sd.CallbackAbort?
        raise sd.CallbackStop from e
    #print('iter result:', iter_result)


midifile = mido.MidiFile(filename)

stream = sd.OutputStream(
    device=device,
    blocksize=blocksize,
    channels=1,
    samplerate=samplerate,
    callback=callback,
    finished_callback=event.set,
)
with stream:
    for message in midifile:
        q.put(message)

    print('end of MIDI messages')

    # TODO: somehow force note_off in all voices?
    event.wait()
    print('stopping stream')
print('the end')

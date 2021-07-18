#!/usr/bin/env python3
import threading

import mido
import numpy as np
import sounddevice as sd


device = None
blocksize = 0
#blocksize = 1024
#filename = 'FurElise.mid'
filename = 'Girl-of-Mine.mid'

amplitude = 0.1

ATTACK = 0.005
DECAY = 0.2
SUSTAIN = 0.4
RELEASE = 0.2

event = threading.Event()

def m2f(note):
    """Convert MIDI note number to frequency in Hertz.

    See https://en.wikipedia.org/wiki/MIDI_Tuning_Standard.

    """
    return 2 ** ((note - 69) / 12) * 440

class MidiSynth:

    def __init__(self, filename, samplerate):
        self.midifile = mido.MidiFile(filename)
        self.samplerate = samplerate
        self.voices = {}
        self.block_end = 0

        # TODO: current index instead of block_end?

        self.next_midi_event = TODO_some_dummy_event_with_time_0

    def midi_events(self, ???):
        # TODO: yield all MIDI events for one block

    def envelope(self, note_on, velocity):
        note_off = None
        data = yield
        while True:
            if data is None:
                peak = amplitude * velocity / 127
                sus = SUSTAIN * peak
                env = sus * np.ones_like(self.t)
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
                    # TODO: calculate from decay and release slope instead?
                    assert note_off
                    return
            else:
                if note_off is None:
                    note_off = data
                data = yield


    def voice(self, pitch, note_on, velocity):
        # NB: There can be multiple consecutive note_on events,
        #     each creating a separate envelope.
        env = self.envelope(note_on, velocity)
        env.send(None)
        envelopes = [env]
        while envelopes:
            event = yield
            if event is not None:
                cmd, *args = event
                if cmd == 'note_on':
                    note_on, velocity = args
                    assert velocity > 0
                    try:
                        envelopes[-1].send(note_on)
                    except StopIteration:
                        print('TODO: StopIteration when forcing note_off')
                    env = self.envelope(note_on, velocity)
                    env.send(None)
                    envelopes.append(env)
                elif cmd == 'note_off':
                    note_off, = args
                    try:
                        envelopes[-1].send(note_off)
                    except StopIteration:
                        print('TODO: StopIteration when sending note_off')
                else:
                    assert False
                continue

            env = 0
            for i in reversed(range(len(envelopes))):
                try:
                    env = env + envelopes[i].send(None)
                except StopIteration:
                    del envelopes[i]
            sine = np.sin(2 * np.pi * m2f(pitch) * self.t)
            self.outdata[:, 0] += env * sine


    def process_audio_block(outdata, frames, time, status):
        if status:
            print(status)
        outdata.fill(0)



        start_idx = self.block_end
        self.t = np.arange(start_idx, start_idx + frames) / self.samplerate



        current_time = self.t[0]



        for evt in self.midi_events():
            current_time += evt.time


            # TODO: this should be done in midi_events():
            #if current_time > self.t[-1]:
            #    break


            if evt.type in ('note_off', 'note_on'):
                key = evt.channel, evt.note
                voice = self.voices.get(key)
                if evt.type == 'note_on' and evt.velocity > 0:
                    if voice is None:

                        # TODO: create voice

                        # TODO: don't create envelope yet (wait for note off)

                        voice = self.voice(
                            evt.note, current_time, evt.velocity)
                        voice.send(None)
                        self.voices[key] = voice

                    else:

                        # TODO: force note off


                        # TODO: don't create new envelope yet

                        voice.send(('note_on', current_time, evt.velocity))
                elif voice is None:
                    print('note off without note on (ignored)')
                else:
                    # NB: note_off velocity is ignored

                    # TODO: create envelope


                    voice.send(('note_off', current_time))
        else:
            # TODO: no more midi events?
            pass
        for voice in self.voices:
            voice.send(('note_off', current_time))
        while self.voices:
            yield from self.update_audio_block()






        # Iterating over a copy because item may be removed
        for k in list(self.voices):
            voice = self.voices[k]

            # TODO: process voice

            # TODO: delete voice if not needed anymore
            #del self.voices[k]


        self.block_end += frames

        # TODO: return something?



samplerate = sd.query_devices(device, 'output')['default_samplerate']

synth = MidiSynth(filename, samplerate)

stream = sd.OutputStream(
    device=device,
    blocksize=blocksize,
    channels=1,
    samplerate=samplerate,
    callback=synth.process_audio_block,
    finished_callback=event.set,
)
with stream:
    event.wait()
    print('stopping stream')
print('the end')

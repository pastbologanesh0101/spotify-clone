"""Generate tiny, fully synthetic sine-wave WAV files.

These are programmatically generated tones -- NOT real music, and no
copyrighted audio is used or referenced anywhere in this project. They exist
purely as short (1-3 second) stand-ins so the app has real playable audio
files to point at. See README.md for details.
"""
import math
import struct
import wave

SAMPLE_RATE = 44100


def generate_tone(path, freq=440.0, duration=2.0, volume=0.25, sample_rate=SAMPLE_RATE):
    """Write a single-channel sine wave tone to ``path`` as a 16-bit WAV file."""
    n_samples = max(1, int(duration * sample_rate))
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for i in range(n_samples):
            t = i / sample_rate
            # Gentle fade in/out to avoid audible clicks at the edges.
            fade = min(1.0, i / (sample_rate * 0.05), (n_samples - i) / (sample_rate * 0.05))
            value = int(volume * fade * 32767.0 * math.sin(2 * math.pi * freq * t))
            frames += struct.pack("<h", value)
        wf.writeframes(bytes(frames))

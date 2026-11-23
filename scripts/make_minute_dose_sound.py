"""Create the royalty-free Minute Dose reveal sting with synthesized tones and filtered noise."""
import math
import random
import struct
import wave
from pathlib import Path

RATE, DURATION = 48000, 2.7
OUT = Path(__file__).resolve().parents[1] / "web" / "brand" / "minute-dose-reveal.wav"
RNG = random.Random(9001)


def sample(t):
    # Soft rushing noise, then three tiny rising pips.
    whoosh_env = max(0.0, min(1.0, t / 0.08)) * math.exp(-max(0.0, t - 0.18) * 4.2)
    x = (RNG.random() * 2 - 1) * 0.07 * whoosh_env
    for start, freq in ((0.48, 1450), (0.62, 1750), (0.76, 2050)):
        d = t - start
        if 0 <= d < 0.11:
            x += 0.09 * math.exp(-d * 32) * math.sin(2 * math.pi * freq * d)
    d = t - 0.92
    if 0 <= d < 0.55:
        f = 118 - 52 * d
        x += 0.23 * math.exp(-d * 7) * math.sin(2 * math.pi * f * d)
        x += 0.07 * math.exp(-d * 9) * math.sin(2 * math.pi * 880 * d)
    if t >= 1.12:
        env = math.exp(-(t - 1.12) * 1.65) * max(0, min(1, (DURATION - t) / 0.28))
        x += env * (0.035 * math.sin(2 * math.pi * 1760 * t) + 0.022 * math.sin(2 * math.pi * 2637 * t))
    return max(-0.85, min(0.85, x))


OUT.parent.mkdir(parents=True, exist_ok=True)
with wave.open(str(OUT), "wb") as wav:
    wav.setparams((2, 2, RATE, 0, "NONE", "not compressed"))
    frames = bytearray()
    for i in range(round(RATE * DURATION)):
        t = i / RATE
        v = int(sample(t) * 32767)
        frames.extend(struct.pack("<hh", v, v))
    wav.writeframes(frames)
print(OUT)

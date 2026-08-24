#!/usr/bin/env python3
"""Generate tiny deterministic audio transport fixtures without third-party packages.

The WAVs are tones, not synthetic speech. Their hashes let the offline ASR adapter
exercise the complete upload/transcription contract while remaining honest about
what is and is not connected.
"""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"


def write_tone(path: Path, frequency: float, seconds: float = 0.8) -> None:
    sample_rate = 16_000
    samples = int(sample_rate * seconds)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        frames = bytearray()
        for index in range(samples):
            envelope = min(1.0, index / 800, (samples - index) / 800)
            value = int(8_000 * envelope * math.sin(2 * math.pi * frequency * index / sample_rate))
            frames.extend(struct.pack("<h", value))
        output.writeframes(bytes(frames))


def main() -> None:
    FIXTURES.mkdir(exist_ok=True)
    write_tone(FIXTURES / "odia_brown_spot_question.wav", 440)
    write_tone(FIXTURES / "odia_unclear_question.wav", 260)
    print("Generated deterministic WAV fixtures")


if __name__ == "__main__":
    main()

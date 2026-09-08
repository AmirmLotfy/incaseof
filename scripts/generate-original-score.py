#!/usr/bin/env python3
"""Render the original understated score used by the hackathon film."""

from __future__ import annotations

import argparse
import math
import wave
from array import array
from pathlib import Path

SAMPLE_RATE = 24_000
CHORD_SECONDS = 12.0
CHORDS = (
    (73.42, 87.31, 110.00),  # D minor
    (58.27, 73.42, 87.31),  # B-flat major
    (87.31, 110.00, 130.81),  # F major
    (65.41, 82.41, 98.00),  # C major
)
PLUCKS = (440.00, 523.25, 587.33, 523.25, 440.00, 392.00, 349.23, 392.00)


def smoothstep(value: float) -> float:
    value = min(1.0, max(0.0, value))
    return value * value * (3.0 - 2.0 * value)


def render(path: Path, duration: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames_total = int(duration * SAMPLE_RATE)
    pcm = array("h")

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)

        for frame in range(frames_total):
            t = frame / SAMPLE_RATE
            chord_number = int(t // CHORD_SECONDS)
            chord = CHORDS[chord_number % len(CHORDS)]
            within = t % CHORD_SECONDS
            chord_env = min(smoothstep(within / 2.5), smoothstep((CHORD_SECONDS - within) / 2.5))

            master = smoothstep(t / 6.0) * smoothstep((duration - t) / 8.0)
            breath = 0.84 + 0.16 * math.sin(2.0 * math.pi * 0.045 * t)

            left = 0.0
            right = 0.0
            weights = (0.095, 0.065, 0.052)
            for frequency, weight in zip(chord, weights, strict=True):
                left += weight * math.sin(2.0 * math.pi * frequency * t)
                left += weight * 0.24 * math.sin(2.0 * math.pi * frequency * 2.01 * t)
                right += weight * math.sin(2.0 * math.pi * frequency * 1.002 * t + 0.18)
                right += weight * 0.24 * math.sin(2.0 * math.pi * frequency * 1.997 * t + 0.31)

            pluck_slot = int(t // 3.0)
            pluck_age = t % 3.0
            pluck_env = math.exp(-3.4 * pluck_age)
            pluck_freq = PLUCKS[pluck_slot % len(PLUCKS)]
            pluck = (
                0.032
                * pluck_env
                * (
                    math.sin(2.0 * math.pi * pluck_freq * t)
                    + 0.35 * math.sin(2.0 * math.pi * pluck_freq * 2.0 * t)
                )
            )

            pulse = 0.0
            if 24.0 < t < duration - 18.0:
                pulse_age = t % 2.0
                pulse = 0.025 * math.exp(-8.0 * pulse_age) * math.sin(2.0 * math.pi * 55.0 * t)

            left = (left * chord_env * breath + pluck + pulse) * master
            right = (right * chord_env * breath + pluck * 0.82 + pulse) * master
            pcm.append(int(max(-1.0, min(1.0, left)) * 32767))
            pcm.append(int(max(-1.0, min(1.0, right)) * 32767))

            if len(pcm) >= SAMPLE_RATE * 2 * 4:
                wav.writeframes(pcm.tobytes())
                pcm = array("h")

        if pcm:
            wav.writeframes(pcm.tobytes())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--duration", type=float, default=230.0)
    args = parser.parse_args()
    render(args.output, args.duration)


if __name__ == "__main__":
    main()

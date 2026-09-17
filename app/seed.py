"""Demo music library data + seeding logic.

All artists, albums and track titles below are fictional, invented for this
project. Audio is synthetic (see app/audio_gen.py) and never derived from any
real recording.
"""
import os
import re

from . import audio_gen

# (artist_name, album_title, [(track_title, duration_seconds, tone_freq_hz), ...])
LIBRARY = [
    (
        "Nova Ridge",
        "Synth Horizons",
        [
            ("Daybreak Pulse", 2, 220.00),
            ("Neon Static", 3, 246.94),
            ("Glass Skyline", 2, 261.63),
            ("Afterglow", 3, 293.66),
        ],
    ),
    (
        "Echo Valley",
        "Analog Dreams",
        [
            ("Tape Hiss Lullaby", 2, 329.63),
            ("Warm Reverb", 3, 349.23),
            ("Static Bloom", 2, 392.00),
        ],
    ),
    (
        "Circuit Bloom",
        "Voltage Garden",
        [
            ("Pulse Width", 3, 415.30),
            ("Square Wave Sonata", 2, 440.00),
            ("Sawtooth Sunrise", 3, 466.16),
            ("Filter Sweep", 2, 493.88),
        ],
    ),
    (
        "Marble Static",
        "Quiet Machinery",
        [
            ("Idle Hum", 2, 523.25),
            ("Gear Shift", 3, 587.33),
            ("Copper Wire", 2, 622.25),
        ],
    ),
    (
        "Paper Moth",
        "Faint Frequencies",
        [
            ("Signal Drift", 3, 659.25),
            ("Low Battery", 2, 698.46),
            ("Ghost Channel", 3, 739.99),
            ("Dial Tone", 2, 783.99),
        ],
    ),
]


def slugify(value):
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def seed_demo_data(db, generate_audio_files=False, audio_dir=None):
    """Populate artist/album/track tables from LIBRARY.

    When ``generate_audio_files`` is True, real tiny WAV files are written
    into ``audio_dir`` for each track. Tests pass generate_audio_files=False
    so the suite stays fast and has no filesystem side effects.
    """
    for artist_name, album_title, tracks in LIBRARY:
        artist_cur = db.execute("INSERT INTO artist (name) VALUES (?)", (artist_name,))
        artist_id = artist_cur.lastrowid

        album_cur = db.execute(
            "INSERT INTO album (artist_id, title) VALUES (?, ?)",
            (artist_id, album_title),
        )
        album_id = album_cur.lastrowid

        for title, duration, freq in tracks:
            filename = f"{slugify(artist_name)}-{slugify(title)}.wav"
            rel_path = f"audio/{filename}"

            if generate_audio_files and audio_dir:
                full_path = os.path.join(audio_dir, filename)
                audio_gen.generate_tone(full_path, freq=freq, duration=duration)

            db.execute(
                "INSERT INTO track (album_id, title, duration_seconds, audio_file_path) "
                "VALUES (?, ?, ?, ?)",
                (album_id, title, duration, rel_path),
            )

    db.commit()

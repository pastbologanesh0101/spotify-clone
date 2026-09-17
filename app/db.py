import os
import sqlite3

import click
from flask import current_app, g

from . import seed as seed_module


def get_db():
    """Return a per-request SQLite connection, creating it if needed."""
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf8"))


@click.command("init-db")
def init_db_command():
    """Drop and recreate all tables (no seed data)."""
    init_db()
    click.echo("Initialized an empty database.")


@click.command("seed")
def seed_command():
    """Reset the database and load the demo music library, generating
    synthetic sine-wave WAV files as stand-ins for real audio."""
    init_db()
    db = get_db()
    audio_dir = os.path.join(current_app.root_path, "static", "audio")
    os.makedirs(audio_dir, exist_ok=True)
    seed_module.seed_demo_data(db, generate_audio_files=True, audio_dir=audio_dir)
    click.echo("Seeded demo artists/albums/tracks with synthetic audio.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_command)

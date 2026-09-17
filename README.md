# Spotify Clone

A small, scoped-down music streaming app **core** built with Flask and
SQLite: browse artists/albums/tracks, search, build and reorder playlists,
simulate a "now playing" queue (next/previous), record play history, and see
a most-played aggregation.

## Important: the audio is fake

**All audio files in this project are synthetic, programmatically generated
sine-wave tones** created with Python's built-in `wave` module (see
`app/audio_gen.py`). They are short (1-3 second) beeps at different pitches,
used purely as stand-ins for real tracks so the app has real, playable
`.wav` files to point at. **No copyrighted or real-world music is used,
downloaded, or referenced anywhere in this repository.** Artist, album, and
track names in the seed data (`app/seed.py`) are fictional and invented for
this demo.

## Features

- Browse artists → albums → tracks
- Search tracks by title or artist name (substring match)
- Create playlists and add / remove / reorder tracks in them
- A "now playing" queue simulation with next/previous logic (does not
  stream audio into a browser player, though the synthetic `.wav` files are
  served as static files and can be played directly)
- Recording play history via a `POST /api/play` call that simulates
  "playback started"
- A "most played" aggregation computed from play history

### Design notes

- **Playlist ordering**: each `playlist_track` row has an integer
  `position`. Every add/remove/reorder renormalizes the affected playlist's
  positions to a contiguous `0..N-1` range — the same general approach a
  Kanban board uses to keep card ordinals gap-free within a column, applied
  here to playlist tracks instead of cards.
- **Duplicate tracks**: a track *may* appear in the same playlist more than
  once (e.g., to repeat a song), matching how most real playlist apps
  behave. This is intentional and covered by
  `tests/test_app.py::test_duplicate_track_allowed_in_playlist`.
- **Single demo user**: there's no accounts/auth system; all playlists and
  play history belong to one demo user (`user_id = 1`) to keep the scope
  small.

## Project layout

```
app/
  __init__.py       # create_app() application factory
  db.py             # SQLite connection handling + `flask init-db` / `flask seed` CLI commands
  schema.sql         # table definitions
  seed.py            # demo artist/album/track library + seeding logic
  audio_gen.py        # synthetic sine-wave WAV generator
  playlists.py         # add/remove/reorder playlist-track helpers
  queue.py             # pure next/previous "now playing" queue logic
  routes.py            # all Flask routes
  templates/           # Jinja2 templates
  static/style.css     # plain CSS
  static/audio/        # generated .wav files (git-ignored, created by `flask seed`)
tests/
  test_app.py          # unit tests using Flask's test client
wsgi.py                 # `python wsgi.py` / `flask --app wsgi run` entry point
```

## Running it locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create the schema and load the demo library (also generates the synthetic
# .wav files into app/static/audio/):
flask --app wsgi:app --debug init-db
flask --app wsgi:app seed

# Run the dev server:
flask --app wsgi:app --debug run
```

Then visit `http://127.0.0.1:5000/`.

## Example usage

- Browse: `GET /` → list artists → click through to an album → see tracks.
- Search: `GET /search?q=Neon` matches tracks/artists containing "Neon".
- Create a playlist: `POST /playlists/create` with form field `name`.
- Add a track: `POST /playlists/<playlist_id>/add` with form field
  `track_id`.
- Reorder a playlist: `POST /playlists/<playlist_id>/reorder` with form
  field `order` set to a comma-separated list of `playlist_track` ids in
  the new order (also accepts JSON: `{"order": [3, 1, 2]}`).
- "Play" a track (records history): `POST /api/play` with form field
  `track_id`.
- Queue navigation: `GET /api/queue/<playlist_id>/next?current=<track_id>`
  and `GET /api/queue/<playlist_id>/previous?current=<track_id>` return
  `{"next_track_id": ...}` / `{"previous_track_id": ...}`, or `null` at the
  end/start of the playlist.
- Most played: `GET /most-played`.

## Running the tests

```bash
pip install -r requirements.txt
pytest -v
```

Tests use `create_app(testing=True)`, which points Flask at a throwaway
temporary SQLite file, initializes the schema, and seeds the demo library
(without generating audio files, so the suite runs fast with no
filesystem/audio side effects).

Continuous integration runs the same suite on Python 3.11 and 3.12 via
`.github/workflows/tests.yml`.

## License

MIT — see [LICENSE](LICENSE).

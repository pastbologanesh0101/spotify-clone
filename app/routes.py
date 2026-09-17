import datetime

from flask import Blueprint, jsonify, redirect, render_template, request, url_for

from . import playlists as playlists_module
from . import queue as queue_module
from .db import get_db

bp = Blueprint("main", __name__)

# Single demo user for this scoped-down clone -- no auth/accounts system.
DEMO_USER_ID = 1


def _most_played_rows(db, limit=20):
    return db.execute(
        """
        SELECT t.id AS track_id, t.title, ar.name AS artist_name,
               COUNT(ph.id) AS play_count
        FROM play_history ph
        JOIN track t ON ph.track_id = t.id
        JOIN album al ON t.album_id = al.id
        JOIN artist ar ON al.artist_id = ar.id
        GROUP BY t.id
        ORDER BY play_count DESC, t.title ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


@bp.route("/")
def index():
    db = get_db()
    artists = db.execute("SELECT * FROM artist ORDER BY name").fetchall()
    return render_template("index.html", artists=artists)


@bp.route("/artists/<int:artist_id>")
def artist_detail(artist_id):
    db = get_db()
    artist = db.execute("SELECT * FROM artist WHERE id = ?", (artist_id,)).fetchone()
    albums = db.execute(
        "SELECT * FROM album WHERE artist_id = ? ORDER BY title", (artist_id,)
    ).fetchall()
    return render_template("artist.html", artist=artist, albums=albums)


@bp.route("/albums/<int:album_id>")
def album_detail(album_id):
    db = get_db()
    album = db.execute(
        """
        SELECT al.*, ar.name AS artist_name
        FROM album al JOIN artist ar ON al.artist_id = ar.id
        WHERE al.id = ?
        """,
        (album_id,),
    ).fetchone()
    tracks = db.execute(
        "SELECT * FROM track WHERE album_id = ? ORDER BY id", (album_id,)
    ).fetchall()
    playlists = db.execute(
        "SELECT * FROM playlist WHERE user_id = ? ORDER BY id", (DEMO_USER_ID,)
    ).fetchall()
    return render_template(
        "album.html", album=album, tracks=tracks, playlists=playlists
    )


@bp.route("/search")
def search():
    q = request.args.get("q", "").strip()
    db = get_db()
    tracks = []
    if q:
        like = f"%{q}%"
        tracks = db.execute(
            """
            SELECT t.*, al.title AS album_title, ar.name AS artist_name
            FROM track t
            JOIN album al ON t.album_id = al.id
            JOIN artist ar ON al.artist_id = ar.id
            WHERE t.title LIKE ? OR ar.name LIKE ?
            ORDER BY t.title
            """,
            (like, like),
        ).fetchall()
    return render_template("search.html", q=q, tracks=tracks)


@bp.route("/playlists")
def playlist_list():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM playlist WHERE user_id = ? ORDER BY id", (DEMO_USER_ID,)
    ).fetchall()
    return render_template("playlists.html", playlists=rows)


@bp.route("/playlists/create", methods=["POST"])
def create_playlist():
    name = (request.form.get("name") or "").strip() or "New Playlist"
    db = get_db()
    cur = db.execute(
        "INSERT INTO playlist (user_id, name) VALUES (?, ?)", (DEMO_USER_ID, name)
    )
    db.commit()
    return redirect(url_for("main.playlist_detail", playlist_id=cur.lastrowid))


@bp.route("/playlists/<int:playlist_id>")
def playlist_detail(playlist_id):
    db = get_db()
    playlist = db.execute(
        "SELECT * FROM playlist WHERE id = ?", (playlist_id,)
    ).fetchone()
    tracks = db.execute(
        """
        SELECT pt.id AS playlist_track_id, pt.position, t.id AS track_id,
               t.title, t.duration_seconds, t.audio_file_path, ar.name AS artist_name
        FROM playlist_track pt
        JOIN track t ON pt.track_id = t.id
        JOIN album al ON t.album_id = al.id
        JOIN artist ar ON al.artist_id = ar.id
        WHERE pt.playlist_id = ?
        ORDER BY pt.position
        """,
        (playlist_id,),
    ).fetchall()
    return render_template("playlist_detail.html", playlist=playlist, tracks=tracks)


@bp.route("/playlists/<int:playlist_id>/add", methods=["POST"])
def add_to_playlist(playlist_id):
    track_id = request.form.get("track_id", type=int)
    if track_id is None and request.is_json:
        track_id = (request.get_json(silent=True) or {}).get("track_id")
    db = get_db()
    playlists_module.add_track(db, playlist_id, track_id)
    if request.is_json:
        return jsonify({"status": "ok"})
    return redirect(request.referrer or url_for("main.playlist_detail", playlist_id=playlist_id))


@bp.route("/playlists/<int:playlist_id>/remove/<int:playlist_track_id>", methods=["POST"])
def remove_from_playlist(playlist_id, playlist_track_id):
    db = get_db()
    playlists_module.remove_track(db, playlist_id, playlist_track_id)
    if request.is_json:
        return jsonify({"status": "ok"})
    return redirect(url_for("main.playlist_detail", playlist_id=playlist_id))


@bp.route("/playlists/<int:playlist_id>/reorder", methods=["POST"])
def reorder_playlist(playlist_id):
    if request.is_json:
        ids = (request.get_json(silent=True) or {}).get("order", [])
    else:
        raw = request.form.get("order", "")
        ids = [int(x) for x in raw.split(",") if x.strip()]
    db = get_db()
    playlists_module.reorder(db, playlist_id, ids)
    if request.is_json:
        return jsonify({"status": "ok"})
    return redirect(url_for("main.playlist_detail", playlist_id=playlist_id))


@bp.route("/api/queue/<int:playlist_id>/next")
def queue_next(playlist_id):
    current = request.args.get("current", type=int)
    db = get_db()
    ordered = playlists_module.ordered_track_ids(db, playlist_id)
    return jsonify({"next_track_id": queue_module.next_track_id(ordered, current)})


@bp.route("/api/queue/<int:playlist_id>/previous")
def queue_previous(playlist_id):
    current = request.args.get("current", type=int)
    db = get_db()
    ordered = playlists_module.ordered_track_ids(db, playlist_id)
    return jsonify(
        {"previous_track_id": queue_module.previous_track_id(ordered, current)}
    )


@bp.route("/playlists/<int:playlist_id>/queue")
def queue_view(playlist_id):
    current = request.args.get("current", type=int)
    db = get_db()
    playlist = db.execute(
        "SELECT * FROM playlist WHERE id = ?", (playlist_id,)
    ).fetchone()
    ordered = playlists_module.ordered_track_ids(db, playlist_id)
    if current is None and ordered:
        current = ordered[0]
    current_track = None
    if current is not None:
        current_track = db.execute(
            "SELECT * FROM track WHERE id = ?", (current,)
        ).fetchone()
    next_id = queue_module.next_track_id(ordered, current)
    prev_id = queue_module.previous_track_id(ordered, current)
    return render_template(
        "queue.html",
        playlist=playlist,
        current_track=current_track,
        next_id=next_id,
        prev_id=prev_id,
    )


@bp.route("/api/play", methods=["POST"])
def play_track():
    track_id = request.form.get("track_id", type=int)
    if track_id is None and request.is_json:
        track_id = (request.get_json(silent=True) or {}).get("track_id")
    db = get_db()
    played_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    db.execute(
        "INSERT INTO play_history (user_id, track_id, played_at) VALUES (?, ?, ?)",
        (DEMO_USER_ID, track_id, played_at),
    )
    db.commit()
    return jsonify({"status": "ok", "track_id": track_id, "played_at": played_at})


@bp.route("/most-played")
def most_played():
    db = get_db()
    rows = _most_played_rows(db)
    return render_template("most_played.html", rows=rows)

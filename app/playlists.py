"""Playlist mutation helpers: add / remove / reorder.

Design note on duplicates: a track MAY appear in the same playlist more than
once (e.g. "Play this hype song twice in a row"), same as real streaming
playlists. Duplicates are allowed; see tests/test_app.py::test_duplicate_track_allowed.

Position management follows the same contiguous-ordinal-per-column approach
used by Kanban-style boards: every playlist_track row has an integer
``position`` and after any add/remove/reorder we renormalize the affected
playlist's rows to a gap-free 0..N-1 sequence, so ordering stays simple and
UI drag-and-drop reorder always has clean neighbors to work with.
"""


def add_track(db, playlist_id, track_id):
    """Append a track to the end of a playlist's queue. Returns the new
    playlist_track row id."""
    row = db.execute(
        "SELECT COALESCE(MAX(position), -1) AS max_pos FROM playlist_track WHERE playlist_id = ?",
        (playlist_id,),
    ).fetchone()
    next_position = row["max_pos"] + 1
    cur = db.execute(
        "INSERT INTO playlist_track (playlist_id, track_id, position) VALUES (?, ?, ?)",
        (playlist_id, track_id, next_position),
    )
    db.commit()
    return cur.lastrowid


def remove_track(db, playlist_id, playlist_track_id):
    """Remove one playlist_track row and renormalize remaining positions to
    0..N-1 so there are no gaps left behind."""
    db.execute(
        "DELETE FROM playlist_track WHERE id = ? AND playlist_id = ?",
        (playlist_track_id, playlist_id),
    )
    remaining = db.execute(
        "SELECT id FROM playlist_track WHERE playlist_id = ? ORDER BY position",
        (playlist_id,),
    ).fetchall()
    for index, row in enumerate(remaining):
        db.execute(
            "UPDATE playlist_track SET position = ? WHERE id = ?",
            (index, row["id"]),
        )
    db.commit()


def reorder(db, playlist_id, ordered_playlist_track_ids):
    """Given the full list of playlist_track ids in their new desired order,
    rewrite positions to match (0..N-1). Ids that don't belong to this
    playlist are ignored."""
    valid_ids = {
        row["id"]
        for row in db.execute(
            "SELECT id FROM playlist_track WHERE playlist_id = ?", (playlist_id,)
        ).fetchall()
    }
    position = 0
    for pt_id in ordered_playlist_track_ids:
        if pt_id in valid_ids:
            db.execute(
                "UPDATE playlist_track SET position = ? WHERE id = ? AND playlist_id = ?",
                (position, pt_id, playlist_id),
            )
            position += 1
    db.commit()


def ordered_track_ids(db, playlist_id):
    """Return the playlist's track ids in queue order (for queue/next/prev)."""
    rows = db.execute(
        "SELECT track_id FROM playlist_track WHERE playlist_id = ? ORDER BY position",
        (playlist_id,),
    ).fetchall()
    return [row["track_id"] for row in rows]

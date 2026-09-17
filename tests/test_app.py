import pytest

from app import create_app
from app.db import get_db
from app.queue import next_track_id, previous_track_id


@pytest.fixture
def app():
    application = create_app(testing=True)
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


def _track_ids(app, limit=5):
    with app.app_context():
        db = get_db()
        rows = db.execute("SELECT id FROM track ORDER BY id LIMIT ?", (limit,)).fetchall()
        return [row["id"] for row in rows]


def _create_playlist(client, name="My Playlist"):
    resp = client.post("/playlists/create", data={"name": name}, follow_redirects=True)
    assert resp.status_code == 200
    with client.application.app_context():
        db = get_db()
        row = db.execute(
            "SELECT id FROM playlist WHERE name = ? ORDER BY id DESC LIMIT 1", (name,)
        ).fetchone()
    return row["id"]


def _playlist_track_ids(app, playlist_id):
    """Returns list of (playlist_track_id, track_id) ordered by position."""
    with app.app_context():
        db = get_db()
        rows = db.execute(
            "SELECT id, track_id FROM playlist_track WHERE playlist_id = ? ORDER BY position",
            (playlist_id,),
        ).fetchall()
        return [(row["id"], row["track_id"]) for row in rows]


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def test_search_matches_by_track_title(client):
    resp = client.get("/search", query_string={"q": "Neon Static"})
    assert resp.status_code == 200
    assert b"Neon Static" in resp.data
    assert b"Nova Ridge" in resp.data


def test_search_matches_by_artist_name(client):
    resp = client.get("/search", query_string={"q": "Circuit Bloom"})
    assert resp.status_code == 200
    # All tracks by this artist's album (Voltage Garden) should appear.
    assert b"Pulse Width" in resp.data
    assert b"Square Wave Sonata" in resp.data


def test_search_is_substring_case_style_match_and_no_bogus_hits(client):
    resp = client.get("/search", query_string={"q": "zzz-no-such-track"})
    assert resp.status_code == 200
    assert b"No matches." in resp.data


# ---------------------------------------------------------------------------
# Playlist add/remove/reorder
# ---------------------------------------------------------------------------

def test_add_track_to_playlist(client, app):
    playlist_id = _create_playlist(client)
    track_ids = _track_ids(app, 2)

    resp = client.post(
        f"/playlists/{playlist_id}/add",
        data={"track_id": track_ids[0]},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    rows = _playlist_track_ids(app, playlist_id)
    assert len(rows) == 1
    assert rows[0][1] == track_ids[0]


def test_remove_track_reorders_remaining_correctly(client, app):
    playlist_id = _create_playlist(client)
    track_ids = _track_ids(app, 4)
    for tid in track_ids:
        client.post(f"/playlists/{playlist_id}/add", data={"track_id": tid})

    rows_before = _playlist_track_ids(app, playlist_id)
    assert [t for _, t in rows_before] == track_ids

    # Remove the second entry (index 1).
    middle_pt_id = rows_before[1][0]
    resp = client.post(
        f"/playlists/{playlist_id}/remove/{middle_pt_id}", follow_redirects=True
    )
    assert resp.status_code == 200

    rows_after = _playlist_track_ids(app, playlist_id)
    # Remaining 3 tracks, in original relative order, minus the removed one.
    assert [t for _, t in rows_after] == [track_ids[0], track_ids[2], track_ids[3]]

    # Positions must be contiguous 0..N-1 with no gap left by the removal.
    with app.app_context():
        db = get_db()
        positions = [
            r["position"]
            for r in db.execute(
                "SELECT position FROM playlist_track WHERE playlist_id = ? ORDER BY position",
                (playlist_id,),
            ).fetchall()
        ]
    assert positions == [0, 1, 2]


def test_reorder_playlist_tracks(client, app):
    playlist_id = _create_playlist(client)
    track_ids = _track_ids(app, 3)
    for tid in track_ids:
        client.post(f"/playlists/{playlist_id}/add", data={"track_id": tid})

    rows = _playlist_track_ids(app, playlist_id)
    pt_ids = [pt for pt, _ in rows]
    # Reverse the order.
    new_order = list(reversed(pt_ids))

    resp = client.post(
        f"/playlists/{playlist_id}/reorder",
        data={"order": ",".join(str(x) for x in new_order)},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    rows_after = _playlist_track_ids(app, playlist_id)
    assert [pt for pt, _ in rows_after] == new_order
    assert [t for _, t in rows_after] == list(reversed(track_ids))


def test_duplicate_track_allowed_in_playlist(client, app):
    """Design choice: the same track may be added to a playlist more than
    once (mirrors real playlist apps letting you repeat a song). This test
    documents and locks in that behavior."""
    playlist_id = _create_playlist(client)
    track_ids = _track_ids(app, 1)
    tid = track_ids[0]

    client.post(f"/playlists/{playlist_id}/add", data={"track_id": tid})
    client.post(f"/playlists/{playlist_id}/add", data={"track_id": tid})

    rows = _playlist_track_ids(app, playlist_id)
    assert len(rows) == 2
    assert rows[0][1] == tid and rows[1][1] == tid


# ---------------------------------------------------------------------------
# Play history / most played
# ---------------------------------------------------------------------------

def test_play_history_recorded_on_play(client, app):
    track_ids = _track_ids(app, 1)
    tid = track_ids[0]

    resp = client.post("/api/play", data={"track_id": tid})
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["track_id"] == tid
    assert payload["played_at"]

    with app.app_context():
        db = get_db()
        count = db.execute(
            "SELECT COUNT(*) AS c FROM play_history WHERE track_id = ?", (tid,)
        ).fetchone()["c"]
    assert count == 1


def test_most_played_aggregation_is_correct(client, app):
    track_ids = _track_ids(app, 2)
    popular, unpopular = track_ids[0], track_ids[1]

    for _ in range(3):
        client.post("/api/play", data={"track_id": popular})
    client.post("/api/play", data={"track_id": unpopular})

    resp = client.get("/most-played")
    assert resp.status_code == 200

    with app.app_context():
        db = get_db()
        rows = db.execute(
            """
            SELECT track_id, COUNT(*) AS c FROM play_history
            GROUP BY track_id ORDER BY c DESC
            """
        ).fetchall()
    assert rows[0]["track_id"] == popular
    assert rows[0]["c"] == 3
    assert dict((r["track_id"], r["c"]) for r in rows)[unpopular] == 1


# ---------------------------------------------------------------------------
# Now-playing queue: next/previous, including boundaries
# ---------------------------------------------------------------------------

def test_queue_next_and_previous_within_bounds(client, app):
    playlist_id = _create_playlist(client)
    track_ids = _track_ids(app, 3)
    for tid in track_ids:
        client.post(f"/playlists/{playlist_id}/add", data={"track_id": tid})

    resp = client.get(
        f"/api/queue/{playlist_id}/next", query_string={"current": track_ids[0]}
    )
    assert resp.get_json()["next_track_id"] == track_ids[1]

    resp = client.get(
        f"/api/queue/{playlist_id}/previous", query_string={"current": track_ids[1]}
    )
    assert resp.get_json()["previous_track_id"] == track_ids[0]


def test_queue_next_returns_none_at_end_boundary(client, app):
    playlist_id = _create_playlist(client)
    track_ids = _track_ids(app, 3)
    for tid in track_ids:
        client.post(f"/playlists/{playlist_id}/add", data={"track_id": tid})

    resp = client.get(
        f"/api/queue/{playlist_id}/next", query_string={"current": track_ids[-1]}
    )
    assert resp.get_json()["next_track_id"] is None


def test_queue_previous_returns_none_at_start_boundary(client, app):
    playlist_id = _create_playlist(client)
    track_ids = _track_ids(app, 3)
    for tid in track_ids:
        client.post(f"/playlists/{playlist_id}/add", data={"track_id": tid})

    resp = client.get(
        f"/api/queue/{playlist_id}/previous", query_string={"current": track_ids[0]}
    )
    assert resp.get_json()["previous_track_id"] is None


def test_queue_pure_functions_boundaries_directly():
    ordered = [10, 20, 30]
    assert next_track_id(ordered, 30) is None
    assert previous_track_id(ordered, 10) is None
    assert next_track_id(ordered, 10) == 20
    assert previous_track_id(ordered, 30) == 20
    assert next_track_id(ordered, 999) is None
    assert previous_track_id([], 10) is None


# ---------------------------------------------------------------------------
# Misc browsing
# ---------------------------------------------------------------------------

def test_index_lists_seeded_artists(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Nova Ridge" in resp.data
    assert b"Echo Valley" in resp.data


def test_create_playlist_then_view_it(client):
    resp = client.post(
        "/playlists/create", data={"name": "Road Trip"}, follow_redirects=True
    )
    assert resp.status_code == 200
    assert b"Road Trip" in resp.data

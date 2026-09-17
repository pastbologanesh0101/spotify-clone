DROP TABLE IF EXISTS play_history;
DROP TABLE IF EXISTS playlist_track;
DROP TABLE IF EXISTS playlist;
DROP TABLE IF EXISTS track;
DROP TABLE IF EXISTS album;
DROP TABLE IF EXISTS artist;

CREATE TABLE artist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);

CREATE TABLE album (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artist_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    FOREIGN KEY (artist_id) REFERENCES artist (id)
);

CREATE TABLE track (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    album_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL,
    audio_file_path TEXT,
    FOREIGN KEY (album_id) REFERENCES album (id)
);

CREATE TABLE playlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL
);

-- Join table that also tracks per-playlist ordering of tracks.
-- "position" is a zero-based, contiguous integer per playlist_id, similar in
-- spirit to how a Kanban board keeps contiguous ordinal positions for cards
-- within a column: every mutation (add/remove/reorder) renormalizes the
-- positions of the affected playlist to 0..N-1 so there are never gaps.
CREATE TABLE playlist_track (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    playlist_id INTEGER NOT NULL,
    track_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    FOREIGN KEY (playlist_id) REFERENCES playlist (id),
    FOREIGN KEY (track_id) REFERENCES track (id)
);

CREATE TABLE play_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    track_id INTEGER NOT NULL,
    played_at TEXT NOT NULL,
    FOREIGN KEY (track_id) REFERENCES track (id)
);

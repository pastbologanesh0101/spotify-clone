"""Pure "now playing" queue helpers.

Kept free of any DB/Flask dependency so the next/previous boundary logic is
trivial to unit test directly, in addition to being exercised through the
/api/queue/<playlist_id>/(next|previous) HTTP endpoints.
"""


def next_track_id(ordered_track_ids, current_track_id):
    """Return the track id after ``current_track_id`` in the ordered queue,
    or None if there is no current track or it is already the last one
    (end-of-playlist boundary)."""
    if current_track_id is None or current_track_id not in ordered_track_ids:
        return None
    idx = ordered_track_ids.index(current_track_id)
    if idx + 1 < len(ordered_track_ids):
        return ordered_track_ids[idx + 1]
    return None


def previous_track_id(ordered_track_ids, current_track_id):
    """Return the track id before ``current_track_id`` in the ordered queue,
    or None if there is no current track or it is already the first one
    (start-of-playlist boundary)."""
    if current_track_id is None or current_track_id not in ordered_track_ids:
        return None
    idx = ordered_track_ids.index(current_track_id)
    if idx - 1 >= 0:
        return ordered_track_ids[idx - 1]
    return None

"""Shared Tidal authentication, search, and matching logic."""

import json
import re
import subprocess
import sys
import time

import tidalapi

KEYCHAIN_SERVICE = "tpb-tidal"
KEYCHAIN_ACCOUNT = "oauth-session"


def load_keychain_tokens():
    """Load OAuth tokens from macOS Keychain (tpb-tidal entry)."""
    result = subprocess.run(
        ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", KEYCHAIN_ACCOUNT, "-w"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"ERROR: Could not read Keychain entry '{KEYCHAIN_SERVICE}/{KEYCHAIN_ACCOUNT}'")
        print(f"  Run `tpb auth` first to authenticate with Tidal.")
        sys.exit(1)

    hex_str = result.stdout.strip()
    try:
        decoded = bytes.fromhex(hex_str).decode("utf-8")
        return json.loads(decoded)
    except (ValueError, json.JSONDecodeError):
        return json.loads(hex_str)


def create_session():
    """Authenticate with Tidal via Keychain tokens. Returns a tidalapi.Session."""
    tokens = load_keychain_tokens()
    session = tidalapi.Session()
    success = session.load_oauth_session(
        token_type="Bearer",
        access_token=tokens["access_token"],
        refresh_token=tokens.get("refresh_token"),
    )
    if not success:
        print("ERROR: Failed to authenticate with Tidal. Token may be expired.")
        print("  Run `tpb auth --force` to re-authenticate.")
        sys.exit(1)
    print(f"Authenticated as user {session.user.id} ({session.country_code})")
    return session


def normalize(s):
    """Normalize string for comparison: lowercase, strip parenthetical/bracket suffixes."""
    s = s.lower().strip()
    s = re.sub(r'\s*\(.*?\)\s*', ' ', s)
    s = re.sub(r'\s*\[.*?\]\s*', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def artist_match(query_artist, track_artist, aliases=None):
    """Check if artists match.

    Args:
        query_artist: The artist name from the track file.
        track_artist: The artist name from Tidal search results.
        aliases: Optional list of additional artist name fragments to match
                 (e.g. ["sullivan"] for New Model Army, ["bowie", "tin machine"] for Bowie).
    """
    qa = query_artist.lower()
    ta = track_artist.lower()
    if qa in ta or ta in qa:
        return True
    if aliases:
        for alias in aliases:
            alias_lower = alias.lower()
            # Match if the Tidal result artist contains any known alias.
            # Covers cases like query="New Model Army" but Tidal credits="Justin Sullivan"
            if alias_lower in ta:
                return True
    return False


def title_match(query_title, track_title):
    """Check if titles match, ignoring remaster/version suffixes."""
    qt = normalize(query_title)
    tt = normalize(track_title)
    if qt == tt:
        return True
    # Substring match with minimum 60% length ratio to prevent false positives
    if qt in tt or tt in qt:
        shorter = min(len(qt), len(tt))
        longer = max(len(qt), len(tt))
        if longer > 0 and shorter / longer >= 0.6:
            return True
    return False


def search_track(session, artist, title, aliases=None, prefer_live=False):
    """Search Tidal for a track. Returns (track_id, tidal_title) or (None, None).

    Args:
        session: Authenticated tidalapi.Session.
        artist: Artist name to search for.
        title: Track title to search for.
        aliases: Optional artist name aliases for matching.
        prefer_live: If True, prefer live/orchestral versions over studio.
    """
    query = f"{artist} {title}"
    results = session.search(query, models=[tidalapi.Track], limit=20)
    tracks = results.get("tracks", []) or []

    # If looking for live versions, try to find those first
    if prefer_live:
        for track in tracks:
            track_artist = track.artist.name if track.artist else ""
            track_title = track.name if track.name else ""
            title_lower = track_title.lower()
            if artist_match(artist, track_artist, aliases) and title_match(title, track_title):
                if "live" in title_lower or "orchestral" in title_lower or "sinfonia" in title_lower:
                    return track.id, f"{track.artist.name} - {track.name}"

    # Standard strict match: both artist AND title must match
    for track in tracks:
        track_artist = track.artist.name if track.artist else ""
        track_title = track.name if track.name else ""
        if artist_match(artist, track_artist, aliases) and title_match(title, track_title):
            return track.id, f"{track.artist.name} - {track.name}"

    # Strategy 2: title-only search with strict artist filter
    results = session.search(title, models=[tidalapi.Track], limit=20)
    tracks = results.get("tracks", []) or []

    for track in tracks:
        track_artist = track.artist.name if track.artist else ""
        track_title = track.name if track.name else ""
        if artist_match(artist, track_artist, aliases) and title_match(title, track_title):
            return track.id, f"{track.artist.name} - {track.name}"

    # Strategy 3: punctuation variants (D.J., R.I.P., etc.)
    dotted = re.sub(r'\b([A-Z])([A-Z])\b', r'\1.\2.', title)
    if dotted != title:
        results = session.search(f"{artist} {dotted}", models=[tidalapi.Track], limit=10)
        tracks = results.get("tracks", []) or []
        for track in tracks:
            track_artist = track.artist.name if track.artist else ""
            track_title = track.name if track.name else ""
            if artist_match(artist, track_artist, aliases) and title_match(dotted, track_title):
                return track.id, f"{track.artist.name} - {track.name}"

    return None, None


def parse_track_file(filepath):
    """Parse a track list file (Artist - Title per line). Returns list of (artist, title)."""
    tracks = []
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(" - ", 1)
            if len(parts) == 2:
                tracks.append((parts[0].strip(), parts[1].strip()))
    return tracks


def find_track_by_hint(tracks, title_hint, used_ids):
    """Find a track in a playlist by title substring, skipping already-used tracks."""
    hint = normalize(title_hint)
    best = None
    best_score = 0.0

    for t in tracks:
        if t.id in used_ids:
            continue
        t_title = normalize(t.name)

        if hint == t_title:
            return t

        if hint in t_title or t_title in hint:
            shorter = min(len(hint), len(t_title))
            longer = max(len(hint), len(t_title))
            score = shorter / longer if longer > 0 else 0
            if score > best_score:
                best = t
                best_score = score

    return best if best_score >= 0.5 else None

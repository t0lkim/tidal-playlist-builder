#!/usr/bin/env python3
"""Add supplementary tracks (EPs, singles, B-sides) to existing anthology playlists.

Usage:
    python scripts/add_tracks.py anthologies/david-bowie/ [--dry-run]

Reads supplements.json from the artist directory. Format:
{
    "playlist_ids": {
        "vol01": "uuid-here",
        ...
    },
    "additions": {
        "vol01": [
            ["tidal-track-id", "Description for logging"],
            ...
        ]
    }
}
"""

import json
import os
import sys
import time

from tidal_common import create_session


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: python add_tracks.py <anthology-dir> [--dry-run]")
        sys.exit(0)

    anthology_dir = sys.argv[1]
    dry_run = "--dry-run" in sys.argv

    supplements_path = os.path.join(anthology_dir, "supplements.json")
    if not os.path.exists(supplements_path):
        print(f"ERROR: No supplements.json found in {anthology_dir}")
        sys.exit(1)

    with open(supplements_path) as f:
        data = json.load(f)

    playlist_ids = data["playlist_ids"]
    additions = data["additions"]

    if dry_run:
        print("DRY RUN MODE — no tracks will be added\n")

    print("Authenticating with Tidal...")
    session = create_session()

    total_added = 0

    for vol_key in sorted(additions.keys()):
        tracks = additions[vol_key]
        playlist_id = playlist_ids.get(vol_key)
        if not playlist_id:
            print(f"WARNING: No playlist ID for {vol_key}, skipping")
            continue

        print(f"{'='*60}")
        print(f"  {vol_key.upper()} — Adding {len(tracks)} supplementary tracks")
        print(f"  Playlist: {playlist_id}")
        print(f"{'='*60}")

        track_ids = []
        for tid, desc in tracks:
            print(f"  [+] {desc}")
            track_ids.append(tid)

        if not dry_run:
            playlist = session.playlist(playlist_id).factory()
            added = playlist.add(track_ids)
            print(f"\n  Added {len(added)} tracks to playlist")
            total_added += len(added)
            time.sleep(0.5)
        else:
            print(f"\n  [DRY RUN] Would add {len(track_ids)} tracks")
            total_added += len(track_ids)

        print()

    print(f"{'='*60}")
    print(f"  SUPPLEMENT COMPLETE")
    print(f"  Total tracks added: {total_added}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

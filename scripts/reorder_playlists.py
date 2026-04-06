#!/usr/bin/env python3
"""Reorder existing anthology playlists into a desired track order.

Usage:
    python scripts/reorder_playlists.py anthologies/david-bowie/ [--dry-run]

Reads order.json from the artist directory. Format:
{
    "playlist_ids": {
        "vol01": "uuid-here",
        ...
    },
    "order": {
        "vol01": [
            "Title Substring 1",
            "Title Substring 2",
            ...
        ]
    }
}
"""

import json
import os
import sys
import time

from tidal_common import create_session, find_track_by_hint


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: python reorder_playlists.py <anthology-dir> [--dry-run]")
        sys.exit(0)

    anthology_dir = sys.argv[1]
    dry_run = "--dry-run" in sys.argv

    order_path = os.path.join(anthology_dir, "order.json")
    if not os.path.exists(order_path):
        print(f"ERROR: No order.json found in {anthology_dir}")
        sys.exit(1)

    with open(order_path) as f:
        data = json.load(f)

    playlist_ids = data["playlist_ids"]
    desired_orders = data["order"]

    if dry_run:
        print("DRY RUN MODE — no playlists will be modified\n")

    print("Authenticating with Tidal...")
    session = create_session()

    total_reordered = 0
    total_volumes = len(desired_orders)

    for vol_key in sorted(desired_orders.keys()):
        desired_order = desired_orders[vol_key]
        playlist_id = playlist_ids.get(vol_key)
        if not playlist_id:
            print(f"WARNING: No playlist ID for {vol_key}, skipping")
            continue

        print(f"{'='*60}")
        print(f"  {vol_key.upper()} — {len(desired_order)} tracks expected")
        print(f"  Playlist: {playlist_id}")
        print(f"{'='*60}")

        playlist = session.playlist(playlist_id)
        tracks = playlist.tracks()
        print(f"  Current tracks in playlist: {len(tracks)}")

        if len(tracks) != len(desired_order):
            print(f"  [!!] COUNT MISMATCH: playlist has {len(tracks)}, expected {len(desired_order)}")
            print(f"  Current tracks:")
            for i, t in enumerate(tracks):
                artist_name = t.artist.name if t.artist else "?"
                print(f"    {i+1:2d}. {artist_name} - {t.name}")
            print(f"  SKIPPING this volume\n")
            continue

        ordered_ids = []
        used_ids = set()
        errors = False

        for title_hint in desired_order:
            match = find_track_by_hint(tracks, title_hint, used_ids)
            if match:
                ordered_ids.append(str(match.id))
                used_ids.add(match.id)
                artist_name = match.artist.name if match.artist else "?"
                print(f"  [OK] {title_hint:45s} -> {artist_name} - {match.name}")
            else:
                print(f"  [!!] NO MATCH: {title_hint}")
                errors = True

        all_ids = {t.id for t in tracks}
        unmatched = all_ids - used_ids
        if unmatched:
            for t in tracks:
                if t.id in unmatched:
                    artist_name = t.artist.name if t.artist else "?"
                    print(f"  [!!] UNMATCHED in playlist: {artist_name} - {t.name}")
            errors = True

        if errors:
            print(f"\n  SKIPPING {vol_key} due to matching errors\n")
            continue

        current_ids = [str(t.id) for t in tracks]
        if current_ids == ordered_ids:
            print(f"\n  Already in correct order!\n")
            total_reordered += 1
            continue

        if not dry_run:
            print(f"\n  Clearing playlist...")
            user_playlist = session.playlist(playlist_id).factory()
            user_playlist.clear()
            time.sleep(0.5)

            print(f"  Re-adding {len(ordered_ids)} tracks in desired order...")
            for i in range(0, len(ordered_ids), 50):
                batch = ordered_ids[i:i+50]
                user_playlist.add(batch)
                if i + 50 < len(ordered_ids):
                    time.sleep(0.5)

            print(f"  Reordered successfully!")
            total_reordered += 1
            time.sleep(0.5)
        else:
            print(f"\n  [DRY RUN] Would clear and re-add {len(ordered_ids)} tracks")
            total_reordered += 1

        print()

    print(f"{'='*60}")
    print(f"  REORDER COMPLETE")
    print(f"  Volumes processed: {total_reordered}/{total_volumes}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

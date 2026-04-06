#!/usr/bin/env python3
"""Build an anthology as Tidal playlists from any artist directory.

Usage:
    python scripts/build_anthology.py anthologies/david-bowie/ [--dry-run]
    python scripts/build_anthology.py anthologies/new-model-army/ --dry-run

Each artist directory must contain:
    manifest.json   — folder name, volume definitions, artist aliases
    vol*.txt        — track files (Artist - Title per line)
"""

import json
import os
import sys
import time

from tidal_common import create_session, parse_track_file, search_track


def load_manifest(anthology_dir):
    """Load and validate manifest.json from an anthology directory."""
    manifest_path = os.path.join(anthology_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        print(f"ERROR: No manifest.json found in {anthology_dir}")
        print(f"  Create one with: folder_name, volumes[], and optional artist_aliases[]")
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    required = ["folder_name", "volumes"]
    for key in required:
        if key not in manifest:
            print(f"ERROR: manifest.json missing required key: {key}")
            sys.exit(1)

    return manifest


def build_anthology(session, anthology_dir, dry_run=False):
    """Build the complete anthology from a manifest."""
    manifest = load_manifest(anthology_dir)
    folder_name = manifest["folder_name"]
    volumes = manifest["volumes"]
    aliases = manifest.get("artist_aliases", [])
    user = session.user

    if dry_run:
        print(f"\n[DRY RUN] Would create folder: {folder_name}")
        folder_id = "dry-run-folder"
    else:
        print(f"\nCreating folder: {folder_name}")
        folder = user.create_folder(folder_name)
        folder_id = folder.id
        print(f"  Folder ID: {folder_id}")

    total_matched = 0
    total_failed = 0
    total_tracks = 0
    failed_tracks = []

    for vol in volumes:
        filename = vol["file"]
        playlist_name = vol["title"]
        description = vol.get("description", "")
        prefer_live = vol.get("prefer_live", False)

        filepath = os.path.join(anthology_dir, filename)
        if not os.path.exists(filepath):
            print(f"\nWARNING: {filename} not found, skipping")
            continue

        tracks = parse_track_file(filepath)
        print(f"\n{'='*60}")
        print(f"  {playlist_name}")
        if description:
            print(f"  {description}")
        print(f"  {len(tracks)} tracks to search")
        if prefer_live:
            print(f"  (Preferring live/orchestral versions)")
        print(f"{'='*60}")

        matched_ids = []
        vol_matched = 0
        vol_failed = 0

        for artist, title in tracks:
            track_id, tidal_name = search_track(
                session, artist, title,
                aliases=aliases,
                prefer_live=prefer_live,
            )
            if track_id:
                matched_ids.append(str(track_id))
                vol_matched += 1
                print(f"  [OK] {artist} - {title}")
                if tidal_name and tidal_name.lower() != f"{artist} - {title}".lower():
                    print(f"        -> {tidal_name}")
            else:
                vol_failed += 1
                failed_tracks.append(f"{playlist_name}: {artist} - {title}")
                print(f"  [--] {artist} - {title}")
            time.sleep(0.3)

        total_matched += vol_matched
        total_failed += vol_failed
        total_tracks += len(tracks)

        print(f"\n  Matched: {vol_matched}/{len(tracks)}")

        if not dry_run and matched_ids:
            print(f"  Creating playlist...")
            playlist = user.create_playlist(
                title=playlist_name,
                description=f"{folder_name} | {description}",
                parent_id=folder_id,
            )
            for i in range(0, len(matched_ids), 50):
                batch = matched_ids[i:i+50]
                playlist.add(batch)
                if i + 50 < len(matched_ids):
                    time.sleep(0.5)
            print(f"  Playlist created: {playlist_name} ({vol_matched} tracks)")
        elif dry_run:
            print(f"  [DRY RUN] Would create playlist with {vol_matched} tracks")

    # Summary
    print(f"\n{'='*60}")
    print(f"  ANTHOLOGY COMPLETE: {folder_name}")
    print(f"{'='*60}")
    print(f"  Total tracks: {total_tracks}")
    print(f"  Matched:      {total_matched}")
    print(f"  Failed:       {total_failed}")
    if total_tracks > 0:
        print(f"  Match rate:   {total_matched/total_tracks*100:.1f}%")

    if failed_tracks:
        print(f"\n  Failed tracks:")
        for t in failed_tracks:
            print(f"    - {t}")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: python build_anthology.py <anthology-dir> [--dry-run]")
        print()
        print("  <anthology-dir>  Path to an artist directory containing manifest.json")
        print("  --dry-run        Search Tidal but don't create playlists")
        print()
        print("Examples:")
        print("  python scripts/build_anthology.py anthologies/david-bowie/")
        print("  python scripts/build_anthology.py anthologies/new-model-army/ --dry-run")
        sys.exit(0)

    anthology_dir = sys.argv[1]
    dry_run = "--dry-run" in sys.argv

    if not os.path.isdir(anthology_dir):
        print(f"ERROR: {anthology_dir} is not a directory")
        sys.exit(1)

    if dry_run:
        print("DRY RUN MODE — no playlists will be created")

    print("Authenticating with Tidal...")
    session = create_session()

    build_anthology(session, anthology_dir, dry_run=dry_run)


if __name__ == "__main__":
    main()

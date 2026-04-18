# TidalPlaylistBuilder

Build Tidal playlists from BBC programmes, CSV files, and curated text track listings. Supports multi-volume artist anthologies.

## Usage

```bash
tidal-playlist-builder --input tracklist.csv --name "My Playlist"
tidal-playlist-builder --bbc "https://www.bbc.co.uk/programmes/..." --name "BBC Session"
tidal-playlist-builder --anthology "bowie.txt" --volumes 10 --name "Bowie Anthology"
```

## Features

- Parse track listings from BBC programme pages, CSV, and plain text
- Fuzzy-match tracks against Tidal's catalogue
- OAuth 2.0 device flow authentication
- Multi-volume anthology system for large collections
- Create or update playlists via the Tidal API

## Language

Rust

## License

MIT

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Track {
    pub artist: String,
    pub title: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct MatchResult {
    pub input: Track,
    pub tidal_id: Option<u64>,
    pub tidal_artist: Option<String>,
    pub tidal_title: Option<String>,
    pub matched: bool,
}

#[derive(Debug, Clone, Serialize)]
pub struct PushReport {
    pub playlist_name: String,
    pub total: usize,
    pub matched: usize,
    pub failed: usize,
    pub results: Vec<MatchResult>,
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_track() -> Track {
        Track {
            artist: "Radiohead".to_string(),
            title: "Everything In Its Right Place".to_string(),
        }
    }

    #[test]
    fn track_serialise_round_trip() {
        let track = sample_track();
        let json = serde_json::to_string(&track).unwrap();
        let restored: Track = serde_json::from_str(&json).unwrap();

        assert_eq!(restored.artist, "Radiohead");
        assert_eq!(restored.title, "Everything In Its Right Place");
    }

    #[test]
    fn track_clone_is_independent() {
        let track = sample_track();
        let mut cloned = track.clone();
        cloned.artist = "Modified".to_string();

        assert_eq!(track.artist, "Radiohead");
        assert_eq!(cloned.artist, "Modified");
    }

    #[test]
    fn match_result_matched() {
        let result = MatchResult {
            input: sample_track(),
            tidal_id: Some(123456),
            tidal_artist: Some("Radiohead".to_string()),
            tidal_title: Some("Everything In Its Right Place".to_string()),
            matched: true,
        };

        assert!(result.matched);
        assert_eq!(result.tidal_id, Some(123456));
    }

    #[test]
    fn match_result_unmatched() {
        let result = MatchResult {
            input: sample_track(),
            tidal_id: None,
            tidal_artist: None,
            tidal_title: None,
            matched: false,
        };

        assert!(!result.matched);
        assert!(result.tidal_id.is_none());
    }

    #[test]
    fn match_result_serialise_json() {
        let result = MatchResult {
            input: sample_track(),
            tidal_id: Some(99),
            tidal_artist: Some("Radiohead".to_string()),
            tidal_title: Some("Track".to_string()),
            matched: true,
        };
        let json = serde_json::to_string(&result).unwrap();
        let value: serde_json::Value = serde_json::from_str(&json).unwrap();

        assert_eq!(value["matched"], true);
        assert_eq!(value["tidal_id"], 99);
        assert_eq!(value["input"]["artist"], "Radiohead");
    }

    #[test]
    fn push_report_counts() {
        let matched = MatchResult {
            input: sample_track(),
            tidal_id: Some(1),
            tidal_artist: Some("A".to_string()),
            tidal_title: Some("B".to_string()),
            matched: true,
        };
        let failed = MatchResult {
            input: Track {
                artist: "Unknown".to_string(),
                title: "Missing".to_string(),
            },
            tidal_id: None,
            tidal_artist: None,
            tidal_title: None,
            matched: false,
        };

        let report = PushReport {
            playlist_name: "Test Playlist".to_string(),
            total: 2,
            matched: 1,
            failed: 1,
            results: vec![matched, failed],
        };

        assert_eq!(report.total, report.matched + report.failed);
        assert_eq!(report.results.len(), 2);
        assert!(report.results[0].matched);
        assert!(!report.results[1].matched);
    }

    #[test]
    fn push_report_serialise_json() {
        let report = PushReport {
            playlist_name: "My Playlist".to_string(),
            total: 0,
            matched: 0,
            failed: 0,
            results: vec![],
        };
        let json = serde_json::to_string(&report).unwrap();
        let value: serde_json::Value = serde_json::from_str(&json).unwrap();

        assert_eq!(value["playlist_name"], "My Playlist");
        assert!(value["results"].as_array().unwrap().is_empty());
    }
}

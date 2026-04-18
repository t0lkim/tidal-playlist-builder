use anyhow::{Context, Result};
use keyring::Entry;
use tidalrs::Authz;

const SERVICE: &str = "tpb-tidal";
const ACCOUNT: &str = "oauth-session";

fn entry() -> Result<Entry> {
    Entry::new(SERVICE, ACCOUNT).map_err(|e| anyhow::anyhow!("keychain entry: {e}"))
}

pub fn save(authz: &Authz) -> Result<()> {
    let json = serde_json::to_string(authz).context("serialise session")?;
    entry()?
        .set_password(&json)
        .map_err(|e| anyhow::anyhow!("keychain write: {e}"))
}

pub fn load() -> Result<Option<Authz>> {
    match entry()?.get_password() {
        Ok(json) => {
            let authz: Authz =
                serde_json::from_str(&json).context("deserialise session from keychain")?;
            Ok(Some(authz))
        }
        Err(keyring::Error::NoEntry) => Ok(None),
        Err(e) => Err(anyhow::anyhow!("keychain read: {e}")),
    }
}

pub fn delete() -> Result<()> {
    match entry()?.delete_credential() {
        Ok(()) | Err(keyring::Error::NoEntry) => Ok(()),
        Err(e) => Err(anyhow::anyhow!("keychain delete: {e}")),
    }
}

#[cfg(test)]
mod tests {
    use tidalrs::Authz;

    fn test_authz() -> Authz {
        Authz::new(
            "test_access_token".to_string(),
            "test_refresh_token".to_string(),
            12345,
            Some("SG".to_string()),
        )
    }

    #[test]
    fn authz_serialise_round_trip() {
        let authz = test_authz();
        let json = serde_json::to_string(&authz).unwrap();
        let restored: Authz = serde_json::from_str(&json).unwrap();

        assert_eq!(restored.access_token, "test_access_token");
        assert_eq!(restored.refresh_token, "test_refresh_token");
        assert_eq!(restored.user_id, 12345);
        assert_eq!(restored.country_code.as_deref(), Some("SG"));
    }

    #[test]
    fn authz_serialise_without_country_code() {
        let authz = Authz::new(
            "token".to_string(),
            "refresh".to_string(),
            99,
            None,
        );
        let json = serde_json::to_string(&authz).unwrap();
        let restored: Authz = serde_json::from_str(&json).unwrap();

        assert_eq!(restored.user_id, 99);
        assert!(restored.country_code.is_none());
    }

    #[test]
    fn authz_json_contains_expected_fields() {
        let authz = test_authz();
        let json = serde_json::to_string(&authz).unwrap();
        let value: serde_json::Value = serde_json::from_str(&json).unwrap();

        assert!(value.get("access_token").is_some());
        assert!(value.get("refresh_token").is_some());
        assert!(value.get("user_id").is_some());
        assert!(value.get("country_code").is_some());
    }

    #[test]
    fn authz_deserialise_rejects_invalid_json() {
        let result = serde_json::from_str::<Authz>("not json");
        assert!(result.is_err());
    }

    #[test]
    fn authz_deserialise_rejects_missing_fields() {
        let result = serde_json::from_str::<Authz>(r#"{"access_token":"t"}"#);
        assert!(result.is_err());
    }

    #[test]
    #[ignore] // Touches real macOS Keychain — run manually with `cargo test -- --ignored`
    fn keychain_save_load_delete_cycle() {
        let authz = test_authz();

        super::save(&authz).expect("save");
        let loaded = super::load().expect("load").expect("should exist");
        assert_eq!(loaded.access_token, authz.access_token);
        assert_eq!(loaded.user_id, authz.user_id);

        super::delete().expect("delete");
        let gone = super::load().expect("load after delete");
        assert!(gone.is_none());
    }
}

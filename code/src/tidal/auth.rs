use anyhow::{Context, Result};
use tidalrs::{Authz, DeviceType, TidalClient};
use tokio::time::{timeout, Duration};

use crate::keychain;

// Tidal client credentials (same as tidalapi uses for device flow)
const CLIENT_ID: &str = "fX2JxdmntZWK0ixT";
const CLIENT_SECRET: &str = "1Nn9AfDAjxrgJFJbKNWLeAyKGVGmINuXPPLHVXAvxAg==";

fn build_base_client() -> Result<TidalClient> {
    let http = reqwest::Client::builder()
        .timeout(Duration::from_secs(10))
        .build()
        .context("build HTTP client")?;

    Ok(TidalClient::new(CLIENT_ID.to_string())
        .with_client(http)
        .with_device_type(DeviceType::Browser)
        .with_max_backoff_millis(3_000))
}

/// Build an authenticated client from stored Keychain tokens.
/// Registers a refresh callback so updated tokens are persisted automatically.
pub fn build_client() -> Result<TidalClient> {
    let authz = keychain::load()?.ok_or_else(|| anyhow::anyhow!("Not authenticated"))?;

    let client = build_base_client()?
        .with_authz(authz)
        .with_authz_refresh_callback(|new_authz: Authz| {
            if let Err(e) = keychain::save(&new_authz) {
                tracing::error!("Failed to persist refreshed token: {e}");
            } else {
                tracing::debug!("Persisted refreshed token to Keychain");
            }
        });

    Ok(client)
}

/// Run the OAuth device flow, store tokens in Keychain.
pub async fn device_flow(force: bool) -> Result<()> {
    if !force && keychain::load()?.is_some() {
        println!("Already authenticated. Use --force to re-authenticate.");
        return Ok(());
    }

    let client = build_base_client()?;
    let device_auth = client
        .device_authorization()
        .await
        .context("device authorisation request")?;

    println!("Open this URL in your browser:");
    println!("  {}", device_auth.url);
    println!();
    println!("Enter code: {}", device_auth.user_code);
    println!();
    println!("Waiting for authorisation...");

    let authz_token = client
        .authorize(&device_auth.device_code, CLIENT_SECRET)
        .await
        .context("authorisation polling")?;

    let authz = authz_token
        .authz()
        .context("no refresh token in auth response")?;

    keychain::save(&authz).context("save session to Keychain")?;

    println!("Authenticated as user {} ({})", authz.user_id, authz_token.user.username);
    println!("Session stored in macOS Keychain.");
    Ok(())
}

/// Print authentication status.
pub async fn status() -> Result<()> {
    match keychain::load()? {
        Some(authz) => {
            println!("Authenticated");
            println!("  User ID: {}", authz.user_id);
            if let Some(cc) = &authz.country_code {
                println!("  Country: {cc}");
            }

            // Verify the token works with a lightweight API call (5s timeout)
            let client = build_client()?;
            let check = timeout(
                Duration::from_secs(5),
                client.favorite_tracks(Some(0), Some(1), None, None),
            )
            .await;
            match check {
                Ok(Ok(_)) => println!("  Token: valid"),
                Ok(Err(_)) => println!("  Token: expired (re-run `tpb auth --force`)"),
                Err(_) => println!("  Token: check timed out"),
            }
        }
        None => {
            println!("Not authenticated. Run `tpb auth` to log in.");
        }
    }
    Ok(())
}

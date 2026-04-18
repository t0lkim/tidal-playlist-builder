mod cli;
mod error;
mod keychain;
mod model;
mod source;
mod tidal;

use anyhow::Result;
use clap::Parser;
use tracing_subscriber::EnvFilter;

use cli::{Cli, Command};

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .init();

    let cli = Cli::parse();

    match cli.command {
        Command::Auth { force } => tidal::auth::device_flow(force).await?,
        Command::Status => tidal::auth::status().await?,
    }

    Ok(())
}

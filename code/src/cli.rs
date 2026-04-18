use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(
    name = "tpb",
    about = "Build Tidal playlists from BBC programmes, CSV, and text files"
)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Command,
}

#[derive(Subcommand)]
pub enum Command {
    /// Authenticate with Tidal via OAuth device flow
    Auth {
        /// Force re-authentication even if already authenticated
        #[arg(long)]
        force: bool,
    },
    /// Show authentication status
    Status,
}

#[cfg(test)]
mod tests {
    use super::*;
    use clap::Parser;

    #[test]
    fn parse_auth() {
        let cli = Cli::try_parse_from(["tpb", "auth"]).unwrap();
        assert!(matches!(cli.command, Command::Auth { force: false }));
    }

    #[test]
    fn parse_auth_force() {
        let cli = Cli::try_parse_from(["tpb", "auth", "--force"]).unwrap();
        assert!(matches!(cli.command, Command::Auth { force: true }));
    }

    #[test]
    fn parse_status() {
        let cli = Cli::try_parse_from(["tpb", "status"]).unwrap();
        assert!(matches!(cli.command, Command::Status));
    }

    #[test]
    fn parse_no_subcommand_fails() {
        let result = Cli::try_parse_from(["tpb"]);
        assert!(result.is_err());
    }

    #[test]
    fn parse_unknown_subcommand_fails() {
        let result = Cli::try_parse_from(["tpb", "foobar"]);
        assert!(result.is_err());
    }

    #[test]
    fn parse_auth_rejects_unknown_flag() {
        let result = Cli::try_parse_from(["tpb", "auth", "--unknown"]);
        assert!(result.is_err());
    }
}

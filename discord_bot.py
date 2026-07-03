"""Discord entrypoint for the Cyrene diary agent."""

from hermes.config import ConfigError, load_settings
from hermes.discord_app import run_discord_bot


def main() -> None:
    try:
        settings = load_settings()
    except ConfigError as exc:
        raise SystemExit(f"설정 오류: {exc}") from exc
    run_discord_bot(settings)


if __name__ == "__main__":
    main()

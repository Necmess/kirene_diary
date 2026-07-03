"""Runtime configuration for the local agent."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    model: str = "gemma3:4b"
    llm_url: str = "http://localhost:11434/api/chat"
    max_tokens: int = 1024
    memory_dir: str = "memory"


class ConfigError(ValueError):
    """Raised when runtime configuration is invalid."""


def load_dotenv(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_settings() -> Settings:
    load_dotenv()
    max_tokens = _positive_int(
        os.environ.get("CYRENE_MAX_TOKENS", str(Settings.max_tokens)),
        "CYRENE_MAX_TOKENS",
    )
    return Settings(
        model=os.environ.get("CYRENE_MODEL", Settings.model),
        llm_url=os.environ.get("CYRENE_LLM_URL", Settings.llm_url),
        max_tokens=max_tokens,
        memory_dir=os.environ.get("CYRENE_MEMORY_DIR", Settings.memory_dir),
    )


def _positive_int(value: str, name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ConfigError(f"{name}은 양의 정수여야 합니다: {value}") from exc
    if parsed <= 0:
        raise ConfigError(f"{name}은 1 이상이어야 합니다: {value}")
    return parsed

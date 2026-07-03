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
    return Settings(
        model=os.environ.get("CYRENE_MODEL", Settings.model),
        llm_url=os.environ.get("CYRENE_LLM_URL", Settings.llm_url),
        max_tokens=int(os.environ.get("CYRENE_MAX_TOKENS", str(Settings.max_tokens))),
        memory_dir=os.environ.get("CYRENE_MEMORY_DIR", Settings.memory_dir),
    )

"""Runtime configuration for the local agent."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    model: str = "gemma4:e4b"
    llm_url: str = "http://localhost:11434/api/chat"
    max_tokens: int = 1024
    memory_dir: str = "memory"
    storage: str = "local"
    diary_dir: str = "diary"
    notion_token: str = ""
    notion_database_id: str = ""
    notion_version: str = "2022-06-28"
    discord_bot_token: str = ""
    discord_command_prefix: str = "!키레네"
    notion_tool: str = "disabled"
    mcp_notion_url: str = ""
    mcp_timeout: int = 30
    mcp_notion_search_tool: str = "notion_search"
    mcp_notion_read_tool: str = "notion_read_page"
    mcp_notion_todo_tool: str = "notion_create_todo"
    safety_region: str = "GLOBAL"
    obsidian_dir: str = ""
    embed_model: str = "nomic-embed-text"
    embed_url: str = "http://localhost:11434/api/embeddings"


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
    mcp_timeout = _positive_int(
        os.environ.get("CYRENE_MCP_TIMEOUT", str(Settings.mcp_timeout)),
        "CYRENE_MCP_TIMEOUT",
    )
    storage = os.environ.get("CYRENE_STORAGE", Settings.storage).lower()
    if storage not in ("local", "notion"):
        raise ConfigError(f"CYRENE_STORAGE는 local 또는 notion이어야 합니다: {storage}")
    notion_tool = os.environ.get("CYRENE_NOTION_TOOL", Settings.notion_tool).lower()
    if notion_tool not in ("disabled", "mcp"):
        raise ConfigError(
            f"CYRENE_NOTION_TOOL은 disabled 또는 mcp여야 합니다: {notion_tool}"
        )

    settings = Settings(
        model=os.environ.get("CYRENE_MODEL", Settings.model),
        llm_url=os.environ.get("CYRENE_LLM_URL", Settings.llm_url),
        max_tokens=max_tokens,
        memory_dir=os.environ.get("CYRENE_MEMORY_DIR", Settings.memory_dir),
        storage=storage,
        diary_dir=os.environ.get("CYRENE_DIARY_DIR", Settings.diary_dir),
        notion_token=os.environ.get("NOTION_TOKEN", Settings.notion_token),
        notion_database_id=os.environ.get(
            "NOTION_DATABASE_ID", Settings.notion_database_id
        ),
        notion_version=os.environ.get("NOTION_VERSION", Settings.notion_version),
        discord_bot_token=os.environ.get(
            "DISCORD_BOT_TOKEN", Settings.discord_bot_token
        ),
        discord_command_prefix=os.environ.get(
            "DISCORD_COMMAND_PREFIX", Settings.discord_command_prefix
        ),
        notion_tool=notion_tool,
        mcp_notion_url=os.environ.get("CYRENE_MCP_NOTION_URL", Settings.mcp_notion_url),
        mcp_timeout=mcp_timeout,
        mcp_notion_search_tool=os.environ.get(
            "CYRENE_MCP_NOTION_SEARCH_TOOL", Settings.mcp_notion_search_tool
        ),
        mcp_notion_read_tool=os.environ.get(
            "CYRENE_MCP_NOTION_READ_TOOL", Settings.mcp_notion_read_tool
        ),
        mcp_notion_todo_tool=os.environ.get(
            "CYRENE_MCP_NOTION_TODO_TOOL", Settings.mcp_notion_todo_tool
        ),
        safety_region=os.environ.get("CYRENE_SAFETY_REGION", Settings.safety_region),
        obsidian_dir=os.environ.get("CYRENE_OBSIDIAN_DIR", Settings.obsidian_dir),
        embed_model=os.environ.get("CYRENE_EMBED_MODEL", Settings.embed_model),
        embed_url=os.environ.get("CYRENE_EMBED_URL", Settings.embed_url),
    )
    if settings.storage == "notion":
        _required(settings.notion_token, "NOTION_TOKEN")
        _required(settings.notion_database_id, "NOTION_DATABASE_ID")
    return settings


def _positive_int(value: str, name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ConfigError(f"{name}은 양의 정수여야 합니다: {value}") from exc
    if parsed <= 0:
        raise ConfigError(f"{name}은 1 이상이어야 합니다: {value}")
    return parsed


def _required(value: str, name: str) -> None:
    if not value.strip():
        raise ConfigError(f"{name} 환경변수가 필요합니다.")

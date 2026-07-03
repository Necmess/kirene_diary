"""Application factories shared by CLI and Discord entrypoints."""

from pathlib import Path

from storage import DiaryStorage, LocalMarkdownStorage, NotionStorage

from .agent import HermesAgent
from .config import Settings
from .llm import LocalLLMClient
from .memory import DiaryIndexMemory, ProfileMemory
from .mcp_client import DisabledMcpClient, HttpMcpClient, McpClient
from .tool_router import ToolRouter


def build_storage(settings: Settings) -> DiaryStorage:
    if settings.storage == "notion":
        return NotionStorage(
            token=settings.notion_token,
            database_id=settings.notion_database_id,
            notion_version=settings.notion_version,
        )
    return LocalMarkdownStorage(settings.diary_dir)


def build_agent(settings: Settings, memory_scope: str = "") -> HermesAgent:
    memory_dir = _memory_dir(settings.memory_dir, memory_scope)
    llm = LocalLLMClient(
        model=settings.model,
        url=settings.llm_url,
        max_tokens=settings.max_tokens,
    )
    return HermesAgent(
        llm=llm,
        storage=build_storage(settings),
        profile_memory=ProfileMemory(memory_dir / "profile.json"),
        diary_index=DiaryIndexMemory(memory_dir / "diary_index.json"),
        tool_router=build_tool_router(settings),
    )


def build_mcp_client(settings: Settings) -> McpClient:
    if settings.mcp_notion_url:
        return HttpMcpClient(settings.mcp_notion_url, timeout=settings.mcp_timeout)
    return DisabledMcpClient()


def build_tool_router(settings: Settings) -> ToolRouter:
    return ToolRouter(
        mcp_client=build_mcp_client(settings),
        notion_enabled=settings.notion_tool == "mcp",
        notion_search_tool=settings.mcp_notion_search_tool,
    )


def _memory_dir(base_dir: str, scope: str) -> Path:
    if not scope:
        return Path(base_dir)
    safe_scope = "".join(
        character if character.isalnum() or character in ("-", "_") else "_"
        for character in scope
    )
    return Path(base_dir) / safe_scope

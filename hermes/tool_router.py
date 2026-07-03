"""Tool routing layer for optional external MCP tools."""

from dataclasses import dataclass
from typing import Any

from .mcp_client import McpClient, McpClientError


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    message: str
    data: Any = None


class ToolRouter:
    """Routes high-level agent tool requests to concrete tool providers."""

    def __init__(
        self,
        mcp_client: McpClient | None = None,
        notion_enabled: bool = False,
        notion_search_tool: str = "notion_search",
    ) -> None:
        self.mcp_client = mcp_client
        self.notion_enabled = notion_enabled
        self.notion_search_tool = notion_search_tool

    def status_report(self) -> str:
        lines = [
            "## 도구 상태",
            f"- Notion MCP: {'enabled' if self.notion_enabled else 'disabled'}",
        ]
        if self.notion_enabled:
            lines.append(f"- Notion search tool: {self.notion_search_tool}")
        return "\n".join(lines)

    def search_notion(self, query: str) -> ToolResult:
        if not self.notion_enabled or self.mcp_client is None:
            return ToolResult(False, "Notion MCP가 설정되지 않았습니다.")
        cleaned = query.strip()
        if not cleaned:
            return ToolResult(False, "검색어를 함께 입력해주세요.")
        try:
            result = self.mcp_client.call_tool(
                self.notion_search_tool,
                {"query": cleaned},
            )
        except McpClientError as exc:
            return ToolResult(False, str(exc))
        return ToolResult(True, format_tool_result(result), result)


def format_tool_result(result: Any) -> str:
    if isinstance(result, dict):
        if "content" in result:
            return _format_content(result["content"])
        if "result" in result:
            return format_tool_result(result["result"])
        return "\n".join(f"- {key}: {value}" for key, value in result.items())
    if isinstance(result, list):
        return _format_content(result)
    return str(result)


def _format_content(content: Any) -> str:
    if not isinstance(content, list):
        return str(content)
    lines = []
    for item in content:
        if isinstance(item, dict):
            text = item.get("text") or item.get("content") or str(item)
            lines.append(str(text))
        else:
            lines.append(str(item))
    return "\n".join(lines) if lines else "결과가 없습니다."

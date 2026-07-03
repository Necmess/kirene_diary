"""Tool routing layer for optional external MCP tools."""

from dataclasses import dataclass
from typing import Any

from .mcp_client import McpClient, McpClientError


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    message: str
    data: Any = None


@dataclass(frozen=True)
class ToolPolicy:
    allow_read: bool = True
    allow_create: bool = True
    allow_update: bool = False
    allow_delete: bool = False

    def report(self) -> list[str]:
        return [
            f"- read/search: {'allowed' if self.allow_read else 'blocked'}",
            f"- create: {'allowed' if self.allow_create else 'blocked'}",
            f"- update: {'allowed' if self.allow_update else 'blocked'}",
            f"- delete/archive: {'allowed' if self.allow_delete else 'blocked'}",
        ]


class ToolRouter:
    """Routes high-level agent tool requests to concrete tool providers."""

    def __init__(
        self,
        mcp_client: McpClient | None = None,
        notion_enabled: bool = False,
        notion_search_tool: str = "notion_search",
        notion_read_tool: str = "notion_read_page",
        notion_create_todo_tool: str = "notion_create_todo",
        policy: ToolPolicy | None = None,
    ) -> None:
        self.mcp_client = mcp_client
        self.notion_enabled = notion_enabled
        self.notion_search_tool = notion_search_tool
        self.notion_read_tool = notion_read_tool
        self.notion_create_todo_tool = notion_create_todo_tool
        self.policy = policy or ToolPolicy()

    def status_report(self) -> str:
        lines = [
            "## 도구 상태",
            f"- Notion MCP: {'enabled' if self.notion_enabled else 'disabled'}",
        ]
        if self.notion_enabled:
            lines.append(f"- Notion search tool: {self.notion_search_tool}")
            lines.append(f"- Notion read tool: {self.notion_read_tool}")
            lines.append(f"- Notion todo tool: {self.notion_create_todo_tool}")
        lines.append("")
        lines.append("## 도구 정책")
        lines.extend(self.policy.report())
        return "\n".join(lines)

    def search_notion(self, query: str) -> ToolResult:
        if not self.policy.allow_read:
            return ToolResult(False, "Notion 읽기/검색 권한이 비활성화되어 있습니다.")
        cleaned = query.strip()
        if not cleaned:
            return ToolResult(False, "검색어를 함께 입력해주세요.")
        return self._call_notion(self.notion_search_tool, {"query": cleaned})

    def read_notion_page(self, page_ref: str) -> ToolResult:
        if not self.policy.allow_read:
            return ToolResult(False, "Notion 읽기 권한이 비활성화되어 있습니다.")
        cleaned = page_ref.strip()
        if not cleaned:
            return ToolResult(False, "읽을 Notion 페이지 ID 또는 URL을 입력해주세요.")
        return self._call_notion(self.notion_read_tool, {"page": cleaned})

    def create_notion_todo(self, text: str) -> ToolResult:
        if not self.policy.allow_create:
            return ToolResult(False, "Notion 생성 권한이 비활성화되어 있습니다.")
        cleaned = text.strip()
        if not cleaned:
            return ToolResult(False, "추가할 할 일을 입력해주세요.")
        return self._call_notion(self.notion_create_todo_tool, {"text": cleaned})

    def update_notion_page(self, page_ref: str, content: str) -> ToolResult:
        return ToolResult(False, "Notion 페이지 수정은 현재 정책상 비활성화되어 있습니다.")

    def delete_notion_page(self, page_ref: str) -> ToolResult:
        return ToolResult(False, "Notion 삭제/보관은 현재 정책상 비활성화되어 있습니다.")

    def _call_notion(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        if not self.notion_enabled or self.mcp_client is None:
            return ToolResult(False, "Notion MCP가 설정되지 않았습니다.")
        try:
            result = self.mcp_client.call_tool(tool_name, arguments)
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

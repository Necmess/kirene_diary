"""Minimal MCP client primitives.

The HTTP client uses JSON-RPC payloads shaped like MCP's `tools/call` request.
It is intentionally small so the Discord bot can stay a separate process from
the Notion MCP server.
"""

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol


class McpClientError(RuntimeError):
    """Raised when an MCP tool call cannot be completed."""


class McpClient(Protocol):
    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call an MCP tool and return the raw JSON result."""


@dataclass
class HttpMcpClient:
    endpoint: str
    timeout: int = 30

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise McpClientError(f"MCP 호출 실패: {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise McpClientError(f"MCP 서버에 연결할 수 없습니다: {exc}") from exc

        try:
            result = json.loads(body)
        except json.JSONDecodeError as exc:
            raise McpClientError(f"MCP 응답이 JSON이 아닙니다: {body[:200]}") from exc
        if "error" in result:
            raise McpClientError(f"MCP 오류: {result['error']}")
        return result.get("result", result)


class DisabledMcpClient:
    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        raise McpClientError("MCP 서버가 설정되지 않았습니다.")

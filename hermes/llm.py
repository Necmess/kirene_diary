"""Local LLM client.

Defaults to Ollama's chat API at http://localhost:11434/api/chat.
"""

import json
import urllib.error
import urllib.request

from .messages import ChatMessage


class LocalLLMError(RuntimeError):
    """Raised when the local model server cannot produce a response."""


class LocalLLMClient:
    def __init__(
        self,
        model: str = "gemma3:4b",
        url: str = "http://localhost:11434/api/chat",
        max_tokens: int = 1024,
        timeout: int = 120,
    ) -> None:
        self.model = model
        self.url = url
        self.max_tokens = max_tokens
        self.timeout = timeout

    def chat(self, system: str, messages: list[ChatMessage]) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}]
            + [message.as_dict() for message in messages],
            "stream": False,
            "options": {"num_predict": self.max_tokens},
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise LocalLLMError(
                f"로컬 LLM 서버에 연결할 수 없습니다: {self.url}"
            ) from exc

        try:
            result = json.loads(body)
            return result["message"]["content"].strip()
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise LocalLLMError(f"로컬 LLM 응답 형식이 예상과 다릅니다: {body[:200]}") from exc

"""Local embedding client for wiki-style diary linking.

Defaults to Ollama's embeddings API at http://localhost:11434/api/embeddings.
Requires an embedding model to be pulled separately, e.g.
``ollama pull nomic-embed-text``.
"""

import json
import urllib.error
import urllib.request


class EmbeddingError(RuntimeError):
    """Raised when the local embedding server cannot produce a vector."""


class LocalEmbeddingClient:
    def __init__(
        self,
        model: str = "nomic-embed-text",
        url: str = "http://localhost:11434/api/embeddings",
        timeout: int = 30,
    ) -> None:
        self.model = model
        self.url = url
        self.timeout = timeout

    def embed(self, text: str) -> list[float]:
        payload = {"model": self.model, "prompt": text}
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
            raise EmbeddingError(
                f"임베딩 서버에 연결할 수 없습니다: {self.url}"
            ) from exc

        try:
            result = json.loads(body)
            return [float(value) for value in result["embedding"]]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise EmbeddingError(
                f"임베딩 응답 형식이 예상과 다릅니다: {body[:200]}"
            ) from exc

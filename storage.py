"""일기 저장소 추상화."""

from abc import ABC, abstractmethod
from datetime import date
import json
from pathlib import Path
import urllib.error
import urllib.request


class DiaryStorage(ABC):
    """일기 저장소 인터페이스."""

    @abstractmethod
    def save(self, entry_date: date, content: str) -> str:
        """일기를 저장하고 위치(경로/URL)를 반환한다."""

    @abstractmethod
    def load(self, entry_date: date) -> str | None:
        """해당 날짜의 일기를 반환한다. 없으면 None."""


class LocalMarkdownStorage(DiaryStorage):
    """diary/YYYY-MM-DD.md 형태로 저장."""

    def __init__(self, base_dir: str | Path = "diary"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, entry_date: date) -> Path:
        return self.base_dir / f"{entry_date.isoformat()}.md"

    def save(self, entry_date: date, content: str) -> str:
        path = self._path(entry_date)
        header = f"# {entry_date.isoformat()} 일기\n\n"
        path.write_text(header + content.strip() + "\n", encoding="utf-8")
        return str(path)

    def load(self, entry_date: date) -> str | None:
        path = self._path(entry_date)
        return path.read_text(encoding="utf-8") if path.exists() else None


class NotionStorage(DiaryStorage):
    """Save diary entries as pages in a Notion database.

    Expected database properties:
      - Name: title
      - Date: date
    """

    API_URL = "https://api.notion.com/v1/pages"

    def __init__(
        self,
        token: str,
        database_id: str,
        notion_version: str = "2022-06-28",
    ):
        self.token = token
        self.database_id = database_id
        self.notion_version = notion_version

    def save(self, entry_date: date, content: str) -> str:
        payload = self._build_page_payload(entry_date, content)
        result = self._post(self.API_URL, payload)
        return result.get("url", f"notion://{result.get('id', entry_date.isoformat())}")

    def load(self, entry_date: date) -> str | None:
        raise NotImplementedError("Notion 일기 읽기는 아직 구현하지 않았습니다.")

    def _build_page_payload(self, entry_date: date, content: str) -> dict:
        return {
            "parent": {"database_id": self.database_id},
            "properties": {
                "Name": {
                    "title": [
                        {"text": {"content": f"{entry_date.isoformat()} 일기"}}
                    ]
                },
                "Date": {"date": {"start": entry_date.isoformat()}},
            },
            "children": self._content_to_blocks(content),
        }

    def _content_to_blocks(self, content: str) -> list[dict]:
        paragraphs = [part.strip() for part in content.split("\n\n") if part.strip()]
        if not paragraphs:
            paragraphs = [" "]
        blocks = []
        for paragraph in paragraphs:
            for chunk in self._chunks(paragraph, 1800):
                blocks.append(
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": chunk}}]
                        },
                    }
                )
        return blocks

    def _chunks(self, text: str, size: int) -> list[str]:
        return [text[index : index + size] for index in range(0, len(text), size)]

    def _post(self, url: str, payload: dict) -> dict:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Notion-Version": self.notion_version,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Notion 저장 실패: {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Notion에 연결할 수 없습니다: {exc}") from exc
        return json.loads(body)

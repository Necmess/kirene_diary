"""일기 저장소 추상화.

지금은 로컬 마크다운 저장만 구현. 나중에 Notion을 붙일 땐
NotionStorage의 TODO만 채우고 main.py에서 갈아끼우면 된다.
"""

from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path


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
    """Notion 연동 스텁. 나중에 구현.

    구현 가이드:
      1. pip install notion-client
      2. https://www.notion.so/my-integrations 에서 인테그레이션 생성 → NOTION_TOKEN
      3. 일기용 데이터베이스 생성 후 인테그레이션 초대 → NOTION_DATABASE_ID
      4. save(): databases 아래 페이지 생성 (title=날짜, children=본문 블록)
      5. load(): 날짜 프로퍼티로 쿼리 후 블록 텍스트 조합
    """

    def __init__(self, token: str, database_id: str):
        self.token = token
        self.database_id = database_id

    def save(self, entry_date: date, content: str) -> str:
        raise NotImplementedError("Notion 연동은 아직 준비 중이야. NotionStorage TODO를 채워줘.")

    def load(self, entry_date: date) -> str | None:
        raise NotImplementedError

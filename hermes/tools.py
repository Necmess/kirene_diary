"""Tools available to the Hermes agent."""

from datetime import date

from storage import DiaryStorage


class DiaryTool:
    """Writes generated diary entries through the configured storage backend."""

    def __init__(self, storage: DiaryStorage) -> None:
        self.storage = storage

    def save_today(self, content: str) -> str:
        return self.storage.save(date.today(), content)

"""Memory components for the Hermes agent."""

import json
from pathlib import Path
from typing import Any

from .messages import ChatMessage


class ConversationMemory:
    """Keeps the current session transcript in model-ready form."""

    def __init__(self) -> None:
        self._messages: list[ChatMessage] = []

    def add_user(self, content: str) -> None:
        self._messages.append(ChatMessage(role="user", content=content))

    def add_assistant(self, content: str) -> None:
        self._messages.append(ChatMessage(role="assistant", content=content))

    def pop_last(self) -> ChatMessage | None:
        return self._messages.pop() if self._messages else None

    def has_user_messages(self) -> bool:
        return any(message.role == "user" for message in self._messages)

    def as_messages(self) -> list[ChatMessage]:
        return list(self._messages)

    def as_dicts(self) -> list[dict[str, str]]:
        return [message.as_dict() for message in self._messages]


class ProfileMemory:
    """File-backed long-term user profile memory."""

    DEFAULT_PROFILE: dict[str, Any] = {
        "user_name": None,
        "preferences": [],
        "recurring_topics": [],
        "important_people": [],
        "important_places": [],
        "avoid": [],
        "notes": [],
    }

    def __init__(self, path: str | Path = "memory/profile.json") -> None:
        self.path = Path(path)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return dict(self.DEFAULT_PROFILE)
        with self.path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return self._with_defaults(data)

    def save(self, profile: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(self._with_defaults(profile), file, ensure_ascii=False, indent=2)
            file.write("\n")

    def render_context(self) -> str:
        profile = self.load()
        lines: list[str] = []

        if profile["user_name"]:
            lines.append(f"- 사용자 이름: {profile['user_name']}")
        for key, label in (
            ("preferences", "선호"),
            ("recurring_topics", "반복 주제"),
            ("important_people", "중요한 사람"),
            ("important_places", "중요한 장소"),
            ("avoid", "피해야 할 것"),
            ("notes", "메모"),
        ):
            values = [str(value) for value in profile.get(key, []) if str(value).strip()]
            if values:
                lines.append(f"- {label}: {', '.join(values)}")

        if not lines:
            return ""
        return "## 사용자에 대한 장기 기억\n" + "\n".join(lines)

    def _with_defaults(self, data: dict[str, Any]) -> dict[str, Any]:
        profile = dict(self.DEFAULT_PROFILE)
        profile.update(data)
        return profile


class DiaryIndexMemory:
    """File-backed index for generated diary entries."""

    def __init__(self, path: str | Path = "memory/diary_index.json") -> None:
        self.path = Path(path)

    def load(self) -> dict[str, list[dict[str, Any]]]:
        if not self.path.exists():
            return {"entries": []}
        with self.path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        entries = data.get("entries", [])
        return {"entries": entries if isinstance(entries, list) else []}

    def save(self, data: dict[str, list[dict[str, Any]]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")

    def recent_context(self, limit: int = 3) -> str:
        entries = self.load()["entries"][-limit:]
        lines = []
        for entry in entries:
            date = entry.get("date", "unknown")
            summary = entry.get("summary", "")
            if summary:
                lines.append(f"- {date}: {summary}")
        if not lines:
            return ""
        return "## 최근 일기 요약\n" + "\n".join(lines)

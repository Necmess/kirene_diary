"""Memory components for the Hermes agent."""

import json
import math
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .messages import ChatMessage


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


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

    def clear(self) -> None:
        self._messages.clear()

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

    def set_user_name(self, name: str) -> None:
        profile = self.load()
        profile["user_name"] = name.strip() or None
        self.save(profile)

    def add_value(self, key: str, value: str) -> None:
        if key not in self.DEFAULT_PROFILE or key == "user_name":
            raise ValueError(f"지원하지 않는 프로필 키입니다: {key}")
        cleaned = value.strip()
        if not cleaned:
            return
        profile = self.load()
        values = [str(item) for item in profile.get(key, [])]
        if cleaned not in values:
            values.append(cleaned)
        profile[key] = values
        self.save(profile)

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

    def add_entry(
        self,
        entry_date: date,
        location: str,
        content: str,
        summary: str | None = None,
        tags: list[str] | None = None,
        embedding: list[float] | None = None,
    ) -> None:
        data = self.load()
        entries = [
            entry
            for entry in data["entries"]
            if entry.get("date") != entry_date.isoformat()
        ]
        entry: dict[str, Any] = {
            "date": entry_date.isoformat(),
            "location": location,
            "summary": summary or self._excerpt(content),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        if tags:
            entry["tags"] = tags
        if embedding:
            entry["embedding"] = embedding
        entries.append(entry)
        data["entries"] = sorted(entries, key=lambda entry: entry.get("date", ""))
        self.save(data)

    def find_related(
        self,
        embedding: list[float],
        exclude_date: str,
        limit: int = 3,
        threshold: float = 0.6,
    ) -> list[str]:
        """Return dates of past entries whose stored embedding is similar.

        Entries saved before embeddings were enabled simply have no
        "embedding" field and are skipped rather than treated as unrelated.
        """
        if not embedding:
            return []
        scored: list[tuple[float, str]] = []
        for entry in self.load()["entries"]:
            entry_date_str = entry.get("date")
            candidate = entry.get("embedding")
            if entry_date_str == exclude_date or not candidate:
                continue
            score = cosine_similarity(embedding, candidate)
            if score >= threshold:
                scored.append((score, entry_date_str))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [entry_date_str for _, entry_date_str in scored[:limit]]

    def recent_context(self, limit: int = 3) -> str:
        entries = self.recent_entries(limit)
        lines = []
        for entry in entries:
            date = entry.get("date", "unknown")
            summary = entry.get("summary", "")
            if summary:
                lines.append(f"- {date}: {summary}")
        if not lines:
            return ""
        return "## 최근 일기 요약\n" + "\n".join(lines)

    def render_context(self) -> str:
        entries = self.load()["entries"]
        if not entries:
            return ""
        lines = []
        for entry in entries:
            date = entry.get("date", "unknown")
            summary = entry.get("summary", "")
            location = entry.get("location", "")
            line = f"- {date}"
            if summary:
                line += f": {summary}"
            if location:
                line += f" ({location})"
            lines.append(line)
        return "## 일기 인덱스\n" + "\n".join(lines)

    def recent_entries(self, limit: int = 3) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        return self.load()["entries"][-limit:]

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        term = query.strip().lower()
        if not term or limit <= 0:
            return []
        matches = []
        for entry in reversed(self.load()["entries"]):
            haystack = " ".join(
                str(entry.get(key, "")) for key in ("date", "summary", "location")
            ).lower()
            if term in haystack:
                matches.append(entry)
            if len(matches) >= limit:
                break
        return matches

    def _excerpt(self, content: str, limit: int = 120) -> str:
        text = " ".join(line.strip() for line in content.splitlines() if line.strip())
        if len(text) <= limit:
            return text
        return text[: limit - 1].rstrip() + "…"

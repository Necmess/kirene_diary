"""Obsidian-facing knowledge wiki for the Cyrene diary agent.

The diary text itself lives in whatever ``DiaryStorage`` backend is
configured (Notion or local markdown). This module mirrors a lightweight
index of each entry -- summary, tags, links to related past entries --
into an Obsidian vault so the relationships between entries and concepts
become a browsable, linked "brain" separate from the diary book itself.
"""

import re
from pathlib import Path
from typing import Protocol

from .messages import ChatMessage


class ChatClient(Protocol):
    def chat(self, system: str, messages: list[ChatMessage]) -> str: ...


_UNSAFE_NAME_CHARS = re.compile(r'[\\/:*?"<>|]')


def safe_note_name(text: str) -> str:
    cleaned = _UNSAFE_NAME_CHARS.sub("", text).strip()
    return cleaned or "untitled"


def extract_tags(llm: ChatClient, content: str, limit: int = 5) -> list[str]:
    """Ask the local model for a handful of short keyword tags.

    Returns an empty list if the model is unreachable or replies with
    something unusable -- tagging is a nice-to-have, not a hard requirement
    for saving a diary entry.
    """
    prompt = (
        f"다음 일기 내용에서 핵심 키워드를 {limit}개 이하로 뽑아줘. "
        "설명 없이 쉼표로만 구분된 짧은 단어나 구로만 답해.\n\n" + content
    )
    try:
        raw = llm.chat("", [ChatMessage(role="user", content=prompt)])
    except Exception:
        return []

    tags: list[str] = []
    for candidate in raw.replace("\n", ",").split(","):
        tag = candidate.strip(" -•*\"'").strip()
        if tag and len(tag) <= 20 and tag not in tags:
            tags.append(tag)
        if len(tags) >= limit:
            break
    return tags


class ObsidianWiki:
    """Writes per-entry and per-tag notes into an Obsidian vault folder."""

    def __init__(self, vault_dir: str | Path):
        self.vault_dir = Path(vault_dir)
        self.diary_dir = self.vault_dir / "일기"
        self.tag_dir = self.vault_dir / "태그"

    def write_entry(
        self,
        entry_date_iso: str,
        summary: str,
        tags: list[str],
        related_dates: list[str],
        external_link: str = "",
    ) -> Path:
        for tag in tags:
            self._ensure_tag_page(tag)

        lines = ["---", f"date: {entry_date_iso}"]
        if tags:
            lines.append(f"tags: [{', '.join(tags)}]")
        lines.append("---")
        lines.append("")
        lines.append(f"# {entry_date_iso}")
        lines.append("")
        if summary:
            lines.append(summary)
            lines.append("")
        if external_link:
            lines.append(f"원문: {external_link}")
            lines.append("")
        if tags:
            lines.append("## 태그")
            lines.append(" ".join(f"[[{tag}]]" for tag in tags))
            lines.append("")
        if related_dates:
            lines.append("## 관련 일기")
            for related in related_dates:
                lines.append(f"- [[{related}]]")
            lines.append("")

        self.diary_dir.mkdir(parents=True, exist_ok=True)
        path = self.diary_dir / f"{entry_date_iso}.md"
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return path

    def _ensure_tag_page(self, tag: str) -> None:
        self.tag_dir.mkdir(parents=True, exist_ok=True)
        path = self.tag_dir / f"{safe_note_name(tag)}.md"
        if not path.exists():
            path.write_text(
                f"# {tag}\n\n이 태그가 붙은 일기는 Obsidian 백링크에서 확인.\n",
                encoding="utf-8",
            )

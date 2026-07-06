"""Hermes-style orchestrator for the Cyrene diary agent."""

from datetime import date
from typing import Any

from persona import CYRENE_SYSTEM_PROMPT, DIARY_INSTRUCTION
from storage import DiaryStorage

from .llm import LocalLLMClient
from .memory import ConversationMemory, DiaryIndexMemory, ProfileMemory
from .messages import ChatMessage
from .pending import PendingAction
from .safety import SAFETY_COVENANT, SafetyGuard
from .tools import DiaryTool
from .tool_router import ToolRouter
from .wiki import ObsidianWiki, extract_tags


class HermesAgent:
    """Coordinates persona, memory, local model, and tools."""

    def __init__(
        self,
        llm: LocalLLMClient,
        storage: DiaryStorage,
        memory: ConversationMemory | None = None,
        profile_memory: ProfileMemory | None = None,
        diary_index: DiaryIndexMemory | None = None,
        tool_router: ToolRouter | None = None,
        safety_guard: SafetyGuard | None = None,
        wiki: ObsidianWiki | None = None,
        embedding_client: Any | None = None,
    ) -> None:
        self.llm = llm
        self.memory = memory or ConversationMemory()
        self.profile_memory = profile_memory or ProfileMemory()
        self.diary_index = diary_index or DiaryIndexMemory()
        self.diary_tool = DiaryTool(storage)
        self.tool_router = tool_router or ToolRouter()
        self.safety_guard = safety_guard or SafetyGuard()
        self.wiki = wiki
        self.embedding_client = embedding_client
        self.pending_diary: str | None = None
        self.pending_action: PendingAction | None = None

    def respond(self, user_input: str) -> str:
        safety = self.safety_guard.evaluate(user_input)
        if safety.blocked:
            self.memory.add_user(user_input)
            self.memory.add_assistant(safety.response)
            return safety.response
        self.memory.add_user(user_input)
        try:
            reply = self.llm.chat(self._system_prompt(), self.memory.as_messages())
        except Exception:
            self.memory.pop_last()
            raise
        self.memory.add_assistant(reply)
        return reply

    def can_write_diary(self) -> bool:
        return self.memory.has_user_messages()

    def reset_session(self) -> None:
        self.memory.clear()
        self.pending_diary = None
        self.pending_action = None

    def write_diary(self) -> tuple[str, str]:
        entry = self.draft_diary()
        return self.save_diary_draft(entry)

    def draft_diary(self) -> str:
        for message in self.memory.as_messages():
            if message.role == "user" and self.safety_guard.evaluate(message.content).blocked:
                self.pending_diary = None
                return (
                    "오늘의 기록을 쓰기 전에 안전을 먼저 챙기고 싶어. "
                    "자해 방법이나 실행 세부사항은 일기에 남기지 않을게. "
                    "지금 당장 위험하다면 주변 사람이나 긴급 도움에 먼저 연결해줘."
                )
        diary_messages = self.memory.as_messages() + [
            ChatMessage(role="user", content=DIARY_INSTRUCTION)
        ]
        entry = self.llm.chat(self._system_prompt(), diary_messages)
        self.pending_diary = entry
        return entry

    def has_diary_draft(self) -> bool:
        return self.pending_diary is not None

    def save_diary_draft(self, entry: str | None = None) -> tuple[str, str]:
        content = entry or self.pending_diary
        if not content:
            raise ValueError("저장할 일기 초안이 없습니다.")
        location = self.diary_tool.save_today(content)
        today = date.today()
        tags, embedding = self._wiki_metadata(content)
        self.diary_index.add_entry(today, location, content, tags=tags, embedding=embedding)
        self._write_wiki_entry(today, tags, embedding, location)
        self.pending_diary = None
        return content, location

    def _wiki_metadata(self, content: str) -> tuple[list[str], list[float] | None]:
        if self.wiki is None:
            return [], None
        tags = extract_tags(self.llm, content)
        embedding: list[float] | None = None
        if self.embedding_client is not None:
            try:
                embedding = self.embedding_client.embed(content)
            except Exception:
                embedding = None
        return tags, embedding

    def _write_wiki_entry(
        self,
        entry_date: date,
        tags: list[str],
        embedding: list[float] | None,
        location: str,
    ) -> None:
        if self.wiki is None:
            return
        related = (
            self.diary_index.find_related(embedding, entry_date.isoformat())
            if embedding
            else []
        )
        summary_entries = self.diary_index.recent_entries(limit=1)
        summary = summary_entries[0].get("summary", "") if summary_entries else ""
        external_link = location if location.startswith("http") else ""
        self.wiki.write_entry(
            entry_date.isoformat(),
            summary=summary,
            tags=tags,
            related_dates=related,
            external_link=external_link,
        )

    def discard_diary_draft(self) -> bool:
        had_draft = self.pending_diary is not None
        self.pending_diary = None
        return had_draft

    def memory_report(self) -> str:
        contexts = [
            self.profile_memory.render_context(),
            self.diary_index.render_context(),
        ]
        report = "\n\n".join(context for context in contexts if context)
        return report or "아직 저장된 장기 기억이 없습니다."

    def set_user_name(self, name: str) -> None:
        self.profile_memory.set_user_name(name)

    def remember_note(self, note: str) -> None:
        self.profile_memory.add_value("notes", note)

    def remember_preference(self, preference: str) -> None:
        self.profile_memory.add_value("preferences", preference)

    def remember_avoidance(self, avoidance: str) -> None:
        self.profile_memory.add_value("avoid", avoidance)

    def recent_diaries(self, limit: int = 3) -> list[dict]:
        return self.diary_index.recent_entries(limit)

    def search_diaries(self, query: str, limit: int = 5) -> list[dict]:
        return self.diary_index.search(query, limit)

    def tool_status(self) -> str:
        return self.tool_router.status_report()

    def search_notion(self, query: str) -> str:
        return self.tool_router.search_notion(query).message

    def read_notion_page(self, page_ref: str) -> str:
        return self.tool_router.read_notion_page(page_ref).message

    def create_notion_todo(self, text: str) -> str:
        return self.tool_router.create_notion_todo(text).message

    def stage_notion_todo(self, text: str) -> str:
        cleaned = text.strip()
        if not cleaned:
            return "추가할 할 일을 입력해주세요."
        self.pending_action = PendingAction(kind="notion_todo", value=cleaned)
        return f"Notion 할 일로 추가할까?\n- {cleaned}\n확인하려면 /확인, 취소하려면 /취소 라고 말해줘."

    def confirm_pending_action(self) -> str:
        if self.pending_action is None:
            return "확인할 작업이 없어."
        action = self.pending_action
        self.pending_action = None
        if action.kind == "notion_todo":
            return self.create_notion_todo(action.value)
        return "지원하지 않는 작업이야."

    def cancel_pending_action(self) -> str:
        if self.pending_action is None:
            return "취소할 작업이 없어."
        self.pending_action = None
        return "대기 중인 작업을 취소했어."

    def _system_prompt(self) -> str:
        contexts = [
            self.profile_memory.render_context(),
            self.diary_index.recent_context(),
        ]
        memory_context = "\n\n".join(context for context in contexts if context)
        if not memory_context:
            return f"{SAFETY_COVENANT}\n\n{CYRENE_SYSTEM_PROMPT}"
        return f"{SAFETY_COVENANT}\n\n{CYRENE_SYSTEM_PROMPT}\n\n{memory_context}"

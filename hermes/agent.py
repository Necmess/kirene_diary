"""Hermes-style orchestrator for the Cyrene diary agent."""

from datetime import date

from persona import CYRENE_SYSTEM_PROMPT, DIARY_INSTRUCTION
from storage import DiaryStorage

from .llm import LocalLLMClient
from .memory import ConversationMemory, DiaryIndexMemory, ProfileMemory
from .messages import ChatMessage
from .safety import SAFETY_COVENANT, SafetyGuard
from .tools import DiaryTool
from .tool_router import ToolRouter


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
    ) -> None:
        self.llm = llm
        self.memory = memory or ConversationMemory()
        self.profile_memory = profile_memory or ProfileMemory()
        self.diary_index = diary_index or DiaryIndexMemory()
        self.diary_tool = DiaryTool(storage)
        self.tool_router = tool_router or ToolRouter()
        self.safety_guard = safety_guard or SafetyGuard()
        self.pending_diary: str | None = None

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

    def write_diary(self) -> tuple[str, str]:
        entry = self.draft_diary()
        return self.save_diary_draft(entry)

    def draft_diary(self) -> str:
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
        self.diary_index.add_entry(date.today(), location, content)
        self.pending_diary = None
        return content, location

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

    def _system_prompt(self) -> str:
        contexts = [
            self.profile_memory.render_context(),
            self.diary_index.recent_context(),
        ]
        memory_context = "\n\n".join(context for context in contexts if context)
        if not memory_context:
            return f"{SAFETY_COVENANT}\n\n{CYRENE_SYSTEM_PROMPT}"
        return f"{SAFETY_COVENANT}\n\n{CYRENE_SYSTEM_PROMPT}\n\n{memory_context}"

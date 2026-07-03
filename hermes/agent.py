"""Hermes-style orchestrator for the Cyrene diary agent."""

from datetime import date

from persona import CYRENE_SYSTEM_PROMPT, DIARY_INSTRUCTION
from storage import DiaryStorage

from .llm import LocalLLMClient
from .memory import ConversationMemory, DiaryIndexMemory, ProfileMemory
from .messages import ChatMessage
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
    ) -> None:
        self.llm = llm
        self.memory = memory or ConversationMemory()
        self.profile_memory = profile_memory or ProfileMemory()
        self.diary_index = diary_index or DiaryIndexMemory()
        self.diary_tool = DiaryTool(storage)
        self.tool_router = tool_router or ToolRouter()

    def respond(self, user_input: str) -> str:
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
        diary_messages = self.memory.as_messages() + [
            ChatMessage(role="user", content=DIARY_INSTRUCTION)
        ]
        entry = self.llm.chat(self._system_prompt(), diary_messages)
        location = self.diary_tool.save_today(entry)
        self.diary_index.add_entry(date.today(), location, entry)
        return entry, location

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

    def _system_prompt(self) -> str:
        contexts = [
            self.profile_memory.render_context(),
            self.diary_index.recent_context(),
        ]
        memory_context = "\n\n".join(context for context in contexts if context)
        if not memory_context:
            return CYRENE_SYSTEM_PROMPT
        return f"{CYRENE_SYSTEM_PROMPT}\n\n{memory_context}"

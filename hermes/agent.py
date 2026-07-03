"""Hermes-style orchestrator for the Cyrene diary agent."""

from persona import CYRENE_SYSTEM_PROMPT, DIARY_INSTRUCTION
from storage import DiaryStorage

from .llm import LocalLLMClient
from .memory import ConversationMemory, DiaryIndexMemory, ProfileMemory
from .messages import ChatMessage
from .tools import DiaryTool


class HermesAgent:
    """Coordinates persona, memory, local model, and tools."""

    def __init__(
        self,
        llm: LocalLLMClient,
        storage: DiaryStorage,
        memory: ConversationMemory | None = None,
        profile_memory: ProfileMemory | None = None,
        diary_index: DiaryIndexMemory | None = None,
    ) -> None:
        self.llm = llm
        self.memory = memory or ConversationMemory()
        self.profile_memory = profile_memory or ProfileMemory()
        self.diary_index = diary_index or DiaryIndexMemory()
        self.diary_tool = DiaryTool(storage)

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
        return entry, location

    def _system_prompt(self) -> str:
        contexts = [
            self.profile_memory.render_context(),
            self.diary_index.recent_context(),
        ]
        memory_context = "\n\n".join(context for context in contexts if context)
        if not memory_context:
            return CYRENE_SYSTEM_PROMPT
        return f"{CYRENE_SYSTEM_PROMPT}\n\n{memory_context}"

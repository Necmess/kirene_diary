"""Hermes-style orchestrator for the Cyrene diary agent."""

from persona import CYRENE_SYSTEM_PROMPT, DIARY_INSTRUCTION
from storage import DiaryStorage

from .llm import LocalLLMClient
from .memory import ConversationMemory
from .messages import ChatMessage
from .tools import DiaryTool


class HermesAgent:
    """Coordinates persona, memory, local model, and tools."""

    def __init__(
        self,
        llm: LocalLLMClient,
        storage: DiaryStorage,
        memory: ConversationMemory | None = None,
    ) -> None:
        self.llm = llm
        self.memory = memory or ConversationMemory()
        self.diary_tool = DiaryTool(storage)

    def respond(self, user_input: str) -> str:
        self.memory.add_user(user_input)
        try:
            reply = self.llm.chat(CYRENE_SYSTEM_PROMPT, self.memory.as_messages())
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
        entry = self.llm.chat(CYRENE_SYSTEM_PROMPT, diary_messages)
        location = self.diary_tool.save_today(entry)
        return entry, location

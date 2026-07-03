"""Conversation memory for the Hermes agent."""

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

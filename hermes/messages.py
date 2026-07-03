"""Message primitives shared across the local agent."""

from dataclasses import dataclass
from typing import Literal

Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class ChatMessage:
    role: Role
    content: str

    def as_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}

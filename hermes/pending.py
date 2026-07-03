"""Pending confirmation actions for commands that write to external tools."""

from dataclasses import dataclass
from typing import Literal

PendingActionKind = Literal["notion_todo"]


@dataclass(frozen=True)
class PendingAction:
    kind: PendingActionKind
    value: str

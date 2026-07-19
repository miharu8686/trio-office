from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

__all__ = [
    "BubbleType",
    "BubbleContent",
    "SpeechContent",
    "TodoStatus",
    "TodoItem",
    "ReviewItemType",
    "ReviewItem",
]


class BubbleType(StrEnum):
    """Type of speech/thought bubble content."""

    THOUGHT = "thought"
    SPEECH = "speech"


class BubbleContent(BaseModel):
    """Content for speech or thought bubbles."""

    type: BubbleType
    text: str
    icon: str | None = None
    persistent: bool = False


class SpeechContent(BaseModel):
    """Speech content for different characters."""

    boss: str | None = None
    agent: str | None = None
    boss_phone: str | None = None


class TodoStatus(StrEnum):
    """Status of a todo list item."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class ReviewItemType(StrEnum):
    """Kind of item waiting on the PO review desk."""

    COMPLETION = "completion"  # Stop — a finished report awaiting review
    PERMISSION = "permission"  # PermissionRequest — blocked on an approval
    INPUT = "input"  # Notification — waiting for user input


class ReviewItem(BaseModel):
    """A document stacked on the PO review desk.

    Represents one thing the agent is waiting on the human for. Created by
    Stop / PermissionRequest / Notification events and cleared by the next
    UserPromptSubmit in the same session (the PO has judged and moved on).
    """

    id: str
    item_type: ReviewItemType
    label: str
    created_at: datetime


class TodoItem(BaseModel):
    """A single item from the TodoWrite tool or task file system."""

    task_id: str = ""
    content: str
    status: TodoStatus
    active_form: str | None = None
    description: str | None = None
    blocks: list[str] = []
    blocked_by: list[str] = []
    owner: str | None = None
    metadata: dict[str, Any] | None = None

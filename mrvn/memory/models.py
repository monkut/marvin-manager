import logging
from enum import StrEnum

from commons.models import TimestampedModel
from django.db import models

logger = logging.getLogger(__name__)

CONTENT_PREVIEW_LENGTH = 50


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class Session(TimestampedModel):
    """A conversation session tied to a chat room."""

    chat_room = models.ForeignKey(
        "channels.ChatRoom",
        on_delete=models.CASCADE,
        related_name="sessions",
    )

    # Session can be linked to a specific contact
    contact = models.ForeignKey(
        "channels.Contact",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions",
    )

    # Agent handling this session
    agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions",
    )

    is_active = models.BooleanField(default=True)

    # Session metadata (context window info, token counts, etc.)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_datetime"]

    def __str__(self) -> str:
        return f"Session {self.pk} - {self.chat_room}"


class Message(TimestampedModel):
    """A single message in a conversation."""

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    role = models.CharField(
        max_length=20,
        choices=[(r.value, r.name.title()) for r in MessageRole],
    )
    content = models.TextField()

    # Platform message ID for deduplication/tracking
    platform_message_id = models.CharField(max_length=255, blank=True)

    # For tool messages
    tool_call_id = models.CharField(max_length=255, blank=True)
    tool_name = models.CharField(max_length=255, blank=True)

    # Token usage tracking
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)

    # Store raw API response/request for debugging
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_datetime"]

    def __str__(self) -> str:
        if len(self.content) > CONTENT_PREVIEW_LENGTH:
            preview = self.content[:CONTENT_PREVIEW_LENGTH] + "..."
        else:
            preview = self.content
        return f"[{self.role}] {preview}"


class ConversationSummary(TimestampedModel):
    """Summarized context from older messages to maintain long-term memory."""

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="summaries",
    )

    summary = models.TextField()
    messages_summarized = models.IntegerField(default=0)

    # Range of messages this summary covers
    first_message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )
    last_message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-created_datetime"]
        verbose_name_plural = "Conversation Summaries"

    def __str__(self) -> str:
        return f"Summary for Session {self.session_id} ({self.messages_summarized} messages)"

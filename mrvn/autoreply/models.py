import logging
from enum import StrEnum

from commons.models import TimestampedModel
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


class RoutingRuleType(StrEnum):
    KEYWORD = "keyword"
    REGEX = "regex"
    CHANNEL = "channel"
    CONTACT = "contact"
    DEFAULT = "default"


class RoutingRule(TimestampedModel):
    """Rules for routing messages to specific agents."""

    name = models.CharField(max_length=100)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="routing_rules",
    )

    rule_type = models.CharField(
        max_length=20,
        choices=[(rt.value, rt.name.title()) for rt in RoutingRuleType],
    )

    # Pattern for keyword/regex rules
    pattern = models.CharField(max_length=500, blank=True)

    # Specific channel/contact for targeted rules
    channel = models.ForeignKey(
        "channels.Channel",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="routing_rules",
    )
    contact = models.ForeignKey(
        "channels.Contact",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="routing_rules",
    )

    # Agent to route to
    agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.CASCADE,
        related_name="routing_rules",
    )

    # Priority for rule evaluation (higher = evaluated first)
    priority = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-priority", "name"]

    def __str__(self) -> str:
        return f"{self.name} -> {self.agent.name}"


class AutoReplyConfig(TimestampedModel):
    """Global auto-reply configuration for a channel."""

    channel = models.OneToOneField(
        "channels.Channel",
        on_delete=models.CASCADE,
        related_name="autoreply_config",
    )

    is_enabled = models.BooleanField(default=True)

    # Delay before responding (to appear more natural)
    min_delay_seconds = models.IntegerField(default=0)
    max_delay_seconds = models.IntegerField(default=2)

    # Typing indicator settings
    show_typing = models.BooleanField(default=True)

    # Rate limiting
    max_messages_per_minute = models.IntegerField(default=10)

    # Default agent for this channel
    default_agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_for_channels",
    )

    class Meta:
        verbose_name = "Auto-Reply Config"
        verbose_name_plural = "Auto-Reply Configs"

    def __str__(self) -> str:
        status = "enabled" if self.is_enabled else "disabled"
        return f"{self.channel.name} auto-reply ({status})"


class MessageFilter(TimestampedModel):
    """Filters to ignore certain messages."""

    name = models.CharField(max_length=100)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="message_filters",
    )

    # Filter pattern (regex)
    pattern = models.CharField(max_length=500)

    # Apply to specific channel or all
    channel = models.ForeignKey(
        "channels.Channel",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="message_filters",
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

import logging
from enum import StrEnum

from commons.models import TimestampedModel
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


class LLMProvider(StrEnum):
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    VLLM = "vllm"


class Agent(TimestampedModel):
    """An AI agent configuration."""

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="agents",
    )

    # LLM Configuration
    provider = models.CharField(
        max_length=20,
        choices=[(p.value, p.name.title()) for p in LLMProvider],
        default=LLMProvider.ANTHROPIC.value,
    )
    model_name = models.CharField(max_length=100, default="claude-sonnet-4-20250514")

    # Base URL for local LLMs (Ollama, vLLM) or custom API endpoints
    base_url = models.URLField(blank=True, help_text="Required for Ollama/vLLM providers")

    # System prompt
    system_prompt = models.TextField(blank=True)

    # Agent behavior settings
    temperature = models.FloatField(default=0.7)
    max_tokens = models.IntegerField(default=4096)

    is_active = models.BooleanField(default=True)

    # Rate limiting to avoid external API throttling
    rate_limit_enabled = models.BooleanField(
        default=False,
        help_text="Enable rate limiting for API calls",
    )
    rate_limit_rpm = models.PositiveIntegerField(
        default=60,
        help_text="Maximum requests per minute (0 = unlimited)",
    )

    # Additional config (stop sequences, etc.)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("owner", "name")]

    def __str__(self) -> str:
        return f"{self.name} ({self.model_name})"


class AgentCredential(TimestampedModel):
    """API credentials for an agent's LLM provider."""

    agent = models.OneToOneField(
        Agent,
        on_delete=models.CASCADE,
        related_name="credential",
    )

    # Encrypted API key
    encrypted_api_key = models.TextField()

    class Meta:
        verbose_name = "Agent Credential"
        verbose_name_plural = "Agent Credentials"


class Tool(TimestampedModel):
    """A tool that an agent can use."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()

    # Tool schema (JSON Schema for parameters)
    input_schema = models.JSONField(default=dict)

    # Python path to the tool implementation
    handler_path = models.CharField(max_length=255)

    is_active = models.BooleanField(default=True)

    # Security: which contexts can use this tool
    allow_in_groups = models.BooleanField(default=False)
    require_approval = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class AgentTool(TimestampedModel):
    """Many-to-many relationship between agents and tools with config."""

    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name="agent_tools",
    )
    tool = models.ForeignKey(
        Tool,
        on_delete=models.CASCADE,
        related_name="agent_tools",
    )

    is_enabled = models.BooleanField(default=True)

    # Tool-specific configuration for this agent
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("agent", "tool")]

    def __str__(self) -> str:
        return f"{self.agent.name} - {self.tool.name}"

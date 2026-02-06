"""Partition management for EmbeddingChunk table.

Uses psqlextra to manage list partitions by agent_id.
Partitions are created automatically when new agents are added.
"""

from typing import TYPE_CHECKING, Any

from psqlextra.backend.schema import PostgresSchemaEditor
from psqlextra.models import PostgresPartitionedModel
from psqlextra.partitioning import PostgresPartitioningManager
from psqlextra.partitioning.config import PostgresPartitioningConfig
from psqlextra.partitioning.partition import PostgresPartition
from psqlextra.partitioning.strategy import PostgresPartitioningStrategy

if TYPE_CHECKING:
    from collections.abc import Generator


class PostgresListPartition(PostgresPartition):
    """A list partition for a PostgreSQL partitioned table."""

    def __init__(self, name: str, values: list) -> None:
        self._name = name
        self.values = values

    def name(self) -> str:
        return self._name

    def deconstruct(self) -> dict:
        return {
            **super().deconstruct(),
            "values": self.values,
        }

    def create(
        self,
        model: type[PostgresPartitionedModel],
        schema_editor: PostgresSchemaEditor,
        comment: str | None = None,
    ) -> None:
        schema_editor.add_list_partition(
            model=model,
            name=self.name(),
            values=self.values,
            comment=comment,
        )

    def delete(
        self,
        model: type[PostgresPartitionedModel],
        schema_editor: PostgresSchemaEditor,
    ) -> None:
        schema_editor.delete_partition(model, self.name())


class AgentListPartitioningStrategy(PostgresPartitioningStrategy):
    """Strategy for creating list partitions per agent."""

    def to_create(self) -> Generator[PostgresPartition]:
        """Generate partitions to create for each agent."""
        from agents.models import Agent  # noqa: PLC0415

        for agent_id in Agent.objects.values_list("id", flat=True):
            yield PostgresListPartition(
                name=f"agent_{agent_id}",
                values=[agent_id],
            )

    def to_delete(self) -> Generator[PostgresPartition]:
        """Generate partitions to delete (none by default)."""
        # We don't auto-delete partitions - they should be manually removed
        # when an agent is deleted if desired
        return
        yield  # noqa: RET502 - makes this a generator


def get_partitioning_manager() -> PostgresPartitioningManager:
    """Create the partitioning manager for EmbeddingChunk.

    Returns:
        Configured PostgresPartitioningManager instance.
    """
    from memory.models import EmbeddingChunk  # noqa: PLC0415

    return PostgresPartitioningManager(
        configs=[
            PostgresPartitioningConfig(
                model=EmbeddingChunk,
                strategy=AgentListPartitioningStrategy(),
            ),
        ]
    )


class LazyPartitioningManager:
    """Lazy wrapper for PostgresPartitioningManager.

    Delays initialization until first access to avoid import-time DB queries.
    """

    _instance: PostgresPartitioningManager | None = None

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to the actual manager."""
        if self._instance is None:
            self._instance = get_partitioning_manager()
        return getattr(self._instance, name)


# For settings.PSQLEXTRA_PARTITIONING_MANAGER
manager = LazyPartitioningManager()

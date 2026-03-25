"""Domain models for agent runtime."""
from dataclasses import dataclass


@dataclass
class ToolCall:
    """Represents a tool call emitted by the model."""

    id: str
    name: str
    arguments: dict

"""Base Tool class."""
from abc import ABC, abstractmethod


class Tool(ABC):
    """Base class for all tools."""

    name: str = ""
    description: str = ""
    parameters: dict = {}

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Execute the tool with given arguments."""
        pass
"""Base Tool class."""
from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """Base class for all tools."""

    name: str = ""
    description: str = ""
    parameters: dict = {}

    @abstractmethod
    def execute(self, **kwargs: Any) -> str:
        """Execute the tool with given arguments."""
        raise NotImplementedError

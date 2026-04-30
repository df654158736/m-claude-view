"""Base Tool class with auto-discovery registry."""
from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """Base class for all tools.

    Subclasses with a non-empty ``name`` are automatically registered
    and can be looked up via ``Tool.get_class(name)``.
    """

    name: str = ""
    description: str = ""
    parameters: dict = {}

    _registry: dict[str, type["Tool"]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls.name:
            Tool._registry[cls.name] = cls

    @classmethod
    def get_class(cls, name: str) -> type["Tool"] | None:
        return cls._registry.get(name)

    @classmethod
    def registered_names(cls) -> list[str]:
        return list(cls._registry.keys())

    @abstractmethod
    def execute(self, **kwargs: Any) -> str:
        """Execute the tool with given arguments."""
        raise NotImplementedError

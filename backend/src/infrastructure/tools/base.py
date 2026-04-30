"""Base Tool class with Pydantic schema generation and auto-discovery."""
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class Tool(ABC):
    """Base class for all tools.

    Subclasses define an ``Input`` inner class (Pydantic BaseModel) to
    declare parameters.  The JSON Schema for the LLM is generated
    automatically — no hand-written ``parameters`` dict needed.

    Subclasses with a non-empty ``name`` are auto-registered and can be
    looked up via ``Tool.get_class(name)``.

    Example::

        class MyTool(Tool):
            name = "my_tool"
            description = "Does something useful"

            class Input(BaseModel):
                query: str = Field(description="Search query")
                limit: int = Field(default=10, description="Max results")

            def execute(self, args: Input) -> str:
                return f"Found {args.limit} results for {args.query}"
    """

    name: str = ""
    description: str = ""
    Input: type[BaseModel] | None = None

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

    @property
    def parameters(self) -> dict:
        """Generate OpenAI-compatible JSON Schema from the Input model."""
        if self.Input is None:
            return {"type": "object", "properties": {}}
        schema = self.Input.model_json_schema()
        schema.pop("title", None)
        schema.pop("$defs", None)
        return schema

    @abstractmethod
    def execute(self, args: Any) -> str:
        raise NotImplementedError

    def parse_args(self, raw: dict) -> Any:
        """Validate and parse raw arguments dict into an Input instance."""
        if self.Input is None:
            return raw
        return self.Input.model_validate(raw)

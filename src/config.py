"""Configuration loading module."""
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMConfig:
    api_key: str
    base_url: str
    model: str
    max_iterations: int = 20
    temperature: float = 0.7


@dataclass
class DisplayConfig:
    thinking_collapsed: bool = True
    log_level: str = "verbose"


@dataclass
class ToolConfig:
    name: str
    enabled: bool = True
    timeout: int = 30
    command: Optional[str] = None
    args: Optional[list] = None


@dataclass
class MCPServerConfig:
    command: str
    args: list = None
    env: dict = None


@dataclass
class Config:
    llm: LLMConfig
    display: DisplayConfig
    tools: list[ToolConfig]
    mcp: dict


def load_config(config_path: str = "config.yaml") -> Config:
    """Load configuration from YAML file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    return Config(
        llm=LLMConfig(**data.get("llm", {})),
        display=DisplayConfig(**data.get("display", {})),
        tools=[ToolConfig(**t) for t in data.get("tools", [])],
        mcp=data.get("mcp", {}).get("servers", {})
    )
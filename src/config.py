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
    args: Optional[list] = None
    env: Optional[dict] = None


@dataclass
class Config:
    llm: LLMConfig
    display: DisplayConfig
    tools: list[ToolConfig]
    mcp: dict


def load_config(config_path: str = "config.yaml") -> Config:
    """Load configuration from YAML file."""
    import os

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    # Validate and get API key (support env var fallback)
    llm_data = data.get("llm", {})
    api_key = llm_data.get("api_key") or os.environ.get("LLM_API_KEY")
    if not api_key:
        raise ValueError("api_key is required in config.llm or LLM_API_KEY environment variable")

    # Remove api_key from llm_data to avoid duplication
    llm_config_data = {k: v for k, v in llm_data.items() if k != "api_key"}

    return Config(
        llm=LLMConfig(api_key=api_key, **llm_config_data),
        display=DisplayConfig(**data.get("display", {})),
        tools=[ToolConfig(**t) for t in data.get("tools", [])],
        mcp=data.get("mcp", {}).get("servers", {})
    )
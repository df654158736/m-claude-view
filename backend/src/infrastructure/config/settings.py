"""Configuration loading module."""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


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
    packet_log_mode: str = "json"
    color_logs: bool = True
    json_pretty: bool = False
    json_indent: int = 2
    packet_log_file: str = "logs/packets.jsonl"


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

    with open(path, encoding="utf-8") as file:
        data = yaml.safe_load(file)

    llm_data = data.get("llm", {})

    def _get_env_or_cfg(env_key: str, cfg_key: str):
        env_val = os.environ.get(env_key)
        if env_val is not None and str(env_val).strip() != "":
            return env_val
        cfg_val = llm_data.get(cfg_key)
        if cfg_val is None or str(cfg_val).strip() == "":
            return None
        return cfg_val

    api_key = _get_env_or_cfg("LLM_API_KEY", "api_key")
    if not api_key:
        raise ValueError("api_key is required in config.llm or LLM_API_KEY environment variable")
    base_url = _get_env_or_cfg("LLM_BASE_URL", "base_url")
    model = _get_env_or_cfg("LLM_MODEL", "model")
    if not base_url:
        raise ValueError("base_url is required in config.llm or LLM_BASE_URL environment variable")
    if not model:
        raise ValueError("model is required in config.llm or LLM_MODEL environment variable")

    raw_max_iterations = _get_env_or_cfg("LLM_MAX_ITERATIONS", "max_iterations")
    raw_temperature = _get_env_or_cfg("LLM_TEMPERATURE", "temperature")
    try:
        max_iterations = int(raw_max_iterations) if raw_max_iterations is not None else 20
    except (TypeError, ValueError) as err:
        raise ValueError("LLM_MAX_ITERATIONS/max_iterations must be an integer") from err
    try:
        temperature = float(raw_temperature) if raw_temperature is not None else 0.7
    except (TypeError, ValueError) as err:
        raise ValueError("LLM_TEMPERATURE/temperature must be a number") from err

    return Config(
        llm=LLMConfig(
            api_key=api_key,
            base_url=base_url,
            model=model,
            max_iterations=max_iterations,
            temperature=temperature,
        ),
        display=DisplayConfig(**data.get("display", {})),
        tools=[ToolConfig(**tool) for tool in data.get("tools", [])],
        mcp=data.get("mcp", {}).get("servers", {}),
    )

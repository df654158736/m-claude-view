"""Dependency wiring for CLI and HTTP interfaces."""
from src.application.services.agent_task_service import AgentTaskService
from src.domain.agent.engine import ReActEngine
from src.infrastructure.config.settings import load_config
from src.infrastructure.llm.openai_client import LLMClient
from src.infrastructure.tools.factory import setup_tools


def load_settings(config_path: str):
    """Load app settings from yaml/env."""
    return load_config(config_path)


def build_engine(config):
    """Assemble domain engine and infrastructure adapters."""
    llm_client = LLMClient(config.llm)
    tool_registry = setup_tools(config)
    return ReActEngine(llm_client, tool_registry, config)


def build_agent_service(config):
    """Assemble async task service for HTTP entrypoints."""
    engine = build_engine(config)
    return AgentTaskService(engine=engine)

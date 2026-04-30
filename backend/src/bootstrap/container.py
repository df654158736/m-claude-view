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


def print_startup_report(config, engine, *, log_path=None, host=None, port=None) -> None:
    """Print a structured startup report to stdout."""
    sep = "=" * 60
    print(sep)
    print("  MClaude ReAct Agent")
    print(sep)
    print()

    # LLM
    print("[LLM]")
    print(f"  Model:          {config.llm.model}")
    print(f"  Base URL:       {config.llm.base_url}")
    print(f"  Max iterations: {config.llm.max_iterations}")
    print(f"  Temperature:    {config.llm.temperature}")
    print()

    # Tools
    tools = engine.tool_registry.summary()
    active_tools = [t for t in tools if "name" in t]
    print(f"[Tools] {len(active_tools)} registered")
    for t in active_tools:
        req = ", ".join(t["required"]) if t.get("required") else "-"
        all_params = ", ".join(t["params"]) if t.get("params") else "-"
        print(f"  - {t['name']:20s} [{t['type']}]")
        print(f"    {t['description'][:60]}")
        print(f"    params: {all_params}  required: {req}")

    # Deferred MCP tools
    catalog = engine.tool_registry.get_mcp_catalog()
    if catalog:
        print(f"\n[MCP Deferred] {len(catalog)} tools available via load_mcp_tools")
        by_server: dict[str, list[str]] = {}
        for entry in catalog:
            by_server.setdefault(entry["server"], []).append(entry["name"])
        for server, names in by_server.items():
            print(f"  {server}: {len(names)} tools")
            for name in names[:5]:
                print(f"    - {name}")
            if len(names) > 5:
                print(f"    ... and {len(names) - 5} more")
    print()

    # Display / Log
    print("[Display]")
    print(f"  Log mode:       {config.display.packet_log_mode}")
    if log_path:
        print(f"  Log file:       {log_path}")
    print()

    # Server (HTTP only)
    if host and port:
        print(f"[Server]")
        print(f"  Listening:      http://{host}:{port}")
        print(f"  API endpoint:   POST /api/ask")
    print(sep)

"""CLI entry point for ReAct Agent."""
import sys
import logging
from src.config import load_config
from src.llm_client import LLMClient
from src.tools.registry import ToolRegistry
from src.tools.bash import BashTool
from src.react_engine import ReActEngine


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("react_agent")


def setup_tools(config):
    """Setup tool registry with configured tools."""
    registry = ToolRegistry()

    for tool_config in config.tools:
        if not tool_config.enabled:
            continue

        if tool_config.name == "bash":
            registry.register(BashTool())
            logger.info("Registered bash tool")
        else:
            logger.warning(f"Unknown tool: {tool_config.name}")

    return registry


def main():
    """Main CLI entry point."""
    print("=" * 60)
    print("ReAct Agent - 自主思考与工具调用")
    print("=" * 60)
    print()

    # Load config
    try:
        config = load_config("config.yaml")
        print(f"✓ 配置加载成功")
        print(f"  Model: {config.llm.model}")
        print(f"  Max iterations: {config.llm.max_iterations}")
    except Exception as e:
        print(f"✗ 配置加载失败: {e}")
        sys.exit(1)

    # Setup components
    llm_client = LLMClient(config.llm)
    tool_registry = setup_tools(config)
    engine = ReActEngine(llm_client, tool_registry, config)

    print(f"✓ 工具注册完成: {list(tool_registry._tools.keys())}")
    print()
    print("输入任务开始执行，输入 'exit' 或 'quit' 退出")
    print("-" * 60)

    # REPL loop
    while True:
        try:
            task = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n退出")
            break

        if not task:
            continue

        if task.lower() in ("exit", "quit", "q"):
            print("再见!")
            break

        print()
        print("=" * 60)
        print("开始执行任务...")
        print("=" * 60)

        try:
            result = engine.run(task)
        except KeyboardInterrupt:
            print("\n任务被中断")
            continue
        except Exception as e:
            print(f"\n✗ 任务执行失败: {e}")
            logger.exception("Task execution failed")
            continue

        print()
        print("=" * 60)
        print("最终结果:")
        print("=" * 60)
        print(result)


if __name__ == "__main__":
    main()

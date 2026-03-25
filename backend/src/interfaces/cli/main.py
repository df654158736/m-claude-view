"""CLI entry point for ReAct Agent."""
import logging
import sys

from src.bootstrap.container import build_engine, load_settings


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("react_agent")


def main():
    """Main CLI entry point."""
    print("=" * 60)
    print("ReAct Agent - 自主思考与工具调用")
    print("=" * 60)
    print()

    try:
        config = load_settings("config.yaml")
        print("✓ 配置加载成功")
        print(f"  Model: {config.llm.model}")
        print(f"  Max iterations: {config.llm.max_iterations}")
    except Exception as err:  # noqa: BLE001
        print(f"✗ 配置加载失败: {err}")
        sys.exit(1)

    engine = build_engine(config)

    print(f"✓ 工具注册完成: {list(engine.tool_registry._tools.keys())}")
    print()
    print("输入任务开始执行，输入 'exit' 或 'quit' 退出")
    print("-" * 60)

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
        except Exception as err:  # noqa: BLE001
            print(f"\n✗ 任务执行失败: {err}")
            logger.exception("Task execution failed")
            continue

        print()
        print("=" * 60)
        print("最终结果:")
        print("=" * 60)
        print(result)


if __name__ == "__main__":
    main()

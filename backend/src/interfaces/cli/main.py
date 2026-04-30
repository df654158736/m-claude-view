"""CLI entry point for ReAct Agent."""
import logging
import sys

from src.bootstrap.container import build_engine, load_settings, print_startup_report


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("react_agent")


def main():
    """Main CLI entry point."""
    try:
        config = load_settings("config.yaml")
    except Exception as err:  # noqa: BLE001
        print(f"Config load failed: {err}")
        sys.exit(1)

    engine = build_engine(config)
    print_startup_report(config, engine)

    print("Enter a task to execute, type 'exit' or 'quit' to quit")
    print("-" * 60)

    while True:
        try:
            task = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye")
            break

        if not task:
            continue

        if task.lower() in ("exit", "quit", "q"):
            print("Bye!")
            break

        print()
        print("=" * 60)
        print("Running task...")
        print("=" * 60)

        try:
            result = engine.run(task)
        except KeyboardInterrupt:
            print("\nTask interrupted")
            continue
        except Exception as err:  # noqa: BLE001
            print(f"\nTask failed: {err}")
            logger.exception("Task execution failed")
            continue

        print()
        print("=" * 60)
        print("Result:")
        print("=" * 60)
        print(result)


if __name__ == "__main__":
    main()

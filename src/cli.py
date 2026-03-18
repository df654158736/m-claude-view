"""CLI entry point."""
from src.config import load_config


def main():
    config = load_config()
    print("ReAct Agent initialized")
    print(f"Model: {config.llm.model}")


if __name__ == "__main__":
    main()
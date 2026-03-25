"""Run-agent use case."""


def run_agent(engine, task: str) -> str:
    """Execute one end-to-end task through the domain engine."""
    return engine.run(task)

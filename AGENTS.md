# Repository Guidelines

## Project Structure & Module Organization
- `src/` contains runtime code for the ReAct agent:
  - `src/cli.py` is the interactive entry point.
  - `src/react_engine.py` runs the reasoning/tool loop.
  - `src/llm_client.py` wraps chat completion calls.
  - `src/tools/` holds tool interfaces and implementations (`base.py`, `registry.py`, `bash.py`).
- `tests/` contains pytest suites (`test_*.py`) covering core modules and tool behavior.
- `config.yaml` stores local runtime config; `requirements.txt` lists minimal dependencies.
- `docs/plans/` keeps design/implementation plans and should remain documentation-only.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate` creates/activates local env.
- `pip install -r requirements.txt` installs runtime deps (`openai`, `pyyaml`).
- `pytest -q` runs all tests.
- `pytest tests/test_react_engine.py -v` runs a focused test file while iterating.
- `python -m src.cli` starts the interactive REPL agent from repo root.

## Coding Style & Naming Conventions
- Follow existing Python style: 4-space indentation, clear docstrings, and type hints where useful.
- Use `snake_case` for functions/variables, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for constants.
- Keep modules focused by responsibility (engine vs. client vs. tools).
- Prefer small, testable methods; add logging for operationally important paths (see `react_engine.py`).

## Testing Guidelines
- Framework: `pytest` with standard assertions and `unittest.mock` for external dependencies.
- Add tests alongside code changes in `tests/test_<module>.py`.
- Name tests by behavior, e.g., `test_tool_registry_execute`.
- Cover success and failure paths, especially around tool execution and API error handling.

## Commit & Pull Request Guidelines
- Commit format in history follows Conventional Commit prefixes: `feat:`, `fix:`, `chore:`.
- Keep commit messages imperative and scoped (e.g., `fix: handle tool execution exceptions`).
- PRs should include:
  - a short problem/solution summary,
  - linked issue (if available),
  - test evidence (`pytest` command/results),
  - config or behavior changes called out explicitly.

## Security & Configuration Tips
- Do not commit real API keys in `config.yaml`.
- Prefer environment variable fallback: `LLM_API_KEY` (supported by `src/config.py`).
- Treat tool command execution paths carefully; validate new tools before enabling by default.

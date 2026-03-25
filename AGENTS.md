# Repository Guidelines

## Project Structure & Module Organization
- `backend/src/` contains runtime code for the ReAct agent:
  - `backend/src/cli.py` is the interactive entry point.
  - `backend/src/react_engine.py` runs the reasoning/tool loop.
  - `backend/src/llm_client.py` wraps chat completion calls.
  - `backend/src/tools/` holds tool interfaces and implementations (`base.py`, `registry.py`, `bash.py`).
- `backend/tests/` contains pytest suites (`test_*.py`) covering core modules and tool behavior.
- `backend/config.yaml` stores runtime config; `backend/requirements.txt` lists dependencies.
- `frontend/` stores static dashboard assets (`index.html`, `app.css`, `app.js`).
- `docs/` keeps design and integration documentation (for example MCP integration notes).

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate` creates/activates local env.
- `pip install -r backend/requirements.txt` installs runtime deps (`openai`, `pyyaml`).
- `PYTHONPATH=backend pytest -q backend/tests` runs all tests.
- `PYTHONPATH=backend pytest -q backend/tests/test_react_engine.py -v` runs a focused suite.
- `PYTHONPATH=backend python -m src.cli` starts the interactive REPL.
- `./start.sh` starts web mode and serves frontend from `frontend/`.

## Coding Style & Naming Conventions
- Follow existing Python style: 4-space indentation, clear docstrings, and type hints where useful.
- Use `snake_case` for functions/variables, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for constants.
- Keep modules focused by responsibility (engine vs. client vs. tools).
- Prefer small, testable methods; add logging for operationally important paths (see `react_engine.py`).

## Testing Guidelines
- Framework: `pytest` with standard assertions and `unittest.mock` for external dependencies.
- Add tests alongside code changes in `backend/tests/test_<module>.py`.
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
- Prefer environment variable fallback: `LLM_API_KEY` (supported by `backend/src/config.py`).
- Treat tool command execution paths carefully; validate new tools before enabling by default.

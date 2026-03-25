"""FastAPI server for model interaction dashboard."""
from __future__ import annotations

import argparse
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.bootstrap.container import build_agent_service, load_settings
from src.infrastructure.storage.packet_log_repo import build_runs, clear_packet_log, group_packets_by_user, read_packets


REPO_ROOT = Path(__file__).resolve().parents[4]
FRONTEND_DIR = REPO_ROOT / "frontend"


def create_app(log_path: Path, agent_service) -> FastAPI:
    app = FastAPI(title="Agent Trace Dashboard", version="2.0.0")

    if FRONTEND_DIR.exists():
        app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    def index() -> FileResponse:
        index_path = FRONTEND_DIR / "index.html"
        if not index_path.exists():
            raise HTTPException(status_code=500, detail="frontend/index.html not found")
        return FileResponse(index_path)

    @app.get("/api/packets")
    def api_packets(limit: int = Query(default=400, ge=1, le=5000)) -> JSONResponse:
        packets = read_packets(log_path, limit=limit)
        return JSONResponse({"log_path": str(log_path), "packets": packets}, headers={"Cache-Control": "no-store"})

    @app.get("/api/groups")
    def api_groups(
        limit: int = Query(default=400, ge=1, le=5000),
        merge_same_question: bool = Query(default=True),
    ) -> JSONResponse:
        packets = read_packets(log_path, limit=limit)
        groups = group_packets_by_user(packets, merge_same_question=merge_same_question)
        return JSONResponse({"log_path": str(log_path), "groups": groups}, headers={"Cache-Control": "no-store"})

    @app.get("/api/runs")
    def api_runs(limit: int = Query(default=400, ge=1, le=5000)) -> JSONResponse:
        packets = read_packets(log_path, limit=limit)
        runs = build_runs(packets)
        return JSONResponse({"log_path": str(log_path), "runs": runs}, headers={"Cache-Control": "no-store"})

    @app.get("/api/tasks/{task_id}")
    def api_task(task_id: str) -> JSONResponse:
        task = agent_service.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return JSONResponse(task, headers={"Cache-Control": "no-store"})

    @app.post("/api/ask")
    def api_ask(payload: dict = Body(default_factory=dict)) -> JSONResponse:
        question = str(payload.get("question", "")).strip()
        if not question:
            raise HTTPException(status_code=400, detail="question is required")
        task_id = agent_service.submit(question)
        return JSONResponse({"ok": True, "task_id": task_id}, headers={"Cache-Control": "no-store"})

    @app.post("/api/clear")
    def api_clear() -> JSONResponse:
        clear_packet_log(log_path)
        agent_service.clear()
        return JSONResponse({"ok": True, "log_path": str(log_path)}, headers={"Cache-Control": "no-store"})

    return app


def build_handler(log_path: Path, agent_service) -> FastAPI:
    """Compatibility alias for old imports expecting build_handler."""
    return create_app(log_path, agent_service)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run FastAPI interaction dashboard server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--log-file", default=None)
    parser.add_argument("--config", default="backend/config.yaml")
    args = parser.parse_args()

    config = load_settings(args.config)
    log_path = Path(args.log_file) if args.log_file else Path(config.display.packet_log_file)
    agent_service = build_agent_service(config)
    app = create_app(log_path, agent_service)

    print(f"FastAPI dashboard running on http://{args.host}:{args.port}")
    print(f"Reading packet log file: {log_path}")
    print("Agent API ready: POST /api/ask")

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()

"""Application service for asynchronous agent task execution."""
from __future__ import annotations

import threading
import time
import uuid


class AgentTaskService:
    """Async task wrapper around a synchronous agent engine."""

    def __init__(self, engine, max_tasks: int = 200):
        self.engine = engine
        self.max_tasks = max_tasks
        self.tasks: dict[str, dict] = {}
        self._tasks_lock = threading.Lock()
        self._engine_lock = threading.Lock()

    def submit(self, question: str) -> str:
        task_id = uuid.uuid4().hex
        now = time.time()
        task = {
            "id": task_id,
            "question": question,
            "status": "queued",
            "result": None,
            "error": None,
            "created_at": now,
            "updated_at": now,
        }
        with self._tasks_lock:
            self.tasks[task_id] = task
            self._prune_locked()

        thread = threading.Thread(target=self._run, args=(task_id,), daemon=True)
        thread.start()
        return task_id

    def _run(self, task_id: str) -> None:
        with self._tasks_lock:
            task = self.tasks.get(task_id)
            if not task:
                return
            task["status"] = "running"
            task["updated_at"] = time.time()
            question = task["question"]

        try:
            with self._engine_lock:
                result = self.engine.run(question)
            with self._tasks_lock:
                task = self.tasks.get(task_id)
                if task:
                    task["status"] = "done"
                    task["result"] = result
                    task["updated_at"] = time.time()
        except Exception as exc:  # noqa: BLE001
            with self._tasks_lock:
                task = self.tasks.get(task_id)
                if task:
                    task["status"] = "error"
                    task["error"] = str(exc)
                    task["updated_at"] = time.time()

    def get(self, task_id: str) -> dict | None:
        with self._tasks_lock:
            task = self.tasks.get(task_id)
            if not task:
                return None
            return dict(task)

    def clear(self) -> None:
        with self._tasks_lock:
            self.tasks.clear()
        with self._engine_lock:
            reset_session = getattr(self.engine, "reset_session", None)
            if callable(reset_session):
                reset_session()

    def _prune_locked(self) -> None:
        if len(self.tasks) <= self.max_tasks:
            return

        removable = sorted(self.tasks.values(), key=lambda item: item.get("updated_at", 0.0))
        for task in removable[: len(self.tasks) - self.max_tasks]:
            self.tasks.pop(task["id"], None)

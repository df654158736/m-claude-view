"""Packet logging utilities for ReAct engine."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


class PacketLogger:
    """统一管理观测包日志的配置、格式化与持久化。

    该组件负责：
    1. 根据配置决定输出模式（json/readable/both）；
    2. 负责 JSON 紧凑/美化序列化；
    3. 负责可读日志渲染（含颜色）；
    4. 负责 JSONL 落盘。

    这样 Engine 可以只关注执行流程，不被日志细节干扰。
    """

    def __init__(
        self,
        logger,
        packet_log_mode: str = "json",
        color_logs: bool = False,
        json_pretty: bool = False,
        json_indent: int = 2,
        packet_log_file: Optional[Path] = None,
    ):
        self.logger = logger
        self.packet_log_mode = packet_log_mode
        self.color_logs = color_logs
        self.json_pretty = json_pretty
        self.json_indent = json_indent
        self.packet_log_file = packet_log_file

    @classmethod
    def from_config(cls, config, logger) -> "PacketLogger":
        """从配置对象构建 PacketLogger。

        兼容策略：
        - 优先读取 display.*；
        - 若 display 未配置则回退到顶层同名字段；
        - 最后使用默认值，避免因配置缺失导致引擎不可运行。
        """
        display_config = getattr(config, "display", None)
        mode = cls._pick_str(
            getattr(display_config, "packet_log_mode", None),
            getattr(config, "packet_log_mode", None),
            "json",
        )
        color_logs = cls._pick_bool(
            getattr(display_config, "color_logs", None),
            getattr(config, "color_logs", None),
            False,
        )
        json_pretty = cls._pick_bool(
            getattr(display_config, "json_pretty", None),
            getattr(config, "json_pretty", None),
            False,
        )
        json_indent = cls._pick_int(
            getattr(display_config, "json_indent", None),
            getattr(config, "json_indent", None),
            2,
        )
        packet_log_file = cls._pick_path(
            getattr(display_config, "packet_log_file", None),
            getattr(config, "packet_log_file", None),
        )
        return cls(
            logger=logger,
            packet_log_mode=mode,
            color_logs=color_logs,
            json_pretty=json_pretty,
            json_indent=json_indent,
            packet_log_file=packet_log_file,
        )

    def log(self, packet_type: str, iteration: int, **payload) -> None:
        """输出一条结构化观测包。

        输出顺序固定为：
        1. 可选落盘（JSONL）；
        2. 控制台 JSON 输出（如果启用）；
        3. 控制台可读输出（如果启用）。
        """
        packet = {"type": packet_type, "iteration": iteration, **payload}
        self._write_packet_file(packet)
        if self.packet_log_mode in ("json", "both"):
            self.logger.info(self._format_json_packet(packet))
        if self.packet_log_mode in ("readable", "both"):
            self.logger.info(self._format_readable_packet(packet_type, iteration, payload))

    def _format_json_packet(self, packet: dict) -> str:
        if self.json_pretty:
            return json.dumps(packet, ensure_ascii=False, default=str, indent=self.json_indent)
        return json.dumps(packet, ensure_ascii=False, default=str, separators=(",", ":"))

    def _write_packet_file(self, packet: dict) -> None:
        """将观测包追加写入 JSONL 文件。"""
        if not self.packet_log_file:
            return
        try:
            self.packet_log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.packet_log_file, "a", encoding="utf-8") as file:
                file.write(json.dumps(packet, ensure_ascii=False, default=str, separators=(",", ":")))
                file.write("\n")
        except OSError as err:
            self.logger.warning("Failed to write packet log file: %s", err)

    @staticmethod
    def _truncate(value, limit: int = 240) -> str:
        text = str(value)
        return text if len(text) <= limit else text[:limit] + "...(truncated)"

    def _format_readable_packet(self, packet_type: str, iteration: int, payload: dict) -> str:
        """渲染人类可读日志，便于终端快速排障。"""
        if packet_type == "user":
            line = f"[USER][iter={iteration}] {self._truncate(payload.get('content', ''))}"
            return self._with_color("user", line)
        if packet_type == "llm_request":
            msg_count = len(payload.get("messages", []))
            tool_count = len(payload.get("tools", []))
            line = f"[TO_LLM][iter={iteration}] messages={msg_count} tools={tool_count}"
            return self._with_color("llm_request", line)
        if packet_type == "llm_response":
            content = payload.get("content")
            tool_calls = payload.get("tool_calls", [])
            if tool_calls:
                names = ",".join(tc.get("name", "unknown") for tc in tool_calls)
                line = f"[FROM_LLM][iter={iteration}] tool_calls={len(tool_calls)} names={names}"
                return self._with_color("llm_response", line)
            line = f"[FROM_LLM][iter={iteration}] content={self._truncate(content)}"
            return self._with_color("llm_response", line)
        if packet_type == "tool":
            tool_name = payload.get("tool_name", "unknown")
            result = self._truncate(payload.get("result", ""))
            line = f"[TOOL][iter={iteration}][{tool_name}] result={result}"
            return self._with_color("tool", line)
        if packet_type == "agent":
            if "tool_calls" in payload:
                line = f"[AGENT][iter={iteration}] planned_tool_calls={len(payload['tool_calls'])}"
                return self._with_color("agent", line)
            line = f"[AGENT][iter={iteration}] content={self._truncate(payload.get('content', ''))}"
            return self._with_color("agent", line)
        line = f"[{packet_type.upper()}][iter={iteration}] {self._truncate(payload)}"
        return self._with_color(packet_type, line)

    def _with_color(self, packet_type: str, line: str) -> str:
        """按事件类型上色，可关闭。"""
        if not self.color_logs:
            return line
        color_map = {
            "user": "\033[36m",
            "llm_request": "\033[34m",
            "llm_response": "\033[32m",
            "agent": "\033[35m",
            "tool": "\033[33m",
        }
        color = color_map.get(packet_type, "\033[37m")
        return f"{color}{line}\033[0m"

    @staticmethod
    def _pick_str(primary, fallback, default: str) -> str:
        if isinstance(primary, str) and primary:
            return primary
        if isinstance(fallback, str) and fallback:
            return fallback
        return default

    @staticmethod
    def _pick_bool(primary, fallback, default: bool) -> bool:
        if isinstance(primary, bool):
            return primary
        if isinstance(fallback, bool):
            return fallback
        return default

    @staticmethod
    def _pick_int(primary, fallback, default: int) -> int:
        if isinstance(primary, int):
            return primary
        if isinstance(fallback, int):
            return fallback
        return default

    @staticmethod
    def _pick_path(primary, fallback) -> Optional[Path]:
        raw = None
        if isinstance(primary, str) and primary.strip():
            raw = primary.strip()
        elif isinstance(fallback, str) and fallback.strip():
            raw = fallback.strip()
        return Path(raw) if raw else None

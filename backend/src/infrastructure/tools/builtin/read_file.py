"""Read file tool with PDF and text support."""
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from src.infrastructure.tools.base import Tool


class ReadFileTool(Tool):
    """Read file contents with support for plain text and PDF."""

    name = "read_file"
    description = "读取文件内容，支持纯文本文件（txt/md/csv/json/yaml 等）和 PDF 文件"

    class Input(BaseModel):
        path: str = Field(description="文件的绝对路径或相对路径")
        max_chars: int = Field(default=50000, description="最大返回字符数，默认 50000")
        pages: Optional[str] = Field(default=None, description="PDF 页码范围，例如 '1-5' 或 '3'，默认读取全部")

    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

    def execute(self, args: Input) -> str:
        file_path = Path(args.path).expanduser().resolve()

        if not file_path.exists():
            return f"Error: file not found: {file_path}"
        if not file_path.is_file():
            return f"Error: not a file: {file_path}"
        if file_path.stat().st_size > self.MAX_FILE_SIZE:
            return f"Error: file too large ({file_path.stat().st_size} bytes, max {self.MAX_FILE_SIZE})"

        if file_path.suffix.lower() == ".pdf":
            return self._read_pdf(file_path, args.max_chars, args.pages)
        return self._read_text(file_path, args.max_chars)

    def _read_text(self, file_path: Path, max_chars: int) -> str:
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except (OSError, ValueError) as err:
            return f"Error reading file: {err}"

        if len(text) > max_chars:
            return text[:max_chars] + f"\n\n...(truncated, total {len(text)} chars)"
        return text

    def _read_pdf(self, file_path: Path, max_chars: int, pages: str | None) -> str:
        try:
            import fitz  # pymupdf
        except ImportError:
            return "Error: pymupdf is not installed, cannot read PDF"

        try:
            doc = fitz.open(str(file_path))
        except Exception as err:
            return f"Error opening PDF: {err}"

        page_range = self._parse_page_range(pages, len(doc))

        parts: list[str] = []
        total_chars = 0
        for page_num in page_range:
            page = doc[page_num]
            text = page.get_text()
            header = f"--- Page {page_num + 1}/{len(doc)} ---\n"
            parts.append(header + text)
            total_chars += len(header) + len(text)
            if total_chars >= max_chars:
                break

        doc.close()

        result = "\n".join(parts)
        if len(result) > max_chars:
            result = result[:max_chars] + f"\n\n...(truncated, total {len(result)} chars)"
        return result

    @staticmethod
    def _parse_page_range(pages: str | None, total: int) -> range:
        if not pages:
            return range(total)
        pages = pages.strip()
        if "-" in pages:
            start_str, end_str = pages.split("-", 1)
            start = max(0, int(start_str) - 1)
            end = min(total, int(end_str))
            return range(start, end)
        single = int(pages) - 1
        if 0 <= single < total:
            return range(single, single + 1)
        return range(0)

"""
File I/O tools for BioAgent.

Provides read and write operations.
"""

from pathlib import Path
from typing import Optional

from bioagent.tools.base import tool


@tool(domain="files")
async def read_file(
    path: str,
    max_lines: Optional[int] = None
) -> dict:
    """
    Read a file and return its contents.

    Args:
        path: Path to the file to read
        max_lines: Optional maximum number of lines to read

    Returns:
        Dictionary with file contents and metadata
    """
    file_path = Path(path)

    if not file_path.exists():
        return {
            "error": f"File not found: {path}",
            "success": False
        }

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            if max_lines:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    lines.append(line)
                content = "".join(lines)
            else:
                content = f.read()

        return {
            "path": path,
            "content": content,
            "size": file_path.stat().st_size,
            "success": True,
            "lines": len(content.split('\n')) if content else 0
        }

    except Exception as e:
        return {
            "error": str(e),
            "path": path,
            "success": False
        }


@tool(domain="files")
async def write_file(
    path: str,
    content: str,
    create_dirs: bool = False
) -> dict:
    """
    Write content to a file.

    Args:
        path: Path to the file to write
        content: Content to write to the file
        create_dirs: Whether to create parent directories

    Returns:
        Dictionary with write status
    """
    file_path = Path(path)

    try:
        if create_dirs:
            file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return {
            "path": path,
            "bytes_written": len(content.encode('utf-8')),
            "success": True
        }

    except Exception as e:
        return {
            "error": str(e),
            "path": path,
            "success": False
        }

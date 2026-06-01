"""
项目统计工具 — 分析当前项目的文件结构和代码统计

展示如何编写不依赖外部服务的本地工具。
"""

import os
from collections import Counter, defaultdict
from pathlib import Path

from pydantic import BaseModel, Field

from nb_agent.tools import tool

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".mypy_cache", ".pytest_cache"}


class ProjectStatsParams(BaseModel):
    directory: str = Field(default=".", description="项目目录路径，默认当前目录")


@tool(group="project")
def project_stats(params: ProjectStatsParams) -> str:
    """统计项目的文件数量、代码行数、文件类型分布"""
    root = Path(params.directory).resolve()
    if not root.is_dir():
        return f"目录不存在: {params.directory}"

    ext_counter = Counter()
    lines_counter = defaultdict(int)
    total_files = 0
    total_lines = 0
    total_size = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            fpath = Path(dirpath) / fname
            ext = fpath.suffix.lower() or "(无后缀)"
            ext_counter[ext] += 1
            total_files += 1
            total_size += fpath.stat().st_size

            if ext in {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".md", ".yaml", ".yml", ".json", ".toml"}:
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        line_count = sum(1 for _ in f)
                        lines_counter[ext] += line_count
                        total_lines += line_count
                except (OSError, UnicodeDecodeError):
                    pass

    report = [
        f"项目: {root.name}",
        f"路径: {root}",
        f"文件总数: {total_files}",
        f"代码总行数: {total_lines:,}",
        f"总大小: {_format_size(total_size)}",
        "",
        "文件类型分布 (Top 10):",
    ]
    for ext, count in ext_counter.most_common(10):
        lines = lines_counter.get(ext, 0)
        lines_info = f" ({lines:,} 行)" if lines > 0 else ""
        report.append(f"  {ext:>10}: {count:>5} 个{lines_info}")

    return "\n".join(report)


class FindFilesParams(BaseModel):
    pattern: str = Field(description="文件名匹配模式（支持 glob），如 '*.py' 或 'test_*.py'")
    directory: str = Field(default=".", description="搜索目录，默认当前目录")
    max_results: int = Field(default=20, description="最大返回数量")


@tool(group="project")
def find_files(params: FindFilesParams) -> str:
    """在项目中搜索匹配的文件"""
    root = Path(params.directory).resolve()
    if not root.is_dir():
        return f"目录不存在: {params.directory}"

    results = []
    for fpath in root.rglob(params.pattern):
        if any(skip in fpath.parts for skip in SKIP_DIRS):
            continue
        rel = fpath.relative_to(root)
        results.append(str(rel))
        if len(results) >= params.max_results:
            break

    if not results:
        return f"未找到匹配 '{params.pattern}' 的文件"

    return f"找到 {len(results)} 个文件:\n" + "\n".join(f"  {r}" for r in results)


def _format_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

"""
书签管理 MCP Server — 通过 MCP 协议提供书签增删查功能

展示如何用 FastMCP 编写一个 MCP Server，
只需一个 @mcp.tool() 装饰器即可定义工具，
schema 从函数签名 + Pydantic Field 自动生成。

配置方式（在 config.jsonc 的 mcp 节）：
  "bookmark": {
    "type": "local",
    "command": ["python", "mcp_servers/bookmark_server.py"],
    "enabled": true
  }
"""

import json
from datetime import datetime
from pathlib import Path

from pydantic import Field
from mcp.server.fastmcp import FastMCP

BOOKMARKS_FILE = Path(__file__).parent.parent / "data" / "bookmarks.json"

mcp = FastMCP("bookmark-manager")


def _load_bookmarks() -> list:
    if BOOKMARKS_FILE.exists():
        return json.loads(BOOKMARKS_FILE.read_text(encoding="utf-8"))
    return []


def _save_bookmarks(bookmarks: list):
    BOOKMARKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    BOOKMARKS_FILE.write_text(
        json.dumps(bookmarks, ensure_ascii=False, indent=2), encoding="utf-8"
    )


@mcp.tool()
def add_bookmark(
    url: str = Field(description="网页 URL"),
    title: str = Field(description="书签标题"),
    tags: str = Field(default="", description="逗号分隔的标签，如 'python,教程'"),
) -> str:
    """保存一个网页书签"""
    bookmarks = _load_bookmarks()

    for bm in bookmarks:
        if bm["url"] == url:
            return f"书签已存在: {url}"

    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    bookmarks.append({
        "url": url,
        "title": title,
        "tags": tag_list,
        "created": datetime.now().isoformat(),
    })
    _save_bookmarks(bookmarks)
    return f"书签已保存: {title} ({url})"


@mcp.tool()
def search_bookmarks(
    keyword: str = Field(description="搜索关键词"),
    tag: str = Field(default="", description="按标签过滤（可选）"),
) -> str:
    """搜索书签（按关键词或标签）"""
    bookmarks = _load_bookmarks()
    kw = keyword.lower()
    results = []

    for bm in bookmarks:
        if tag and tag.lower() not in [t.lower() for t in bm.get("tags", [])]:
            continue
        if kw in bm["title"].lower() or kw in bm["url"].lower():
            results.append(bm)

    if not results:
        return f"未找到包含 '{keyword}' 的书签"
    return json.dumps(results[:20], ensure_ascii=False, indent=2)


@mcp.tool()
def list_bookmarks(
    limit: int = Field(default=20, description="返回数量上限"),
) -> str:
    """列出所有书签"""
    bookmarks = _load_bookmarks()
    if not bookmarks:
        return "暂无书签"
    display = bookmarks[-limit:]
    display.reverse()
    return json.dumps(display, ensure_ascii=False, indent=2)


@mcp.tool()
def delete_bookmark(
    url: str = Field(description="要删除的书签 URL"),
) -> str:
    """删除一个书签（按 URL 匹配）"""
    bookmarks = _load_bookmarks()
    original_count = len(bookmarks)
    bookmarks = [bm for bm in bookmarks if bm["url"] != url]
    if len(bookmarks) == original_count:
        return f"未找到书签: {url}"
    _save_bookmarks(bookmarks)
    return f"已删除书签: {url}"


if __name__ == "__main__":
    mcp.run(transport="stdio")

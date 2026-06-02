"""
笔记管理工具 — 增删查改笔记

每个工具通过 @tool 装饰器自动注册到 nb_agent。
AI 会根据用户意图自主决定调用哪个工具。
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from nb_agent.tools import tool

NOTES_DIR = Path(__file__).parent.parent / "notes_data"
NOTES_DIR.mkdir(parents=True, exist_ok=True)


class CreateNoteParams(BaseModel):
    title: str = Field(description="笔记标题")
    content: str = Field(description="笔记内容（支持 Markdown）")
    tags: str = Field(default="", description="逗号分隔的标签，如 'work,meeting,todo'")


@tool(group="note")
def create_note(params: CreateNoteParams) -> str:
    """创建一条笔记，保存到本地文件"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c if c.isalnum() or c in "-_ " else "_" for c in params.title)
    filename = f"{ts}_{safe_title}.md"
    filepath = NOTES_DIR / filename

    tags_line = ""
    if params.tags:
        tag_list = [t.strip() for t in params.tags.split(",") if t.strip()]
        tags_line = f"tags: {', '.join(tag_list)}\n"

    note_content = (
        f"---\n"
        f"title: {params.title}\n"
        f"created: {datetime.now().isoformat()}\n"
        f"{tags_line}"
        f"---\n\n"
        f"{params.content}\n"
    )

    filepath.write_text(note_content, encoding="utf-8")
    return f"笔记已创建: {filepath.name}"


class SearchNotesParams(BaseModel):
    keyword: str = Field(description="搜索关键词（在标题和内容中查找）")
    tag: str = Field(default="", description="按标签过滤（可选）")


@tool(group="note")
def search_notes(params: SearchNotesParams) -> str:
    """搜索笔记，按关键词和标签过滤"""
    results = []
    keyword = params.keyword.lower()

    for f in sorted(NOTES_DIR.glob("*.md"), reverse=True):
        content = f.read_text(encoding="utf-8")
        title = _extract_field(content, "title") or f.stem
        tags = _extract_field(content, "tags") or ""
        created = _extract_field(content, "created") or ""

        if params.tag and params.tag.lower() not in tags.lower():
            continue

        if keyword in content.lower() or keyword in title.lower():
            body = content.split("---", 2)[-1].strip() if "---" in content else content
            preview = body[:100].replace("\n", " ")
            results.append({
                "file": f.name,
                "title": title,
                "tags": tags,
                "created": created[:19],
                "preview": preview,
            })

    if not results:
        return f"未找到包含 '{params.keyword}' 的笔记"
    return json.dumps(results[:10], ensure_ascii=False, indent=2)


class ListNotesParams(BaseModel):
    limit: int = Field(default=10, description="返回的笔记数量上限")


@tool(group="note")
def list_notes(params: ListNotesParams) -> str:
    """列出最近的笔记"""
    files = sorted(NOTES_DIR.glob("*.md"), reverse=True)
    if not files:
        return "暂无笔记"

    notes = []
    for f in files[:params.limit]:
        content = f.read_text(encoding="utf-8")
        title = _extract_field(content, "title") or f.stem
        tags = _extract_field(content, "tags") or ""
        created = _extract_field(content, "created") or ""
        notes.append({
            "file": f.name,
            "title": title,
            "tags": tags,
            "created": created[:19],
        })
    return json.dumps(notes, ensure_ascii=False, indent=2)


class ReadNoteParams(BaseModel):
    filename: str = Field(description="笔记文件名，如 '20260527_143000_会议记录.md'")


@tool(group="note")
def read_note(params: ReadNoteParams) -> str:
    """读取某条笔记的完整内容"""
    filepath = NOTES_DIR / params.filename
    if not filepath.exists():
        return f"文件不存在: {params.filename}"
    return filepath.read_text(encoding="utf-8")


class DeleteNoteParams(BaseModel):
    filename: str = Field(description="要删除的笔记文件名")


@tool(group="note")
def delete_note(params: DeleteNoteParams) -> str:
    """删除一条笔记（危险操作，需要用户确认）"""
    filepath = NOTES_DIR / params.filename
    if not filepath.exists():
        return f"文件不存在: {params.filename}"
    filepath.unlink()
    return f"已删除: {params.filename}"


def _extract_field(content: str, field_name: str) -> Optional[str]:
    """从 YAML frontmatter 中提取字段值"""
    for line in content.split("\n"):
        if line.startswith(f"{field_name}:"):
            return line[len(field_name) + 1:].strip()
    return None

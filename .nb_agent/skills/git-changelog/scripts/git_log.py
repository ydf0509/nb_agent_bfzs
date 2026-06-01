#!/usr/bin/env python3
"""
git_log.py — 提取 Git 提交记录并输出结构化数据

用法:
  python3 scripts/git_log.py                    # 最近 7 天
  python3 scripts/git_log.py --days 30          # 最近 30 天
  python3 scripts/git_log.py --since 2026-05-01 # 指定起始日期
  python3 scripts/git_log.py --format markdown  # 直接输出 Markdown
  python3 scripts/git_log.py --help             # 查看帮助
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta


CATEGORIES = {
    "feat": "✨ 新功能",
    "add": "✨ 新功能",
    "new": "✨ 新功能",
    "fix": "🐛 修复",
    "bugfix": "🐛 修复",
    "hotfix": "🐛 修复",
    "refactor": "♻️ 重构",
    "restructure": "♻️ 重构",
    "docs": "📝 文档",
    "readme": "📝 文档",
    "comment": "📝 文档",
    "style": "🎨 样式",
    "ui": "🎨 样式",
    "css": "🎨 样式",
    "perf": "⚡ 性能",
    "optimize": "⚡ 性能",
    "speed": "⚡ 性能",
    "test": "🧪 测试",
    "spec": "🧪 测试",
    "coverage": "🧪 测试",
    "build": "🔧 配置",
    "ci": "🔧 配置",
    "config": "🔧 配置",
    "chore": "🔧 配置",
}

CONVENTIONAL_RE = re.compile(r"^(\w+)(?:\(.+?\))?[!:]")


def classify(message: str) -> str:
    msg_lower = message.lower()
    m = CONVENTIONAL_RE.match(msg_lower)
    if m:
        prefix = m.group(1)
        if prefix in CATEGORIES:
            return CATEGORIES[prefix]
    for keyword, category in CATEGORIES.items():
        if keyword in msg_lower.split():
            return category
    return "📦 其他"


def get_commits(since: str) -> list:
    fmt = "--format=%H|%an|%ai|%s"
    cmd = ["git", "log", f"--since={since}", fmt, "--no-merges"]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, encoding="utf-8"
        )
    except subprocess.CalledProcessError as e:
        print(f"Error: git log failed: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: git not found in PATH", file=sys.stderr)
        sys.exit(1)

    commits = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("|", 3)
        if len(parts) < 4:
            continue
        hash_val, author, date, message = parts
        commits.append({
            "hash": hash_val[:7],
            "author": author.strip(),
            "date": date.strip()[:10],
            "message": message.strip(),
            "category": classify(message),
        })
    return commits


def to_markdown(commits: list, since: str) -> str:
    grouped = {}
    for c in commits:
        grouped.setdefault(c["category"], []).append(c)

    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"# Changelog\n", f"## {since} ~ {today}\n"]

    order = [
        "✨ 新功能", "🐛 修复", "♻️ 重构", "📝 文档",
        "🎨 样式", "⚡ 性能", "🧪 测试", "🔧 配置", "📦 其他",
    ]
    for cat in order:
        items = grouped.get(cat, [])
        if not items:
            continue
        lines.append(f"### {cat}\n")
        for c in items:
            lines.append(f"- {c['message']} (`{c['hash']}` by {c['author']})")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Extract git commits and output structured changelog data"
    )
    parser.add_argument(
        "--days", type=int, default=7,
        help="Number of days to look back (default: 7)"
    )
    parser.add_argument(
        "--since", type=str, default="",
        help="Start date in YYYY-MM-DD format (overrides --days)"
    )
    parser.add_argument(
        "--format", choices=["json", "markdown"], default="json",
        help="Output format: json (default) or markdown"
    )
    args = parser.parse_args()

    if args.since:
        since = args.since
    else:
        since = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")

    commits = get_commits(since)

    if not commits:
        print(f"No commits found since {since}")
        return

    if args.format == "markdown":
        print(to_markdown(commits, since))
    else:
        output = {
            "since": since,
            "total": len(commits),
            "commits": commits,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

---
name: git-changelog
description: >-
  生成 Git 变更日志。当用户要求生成 changelog、查看最近提交记录、
  整理版本发布说明、或总结代码变更历史时使用。
---

# Git 变更日志生成 Skill

根据 Git 提交历史，自动生成结构化的变更日志。

## 可用脚本

- **`scripts/git_log.py`** — 提取 Git 提交记录，输出结构化 JSON
  支持参数：`--days N`（最近 N 天）、`--since DATE`（起始日期）、`--format markdown`（直接输出 Markdown）

## 工作流程

### 1. 收集提交信息

运行脚本获取提交记录：

```bash
python3 scripts/git_log.py --days 7
```

如果用户指定了时间范围：

```bash
python3 scripts/git_log.py --since 2026-05-01
```

### 2. 分类整理

将提交按以下类别分类：

| 类别 | 说明 | Commit 关键词 |
|------|------|---------------|
| ✨ 新功能 | 新增的功能 | feat, add, new |
| 🐛 修复 | Bug 修复 | fix, bugfix, hotfix |
| ♻️ 重构 | 代码重构 | refactor, restructure |
| 📝 文档 | 文档更新 | docs, readme, comment |
| 🎨 样式 | UI/样式调整 | style, ui, css |
| ⚡ 性能 | 性能优化 | perf, optimize, speed |
| 🧪 测试 | 测试相关 | test, spec, coverage |
| 🔧 配置 | 构建/配置 | build, ci, config, chore |

### 3. 生成 Changelog

按以下格式输出：

```markdown
# Changelog

## [日期范围]

### ✨ 新功能
- 功能描述 (commit hash)

### 🐛 修复
- 修复描述 (commit hash)

### ♻️ 重构
- 重构描述 (commit hash)

...
```

### 4. 保存

使用 `create_note` 工具保存变更日志，标题格式：`Changelog-YYYY-MM-DD`，tags 设为 `changelog`。

## 注意事项

- 如果提交信息是英文的，保持英文，不要翻译
- 合并提交（Merge commit）可以跳过
- 同一功能的多个提交合并为一条记录
- 如果用户没指定时间范围，默认取最近 7 天

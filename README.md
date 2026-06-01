# nb_agent_bfzs — 智能笔记助手

> 基于 [nb_agent](https://github.com/xxx/nb_agent) 框架的演示项目，展示如何用极少代码构建自己的 AI Agent + 终端 TUI。

## 快速开始

```bash
pip install nb_agent
cd nb_agent_bfzs
python main.py
```

## 项目结构

```
nb_agent_bfzs/
├── main.py                 # 入口（6 行核心代码）
├── config.jsonc             # 模型 + MCP + 审批配置
├── tools/                   # 自定义工具（@tool 装饰器自动注册）
│   ├── note_tools.py        #   笔记 CRUD（5 个工具）
│   └── project_tools.py     #   项目统计（2 个工具）
├── mcp_servers/             # 自定义 MCP Server
│   └── bookmark_server.py   #   书签管理（FastMCP 实现）
└── .nb_agent/skills/        # Agent Skills（agentskills.io 规范）
    ├── daily-report/         #   日报生成
    ├── meeting-notes/        #   会议纪要
    ├── git-changelog/        #   Git 变更日志（含 scripts/）
    ├── code-review/          #   代码审查
    ├── refactor/             #   代码重构
    └── explain-code/         #   代码解释
```

## 核心代码

```python
# main.py — 就这几行
import tools                          # 导入即注册自定义工具

from nb_agent import load_config, AgentApp

config = load_config()
AgentApp(config).run()
```

## 功能展示

### 自定义工具（@tool 装饰器）

```python
from nb_agent.tools import tool
from pydantic import BaseModel, Field

class CreateNoteParams(BaseModel):
    title: str = Field(description="笔记标题")
    content: str = Field(description="笔记内容")

@tool(group="note")
def create_note(params: CreateNoteParams) -> str:
    """创建一条笔记"""
    # ... 你的逻辑
    return "笔记已创建"
```

### MCP Server（FastMCP）

```python
from mcp.server.fastmcp import FastMCP
from pydantic import Field

mcp = FastMCP("bookmark-manager")

@mcp.tool()
def add_bookmark(url: str = Field(description="URL")) -> str:
    """保存书签"""
    return f"已保存: {url}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### Agent Skills（SKILL.md）

```markdown
---
name: daily-report
description: >-
  生成每日工作日报。当用户提到写日报时使用。
---

# 日报生成 Skill

## 工作流程
1. 查看今日笔记
2. 询问用户完成的任务
3. 按模板生成日报
```

## TUI 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+J` / `Ctrl+Enter` | 发送消息 |
| `F1` | 帮助 |
| `F2` | 切换模型 |
| `F4` | Agent 管理 |
| `F5` | 新建会话 |
| `F6` | 历史会话 |
| `Ctrl+P` | 命令面板 |
| `Ctrl+L` | 清屏 |

## 配置说明

编辑 `config.jsonc`：

- **provider**：配置 LLM 提供商（支持任何 OpenAI 兼容 API）
- **mcp**：配置 MCP Server（stdio/SSE 方式）
- **approval**：配置危险工具需要用户确认
- **agent**：配置 system prompt 和默认模型

## License

MIT

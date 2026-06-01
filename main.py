"""
nb_agent_bfzs — 智能笔记助手（nb_agent 演示项目）

只需几行代码，就拥有自己的 AI Agent + 终端 TUI：

  1. pip install nb_agent
  2. 在 tools/ 下用 @tool 定义工具
  3. 在 .nb_agent/skills/ 下放 SKILL.md
  4. 在 config.jsonc 里配置模型和 MCP
  5. python main.py
"""

import tools  # noqa: F401  导入即注册自定义工具

from nb_agent import load_config, AgentApp

config = load_config()
AgentApp(config).run()

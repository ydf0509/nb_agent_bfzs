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
from approval_rules import ALL_RULES
from nb_agent import load_config, AgentApp

config = load_config()
app = AgentApp(config)

for rule in ALL_RULES: # 注册自定义审批规则（Redis 写命令弹窗确认、危险工具黑名单等）
    app.agent.approval_engine.add_rule(rule)

app.run()


# powershell
# cd D:/codes/nb_agent_bfzs;$env:PYTHONPATH = "D:/codes/nb_agent_bfzs";D:\ProgramData\Miniconda3\envs\py312\python.exe main.py

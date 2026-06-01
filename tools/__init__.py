"""
自定义工具包 — import 即自动注册到 nb_agent

使用 @tool 装饰器的函数在 import 时自动注册，
无需手动调用 register_tool()。
"""

from . import note_tools    # noqa: F401
from . import project_tools  # noqa: F401

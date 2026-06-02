"""
自定义审批规则 — 演示 nb_agent 的工具调用审批机制

nb_agent 的 ApprovalEngine 支持用户注入自定义规则函数:
  - 规则签名: (tool_name: str, tool_kwargs: dict) -> bool
  - 返回 True → 弹窗让用户确认后才执行
  - 返回 False → 放行（不弹窗）
  - 多条规则按顺序检查，任一命中即触发审批

工具名格式:
  - 本地 @tool:          函数名，如 "delete_note"
  - MCP 工具:   mcp__{config 中的 key}__{函数名}，如 "mcp__redis-tools__redis_execute"
"""

# ── Redis 写命令集 ──────────────────────────────
REDIS_WRITE_COMMANDS = {
    "SET", "SETNX", "SETEX", "PSETEX", "MSET", "MSETNX", "APPEND",
    "INCR", "INCRBY", "INCRBYFLOAT", "DECR", "DECRBY",
    "DEL", "UNLINK", "RENAME", "RENAMENX", "EXPIRE", "EXPIREAT",
    "PEXPIRE", "PEXPIREAT", "PERSIST", "MOVE", "COPY",
    "HSET", "HSETNX", "HMSET", "HDEL", "HINCRBY", "HINCRBYFLOAT",
    "LPUSH", "RPUSH", "LPOP", "RPOP", "LSET", "LINSERT", "LREM", "LTRIM",
    "SADD", "SREM", "SPOP", "SMOVE", "SDIFFSTORE", "SINTERSTORE", "SUNIONSTORE",
    "ZADD", "ZREM", "ZINCRBY", "ZPOPMIN", "ZPOPMAX",
    "XADD", "XDEL", "XTRIM",
    "PFADD", "PFMERGE",
    "GEOADD",
}

# ── 始终需要审批的工具黑名单 ──────────────────────
# 工具名格式:
#   - 本地 @tool(group="xxx"):  {group}__{函数名}，如 "note__delete_note"
#   - 本地 @tool():              直接函数名，如 "get_current_time"
#   - MCP 工具:                  mcp__{config key}__{函数名}，如 "mcp__redis-tools__redis_execute"
ALWAYS_APPROVE_TOOLS = {
    "mcp__redis-tools__redis_smart_set",
    "note__delete_note",
}


# ── 规则函数 ────────────────────────────────────

def rule_redis_write(tool_name: str, tool_kwargs: dict) -> bool:
    """Redis redis_execute 中的写命令需要审批，只读命令（GET/HGETALL/INFO）放行"""
    if tool_name != "mcp__redis-tools__redis_execute":
        return False
    cmd_parts = tool_kwargs.get("command", "").strip().split()
    if not cmd_parts:
        return False
    return cmd_parts[0].upper() in REDIS_WRITE_COMMANDS


def rule_dangerous_tools(tool_name: str, tool_kwargs: dict) -> bool:
    """黑名单中的工具始终需要审批"""
    return tool_name in ALWAYS_APPROVE_TOOLS


def rule_note_delete(tool_name: str, tool_kwargs: dict) -> bool:
    """删除笔记操作需要审批"""
    return tool_name == "note__delete_note"


# ── 导出规则列表（main.py 中注册到 ApprovalEngine）──
ALL_RULES = [
    rule_redis_write,
    rule_dangerous_tools,
    rule_note_delete,
]

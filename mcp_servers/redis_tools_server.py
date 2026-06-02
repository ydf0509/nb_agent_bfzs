"""
自定义 Python MCP Server —— Redis 工具 (redis-tools)

设计哲学：
  不逐个封装 200+ Redis 命令，而是提供 7 个高价值工具：
  - 1 个万能命令执行器（AI 自己拼 Redis 命令）
  - 6 个高频/复杂场景的专用工具（AI 容易搞错或需要组合多步的操作）

工具列表:
  1. redis_execute     → 万能 Redis 命令执行器（AI 自己写命令）
  2. redis_info        → 查看服务器状态（内存/连接/版本等）
  3. redis_keys        → 按模式搜索 key（显示类型/TTL/大小）
  4. redis_smart_get   → 智能读取（自动识别 string/hash/list/set/zset 并完整读取）
  5. redis_smart_set   → 智能写入（支持 TTL、自动选择数据类型）
  6. redis_db_stats    → 数据库全局统计（key 总数、内存分布、各类型占比）
  7. redis_slowlog     → 慢查询日志（排查性能问题）

连接配置（通过环境变量，优先级从高到低）:
  REDIS_URL      完整 URL，如 redis://:password@host:6379/0（优先使用）
  REDIS_HOST     主机地址，默认 127.0.0.1
  REDIS_PORT     端口，默认 6379
  REDIS_PASSWORD 密码，默认无
  REDIS_DB       数据库号，默认 0

运行方式:
  由 MCP Client 作为子进程自动启动（stdio 传输）。
  手动测试: python redis_tools_server.py
"""

import os
import json
import shlex

from pydantic import Field
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("redis-tools")

FORBIDDEN_COMMANDS = {
    "FLUSHDB", "FLUSHALL", "SHUTDOWN", "DEBUG", "CONFIG SET",
    "SLAVEOF", "REPLICAOF", "CLUSTER RESET", "SCRIPT FLUSH",
    "KEYS", "EVAL", "EVALSHA", "SCRIPT LOAD", "MODULE LOAD",
    "MODULE UNLOAD", "ACL SETUSER", "ACL DELUSER", "CONFIG RESETSTAT",
    "SWAPDB", "MIGRATE",
}


def _get_redis():
    """创建 Redis 连接（每次调用新建，避免长连接超时问题）"""
    try:
        import redis as redis_lib
    except ImportError:
        raise RuntimeError("需要安装 redis-py: pip install redis")

    redis_url = os.environ.get("REDIS_URL", "").strip()
    if redis_url:
        return redis_lib.Redis.from_url(
            redis_url, decode_responses=True, socket_timeout=10,
        )

    host = os.environ.get("REDIS_HOST", "127.0.0.1")
    port = int(os.environ.get("REDIS_PORT", "6379"))
    password = os.environ.get("REDIS_PASSWORD") or None
    db = int(os.environ.get("REDIS_DB", "0"))

    return redis_lib.Redis(
        host=host, port=port, password=password, db=db,
        decode_responses=True, socket_timeout=10,
    )


def _format_value(value, max_len=2000):
    s = str(value)
    if len(s) > max_len:
        return s[:max_len] + f"... (共 {len(s)} 字符)"
    return s


# ─────────────────────────────────────────────
# 工具 1: 万能命令执行器
# ─────────────────────────────────────────────

@mcp.tool()
def redis_execute(
    command: str = Field(description='完整的 Redis 命令，如 "SET mykey hello EX 60" 或 "HGETALL user:1001"'),
) -> str:
    """执行任意 Redis 命令（FLUSHDB/FLUSHALL/SHUTDOWN 等危险命令被禁止）。"""
    if not command.strip():
        return "错误: 命令不能为空"

    cmd_upper = command.strip().upper()
    for forbidden in FORBIDDEN_COMMANDS:
        if cmd_upper.startswith(forbidden):
            return f"安全限制: 禁止执行命令 {forbidden}。如确需执行，请通过 redis-cli 手动操作。"

    try:
        r = _get_redis()
        try:
            parts = shlex.split(command.strip())
        except ValueError:
            parts = command.strip().split()
        result = r.execute_command(*parts)

        if result is None:
            return "(nil)"
        if isinstance(result, bool):
            return "OK" if result else "FAIL"
        if isinstance(result, (int, float)):
            return str(result)
        if isinstance(result, bytes):
            try:
                return result.decode("utf-8")
            except UnicodeDecodeError:
                return f"(binary data, {len(result)} bytes)"
        if isinstance(result, list):
            lines = []
            for i, item in enumerate(result[:100]):
                lines.append(f"  {i + 1}) {_format_value(item, 500)}")
            if len(result) > 100:
                lines.append(f"  ... (共 {len(result)} 项)")
            return "\n".join(lines) if lines else "(empty list)"
        if isinstance(result, dict):
            return json.dumps(result, ensure_ascii=False, indent=2, default=str)

        return _format_value(result)

    except Exception as e:
        return f"执行失败: {type(e).__name__}: {e}"


# ─────────────────────────────────────────────
# 工具 2: 服务器信息
# ─────────────────────────────────────────────

@mcp.tool()
def redis_info(
    section: str = Field(
        default="overview",
        description="信息区域: overview(精简概要) / server / clients / memory / stats / replication / keyspace / all",
    ),
) -> str:
    """查看 Redis 服务器信息。"""
    try:
        r = _get_redis()

        if section == "overview":
            info = r.info()
            db_info = r.info("keyspace")
            total_keys = sum(
                v.get("keys", 0) for k, v in db_info.items() if k.startswith("db")
            )
            return (
                f"Redis 服务器概要\n"
                f"{'─' * 40}\n"
                f"  版本: {info.get('redis_version', '?')}\n"
                f"  运行时间: {info.get('uptime_in_days', '?')} 天\n"
                f"  已用内存: {info.get('used_memory_human', '?')}\n"
                f"  峰值内存: {info.get('used_memory_peak_human', '?')}\n"
                f"  连接客户端: {info.get('connected_clients', '?')}\n"
                f"  总 key 数: {total_keys}\n"
                f"  命中率: {_calc_hit_rate(info)}\n"
                f"  TCP 端口: {info.get('tcp_port', '?')}\n"
                f"  操作系统: {info.get('os', '?')}"
            )

        if section in ("server", "clients", "memory", "stats", "replication", "keyspace"):
            info = r.info(section)
        elif section == "all":
            info = r.info("all")
        else:
            return f"错误: 不支持的 section '{section}'，可选: overview/server/clients/memory/stats/replication/keyspace/all"

        lines = []
        for k, v in info.items():
            if isinstance(v, dict):
                lines.append(f"[{k}]")
                for sk, sv in v.items():
                    lines.append(f"  {sk}: {sv}")
            else:
                lines.append(f"  {k}: {v}")
        return "\n".join(lines[:200])

    except Exception as e:
        return f"获取信息失败: {type(e).__name__}: {e}"


def _calc_hit_rate(info: dict) -> str:
    hits = info.get("keyspace_hits", 0)
    misses = info.get("keyspace_misses", 0)
    total = hits + misses
    if total == 0:
        return "N/A (无访问)"
    rate = hits / total * 100
    return f"{rate:.1f}% ({hits}/{total})"


# ─────────────────────────────────────────────
# 工具 3: Key 搜索
# ─────────────────────────────────────────────

@mcp.tool()
def redis_keys(
    pattern: str = Field(default="*", description='key 匹配模式，支持 * ? [] 通配符，如 "user:*"'),
    limit: int = Field(default=50, description="最多返回数量（防止 key 太多卡住）"),
    show_details: bool = Field(default=True, description="是否显示每个 key 的类型/TTL/内存大小"),
) -> str:
    """按模式搜索 Redis key，可显示每个 key 的类型、TTL、大小等详情。"""
    try:
        r = _get_redis()
        keys = []
        cursor = 0
        while len(keys) < limit:
            cursor, batch = r.scan(cursor=cursor, match=pattern, count=200)
            keys.extend(batch)
            if cursor == 0:
                break

        keys = keys[:limit]
        if not keys:
            return f"模式 '{pattern}' 没有匹配到任何 key"

        if not show_details:
            return f"匹配 '{pattern}': {len(keys)} 个 key\n" + "\n".join(f"  {k}" for k in keys)

        pipe = r.pipeline()
        for k in keys:
            pipe.type(k)
            pipe.ttl(k)
            pipe.memory_usage(k)
        results = pipe.execute()

        lines = [f"匹配 '{pattern}': {len(keys)} 个 key\n"]
        lines.append(f"  {'Key':<40} {'类型':<10} {'TTL':<12} {'内存':<10}")
        lines.append("  " + "─" * 72)
        for i, k in enumerate(keys):
            key_type = results[i * 3] or "?"
            ttl = results[i * 3 + 1]
            mem = results[i * 3 + 2]
            ttl_str = "永不过期" if ttl == -1 else f"{ttl}s" if ttl >= 0 else "?"
            mem_str = _format_bytes(mem) if mem else "?"
            lines.append(f"  {k:<40} {key_type:<10} {ttl_str:<12} {mem_str:<10}")

        return "\n".join(lines)

    except Exception as e:
        return f"搜索失败: {type(e).__name__}: {e}"


def _format_bytes(n):
    if n is None:
        return "?"
    if n < 1024:
        return f"{n}B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f}KB"
    return f"{n / (1024 * 1024):.1f}MB"


# ─────────────────────────────────────────────
# 工具 4: 智能读取
# ─────────────────────────────────────────────

@mcp.tool()
def redis_smart_get(
    key: str = Field(description="Redis key 名称"),
) -> str:
    """智能读取 Redis key 的值，自动识别数据类型（string/hash/list/set/zset/stream）并完整展示。"""
    try:
        r = _get_redis()

        if not r.exists(key):
            return f"key '{key}' 不存在"

        key_type = r.type(key)
        ttl = r.ttl(key)
        ttl_str = "永不过期" if ttl == -1 else f"{ttl}s"

        header = f"Key: {key}\n类型: {key_type}\nTTL: {ttl_str}\n{'─' * 40}\n"

        if key_type == "string":
            val = r.get(key)
            try:
                parsed = json.loads(val)
                val = json.dumps(parsed, ensure_ascii=False, indent=2)
                header += f"值 (JSON):\n{_format_value(val, 3000)}"
            except (json.JSONDecodeError, TypeError):
                header += f"值: {_format_value(val, 3000)}"

        elif key_type == "hash":
            data = r.hgetall(key)
            header += f"字段数: {len(data)}\n"
            for k, v in list(data.items())[:100]:
                header += f"  {k}: {_format_value(v, 200)}\n"
            if len(data) > 100:
                header += f"  ... (共 {len(data)} 个字段)"

        elif key_type == "list":
            length = r.llen(key)
            items = r.lrange(key, 0, min(99, length - 1))
            header += f"长度: {length}\n"
            for i, item in enumerate(items):
                header += f"  [{i}] {_format_value(item, 200)}\n"
            if length > 100:
                header += f"  ... (共 {length} 项)"

        elif key_type == "set":
            size = r.scard(key)
            members = list(r.sscan_iter(key, count=100))[:100]
            header += f"成员数: {size}\n"
            for m in members:
                header += f"  • {_format_value(m, 200)}\n"
            if size > 100:
                header += f"  ... (共 {size} 个成员)"

        elif key_type == "zset":
            size = r.zcard(key)
            items = r.zrange(key, 0, 99, withscores=True)
            header += f"成员数: {size}\n"
            for member, score in items:
                header += f"  {score:>10.2f}  {_format_value(member, 200)}\n"
            if size > 100:
                header += f"  ... (共 {size} 个成员)"

        elif key_type == "stream":
            length = r.xlen(key)
            entries = r.xrange(key, count=20)
            header += f"消息数: {length}\n"
            for entry_id, fields in entries:
                header += f"  [{entry_id}] {json.dumps(fields, ensure_ascii=False)}\n"
            if length > 20:
                header += f"  ... (共 {length} 条消息)"

        else:
            header += f"(不支持直接显示类型 '{key_type}'，请用 redis_execute 操作)"

        return header

    except Exception as e:
        return f"读取失败: {type(e).__name__}: {e}"


# ─────────────────────────────────────────────
# 工具 5: 智能写入
# ─────────────────────────────────────────────

@mcp.tool()
def redis_smart_set(
    key: str = Field(description="Redis key 名称"),
    value: str = Field(description='要写入的值。string→字符串; hash→JSON对象如{"a":"1"}; list/set→JSON数组如["a","b"]'),
    ttl: int = Field(default=-1, description="过期时间(秒)，-1 表示永不过期"),
    data_type: str = Field(default="string", description="数据类型: string / hash / list / set"),
) -> str:
    """智能写入 Redis key，支持多种数据类型和 TTL 设置。"""
    data_type = data_type.lower().strip()
    if data_type not in ("string", "hash", "list", "set"):
        return f"错误: 不支持的数据类型 '{data_type}'，可选: string / hash / list / set"

    try:
        r = _get_redis()

        if data_type == "string":
            if ttl > 0:
                r.setex(key, ttl, value)
            else:
                r.set(key, value)
            return f"已设置 {key} = {_format_value(value, 200)} (string, TTL={ttl}s)"

        if data_type == "hash":
            try:
                obj = json.loads(value)
                if not isinstance(obj, dict):
                    return "错误: hash 类型的 value 必须是 JSON 对象"
            except json.JSONDecodeError as e:
                return f"错误: JSON 解析失败 — {e}"
            r.delete(key)
            str_obj = {str(k): str(v) for k, v in obj.items()}
            r.hset(key, mapping=str_obj)
            if ttl > 0:
                r.expire(key, ttl)
            return f"已设置 {key} (hash, {len(obj)} 个字段, TTL={ttl}s)"

        if data_type == "list":
            try:
                items = json.loads(value)
                if not isinstance(items, list):
                    return "错误: list 类型的 value 必须是 JSON 数组"
            except json.JSONDecodeError as e:
                return f"错误: JSON 解析失败 — {e}"
            r.delete(key)
            if items:
                r.rpush(key, *[str(i) for i in items])
            if ttl > 0:
                r.expire(key, ttl)
            return f"已设置 {key} (list, {len(items)} 项, TTL={ttl}s)"

        if data_type == "set":
            try:
                items = json.loads(value)
                if not isinstance(items, list):
                    return "错误: set 类型的 value 必须是 JSON 数组"
            except json.JSONDecodeError as e:
                return f"错误: JSON 解析失败 — {e}"
            r.delete(key)
            if items:
                r.sadd(key, *[str(i) for i in items])
            if ttl > 0:
                r.expire(key, ttl)
            return f"已设置 {key} (set, {len(items)} 个成员, TTL={ttl}s)"

    except Exception as e:
        return f"写入失败: {type(e).__name__}: {e}"


# ─────────────────────────────────────────────
# 工具 6: 数据库统计
# ─────────────────────────────────────────────

@mcp.tool()
def redis_db_stats() -> str:
    """查看当前 Redis 数据库的全局统计：key 总数、各类型分布、内存占用等。"""
    try:
        r = _get_redis()
        info = r.info()
        db_info = r.info("keyspace")

        db_num = int(os.environ.get("REDIS_DB", "0"))
        db_key = f"db{db_num}"
        db_data = db_info.get(db_key, {})
        total_keys = db_data.get("keys", 0)

        type_counts = {"string": 0, "hash": 0, "list": 0, "set": 0, "zset": 0, "stream": 0, "other": 0}
        if total_keys > 0 and total_keys <= 10000:
            cursor = 0
            scanned = 0
            pipe = r.pipeline()
            keys_batch = []
            while True:
                cursor, batch = r.scan(cursor=cursor, count=500)
                keys_batch.extend(batch)
                scanned += len(batch)
                if cursor == 0 or scanned >= 10000:
                    break
            for k in keys_batch:
                pipe.type(k)
            types = pipe.execute()
            for t in types:
                t = t if isinstance(t, str) else "other"
                if t in type_counts:
                    type_counts[t] += 1
                else:
                    type_counts["other"] += 1

        lines = [
            f"Redis 数据库统计 (db{db_num})",
            "─" * 40,
            f"  Key 总数: {total_keys}",
            f"  已用内存: {info.get('used_memory_human', '?')}",
            f"  峰值内存: {info.get('used_memory_peak_human', '?')}",
            f"  内存碎片率: {info.get('mem_fragmentation_ratio', '?')}",
            "",
        ]

        if total_keys > 0 and total_keys <= 10000:
            lines.append("  类型分布:")
            for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
                if c > 0:
                    pct = c / total_keys * 100
                    bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
                    lines.append(f"    {t:<10} {bar} {c:>5} ({pct:.1f}%)")
        elif total_keys > 10000:
            lines.append(f"  (key 数量超过 10000，跳过类型统计以避免阻塞)")

        lines.extend([
            "",
            f"  每秒操作数: {info.get('instantaneous_ops_per_sec', '?')}",
            f"  已连接客户端: {info.get('connected_clients', '?')}",
            f"  命中率: {_calc_hit_rate(info)}",
        ])

        return "\n".join(lines)

    except Exception as e:
        return f"统计失败: {type(e).__name__}: {e}"


# ─────────────────────────────────────────────
# 工具 7: 慢查询日志
# ─────────────────────────────────────────────

@mcp.tool()
def redis_slowlog(
    count: int = Field(default=10, description="显示最近几条慢查询，1-50"),
) -> str:
    """查看 Redis 慢查询日志，用于排查性能瓶颈。"""
    try:
        r = _get_redis()
        count = max(1, min(count, 50))
        logs = r.slowlog_get(count)

        if not logs:
            threshold = r.config_get("slowlog-log-slower-than")
            threshold_us = threshold.get("slowlog-log-slower-than", "?")
            return f"暂无慢查询记录\n(当前阈值: {threshold_us}μs)"

        lines = [f"最近 {len(logs)} 条慢查询\n"]
        for entry in logs:
            entry_id = entry.get("id", "?")
            start_time = entry.get("start_time", 0)
            duration = entry.get("duration", 0)
            command = entry.get("command", b"?")

            if isinstance(command, bytes):
                command = command.decode("utf-8", errors="replace")
            elif isinstance(command, (list, tuple)):
                command = " ".join(
                    c.decode("utf-8", errors="replace") if isinstance(c, bytes) else str(c)
                    for c in command
                )

            import datetime
            ts = datetime.datetime.fromtimestamp(start_time).strftime("%Y-%m-%d %H:%M:%S")
            lines.append(
                f"  #{entry_id} | {ts} | 耗时 {duration}μs\n"
                f"    命令: {_format_value(command, 300)}"
            )

        return "\n".join(lines)

    except Exception as e:
        return f"获取慢查询失败: {type(e).__name__}: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")

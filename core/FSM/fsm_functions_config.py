"""
FSM 统一函数配置文件
在这里定义和自定义你的 FSM 函数，可以同时作为条件（cond）和动作（actuator_cmd）使用

设计理念：
- 一个函数可以同时用于条件判断和动作执行
- 作为条件时：函数返回 bool 值（或可转换为 bool 的值）
- 作为动作时：函数返回结果字典或 bool 值

使用方法：
1. 在下面的 UNIFIED_FUNCTIONS 字典中定义你的函数
2. 在 FSM JSON 中：
   - 作为条件：{"cond": "function_name"} 或 {"cond_expr": "function_name and other"}
   - 作为动作：{"actuator_cmd": "func:function_name"} 或 {"actuator_cmd": "function_name"}（如果启用自动注册）
"""

from typing import Callable, Dict, Any, Optional, Union


# ===== 统一函数定义 =====
# 在这里定义你的函数，可以同时作为条件和动作使用
# 函数签名: def function_name(context: dict, *args, **kwargs) -> Union[bool, Dict[str, Any]]
# 支持参数化调用，例如：players_ge(3) 或 elapsed_ge(5000)

def elapsed_ge(context: dict, threshold_ms: int = 5000) -> Union[bool, Dict[str, Any]]:
    """
    任务耗时 >= 指定毫秒数（可作为条件或动作）
    
    Args:
        context: 上下文字典
        threshold_ms: 阈值（毫秒），默认 5000
    
    使用示例：
    - 作为条件: {"cond": "elapsed_ge(5000)"} 或 {"cond": "elapsed_ge(10000)"}
    - 作为动作: {"actuator_cmd": "func:elapsed_ge(5000)"}
    """
    elapsed = int(context.get("elapsed_ms", 0))
    result = elapsed >= threshold_ms
    if context.get("_as_action", False):
        return {"ok": result, "elapsed_ms": elapsed, "threshold_ms": threshold_ms}
    return result


def players_ge(context: dict, threshold: int = 1) -> Union[bool, Dict[str, Any]]:
    """
    玩家数量 >= 指定值（可作为条件或动作）
    
    Args:
        context: 上下文字典
        threshold: 阈值，默认 1
    
    使用示例：
    - 作为条件: {"cond": "players_ge(1)"} 或 {"cond": "players_ge(8)"}
    - 作为动作: {"actuator_cmd": "func:players_ge(3)"}
    """
    players = int(context.get("players", 0))
    result = players >= threshold
    if context.get("_as_action", False):
        return {"ok": result, "players": players, "threshold": threshold}
    return result


def player(context: dict, operator: str, num: int) -> Union[bool, Dict[str, Any]]:
    """
    玩家数量比较（通用函数，支持多种操作符）
    
    Args:
        context: 上下文字典
        operator: 比较操作符
            - "g" 或 "gt": greater than (>)
            - "l" 或 "lt": less than (<)
            - "ge" 或 "gte": greater than or equal (>=)
            - "le" 或 "lte": less than or equal (<=)
            - "e" 或 "eq": equal (==)
        num: 比较的数值
    
    使用示例：
    - 作为条件: {"cond": "player('ge', 6)"} 或 {"cond": "player('g', 5)"}
    - 作为动作: {"actuator_cmd": "func:player('ge', 3)"}
    """
    players = int(context.get("players", 0))
    operator = operator.lower()
    
    if operator in ("g", "gt"):
        result = players > num
    elif operator in ("l", "lt"):
        result = players < num
    elif operator in ("ge", "gte"):
        result = players >= num
    elif operator in ("le", "lte"):
        result = players <= num
    elif operator in ("e", "eq"):
        result = players == num
    else:
        result = False
    
    if context.get("_as_action", False):
        return {
            "ok": result,
            "players": players,
            "operator": operator,
            "threshold": num,
            "result": result
        }
    return result


def elapsed(context: dict, time_str: str) -> Union[bool, Dict[str, Any]]:
    """
    任务耗时检查（支持时间单位：h=小时, m=分钟, s=秒）
    
    Args:
        context: 上下文字典
        time_str: 时间字符串，支持格式：
            - "1h" 或 "1.5h" (小时)
            - "30m" (分钟)
            - "60s" (秒)
            - 纯数字（毫秒）
    
    使用示例：
    - 作为条件: {"cond": "elapsed('1h')"} 或 {"cond": "elapsed('2.5h')"}
    - 作为动作: {"actuator_cmd": "func:elapsed('30m')"}
    """
    elapsed_ms = int(context.get("elapsed_ms", 0))
    
    # 解析时间字符串
    time_str = str(time_str).strip().lower()
    threshold_ms = 0
    
    if time_str.endswith('h'):
        # 小时
        hours = float(time_str[:-1])
        threshold_ms = int(hours * 3600 * 1000)
    elif time_str.endswith('m'):
        # 分钟
        minutes = float(time_str[:-1])
        threshold_ms = int(minutes * 60 * 1000)
    elif time_str.endswith('s'):
        # 秒
        seconds = float(time_str[:-1])
        threshold_ms = int(seconds * 1000)
    else:
        # 假设是毫秒
        try:
            threshold_ms = int(float(time_str))
        except ValueError:
            threshold_ms = 0
    
    result = elapsed_ms >= threshold_ms
    
    if context.get("_as_action", False):
        return {
            "ok": result,
            "elapsed_ms": elapsed_ms,
            "threshold_ms": threshold_ms,
            "time_str": time_str
        }
    return result


def MissionStats(context: dict, status: str) -> Union[bool, Dict[str, Any]]:
    """
    检查任务状态
    
    Args:
        context: 上下文字典
        status: 任务状态
            - "Running": 运行中
            - "Complete": 已完成
            - "Failed": 失败
    
    使用示例：
    - 作为条件: {"cond": "MissionStats('Complete')"} 或 {"cond": "MissionStats('Failed')"}
    - 作为动作: {"actuator_cmd": "func:MissionStats('Running')"}
    
    注意：需要在 context 中提供 'mission_status' 字段
    """
    mission_status = context.get("mission_status", "").strip()
    status = status.strip()
    
    result = str(mission_status).lower() == str(status).lower()
    
    if context.get("_as_action", False):
        return {
            "ok": result,
            "mission_status": mission_status,
            "expected_status": status,
            "matched": result
        }
    return result


def server_ready(context: dict) -> bool:
    """服务器就绪（可作为条件或动作）"""
    ready = bool(context.get("server_ready", False))
    if context.get("_as_action", False):
        return {"ok": ready, "server_ready": ready}
    return ready


def stage_equals(context: dict, target: Optional[str] = None) -> Union[bool, Dict[str, Any]]:
    """
    当前阶段等于指定值（可作为条件或动作）
    
    Args:
        context: 上下文字典
        target: 目标阶段值，如果不提供则从 context['target_stage'] 获取
    
    使用示例：
    - 作为条件: {"cond": "stage_equals('stage1')"} 或 {"cond": "stage_equals"}
    - 作为动作: {"actuator_cmd": "func:stage_equals('stage1')"}
    """
    stage = context.get("stage", "")
    target_stage = target if target is not None else context.get("target_stage", "")
    result = str(stage) == str(target_stage)
    if context.get("_as_action", False):
        return {"ok": result, "stage": stage, "target_stage": target_stage, "matched": result}
    return result


# ===== 统一函数注册映射 =====
# 将函数注册到名称，可以同时用于条件和动作
# 格式: "function_name": function
# 
# 在 JSON 中使用：
# - 作为条件: {"cond": "function_name"} 或 {"cond_expr": "function_name and other"}
# - 作为动作: {"actuator_cmd": "func:function_name"}
UNIFIED_FUNCTIONS: Dict[str, Callable] = {
    # 通用函数（推荐使用）
    "player": player,
    "elapsed": elapsed,
    "MissionStats": MissionStats,
    
    # 参数化函数（向后兼容）
    "elapsed_ge": elapsed_ge,
    "players_ge": players_ge,
    "server_ready": server_ready,
    "stage_equals": stage_equals,
    

    
    # 你可以添加更多统一函数：
    # "my_function": my_function,
}


# ===== 获取函数文档 =====
def get_functions_doc() -> Dict[str, str]:
    """
    返回所有可用函数的文档
    
    Returns:
        函数名到描述的字典
    """
    return {
        "player": "玩家数量比较，操作符：g/gt(>), l/lt(<), ge/gte(>=), le/lte(<=), e/eq(==)，例如：player('ge', 6)",
        "elapsed": "任务耗时检查，支持时间单位：h(小时), m(分钟), s(秒)，例如：elapsed('1h') 或 elapsed('2.5h')",
        "MissionStats": "检查任务状态：Running/Complete/Failed，例如：MissionStats('Complete')",
        "elapsed_ge": "任务耗时 >= 指定毫秒数，例如：elapsed_ge(5000)",
        "players_ge": "玩家数量 >= 指定值，例如：players_ge(3)",
        "server_ready": "服务器就绪",
        "stage_equals": "当前阶段等于指定值，例如：stage_equals('stage1')",
        # 向后兼容
        "elapsed_ge_5s": "任务耗时 >= 5 秒（向后兼容）",
        "elapsed_ge_10s": "任务耗时 >= 10 秒（向后兼容）",
        "players_ge_1": "玩家数量 >= 1（向后兼容）",
        "players_ge_8": "玩家数量 >= 8（向后兼容）",
    }


# ===== 使用示例 =====
"""
在 JSON 中使用这些函数：

1. 作为条件（支持参数化）：
   {"to": "2", "cond": "elapsed_ge(5000)", "actuator_cmd": "start_next"}
   {"to": "3", "cond": "players_ge(3)", "actuator_cmd": "start_next"}
   {"to": "4", "cond_expr": "elapsed_ge(5000) and players_ge(1)", "actuator_cmd": "start_next"}
   {"to": "5", "cond": "stage_equals('stage1')", "actuator_cmd": "start_next"}

2. 作为动作（支持参数化）：
   a) 使用 func: 前缀（推荐）：
      {"to": "6", "cond": "server_ready", "actuator_cmd": "func:players_ge(3)"}
      {"to": "7", "cond": "server_ready", "actuator_cmd": "func:elapsed_ge(10000)"}
   b) 直接使用函数名（如果函数名不与 socket 命令冲突）：
      {"to": "8", "cond": "server_ready", "actuator_cmd": "players_ge(5)"}

3. 向后兼容（旧函数名仍可使用）：
   {"to": "9", "cond": "players_ge_1", "actuator_cmd": "start_next"}
   {"to": "10", "cond": "elapsed_ge_5s", "actuator_cmd": "start_next"}

优势：
- 代码复用：一个函数可以同时用于条件判断和动作执行
- 参数化：支持传入参数，避免重复定义相似函数
- 统一管理：所有函数在一个地方定义和维护
- 灵活使用：可以根据需要选择作为条件或动作

注意：
- 函数接收 context 字典，可以访问 elapsed_ms, players, server_ready, stage 等字段
- 作为动作调用时，context 中会包含 "_as_action": True，函数可以返回更详细的结果
- 参数支持：数字、字符串（用引号）、布尔值
- 自定义函数需要添加到 UNIFIED_FUNCTIONS 字典中
- 如果函数名与 socket 命令冲突，建议使用 "func:" 前缀明确指定
"""


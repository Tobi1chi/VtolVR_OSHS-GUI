"""
FSM Unified Function Configuration File
Define and customize your FSM functions here, can be used as both conditions (cond) and actions (actuator_cmd)

Design Philosophy:
- A function can be used for both condition checking and action execution
- As condition: function returns bool value (or value convertible to bool)
- As action: function returns result dict or bool value

Usage:
1. Define your functions in the UNIFIED_FUNCTIONS dictionary below
2. In FSM JSON:
   - As condition: {"cond": "function_name"} or {"cond_expr": "function_name and other"}
   - As action: {"actuator_cmd": "func:function_name"} or {"actuator_cmd": "function_name"} (if auto-registration is enabled)
"""

from typing import Callable, Dict, Any, Optional, Union


# ===== Unified Function Definitions =====
# Define your functions here, can be used as both conditions and actions
# Function signature: def function_name(context: dict, *args, **kwargs) -> Union[bool, Dict[str, Any]]
# Supports parameterized calls, for example: players_ge(3) or elapsed_ge(5000)

def elapsed_ge(context: dict, threshold_ms: int = 5000) -> Union[bool, Dict[str, Any]]:
    """
    Task elapsed time >= specified milliseconds (can be used as condition or action)
    
    Args:
        context: Context dictionary
        threshold_ms: Threshold (milliseconds), default 5000
    
    Usage examples:
    - As condition: {"cond": "elapsed_ge(5000)"} or {"cond": "elapsed_ge(10000)"}
    - As action: {"actuator_cmd": "func:elapsed_ge(5000)"}
    """
    elapsed = int(context.get("elapsed_ms", 0))
    result = elapsed >= threshold_ms
    if context.get("_as_action", False):
        return {"ok": result, "elapsed_ms": elapsed, "threshold_ms": threshold_ms}
    return result


def players_ge(context: dict, threshold: int = 1) -> Union[bool, Dict[str, Any]]:
    """
    Player count >= specified value (can be used as condition or action)
    
    Args:
        context: Context dictionary
        threshold: Threshold, default 1
    
    Usage examples:
    - As condition: {"cond": "players_ge(1)"} or {"cond": "players_ge(8)"}
    - As action: {"actuator_cmd": "func:players_ge(3)"}
    """
    players = int(context.get("players", 0))
    result = players >= threshold
    if context.get("_as_action", False):
        return {"ok": result, "players": players, "threshold": threshold}
    return result


def player(context: dict, operator: str, num: int) -> Union[bool, Dict[str, Any]]:
    """
    Player count comparison (generic function, supports multiple operators)
    
    Args:
        context: Context dictionary
        operator: Comparison operator
            - "g" or "gt": greater than (>)
            - "l" or "lt": less than (<)
            - "ge" or "gte": greater than or equal (>=)
            - "le" or "lte": less than or equal (<=)
            - "e" or "eq": equal (==)
        num: Number to compare against
    
    Usage examples:
    - As condition: {"cond": "player('ge', 6)"} or {"cond": "player('g', 5)"}
    - As action: {"actuator_cmd": "func:player('ge', 3)"}
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
    Task elapsed time check (supports time units: h=hours, m=minutes, s=seconds)
    
    Args:
        context: Context dictionary
        time_str: Time string, supported formats:
            - "1h" or "1.5h" (hours)
            - "30m" (minutes)
            - "60s" (seconds)
            - Plain number (milliseconds)
    
    Usage examples:
    - As condition: {"cond": "elapsed('1h')"} or {"cond": "elapsed('2.5h')"}
    - As action: {"actuator_cmd": "func:elapsed('30m')"}
    """
    elapsed_ms = int(context.get("elapsed_ms", 0))
    
    # Parse time string
    time_str = str(time_str).strip().lower()
    threshold_ms = 0
    
    if time_str.endswith('h'):
        # Hours
        hours = float(time_str[:-1])
        threshold_ms = int(hours * 3600 * 1000)
    elif time_str.endswith('m'):
        # Minutes
        minutes = float(time_str[:-1])
        threshold_ms = int(minutes * 60 * 1000)
    elif time_str.endswith('s'):
        # Seconds
        seconds = float(time_str[:-1])
        threshold_ms = int(seconds * 1000)
    else:
        # Assume milliseconds
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
    Check mission status
    
    Args:
        context: Context dictionary
        status: Mission status
            - "Running": Running
            - "Complete": Completed
            - "Failed": Failed
    
    Usage examples:
    - As condition: {"cond": "MissionStats('Complete')"} or {"cond": "MissionStats('Failed')"}
    - As action: {"actuator_cmd": "func:MissionStats('Running')"}
    
    Note: Requires 'mission_status' field in context
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
    """Server ready (can be used as condition or action)"""
    ready = bool(context.get("server_ready", False))
    if context.get("_as_action", False):
        return {"ok": ready, "server_ready": ready}
    return ready


def stage_equals(context: dict, target: Optional[str] = None) -> Union[bool, Dict[str, Any]]:
    """
    Current stage equals specified value (can be used as condition or action)
    
    Args:
        context: Context dictionary
        target: Target stage value, if not provided, gets from context['target_stage']
    
    Usage examples:
    - As condition: {"cond": "stage_equals('stage1')"} or {"cond": "stage_equals"}
    - As action: {"actuator_cmd": "func:stage_equals('stage1')"}
    """
    stage = context.get("stage", "")
    target_stage = target if target is not None else context.get("target_stage", "")
    result = str(stage) == str(target_stage)
    if context.get("_as_action", False):
        return {"ok": result, "stage": stage, "target_stage": target_stage, "matched": result}
    return result


# ===== Unified Function Registry =====
# Register functions to names, can be used for both conditions and actions
# Format: "function_name": function
# 
# Usage in JSON:
# - As condition: {"cond": "function_name"} or {"cond_expr": "function_name and other"}
# - As action: {"actuator_cmd": "func:function_name"}
UNIFIED_FUNCTIONS: Dict[str, Callable] = {
    # Generic functions (recommended)
    "player": player,
    "elapsed": elapsed,
    "MissionStats": MissionStats,
    
    # Parameterized functions (backward compatible)
    "elapsed_ge": elapsed_ge,
    "players_ge": players_ge,
    "server_ready": server_ready,
    "stage_equals": stage_equals,
    

    
    # You can add more unified functions:
    # "my_function": my_function,
}


# ===== Get Function Documentation =====
def get_functions_doc() -> Dict[str, str]:
    """
    Return documentation for all available functions
    
    Returns:
        Dictionary mapping function names to descriptions
    """
    return {
        "player": "Player count comparison, operators: g/gt(>), l/lt(<), ge/gte(>=), le/lte(<=), e/eq(==), example: player('ge', 6)",
        "elapsed": "Task elapsed time check, supports time units: h(hours), m(minutes), s(seconds), example: elapsed('1h') or elapsed('2.5h')",
        "MissionStats": "Check mission status: Running/Complete/Failed, example: MissionStats('Complete')",
        "elapsed_ge": "Task elapsed time >= specified milliseconds, example: elapsed_ge(5000)",
        "players_ge": "Player count >= specified value, example: players_ge(3)",
        "server_ready": "Server ready",
        "stage_equals": "Current stage equals specified value, example: stage_equals('stage1')",
        # Backward compatible
        "elapsed_ge_5s": "Task elapsed time >= 5 seconds (backward compatible)",
        "elapsed_ge_10s": "Task elapsed time >= 10 seconds (backward compatible)",
        "players_ge_1": "Player count >= 1 (backward compatible)",
        "players_ge_8": "Player count >= 8 (backward compatible)",
    }


# ===== Usage Examples =====
"""
Using these functions in JSON:

1. As conditions (supports parameterization):
   {"to": "2", "cond": "elapsed_ge(5000)", "actuator_cmd": "start_next"}
   {"to": "3", "cond": "players_ge(3)", "actuator_cmd": "start_next"}
   {"to": "4", "cond_expr": "elapsed_ge(5000) and players_ge(1)", "actuator_cmd": "start_next"}
   {"to": "5", "cond": "stage_equals('stage1')", "actuator_cmd": "start_next"}

2. As actions (supports parameterization):
   a) Using func: prefix (recommended):
      {"to": "6", "cond": "server_ready", "actuator_cmd": "func:players_ge(3)"}
      {"to": "7", "cond": "server_ready", "actuator_cmd": "func:elapsed_ge(10000)"}
   b) Direct function name (if function name doesn't conflict with socket commands):
      {"to": "8", "cond": "server_ready", "actuator_cmd": "players_ge(5)"}

3. Backward compatible (old function names still work):
   {"to": "9", "cond": "players_ge_1", "actuator_cmd": "start_next"}
   {"to": "10", "cond": "elapsed_ge_5s", "actuator_cmd": "start_next"}

Advantages:
- Code reuse: one function can be used for both condition checking and action execution
- Parameterization: supports passing arguments, avoids defining similar functions repeatedly
- Unified management: all functions defined and maintained in one place
- Flexible usage: can choose to use as condition or action as needed

Notes:
- Functions receive context dict, can access elapsed_ms, players, server_ready, stage, etc.
- When called as action, context will contain "_as_action": True, function can return more detailed results
- Parameter support: numbers, strings (with quotes), booleans
- Custom functions need to be added to UNIFIED_FUNCTIONS dictionary
- If function name conflicts with socket commands, recommend using "func:" prefix for explicit specification
"""


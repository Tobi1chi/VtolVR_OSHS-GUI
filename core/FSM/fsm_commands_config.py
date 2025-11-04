"""
FSM 指令配置文件
在这里定义和自定义你的 FSM actuator_cmd 指令

使用方法：
1. 在下面的 CUSTOM_COMMANDS 字典中定义你的命令
2. 在 CUSTOM_ACTION_HANDLERS 字典中注册自定义处理器
3. 在 FSM JSON 的 actuator_cmd 字段中使用这些命令
"""

from typing import Callable, Dict, Any, Optional
from core.Socket.socket_service import socket_service


# ===== 命令定义 =====
# 在这里定义你的命令列表，用于文档和验证
# 格式: "命令名": "命令描述"
CUSTOM_COMMANDS = {
    # Socket 命令（默认，直接发送）
    "start_next": "进入下一环节/任务",
    "fallback": "条件未命中时的兜底指令",
    "getstage": "请求服务器下发当前阶段",
    "host": "启动服务器",
    "start": "开始游戏",
    "skip": "跳过当前任务",
    "restart": "重启游戏",
    "quit": "退出游戏",
    
    # 自定义命令示例（需要注册处理器）
    # "custom:my_command": "自定义命令示例",
}


# ===== 自定义 Action 处理器 =====
# 在这里定义你的自定义处理器函数
# 函数签名: def handler_name(command: str, context: dict) -> None

def log_action_handler(command: str, context: dict) -> None:
    """日志记录处理器示例"""
    print(f"[FSM Log] 执行命令: {command}")
    print(f"[FSM Log] 上下文: {context}")


def custom_logic_handler(command: str, context: dict) -> None:
    """自定义逻辑处理器示例"""
    # 根据命令执行不同的逻辑
    if command == "my_command":
        print(f"执行自定义命令: {command}")
        # 你的自定义逻辑
        # 例如：调用其他模块的函数
        # 例如：修改全局状态
        # 例如：触发事件
    else:
        print(f"未知的自定义命令: {command}")


# ===== 处理器注册映射 =====
# 将自定义处理器注册到 action 类型
# 格式: "action_prefix": handler_function
# 在 JSON 中使用: {"actuator_cmd": "action_prefix:command"}
CUSTOM_ACTION_HANDLERS: Dict[str, Callable[[str, dict], None]] = {
    # 示例：注册 "log" 前缀的处理器
    # "log": log_action_handler,
    
    # 示例：注册 "custom" 前缀的处理器
    # "custom": custom_logic_handler,
    
    # 你可以添加更多处理器：
    # "timer": timer_action_handler,
    # "file": file_action_handler,
    # "notify": notification_handler,
}


# ===== 配置初始化函数 =====
def register_custom_commands(actuator_instance) -> None:
    """
    将自定义命令注册到 FSM Actuator
    
    Args:
        actuator_instance: FSMActuator 实例
    """
    # 注册所有自定义处理器
    for action_prefix, handler in CUSTOM_ACTION_HANDLERS.items():
        actuator_instance.register_action(action_prefix, handler)
        print(f"[FSM Config] 已注册 action 处理器: {action_prefix}")


# ===== 获取命令文档 =====
def get_commands_doc() -> Dict[str, str]:
    """
    返回所有可用命令的文档
    
    Returns:
        命令名到描述的字典
    """
    return CUSTOM_COMMANDS.copy()


# ===== 使用示例 =====
"""
在 JSON 中使用这些命令：

1. Socket 命令（默认，无需前缀）：
   {"to": "2", "cond": "elapsed_ge_5s", "actuator_cmd": "start_next"}

2. 自定义处理器（需要前缀）：
   {"to": "3", "cond": "some_cond", "actuator_cmd": "log:test_command"}
   {"to": "4", "cond": "other_cond", "actuator_cmd": "custom:my_command"}

3. 多个命令（需要修改 fsm_actuator 支持，或使用逗号分隔）：
   {"actuator_cmd": "start_next,log:action_logged"}
"""


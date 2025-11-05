from typing import Callable, Dict, Optional, Any, Union, Tuple
from core.Socket.socket_service import socket_service

# 导入配置文件
try:
    from core.FSM.fsm_commands_config import register_custom_commands
except ImportError:
    # 如果配置文件不存在，使用空函数
    def register_custom_commands(actuator_instance):
        pass


class FSMActuator:
    """
    FSM Action 执行器：
    - 负责解释和执行 FSM 转移中的 actuator_cmd
    - 支持注册不同类型的 action 处理器（socket 命令、自定义函数等）
    - 提供统一的执行接口
    """

    def __init__(self):
        self.action_registry: Dict[str, Callable[[str, dict], Optional[Union[bool, Dict[str, Any]]]]] = {}
        self._register_default_actions()
        # 加载自定义命令配置
        register_custom_commands(self)

    def _register_default_actions(self):
        """注册默认的 action 处理器"""
        # 默认行为：将所有未注册的 action 当作 socket 命令发送
        self.register_action("socket", self._execute_socket_command)

    def register_action(self, action_name: str, handler: Callable[[str, dict], Optional[Union[bool, Dict[str, Any]]]]) -> None:
        """
        注册一个 action 处理器
        
        Args:
            action_name: action 名称（如 "socket", "custom_func"）
            handler: 处理函数，接收 (command_str, context) 参数，可返回结果字典
        """
        self.action_registry[action_name] = handler

    def execute(self, actuator_cmd: str, context: Optional[dict] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        执行 actuator_cmd
        
        Args:
            actuator_cmd: 要执行的命令字符串
            context: 可选的上下文信息（用于传递给自定义处理器）
        
        Returns:
            (是否执行成功, 执行结果（如果有）)
        
        支持的格式：
        1. 普通字符串（如 "start_next"）：作为 socket 命令发送
        2. 带前缀的格式（如 "socket:start_next"）：明确指定使用 socket 处理器
        3. 自定义格式（如 "custom:func_name"）：使用注册的自定义处理器
        """
        if not actuator_cmd or not actuator_cmd.strip():
            return False, None

        context = context or {}
        cmd_str = actuator_cmd.strip()

        # 检查是否有前缀（格式：prefix:command）
        if ':' in cmd_str:
            prefix, command = cmd_str.split(':', 1)
            prefix = prefix.strip().lower()
            command = command.strip()

            handler = self.action_registry.get(prefix)
            if handler:
                try:
                    result = handler(command, context)
                    # 如果返回的是字典，则认为是执行结果
                    if isinstance(result, dict):
                        return True, result
                    # 如果返回的是布尔值，则认为是执行状态
                    elif isinstance(result, bool):
                        return result, None
                    # 其他情况认为执行成功但无返回值
                    else:
                        return True, None
                except Exception as e:
                    print(f"[FSMActuator] 执行 action '{prefix}:{command}' 失败: {e}")
                    return False, None
            else:
                # 未找到处理器，回退到默认 socket 行为
                print(f"[FSMActuator] 未找到 action 处理器 '{prefix}'，回退到 socket")
                success = self._execute_socket_command(cmd_str, context)
                return success, None
        else:
            # 无前缀，默认作为 socket 命令
            success = self._execute_socket_command(cmd_str, context)
            return success, None

    def _execute_socket_command(self, command: str, context: dict) -> Union[bool, Dict[str, Any]]:
        """执行 socket 命令（默认处理器）"""
        try:
            socket_service.send_command(command)
            return True
        except Exception as e:
            print(f"[FSMActuator] 发送 socket 命令失败: {e}")
            return False
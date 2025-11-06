from typing import Callable, Dict, Optional, Any, Union, Tuple, List
from core.Socket.socket_service import socket_service
from PyQt6.QtCore import QTimer, QObject

# 导入统一函数注册表
try:
    from core.FSM.fsm_functions_config import UNIFIED_FUNCTIONS
except ImportError:
    UNIFIED_FUNCTIONS = {}


class FSMActuator(QObject):
    """
    FSM Action 执行器：
    - 负责解释和执行 FSM 转移中的 actuator_cmd
    - 支持注册不同类型的 action 处理器（socket 命令、自定义函数等）
    - 提供统一的执行接口
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.action_registry: Dict[str, Callable[[str, dict], Optional[Union[bool, Dict[str, Any]]]]] = {}
        self._pending_delays: Dict[int, QTimer] = {}  # 存储待执行的延迟任务
        self._pending_transitions: Dict[int, tuple] = {}  # 存储待执行的状态转移 (timer_id, next_key, callback)
        self._register_default_actions()
        # 注册统一函数作为动作处理器（使用 "func" 前缀）
        self._register_unified_functions()
        # 注册延迟动作处理器
        self._register_delay_action()

    def _register_default_actions(self):
        """注册默认的 action 处理器"""
        # 默认行为：将所有未注册的 action 当作 socket 命令发送
        self.register_action("socket", self._execute_socket_command)
    
    def _register_delay_action(self):
        """注册延迟动作处理器"""
        def delay_handler(command: str, context: dict) -> Optional[Union[bool, Dict[str, Any]]]:
            """
            延迟动作处理器：delay:time,command 格式
            例如：delay:5s,start_next 表示延迟5秒后执行 start_next
            
            Args:
                command: 延迟时间和命令，格式 "time,command" 或 "time"
                context: 上下文
            """
            # 解析命令：time,command 或 time
            parts = command.split(',', 1)
            time_str = parts[0].strip()
            delayed_command = parts[1].strip() if len(parts) > 1 else None
            
            # 解析时间字符串
            delay_ms = self._parse_time_string(time_str)
            if delay_ms <= 0:
                return {"ok": False, "error": f"无效的延迟时间: {time_str}"}
            
            # 创建延迟定时器（使用 self 作为父对象）
            timer = QTimer(self)
            timer.setSingleShot(True)
            
            # 设置延迟后执行的回调
            timer_id = id(timer)
            def delayed_execute():
                if delayed_command:
                    # 延迟后执行命令
                    success, result, _ = self.execute(delayed_command, context)
                    # 输出到终端（如果可用）
                    try:
                        from GUI.MainPage import terminal
                        if terminal:
                            terminal.append_output(f"[FSM Delay] 延迟 {time_str} 后执行命令: {delayed_command}")
                            if result:
                                terminal.append_output(f"[FSM Delay] 返回结果: {result}")
                    except:
                        print(f"[FSMActuator Delay] 延迟 {time_str} 后执行命令: {delayed_command}, 结果: {success}")
                
                # 检查是否有待执行的状态转移回调（延迟完成后调用）
                if timer_id in self._pending_transitions:
                    _, _, callback = self._pending_transitions[timer_id]
                    if callback:
                        callback()
                    del self._pending_transitions[timer_id]
                
                # 清理定时器引用
                if timer_id in self._pending_delays:
                    del self._pending_delays[timer_id]
            
            timer.timeout.connect(delayed_execute)
            timer.start(delay_ms)
            
            # 保存定时器引用（防止被垃圾回收）
            self._pending_delays[id(timer)] = timer
            
            # 输出延迟信息到终端（如果可用）
            try:
                from GUI.MainPage import terminal
                if terminal:
                    terminal.append_output(f"[FSM] 已设置延迟 {time_str}，将在延迟后执行命令: {delayed_command or '(无)'}")
            except:
                pass
            
            timer_id = id(timer)
            return {
                "ok": True,
                "delay_ms": delay_ms,
                "delay_str": time_str,
                "delayed_command": delayed_command,
                "timer_id": timer_id,  # 返回定时器 ID，用于关联回调
                "message": f"已设置延迟 {time_str}，将在延迟后执行命令"
            }
        
        self.register_action("delay", delay_handler)
    
    def _set_delay_complete_callback(self, delay_result: Dict[str, Any], callback: Callable[[], None]):
        """
        为延迟操作设置完成回调
        
        Args:
            delay_result: delay 操作的返回结果（包含 timer_id）
            callback: 延迟完成后要调用的回调函数
        """
        timer_id = delay_result.get("timer_id")
        if timer_id and timer_id in self._pending_delays:
            self._pending_transitions[timer_id] = (timer_id, None, callback)
    
    def _parse_time_string(self, time_str: str) -> int:
        """
        解析时间字符串，返回毫秒数
        
        支持格式：
        - "5s" 或 "5.5s" (秒)
        - "10m" 或 "10.5m" (分钟)
        - "1h" 或 "1.5h" (小时)
        - 纯数字（毫秒）
        """
        time_str = str(time_str).strip().lower()
        
        if time_str.endswith('h'):
            # 小时
            hours = float(time_str[:-1])
            return int(hours * 3600 * 1000)
        elif time_str.endswith('m'):
            # 分钟
            minutes = float(time_str[:-1])
            return int(minutes * 60 * 1000)
        elif time_str.endswith('s'):
            # 秒
            seconds = float(time_str[:-1])
            return int(seconds * 1000)
        else:
            # 假设是毫秒
            try:
                return int(float(time_str))
            except ValueError:
                return 0
    
    def _register_unified_functions(self):
        """注册统一函数作为动作处理器（使用 func 前缀）"""
        def unified_function_handler(command: str, context: dict) -> Optional[Union[bool, Dict[str, Any]]]:
            """
            统一函数处理器：使用 func:function_name 或 func:function_name(args) 格式调用
            
            Args:
                command: 函数名称或函数调用（如 "players_ge(3)"）
                context: 上下文
            """
            # 解析函数调用（支持参数）
            func_name, args = self._parse_function_call(command)
            
            func = UNIFIED_FUNCTIONS.get(func_name)
            if func is None:
                return {"ok": False, "error": f"统一函数 '{func_name}' 未找到"}
            
            # 设置标志，表示这是作为动作调用
            action_context = {**context, "_as_action": True}
            try:
                result = func(action_context, *args) if args else func(action_context)
                # 如果返回字典，直接返回
                if isinstance(result, dict):
                    return result
                # 如果返回 bool，转换为字典格式
                elif isinstance(result, bool):
                    return {"ok": result, "function": func_name}
                # 其他情况
                else:
                    return {"ok": True, "function": func_name, "result": result}
            except Exception as e:
                return {"ok": False, "error": str(e), "function": func_name}
        
        # 注册 "func" 前缀处理器
        self.register_action("func", unified_function_handler)
    
    def _parse_function_call(self, cmd_str: str) -> Tuple[str, List[Any]]:
        """
        解析函数调用字符串，提取函数名和参数
        
        Args:
            cmd_str: 函数调用字符串，如 "players_ge(3)" 或 "server_ready"
        
        Returns:
            (函数名, 参数列表)
        """
        if '(' in cmd_str and cmd_str.endswith(')'):
            func_name = cmd_str[:cmd_str.index('(')].strip()
            args_str = cmd_str[cmd_str.index('(')+1:-1].strip()
            
            # 解析参数
            args = []
            if args_str:
                # 简单的参数解析
                import re
                # 匹配字符串（单引号或双引号）、数字、或其他标识符
                pattern = r'(".*?"|\'.*?\'|\d+\.?\d*|[^,\s]+)'
                matches = re.findall(pattern, args_str)
                for match in matches:
                    match = match.strip()
                    if not match or match == ',':
                        continue
                    # 字符串字面量
                    if (match.startswith('"') and match.endswith('"')) or \
                       (match.startswith("'") and match.endswith("'")):
                        args.append(match[1:-1])  # 移除引号
                    # 数字
                    elif match.replace('.', '').replace('-', '').isdigit():
                        try:
                            args.append(float(match) if '.' in match else int(match))
                        except ValueError:
                            args.append(match)
                    # 布尔值
                    elif match.lower() == 'true':
                        args.append(True)
                    elif match.lower() == 'false':
                        args.append(False)
                    else:
                        args.append(match)
            
            return func_name, args
        else:
            return cmd_str.strip(), []

    def register_action(self, action_name: str, handler: Callable[[str, dict], Optional[Union[bool, Dict[str, Any]]]]) -> None:
        """
        注册一个 action 处理器
        
        Args:
            action_name: action 名称（如 "socket", "custom_func"）
            handler: 处理函数，接收 (command_str, context) 参数，可返回结果字典
        """
        self.action_registry[action_name] = handler

    def execute(self, actuator_cmd: str, context: Optional[dict] = None, 
                on_complete: Optional[Callable[[], None]] = None) -> Tuple[bool, Optional[Dict[str, Any]], bool]:
        """
        执行 actuator_cmd
        
        Args:
            actuator_cmd: 要执行的命令字符串
            context: 可选的上下文信息（用于传递给自定义处理器）
            on_complete: 可选的回调函数，在所有 action 完成后调用（包括延迟）
        
        Returns:
            (是否执行成功, 执行结果（如果有）, 是否有延迟操作)
        
        支持的格式：
        1. 普通字符串（如 "start_next"）：作为 socket 命令发送
        2. 带前缀的格式（如 "socket:start_next"）：明确指定使用 socket 处理器
        3. 自定义格式（如 "custom:func_name"）：使用注册的自定义处理器
        4. 延迟格式（如 "delay:5s,start_next"）：延迟后执行命令
        """
        if not actuator_cmd or not actuator_cmd.strip():
            return False, None, False

        context = context or {}
        cmd_str = actuator_cmd.strip()
        has_delay = False

        # 检查是否有前缀（格式：prefix:command）
        if ':' in cmd_str:
            prefix, command = cmd_str.split(':', 1)
            prefix = prefix.strip().lower()
            command = command.strip()

            handler = self.action_registry.get(prefix)
            if handler:
                try:
                    result = handler(command, context)
                    # 检查是否是延迟操作
                    if prefix == "delay":
                        has_delay = True
                        # 如果有延迟，设置完成回调
                        if on_complete:
                            self._set_delay_complete_callback(result, on_complete)
                    
                    # 如果返回的是字典，则认为是执行结果
                    if isinstance(result, dict):
                        return True, result, has_delay
                    # 如果返回的是布尔值，则认为是执行状态
                    elif isinstance(result, bool):
                        return result, None, has_delay
                    # 其他情况认为执行成功但无返回值
                    else:
                        return True, None, has_delay
                except Exception as e:
                    print(f"[FSMActuator] 执行 action '{prefix}:{command}' 失败: {e}")
                    return False, None, False
            else:
                # 未找到处理器，回退到默认 socket 行为
                print(f"[FSMActuator] 未找到 action 处理器 '{prefix}'，回退到 socket")
                success = self._execute_socket_command(cmd_str, context)
                return success, None, False
        else:
            # 无前缀，检查是否是统一函数名（支持函数调用）
            func_name, args = self._parse_function_call(cmd_str)
            if func_name in UNIFIED_FUNCTIONS:
                # 直接使用统一函数（作为动作）
                func = UNIFIED_FUNCTIONS[func_name]
                action_context = {**context, "_as_action": True}
                try:
                    result = func(action_context, *args) if args else func(action_context)
                    if isinstance(result, dict):
                        return True, result, False
                    elif isinstance(result, bool):
                        return result, {"ok": result, "function": func_name}, False
                    else:
                        return True, {"ok": True, "function": func_name, "result": result}, False
                except Exception as e:
                    print(f"[FSMActuator] 执行统一函数 '{func_name}' 失败: {e}")
                    return False, None, False
            else:
                # 默认作为 socket 命令
                success = self._execute_socket_command(cmd_str, context)
                return success, None, False

    def _execute_socket_command(self, command: str, context: dict) -> Union[bool, Dict[str, Any]]:
        """执行 socket 命令（默认处理器）"""
        try:
            socket_service.send_command(command)
            return True
        except Exception as e:
            print(f"[FSMActuator] 发送 socket 命令失败: {e}")
            return False


# 全局 FSM Actuator 实例
fsm_actuator = FSMActuator()
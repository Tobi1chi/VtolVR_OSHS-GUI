import uuid
from typing import Callable, Dict, Optional, Any, Union, Tuple, List
from core.Socket.socket_service import socket_service
from PyQt6.QtCore import QObject
from core.Timer import TimerManager

# Import unified function registry
try:
    from core.FSM.fsm_functions_config import UNIFIED_FUNCTIONS
except ImportError:
    UNIFIED_FUNCTIONS = {}


class FSMActuator(QObject):
    """
    FSM Action Executor:
    - Responsible for interpreting and executing actuator_cmd in FSM transitions
    - Supports registering different types of action handlers (socket commands, custom functions, etc.)
    - Provides unified execution interface
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.action_registry: Dict[str, Callable[[str, dict], Optional[Union[bool, Dict[str, Any]]]]] = {}
        self.timer_manager = TimerManager(self)
        self._pending_delays: Dict[str, Dict[str, Any]] = {}
        self._pending_transitions: Dict[str, Callable[[], None]] = {}
        self._register_default_actions()
        # Register unified functions as action handlers (using "func" prefix)
        self._register_unified_functions()
        # Register delay action handler
        self._register_delay_action()

    def _register_default_actions(self):
        """Register default action handlers"""
        # Default behavior: send all unregistered actions as socket commands
        self.register_action("socket", self._execute_socket_command)
        # Register init action handler
        self.register_action("init", self._execute_init_action)
    
    def _register_delay_action(self):
        """Register delay action handler"""
        def delay_handler(command: str, context: dict) -> Optional[Union[bool, Dict[str, Any]]]:
            """
            Delay action handler: delay:time,command format
            Example: delay:5s,start_next means execute start_next after 5 seconds delay
            
            Args:
                command: Delay time and command, format "time,command" or "time"
                context: Context
            """
            # Parse command: time,command or time
            parts = command.split(',', 1)
            time_str = parts[0].strip()
            delayed_command = parts[1].strip() if len(parts) > 1 else None
            
            # Parse time string
            delay_ms = self._parse_time_string(time_str)
            if delay_ms <= 0:
                return {"ok": False, "error": f"Invalid delay time: {time_str}"}
            
            timer_name = f"fsm_delay_{id(self)}_{uuid.uuid4().hex}"
            def delayed_execute():
                if delayed_command:
                    # Execute command after delay
                    success, result, _ = self.execute(delayed_command, context)
                    # Output to terminal (if available)
                    try:
                        from GUI.MainPage import terminal
                        if terminal:
                            terminal.append_output(f"[FSM Delay] Executed command after {time_str} delay: {delayed_command}")
                            if result:
                                terminal.append_output(f"[FSM Delay] Return result: {result}")
                    except:
                        print(f"[FSMActuator Delay] Executed command after {time_str} delay: {delayed_command}, result: {success}")
                
                callback = self._pending_transitions.pop(timer_name, None)
                if callback:
                    callback()
                self._pending_delays.pop(timer_name, None)
            
            self._start_single_shot_timer(timer_name, delay_ms, delayed_execute)
            self._pending_delays[timer_name] = {
                "name": timer_name,
                "command": delayed_command,
                "delay_ms": delay_ms,
            }
            
            # Output delay info to terminal (if available)
            try:
                from GUI.MainPage import terminal
                if terminal:
                    terminal.append_output(f"[FSM] Delay set to {time_str}, will execute command after delay: {delayed_command or '(none)'}")
            except:
                pass
            
            return {
                "ok": True,
                "delay_ms": delay_ms,
                "delay_str": time_str,
                "delayed_command": delayed_command,
                "timer_name": timer_name,
                "message": f"Delay set to {time_str}, will execute command after delay"
            }
        
        self.register_action("delay", delay_handler)

    def _start_single_shot_timer(self, timer_name: str, interval_ms: int, callback: Callable[[], None]) -> None:
        """
        Helper to start a single-shot timer managed by TimerManager.
        Ensures timer cleanup after execution.
        """
        def wrapper():
            try:
                callback()
            finally:
                self.timer_manager.stop_timer(timer_name)

        self.timer_manager.start_timer(timer_name, interval_ms, wrapper, single_shot=True)
    
    def _set_delay_complete_callback(self, delay_result: Dict[str, Any], callback: Callable[[], None]):
        """
        Set completion callback for delay operation
        
        Args:
            delay_result: Return result of delay operation (contains timer_id)
            callback: Callback function to call after delay completes
        """
        timer_name = delay_result.get("timer_name") or delay_result.get("timer_id")
        if timer_name and timer_name in self._pending_delays:
            self._pending_transitions[timer_name] = callback
    
    def _parse_time_string(self, time_str: str) -> int:
        """
        Parse time string, return milliseconds
        
        Supported formats:
        - "5s" or "5.5s" (seconds)
        - "10m" or "10.5m" (minutes)
        - "1h" or "1.5h" (hours)
        - Plain number (milliseconds)
        """
        time_str = str(time_str).strip().lower()
        
        if time_str.endswith('h'):
            # Hours
            hours = float(time_str[:-1])
            return int(hours * 3600 * 1000)
        elif time_str.endswith('m'):
            # Minutes
            minutes = float(time_str[:-1])
            return int(minutes * 60 * 1000)
        elif time_str.endswith('s'):
            # Seconds
            seconds = float(time_str[:-1])
            return int(seconds * 1000)
        else:
            # Assume milliseconds
            try:
                return int(float(time_str))
            except ValueError:
                return 0
    
    def _register_unified_functions(self):
        """Register unified functions as action handlers (using func prefix)"""
        def unified_function_handler(command: str, context: dict) -> Optional[Union[bool, Dict[str, Any]]]:
            """
            Unified function handler: use func:function_name or func:function_name(args) format
            
            Args:
                command: Function name or function call (like "players_ge(3)")
                context: Context
            """
            # Parse function call (supports arguments)
            func_name, args = self._parse_function_call(command)
            
            func = UNIFIED_FUNCTIONS.get(func_name)
            if func is None:
                return {"ok": False, "error": f"Unified function '{func_name}' not found"}
            
            # Set flag to indicate this is called as an action
            action_context = {**context, "_as_action": True}
            try:
                result = func(action_context, *args) if args else func(action_context)
                # If returns dict, return directly
                if isinstance(result, dict):
                    return result
                # If returns bool, convert to dict format
                elif isinstance(result, bool):
                    return {"ok": result, "function": func_name}
                # Other cases
                else:
                    return {"ok": True, "function": func_name, "result": result}
            except Exception as e:
                return {"ok": False, "error": str(e), "function": func_name}
        
        # Register "func" prefix handler
        self.register_action("func", unified_function_handler)
    
    def _parse_function_call(self, cmd_str: str) -> Tuple[str, List[Any]]:
        """
        Parse function call string, extract function name and arguments
        
        Args:
            cmd_str: Function call string, like "players_ge(3)" or "server_ready"
        
        Returns:
            (function_name, argument_list)
        """
        if '(' in cmd_str and cmd_str.endswith(')'):
            func_name = cmd_str[:cmd_str.index('(')].strip()
            args_str = cmd_str[cmd_str.index('(')+1:-1].strip()
            
            # Parse arguments
            args = []
            if args_str:
                # Simple argument parsing
                import re
                # Match strings (single or double quotes), numbers, or other identifiers
                pattern = r'(".*?"|\'.*?\'|\d+\.?\d*|[^,\s]+)'
                matches = re.findall(pattern, args_str)
                for match in matches:
                    match = match.strip()
                    if not match or match == ',':
                        continue
                    # String literal
                    if (match.startswith('"') and match.endswith('"')) or \
                       (match.startswith("'") and match.endswith("'")):
                        args.append(match[1:-1])  # Remove quotes
                    # Number
                    elif match.replace('.', '').replace('-', '').isdigit():
                        try:
                            args.append(float(match) if '.' in match else int(match))
                        except ValueError:
                            args.append(match)
                    # Boolean
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
        Register an action handler
        
        Args:
            action_name: Action name (like "socket", "custom_func")
            handler: Handler function, receives (command_str, context) parameters, can return result dict
        """
        self.action_registry[action_name] = handler

    def execute(self, actuator_cmd: str, context: Optional[dict] = None, 
                on_complete: Optional[Callable[[], None]] = None) -> Tuple[bool, Optional[Dict[str, Any]], bool]:
        """
        Execute actuator_cmd
        
        Args:
            actuator_cmd: Command string to execute
            context: Optional context information (passed to custom handlers)
            on_complete: Optional callback function, called after all actions complete (including delays)
        
        Returns:
            (whether execution succeeded, execution result (if any), whether has delay operation)
        
        Supported formats:
        1. Plain string (like "start_next"): sent as socket command
        2. Prefixed format (like "socket:start_next"): explicitly specify using socket handler
        3. Custom format (like "custom:func_name"): use registered custom handler
        4. Delay format (like "delay:5s,start_next"): execute command after delay
        """
        if not actuator_cmd or not actuator_cmd.strip():
            return False, None, False

        context = context or {}
        cmd_str = actuator_cmd.strip()
        has_delay = False

        # Check if there's a prefix (format: prefix:command)
        if ':' in cmd_str:
            prefix, command = cmd_str.split(':', 1)
            prefix = prefix.strip().lower()
            command = command.strip()

            handler = self.action_registry.get(prefix)
            if handler:
                try:
                    result = handler(command, context)
                    # Check if it's a delay operation
                    if prefix == "delay":
                        has_delay = True
                        # If there's a delay, set completion callback
                        if on_complete:
                            self._set_delay_complete_callback(result, on_complete)
                    
                    # If return is dict, treat as execution result
                    if isinstance(result, dict):
                        return True, result, has_delay
                    # If return is bool, treat as execution status
                    elif isinstance(result, bool):
                        return result, None, has_delay
                    # Other cases treat as successful execution with no return value
                    else:
                        return True, None, has_delay
                except Exception as e:
                    print(f"[FSMActuator] Failed to execute action '{prefix}:{command}': {e}")
                    return False, None, False
            else:
                # Handler not found, fall back to default socket behavior
                print(f"[FSMActuator] Action handler '{prefix}' not found, falling back to socket")
                success = self._execute_socket_command(cmd_str, context)
                return success, None, False
        else:
            # No prefix, check if it's a unified function name (supports function calls)
            func_name, args = self._parse_function_call(cmd_str)
            if func_name in UNIFIED_FUNCTIONS:
                # Directly use unified function (as action)
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
                    print(f"[FSMActuator] Failed to execute unified function '{func_name}': {e}")
                    return False, None, False
            else:
                # Default as socket command
                success = self._execute_socket_command(cmd_str, context)
                return success, None, False

    def _execute_init_action(self, command: str, context: dict) -> Union[bool, Dict[str, Any]]:
        """
        Execute initialization action: automatically configure and start map based on campaign id and mapname
        
        Args:
            command: Format "campaign_id,mapname"
            context: Context dictionary
        
        Returns:
            Execution result
        """
        try:
            parts = command.split(',')
            if len(parts) < 2:
                print(f"[FSMActuator Init] Error: init command format should be 'campaign_id,mapname'")
                return False
            
            campaign_id = parts[0].strip()
            mapname = parts[1].strip()
            
            # Execute configuration command sequence using TimerManager for non-blocking scheduling
            command_1 = [
                f"sethost campaign {campaign_id}",
                f"sethost mission {mapname}",
                "config",
                "checkhost",
                "host"
            ]
            command_2 = [
                f"sethost campaign {campaign_id}",
                f"sethost mission {mapname}",
                "checkhost",
                "config",
                "restart"
            ]


            commands = command_1
            # Use TimerManager to send commands sequentially, with 100ms interval between each
            delay = 0
            base_timer_name = f"fsm_init_{id(self)}_{uuid.uuid4().hex}"
            for index, cmd in enumerate(commands):
                timer_name = f"{base_timer_name}_{index}"

                def send_command(command_to_send: str):
                    def _send():
                        socket_service.send_command(command_to_send)
                    return _send

                self._start_single_shot_timer(timer_name, delay, send_command(cmd))
                
                delay += 100  # 100ms interval between each command
            try:
                from GUI.MainPage import tm
                if not tm.is_stopwatch_running("task_timer"):
                    tm.start_stopwatch("task_timer")
            except Exception as exc:
                print(f"[FSMActuator Init] Warning: failed to start task_timer stopwatch: {exc}")
            return {
                "ok": True,
                "campaign_id": campaign_id,
                "mapname": mapname,
                "commands": commands
            }
        except Exception as e:
            print(f"[FSMActuator Init] Failed to execute init action: {e}")
            return False
    
    def _execute_socket_command(self, command: str, context: dict) -> Union[bool, Dict[str, Any]]:
        """Execute socket command (default handler)"""
        try:
            socket_service.send_command(command)
            return True
        except Exception as e:
            print(f"[FSMActuator] Failed to send socket command: {e}")
            return False


# Global FSM Actuator instance
fsm_actuator = FSMActuator()
import json.tool
import sys
import socket
import threading
import time
import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QTextEdit,
    QHBoxLayout, QVBoxLayout, QSplitter, QComboBox, QCheckBox,
    QLabel, QStackedWidget, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QFont
from core.Socket import SocketWorker
from core.Socket import socket_service
from core.SysState import SysState
from core.StringParser import JsonParser
from core.ServerReplyProcess import ServerReplyProcess
from core.ReplayPackger import replayPacker
from core.Timer import TimerManager
from core.FSM import FSMEngine
from core.FSM import fsm_actuator
from core.FSM import get_default_condition_registry
serverReplyProcess = ServerReplyProcess()
rpPacker = replayPacker()
terminal = None

tm = TimerManager()
# Old test FSMActuator has been removed, now using core.FSM.fsm_actuator
#Private constants
S2MS = 1000
MIN2MS = 60 * S2MS
H2MS = 60 * MIN2MS
# ========== Page 1: Main Page ==========
class MainPage(QWidget):
    def __init__(self, switch_callback):
        super().__init__()
        self.switch_callback = switch_callback
        self.task_running:bool = False
        self.auto_fsm_enabled: bool = False
        self.auto_fsm_timer = None
        global tm
        layout = QVBoxLayout()
        self.setLayout(layout)
        # Top bar
        top_bar = QHBoxLayout()
        buttons = ["Connect", "Clear", "Check Host", "Config Host", "Host", "Start", "Skip", "Restart", "Quit", "Quit Server"]
        buttons.append("Test")
        buttons.append("Load FSM")
        buttons.append("Run FSM")
        buttons.append("Auto FSM")
        for name in buttons:
            btn = QPushButton(name)
            if name == "Quit":
                btn.clicked.connect(self.quit_game)
            elif name == "Connect":
                btn.clicked.connect(self.connect_terminal)
            elif name == "Host":
                btn.clicked.connect(self.host_game)
            elif name == "Check Host":
                btn.clicked.connect(self.check_host)
            elif name == "Config Host":
                btn.clicked.connect(self.config_host)
            elif name == "Start":
                btn.clicked.connect(self.start_game)
            elif name == "Skip":
                btn.clicked.connect(self.skip_game)
            elif name == "Restart":
                btn.clicked.connect(self.restart_game)
            elif name == "Quit Server":
                btn.clicked.connect(self.quit_server)
            elif name == "Clear":
                btn.clicked.connect(self.clear_console)
            elif name == "Test":
                btn.clicked.connect(self.TestFunc)
            elif name == "Load FSM":
                btn.clicked.connect(self.load_fsm_config)
            elif name == "Run FSM":
                btn.clicked.connect(self.run_fsm_step)
            elif name == "Auto FSM":
                btn.setCheckable(True)
                btn.clicked.connect(self.toggle_auto_fsm)
            top_bar.addWidget(btn)

        self.switch_btn = QPushButton("Mission Editor")
        self.switch_btn.setStyleSheet("background-color: #FFD700; font-weight: bold;")
        self.switch_btn.clicked.connect(self.switch_callback)
        top_bar.addWidget(self.switch_btn)
        #top_bar.addStretch()
        layout.addLayout(top_bar)

        # Main content
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Terminal
        self.terminal = TerminalWidget()
        global terminal
        terminal = self.terminal
        # Right: Dashboard
        self.dashboard = DashboardWidget(self.terminal)

        splitter.addWidget(self.terminal)
        splitter.addWidget(self.dashboard)
        splitter.setSizes([300, 900])  # Initial ratio

        layout.addWidget(splitter)

        # ===== FSM Engine and Condition Registry =====
        self._load_and_init_fsm()
        
        # Initialize auto FSM detection timer (disabled by default)
        self._init_auto_fsm_timer()
        
        # Initialize log recording related
        self.current_session_id = None
    
    def _save_session_logs(self):
        """
        Save current session logs (flightlog and debuglog)
        """
        global rpPacker
        
        # If flightlog is not empty, save it
        if serverReplyProcess.flightlog:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"flightlog_{timestamp}.txt"
            rpPacker.SaveFlightlog(serverReplyProcess.flightlog, filename)
        
        # If debuglog is not empty, save it
        if serverReplyProcess.debuglog:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"debuglog_{timestamp}.txt"
            rpPacker.SaveDebuglog(serverReplyProcess.debuglog, filename)

    def connect_terminal(self):
        self.terminal.connect_to_server()
    def host_game(self):
        # Before starting new session, save previous session logs
        self._save_session_logs()
        serverReplyProcess.clear_session_logs()
        self.terminal.send_command_api("host")
    def check_host(self):
        self.terminal.send_command_api("checkhost")
    def config_host(self):
        self.terminal.send_command_api("config")
    def start_game(self):
        # Before starting game, save previous session logs
        self._save_session_logs()
        serverReplyProcess.clear_session_logs()
        self.terminal.send_command_api("start")
    def skip_game(self):
        self.terminal.send_command_api("skip")
    def restart_game(self):
        # Save current session logs before restart
        self._save_session_logs()
        serverReplyProcess.clear_session_logs()
        self.terminal.send_command_api("restart")
    def quit_game(self):
        # Save current session logs before quit
        self._save_session_logs()
        serverReplyProcess.clear_session_logs()
        self.terminal.send_command_api("quit")
    def quit_server(self):
        self.terminal.send_command_api("exitapp")
    def clear_console(self):
        self.terminal.clear()
    def TestFunc(self):
        # Use Test button as demo: first click starts task timer; second click ends and evaluates conditions to advance state and send commands
        if not self.task_running:
            self.task_running = True
            self.TestClick = True
            # Use TimerManager to start task timer
            tm.start_stopwatch("task_timer")
            # Ensure socket is connected
            if not socket_service.is_connected():
                socket_service.connect()
            # Start FSM to an initial state (if not specified in JSON, can choose "1")
            if self.fsm_engine:
                start_key = next(iter(self.fsm_engine.state_by_key.keys()), None)
                if start_key:
                    self.fsm_engine.start(start_key)
            self.terminal.append_output("[Demo] Task started, timer started")
        else:
            self.task_running = False
            self.TestClick = False
            # Use TimerManager to stop task timer and get elapsed time
            elapsed = tm.stop_stopwatch("task_timer")
            if elapsed is None:
                elapsed = 0
            context = {
                "elapsed_ms": elapsed,
                "server_ready": True,
                "players": len(serverReplyProcess.players),
            }
            step_result = self.fsm_engine.step(context) if self.fsm_engine else None
            if step_result:
                next_key, actuator_cmd = step_result
                current_key = self.fsm_engine.get_current()
                
                # Define state transition callback
                def apply_transition():
                    self.fsm_engine.apply_transition(next_key)
                    self.terminal.append_output(f"[Demo] State transition completed: {current_key} -> {next_key}")
                
                self.terminal.append_output(f"[Demo] Task ended, elapsed {elapsed} ms → preparing to transition to state {next_key}")
                if actuator_cmd:
                    # Use FSM Actuator executor to handle action
                    success, result, has_delay = fsm_actuator.execute(
                        actuator_cmd, 
                        context,
                        on_complete=apply_transition
                    )
                    if success:
                        self.terminal.append_output(f"> {actuator_cmd}")
                        # If there's a return result, display it too
                        if result:
                            self.terminal.append_output(f"Return result: {result}")
                        
                        # If no delay, apply state transition immediately
                        if not has_delay:
                            apply_transition()
                        else:
                            self.terminal.append_output(f"[Demo] Waiting for delay operation to complete before transition...")
                    else:
                        self.terminal.append_output(f"[Error] Failed to execute action '{actuator_cmd}'")
                else:
                    # No action, apply state transition immediately
                    apply_transition()
            else:
                self.terminal.append_output(f"[Demo] Task ended, elapsed {elapsed} ms, no available transition")

    def _load_and_init_fsm(self, json_path: str = None):
        """
        Load and initialize FSM engine
        
        Args:
            json_path: FSM JSON file path, if None uses default path state_machine1.json
        """
        import os, json
        self.fsm_engine = None
        states = []
        
        # If no path specified, use default path
        if json_path is None:
            json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state_machine1.json")
        
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                states = data.get("StateMachine", [])
                self.terminal.append_output(f"[FSM] 已加载配置文件: {json_path}")
                self.terminal.append_output(f"[FSM] 状态数量: {len(states)}")
        except FileNotFoundError:
            self.terminal.append_output(f"[FSM] 警告: 配置文件不存在: {json_path}")
            states = []
        except Exception as e:
            self.terminal.append_output(f"[FSM] 错误: 加载配置文件失败: {e}")
            states = []

        # Load condition registry from config file
        condition_registry = get_default_condition_registry()
        self.terminal.append_output(f"[FSM] Registered condition count: {len(condition_registry)}")

        self.fsm_engine = FSMEngine(states, condition_registry)
        
        # If there are states, auto-start to first state
        if states:
            start_key = next(iter(self.fsm_engine.state_by_key.keys()), None)
            if start_key:
                self.fsm_engine.start(start_key)
                self.terminal.append_output(f"[FSM] State machine started, current state: {start_key}")
                
                # Execute initial state Entry action (if exists)
                entry_action = self.fsm_engine.get_state_entry_action(start_key)
                if entry_action:
                    self.terminal.append_output(f"[FSM] Executing initial state {start_key} Entry action: {entry_action}")
                    # Build basic context
                    context = {
                        "server_ready": socket_service.is_connected(),
                        "players": len(serverReplyProcess.players),
                        "stage": serverReplyProcess.stage,
                    }
                    fsm_actuator.execute(entry_action, context)
    
    def load_fsm_config(self):
        """Load FSM configuration file from file dialog"""
        import os
        from PyQt6.QtWidgets import QFileDialog
        
        default_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state_machine1.json")
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Load FSM Configuration", 
            default_path,
            "JSON Files (*.json)"
        )
        
        if file_path:
            self._load_and_init_fsm(file_path)
    
    def run_fsm_step(self):
        """Execute one FSM state transition (evaluate conditions and execute actions)"""
        if not self.fsm_engine:
            self.terminal.append_output("[FSM] Error: State machine not initialized, please load FSM config file first")
            return
        
        current_key = self.fsm_engine.get_current()
        if current_key is None:
            self.terminal.append_output("[FSM] Error: State machine not started")
            return
        
        # Build context
        context = {
            "elapsed_ms": tm.get_elapsed_time("task_timer") if tm.is_stopwatch_running("task_timer") else 0,
            "server_ready": socket_service.is_connected(),
            "players": len(serverReplyProcess.players),
            "stage": serverReplyProcess.stage,
            "mission_status": getattr(serverReplyProcess, 'mission_status', 'Running'),
        }
        
        # Execute one state transition step (do not apply state immediately)
        step_result = self.fsm_engine.step(context)
        
        if step_result:
            next_key, actuator_cmd = step_result
            
            # Define state transition callback
            def apply_transition():
                self.fsm_engine.apply_transition(next_key)
                self.terminal.append_output(f"[FSM] State transition completed: {current_key} -> {next_key}")
                
                # Execute new state Entry action (if exists)
                entry_action = self.fsm_engine.get_state_entry_action(next_key)
                if entry_action:
                    self.terminal.append_output(f"[FSM] Executing state {next_key} Entry action: {entry_action}")
                    fsm_actuator.execute(entry_action, context)
            
            if actuator_cmd:
                # Execute action and pass completion callback
                success, result, has_delay = fsm_actuator.execute(
                    actuator_cmd, 
                    context,
                    on_complete=apply_transition if actuator_cmd else None
                )
                
                if success:
                    self.terminal.append_output(f"[FSM] Executed command: {actuator_cmd}")
                    if result:
                        self.terminal.append_output(f"[FSM] Return result: {result}")
                    
                    # If no delay, apply state transition immediately
                    if not has_delay:
                        apply_transition()
                    else:
                        self.terminal.append_output(f"[FSM] Waiting for delay operation to complete before transition...")
                else:
                    self.terminal.append_output(f"[FSM] Error: Failed to execute command '{actuator_cmd}'")
                    # Apply state transition even if failed (optional, depends on requirements)
            else:
                # No action, apply state transition immediately
                apply_transition()
        else:
            self.terminal.append_output(f"[FSM] Current state {current_key} has no available transitions")
    
    def _init_auto_fsm_timer(self):
        """Initialize auto FSM detection timer"""
        from PyQt6.QtCore import QTimer
        self.auto_fsm_timer = QTimer(self)
        self.auto_fsm_timer.timeout.connect(self._auto_fsm_check)
        # Default: check every 1 second (1000 milliseconds)
        self.auto_fsm_timer.setInterval(1000)
    
    def toggle_auto_fsm(self, checked: bool):
        """Toggle auto FSM detection switch"""
        self.auto_fsm_enabled = checked
        if checked:
            if not self.fsm_engine:
                self.terminal.append_output("[FSM] Error: State machine not initialized, please load FSM config file first")
                # Reset button state
                sender = self.sender()
                if sender:
                    sender.setChecked(False)
                return
            
            current_key = self.fsm_engine.get_current()
            if current_key is None:
                # Auto-start to first state
                states = list(self.fsm_engine.state_by_key.keys())
                if states:
                    self.fsm_engine.start(states[0])
                    self.terminal.append_output(f"[FSM] Auto-detection started, current state: {states[0]}")
                else:
                    self.terminal.append_output("[FSM] Error: State machine has no states")
                    sender = self.sender()
                    if sender:
                        sender.setChecked(False)
                    return
            
            self.auto_fsm_timer.start()
            self.terminal.append_output("[FSM] Auto-detection enabled (checking every 1 second)")
        else:
            self.auto_fsm_timer.stop()
            self.terminal.append_output("[FSM] Auto-detection disabled")
    
    def _auto_fsm_check(self):
        """Auto FSM detection callback (triggered by timer)"""
        if not self.fsm_engine or not self.auto_fsm_enabled:
            return
        
        current_key = self.fsm_engine.get_current()
        if current_key is None:
            return
        
        # Build context (get latest data in real-time)
        context = {
            "elapsed_ms": tm.get_elapsed_time("task_timer") if tm.is_stopwatch_running("task_timer") else 0,
            "server_ready": socket_service.is_connected(),
            "players": len(serverReplyProcess.players),
            "stage": serverReplyProcess.stage,
            "mission_status": getattr(serverReplyProcess, 'mission_status', 'Running'),  # Need to set in actual code
        }
        
        # Execute one state transition step (do not apply state immediately)
        step_result = self.fsm_engine.step(context)
        
        if step_result:
            next_key, actuator_cmd = step_result
            
            # Define state transition callback
            def apply_transition():
                self.fsm_engine.apply_transition(next_key)
                self.terminal.append_output(f"[FSM Auto] State transition completed: {current_key} -> {next_key}")
                
                # Execute new state Entry action (if exists)
                entry_action = self.fsm_engine.get_state_entry_action(next_key)
                if entry_action:
                    self.terminal.append_output(f"[FSM Auto] Executing state {next_key} Entry action: {entry_action}")
                    fsm_actuator.execute(entry_action, context)
            
            if actuator_cmd:
                # Execute action and pass completion callback
                success, result, has_delay = fsm_actuator.execute(
                    actuator_cmd, 
                    context,
                    on_complete=apply_transition
                )
                
                if success:
                    self.terminal.append_output(f"[FSM Auto] Executed command: {actuator_cmd}")
                    if result:
                        self.terminal.append_output(f"[FSM Auto] Return result: {result}")
                    
                    # If no delay, apply state transition immediately
                    if not has_delay:
                        apply_transition()
                    else:
                        self.terminal.append_output(f"[FSM Auto] Waiting for delay operation to complete before transition...")
                else:
                    self.terminal.append_output(f"[FSM Auto] Error: Failed to execute command '{actuator_cmd}'")
            else:
                # No action, apply state transition immediately
                apply_transition()
# ========== Terminal Component ==========
class TerminalWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Arial", 10))
        self.input = QTextEdit()
        self.input.setMaximumHeight(50)
        self.input.setPlaceholderText("Enter command and press Ctrl+Enter")

        self.layout.addWidget(QLabel("Console (localhost:23232)"))
        self.layout.addWidget(self.output)
        self.layout.addWidget(self.input)

        self.input.installEventFilter(self)

        # Use global SocketService worker, keep property name unchanged for compatibility with other code
        self.socket_worker = socket_service.worker
        self.socket_worker.message_received.connect(self.onReceive)
        self.socket_worker.debug_received.connect(self.append_output)
        #self.socket_worker.message_received.connect(JsonParser.test)
        self.parser = JsonParser("Socket")
        self.dict_json = {}
        self.auto_command = False
        self.debug_mode = False  # Debug mode flag

    def eventFilter(self, obj, event):
        if obj == self.input and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                cmd = self.input.toPlainText().strip()
                if cmd:
                    self.append_output(f"> {cmd}")
                    self.socket_worker.send_command(cmd)
                    self.input.clear()
                return True
        return super().eventFilter(obj, event)

    def onReceive(self, text:str):
        self.dict_json = self.parser.todict(text)
        if self.dict_json != {}:
            # Check if debug mode is disabled and if message is GetStage or GetFlightLog
            should_show = True
            if not self.debug_mode:
                # In non-debug mode, filter out GetStage and GetFlightLog messages
                if self.dict_json.get('src') in ['GetStage', 'GetFlightLog','ListPlayer','ListActors']:
                    should_show = False
            
            if self.auto_command and self.dict_json['type'] == 'r':
                self.auto_command = False
            elif should_show:
                self.append_output(json.dumps(self.dict_json, indent=4, ensure_ascii=False))
            serverReplyProcess.process(self.dict_json)
    
    def append_output(self, text):
        self.output.append(text)
    
    def connect_to_server(self):
        socket_service.connect()

    def send_command_api(self, command:str, auto=False):
        # Avoid repeated auto command
        if auto and self.auto_command:
            return
        self.auto_command = auto
        socket_service.send_command(command)
        if not auto:
            self.output.append(f"> {command}")
    
    def clear(self):
        self.output.clear()

# ========== Dashboard Component ==========
class DashboardWidget(QWidget):
    def __init__(self, terminal_widget):
        super().__init__()
        self.terminal_widget = terminal_widget  # Reference to terminal widget for debug mode control
        layout = QVBoxLayout()
        self.setLayout(layout)
        # Core utils
        self.stats = SysState()

        self.display_area = QTextEdit()
        self.display_area.setReadOnly(True)
        self.display_area.setPlaceholderText("Information will appear here...")

        # Create mode switch buttons
        self.switch_btn1 = QPushButton("Player List")
        self.switch_btn2 = QPushButton("Actor List")
        self.switch_btn3 = QPushButton("Flight Logs")
        self.switch_btn4 = QPushButton("System States")

        # Make buttons checkable and mutually exclusive
        for btn in [self.switch_btn1, self.switch_btn2, self.switch_btn3, self.switch_btn4]:
            btn.setCheckable(True)

        self.switch_btn4.setChecked(True)  # Default to System States

        # Create button group for exclusive selection
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        for btn in [self.switch_btn1, self.switch_btn2, self.switch_btn3, self.switch_btn4]:
            self.button_group.addButton(btn)

        # Connect signals
        self.switch_btn1.clicked.connect(lambda: self.update_display("Player List"))
        self.switch_btn2.clicked.connect(lambda: self.update_display("Actor List"))
        self.switch_btn3.clicked.connect(lambda: self.update_display("Flight Logs"))
        self.switch_btn4.clicked.connect(lambda: self.update_display("States"))

        # Switch layout
        switch_layout = QHBoxLayout()
        switch_layout.addWidget(QLabel("Display Mode:"))
        switch_layout.addWidget(self.switch_btn4)
        switch_layout.addWidget(self.switch_btn1)
        switch_layout.addWidget(self.switch_btn2)
        switch_layout.addWidget(self.switch_btn3)
        switch_layout.addStretch()

        # Combo boxes (placeholders)
        self.combo1 = QComboBox()
        self.combo1.addItems([])
        self.combo2 = QComboBox()
        self.combo2.addItems([])

        combo_layout = QHBoxLayout()
        combo_layout.addWidget(QLabel("Preset Config:"))
        combo_layout.addWidget(self.combo1)
        combo_layout.addWidget(QLabel("Mission Package:"))
        combo_layout.addWidget(self.combo2)
        combo_layout.addStretch()

        # Checkboxes
        self.check_auto_refresh = QCheckBox("Auto-refresh (All States)")
        self.check_debug_mode = QCheckBox("Debug Mode (Show All Server Replies)")
        check_layout = QHBoxLayout()
        check_layout.addWidget(self.check_auto_refresh)
        check_layout.addWidget(self.check_debug_mode)
        check_layout.addStretch()

        # Assemble main layout
        layout.addWidget(QLabel("Dashboard"))
        layout.addWidget(self.display_area)
        layout.addLayout(switch_layout)
        layout.addLayout(combo_layout)
        layout.addLayout(check_layout)
        layout.addStretch()

        # Auto-refresh timer
        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.timeout.connect(self._auto_refresh_display)
        self.check_auto_refresh.stateChanged.connect(self._toggle_auto_refresh)
        
        # Debug mode control
        self.check_debug_mode.stateChanged.connect(self._toggle_debug_mode)

        # Initial display
        self.update_display("States")

    def _toggle_auto_refresh(self, state):
        """Toggle auto-refresh switch"""
        if state == Qt.CheckState.Checked.value:  # PyQt6
            self.auto_refresh_timer.start(1000)  # 1 second
        else:
            self.auto_refresh_timer.stop()
    
    def _toggle_debug_mode(self, state):
        """Toggle debug mode switch"""
        if state == Qt.CheckState.Checked.value:  # PyQt6
            self.terminal_widget.debug_mode = True
        else:
            self.terminal_widget.debug_mode = False

    def _auto_refresh_display(self):
        """
        Auto-refresh display: fetch all state information every time (local socket, no network overhead)
        """
        global serverReplyProcess
        global terminal
        terminalAvail = (not terminal is None) and terminal.socket_worker.running
        
        if not terminalAvail:
            return
        
        # Request all states on each auto-refresh
        serverReplyProcess.request_all_states()  # Request actors, players, stage
        terminal.send_command_api("flightlog", auto=True)  # Request flightlog
        
        # Determine current mode and update display
        if self.switch_btn1.isChecked():
            mode = "Player List"
        elif self.switch_btn2.isChecked():
            mode = "Actor List"
        elif self.switch_btn3.isChecked():
            mode = "Flight Logs"
        elif self.switch_btn4.isChecked():
            mode = "States"
        else:
            mode = "States"  # fallback (should not happen)

        self.update_display(mode)

    def update_display(self, mode):
        """
        Update display content (does not actively request data, data provided by auto-refresh mechanism)
        """
        global serverReplyProcess
        global terminal
        terminalAvail = (not terminal is None) and terminal.socket_worker.running
        
        if mode == "States":
            processName = "VTOLVR.exe"
            mem = self.stats.memory
            pid = self.stats.find_pid_by_name(processName)
            mem_usage_dict = self.stats.findMemUsageByPID(pid)
            mem_usage_arr = [0]*4
            if "pid" in mem_usage_dict:
                mem_usage_arr[0] = mem_usage_dict.get('pid')
                mem_usage_arr[1] = mem_usage_dict.get('rss_mb')
                mem_usage_arr[2] = mem_usage_dict.get('vms_mb')
                mem_usage_arr[3] = mem_usage_dict.get("memory_percent")
                
            content = (
                f"Performance stats:\n"
                f"    - 总内存: {mem.total / (1024**3):.2f} GB\n"
                f"    - 已用内存: {mem.used / (1024**3):.2f} GB\n"
                f"    - 可用内存: {mem.available / (1024**3):.2f} GB\n"
                f"    - 内存使用率: {mem.percent}%\n"
                f"    - 检测pid: {pid}\n"
                f"    - 游戏内存占用：{mem_usage_arr[3]}%\n"
                f"Last replied state change:\n"
                f"    - {serverReplyProcess.lastState}"
            )
        elif mode == "Player List":
            if serverReplyProcess.players:
                content = "Player List\n" + "\n".join(serverReplyProcess.players)
            else:
                content = "Player List\n(No player data, waiting for auto-refresh...)"
        elif mode == "Actor List":
            if serverReplyProcess.actors:
                content = "Actor List\n" + "\n".join([str(u) for u in serverReplyProcess.actors])
            else:
                content = "Actor List\n(No actor data, waiting for auto-refresh...)"
        elif mode == "Flight Logs":
            if serverReplyProcess.flightlog:
                content = "Flight Logs\n" + "\n".join(serverReplyProcess.flightlog)
            else:
                content = "Flight Logs\n(No log data, waiting for auto-refresh...)"
        else:
            content = "Unknown mode"

        # Replace tabs with spaces for consistent display
        content = content.replace("\t", "    ")
        scrollbarpos = self.display_area.verticalScrollBar().value()
        self.display_area.setText(content)
        self.display_area.verticalScrollBar().setValue(scrollbarpos)



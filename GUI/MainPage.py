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
# 旧的测试用 FSMActuator 已移除，现在使用 core.FSM.fsm_actuator
#Private constants
S2MS = 1000
MIN2MS = 60 * S2MS
H2MS = 60 * MIN2MS
# ========== Page 1: 原始主界面 ==========
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
        self.dashboard = DashboardWidget()

        splitter.addWidget(self.terminal)
        splitter.addWidget(self.dashboard)
        splitter.setSizes([300, 900])  # 初始比例

        layout.addWidget(splitter)

        # ===== FSM 引擎与条件注册表 =====
        self._load_and_init_fsm()
        
        # 初始化自动 FSM 检测定时器（默认关闭）
        self._init_auto_fsm_timer()
        
        # 初始化日志记录相关
        self.current_session_id = None
    
    def _save_session_logs(self):
        """
        保存当前会话的日志（flightlog 和 debuglog）
        """
        global rpPacker
        
        # 如果 flightlog 不为空，保存它
        if serverReplyProcess.flightlog:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"flightlog_{timestamp}.txt"
            rpPacker.SaveFlightlog(serverReplyProcess.flightlog, filename)
        
        # 如果 debuglog 不为空，保存它
        if serverReplyProcess.debuglog:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"debuglog_{timestamp}.txt"
            rpPacker.SaveDebuglog(serverReplyProcess.debuglog, filename)

    def connect_terminal(self):
        self.terminal.connect_to_server()
    def host_game(self):
        # 开始新一局前，保存上一局的日志
        self._save_session_logs()
        serverReplyProcess.clear_session_logs()
        self.terminal.send_command_api("host")
    def check_host(self):
        self.terminal.send_command_api("checkhost")
    def config_host(self):
        self.terminal.send_command_api("config")
    def start_game(self):
        # 开始游戏前，保存上一局的日志
        self._save_session_logs()
        serverReplyProcess.clear_session_logs()
        self.terminal.send_command_api("start")
    def skip_game(self):
        self.terminal.send_command_api("skip")
    def restart_game(self):
        # 重启前保存当前局的日志
        self._save_session_logs()
        serverReplyProcess.clear_session_logs()
        self.terminal.send_command_api("restart")
    def quit_game(self):
        # 退出前保存当前局的日志
        self._save_session_logs()
        serverReplyProcess.clear_session_logs()
        self.terminal.send_command_api("quit")
    def quit_server(self):
        self.terminal.send_command_api("exitapp")
    def clear_console(self):
        self.terminal.clear()
    def TestFunc(self):
        # 将 Test 按钮用作演示：第一次点击开始任务计时；第二次点击结束并评估条件推进状态与发送命令
        if not self.task_running:
            self.task_running = True
            self.TestClick = True
            # 使用 TimerManager 启动任务计时器
            tm.start_stopwatch("task_timer")
            # 确保 socket 已连接
            if not socket_service.is_connected():
                socket_service.connect()
            # 启动 FSM 到一个起始状态（若 JSON 未指定，可选择 "1"）
            if self.fsm_engine:
                start_key = next(iter(self.fsm_engine.state_by_key.keys()), None)
                if start_key:
                    self.fsm_engine.start(start_key)
            self.terminal.append_output("[Demo] 任务开始，已启动计时器")
        else:
            self.task_running = False
            self.TestClick = False
            # 使用 TimerManager 停止任务计时器并获取经过时间
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
                
                # 定义状态转移回调
                def apply_transition():
                    self.fsm_engine.apply_transition(next_key)
                    self.terminal.append_output(f"[Demo] 状态转移完成: {current_key} -> {next_key}")
                
                self.terminal.append_output(f"[Demo] 任务结束，耗时 {elapsed} ms → 准备跳转状态 {next_key}")
                if actuator_cmd:
                    # 使用 FSM Actuator 执行器处理 action
                    success, result, has_delay = fsm_actuator.execute(
                        actuator_cmd, 
                        context,
                        on_complete=apply_transition
                    )
                    if success:
                        self.terminal.append_output(f"> {actuator_cmd}")
                        # 如果有返回结果，也显示出来
                        if result:
                            self.terminal.append_output(f"返回结果: {result}")
                        
                        # 如果没有延迟，立即应用状态转移
                        if not has_delay:
                            apply_transition()
                        else:
                            self.terminal.append_output(f"[Demo] 等待延迟操作完成后再转移状态...")
                    else:
                        self.terminal.append_output(f"[错误] 执行 action '{actuator_cmd}' 失败")
                else:
                    # 没有 action，立即应用状态转移
                    apply_transition()
            else:
                self.terminal.append_output(f"[Demo] 任务结束，耗时 {elapsed} ms，无可用转移")

    def _load_and_init_fsm(self, json_path: str = None):
        """
        加载并初始化 FSM 引擎
        
        Args:
            json_path: FSM JSON 文件路径，如果为 None 则使用默认路径 state_machine1.json
        """
        import os, json
        self.fsm_engine = None
        states = []
        
        # 如果没有指定路径，使用默认路径
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

        # 从配置文件加载条件注册表
        condition_registry = get_default_condition_registry()
        self.terminal.append_output(f"[FSM] 已注册条件数量: {len(condition_registry)}")

        self.fsm_engine = FSMEngine(states, condition_registry)
        
        # 如果有状态，自动启动到第一个状态
        if states:
            start_key = next(iter(self.fsm_engine.state_by_key.keys()), None)
            if start_key:
                self.fsm_engine.start(start_key)
                self.terminal.append_output(f"[FSM] 状态机已启动，当前状态: {start_key}")
                
                # 执行初始状态的Entry动作（如果有）
                entry_action = self.fsm_engine.get_state_entry_action(start_key)
                if entry_action:
                    self.terminal.append_output(f"[FSM] 执行初始状态 {start_key} 的Entry动作: {entry_action}")
                    # 构建基本上下文
                    context = {
                        "server_ready": socket_service.is_connected(),
                        "players": len(serverReplyProcess.players),
                        "stage": serverReplyProcess.stage,
                    }
                    fsm_actuator.execute(entry_action, context)
    
    def load_fsm_config(self):
        """从文件对话框加载 FSM 配置文件"""
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
        """执行一次 FSM 状态转移（评估条件并执行动作）"""
        if not self.fsm_engine:
            self.terminal.append_output("[FSM] 错误: 状态机未初始化，请先加载 FSM 配置文件")
            return
        
        current_key = self.fsm_engine.get_current()
        if current_key is None:
            self.terminal.append_output("[FSM] 错误: 状态机未启动")
            return
        
        # 构建上下文
        context = {
            "elapsed_ms": tm.get_elapsed_time("task_timer") if tm.is_stopwatch_running("task_timer") else 0,
            "server_ready": socket_service.is_connected(),
            "players": len(serverReplyProcess.players),
            "stage": serverReplyProcess.stage,
            "mission_status": getattr(serverReplyProcess, 'mission_status', 'Running'),
        }
        
        # 执行一步状态转移（不立即应用状态）
        step_result = self.fsm_engine.step(context)
        
        if step_result:
            next_key, actuator_cmd = step_result
            
            # 定义状态转移回调
            def apply_transition():
                self.fsm_engine.apply_transition(next_key)
                self.terminal.append_output(f"[FSM] 状态转移完成: {current_key} -> {next_key}")
                
                # 执行新状态的Entry动作（如果有）
                entry_action = self.fsm_engine.get_state_entry_action(next_key)
                if entry_action:
                    self.terminal.append_output(f"[FSM] 执行状态 {next_key} 的Entry动作: {entry_action}")
                    fsm_actuator.execute(entry_action, context)
            
            if actuator_cmd:
                # 执行 action，并传入完成回调
                success, result, has_delay = fsm_actuator.execute(
                    actuator_cmd, 
                    context,
                    on_complete=apply_transition if actuator_cmd else None
                )
                
                if success:
                    self.terminal.append_output(f"[FSM] 执行命令: {actuator_cmd}")
                    if result:
                        self.terminal.append_output(f"[FSM] 返回结果: {result}")
                    
                    # 如果没有延迟，立即应用状态转移
                    if not has_delay:
                        apply_transition()
                    else:
                        self.terminal.append_output(f"[FSM] 等待延迟操作完成后再转移状态...")
                else:
                    self.terminal.append_output(f"[FSM] 错误: 执行命令 '{actuator_cmd}' 失败")
                    # 即使失败也应用状态转移（可选，根据需求决定）
            else:
                # 没有 action，立即应用状态转移
                apply_transition()
        else:
            self.terminal.append_output(f"[FSM] 当前状态 {current_key} 无可用转移")
    
    def _init_auto_fsm_timer(self):
        """初始化自动 FSM 检测定时器"""
        from PyQt6.QtCore import QTimer
        self.auto_fsm_timer = QTimer(self)
        self.auto_fsm_timer.timeout.connect(self._auto_fsm_check)
        # 默认每 1 秒检查一次（1000 毫秒）
        self.auto_fsm_timer.setInterval(1000)
    
    def toggle_auto_fsm(self, checked: bool):
        """切换自动 FSM 检测开关"""
        self.auto_fsm_enabled = checked
        if checked:
            if not self.fsm_engine:
                self.terminal.append_output("[FSM] 错误: 状态机未初始化，请先加载 FSM 配置文件")
                # 重置按钮状态
                sender = self.sender()
                if sender:
                    sender.setChecked(False)
                return
            
            current_key = self.fsm_engine.get_current()
            if current_key is None:
                # 自动启动到第一个状态
                states = list(self.fsm_engine.state_by_key.keys())
                if states:
                    self.fsm_engine.start(states[0])
                    self.terminal.append_output(f"[FSM] 自动检测已启动，当前状态: {states[0]}")
                else:
                    self.terminal.append_output("[FSM] 错误: 状态机没有状态")
                    sender = self.sender()
                    if sender:
                        sender.setChecked(False)
                    return
            
            self.auto_fsm_timer.start()
            self.terminal.append_output("[FSM] 自动检测已启用（每1秒检查一次）")
        else:
            self.auto_fsm_timer.stop()
            self.terminal.append_output("[FSM] 自动检测已禁用")
    
    def _auto_fsm_check(self):
        """自动 FSM 检测回调（定时器触发）"""
        if not self.fsm_engine or not self.auto_fsm_enabled:
            return
        
        current_key = self.fsm_engine.get_current()
        if current_key is None:
            return
        
        # 构建上下文（实时获取最新数据）
        context = {
            "elapsed_ms": tm.get_elapsed_time("task_timer") if tm.is_stopwatch_running("task_timer") else 0,
            "server_ready": socket_service.is_connected(),
            "players": len(serverReplyProcess.players),
            "stage": serverReplyProcess.stage,
            "mission_status": getattr(serverReplyProcess, 'mission_status', 'Running'),  # 需要在实际代码中设置
        }
        
        # 执行一步状态转移（不立即应用状态）
        step_result = self.fsm_engine.step(context)
        
        if step_result:
            next_key, actuator_cmd = step_result
            
            # 定义状态转移回调
            def apply_transition():
                self.fsm_engine.apply_transition(next_key)
                self.terminal.append_output(f"[FSM Auto] 状态转移完成: {current_key} -> {next_key}")
                
                # 执行新状态的Entry动作（如果有）
                entry_action = self.fsm_engine.get_state_entry_action(next_key)
                if entry_action:
                    self.terminal.append_output(f"[FSM Auto] 执行状态 {next_key} 的Entry动作: {entry_action}")
                    fsm_actuator.execute(entry_action, context)
            
            if actuator_cmd:
                # 执行 action，并传入完成回调
                success, result, has_delay = fsm_actuator.execute(
                    actuator_cmd, 
                    context,
                    on_complete=apply_transition
                )
                
                if success:
                    self.terminal.append_output(f"[FSM Auto] 执行命令: {actuator_cmd}")
                    if result:
                        self.terminal.append_output(f"[FSM Auto] 返回结果: {result}")
                    
                    # 如果没有延迟，立即应用状态转移
                    if not has_delay:
                        apply_transition()
                    else:
                        self.terminal.append_output(f"[FSM Auto] 等待延迟操作完成后再转移状态...")
                else:
                    self.terminal.append_output(f"[FSM Auto] 错误: 执行命令 '{actuator_cmd}' 失败")
            else:
                # 没有 action，立即应用状态转移
                apply_transition()
# ========== Terminal 组件（不变） ==========
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

        # 使用全局 SocketService 的 worker，保持属性名不变以兼容其他代码
        self.socket_worker = socket_service.worker
        self.socket_worker.message_received.connect(self.onReceive)
        self.socket_worker.debug_received.connect(self.append_output)
        #self.socket_worker.message_received.connect(JsonParser.test)
        self.parser = JsonParser("Socket")
        self.dict_json = {}
        self.auto_command = False

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
            if self.auto_command and self.dict_json['type'] == 'r':
                self.auto_command = False
            else:
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

# ========== Dashboard 组件（不变） ==========
class DashboardWidget(QWidget):
    def __init__(self):
        super().__init__()
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
        check_layout = QHBoxLayout()
        check_layout.addWidget(self.check_auto_refresh)
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

        # Initial display
        self.update_display("States")

    def _toggle_auto_refresh(self, state):
        """切换自动刷新开关"""
        if state == Qt.CheckState.Checked.value:  # PyQt6
            self.auto_refresh_timer.start(1000)  # 1 second
        else:
            self.auto_refresh_timer.stop()

    def _auto_refresh_display(self):
        """
        自动刷新显示：每次都获取所有状态信息（本地 socket，无网络开销）
        """
        global serverReplyProcess
        global terminal
        terminalAvail = (not terminal is None) and terminal.socket_worker.running
        
        if not terminalAvail:
            return
        
        # 每次自动刷新都请求所有状态
        serverReplyProcess.request_all_states()  # 请求 actors, players, stage
        terminal.send_command_api("flightlog", auto=True)  # 请求 flightlog
        
        # 确定当前模式并更新显示
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
        更新显示内容（不主动请求数据，数据由自动刷新机制提供）
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
                content = "Player List\n(暂无玩家数据，等待自动刷新...)"
        elif mode == "Actor List":
            if serverReplyProcess.actors:
                content = "Actor List\n" + "\n".join([str(u) for u in serverReplyProcess.actors])
            else:
                content = "Actor List\n(暂无 Actor 数据，等待自动刷新...)"
        elif mode == "Flight Logs":
            if serverReplyProcess.flightlog:
                content = "Flight Logs\n" + "\n".join(serverReplyProcess.flightlog)
            else:
                content = "Flight Logs\n(暂无日志数据，等待自动刷新...)"
        else:
            content = "Unknown mode"

        # Replace tabs with spaces for consistent display
        content = content.replace("\t", "    ")
        scrollbarpos = self.display_area.verticalScrollBar().value()
        self.display_area.setText(content)
        self.display_area.verticalScrollBar().setValue(scrollbarpos)



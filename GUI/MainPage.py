import json.tool
import sys
import socket
import threading
import psutil
import time
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QTextEdit,
    QHBoxLayout, QVBoxLayout, QSplitter, QComboBox, QCheckBox,
    QLabel, QStackedWidget, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QFont
from core.SocketWorker import SocketWorker
from core.SysState import SysState
from core.StringParser import JsonParser
from core.ServerReplyProcess import ServerReplyProcess

serverReplyProcess = ServerReplyProcess()
terminal = None

# ========== Page 1: 原始主界面 ==========
class MainPage(QWidget):
    def __init__(self, switch_callback):
        super().__init__()
        self.switch_callback = switch_callback

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Top bar
        top_bar = QHBoxLayout()
        buttons = ["Connect", "Clear", "Check Host", "Config Host", "Host", "Start", "Skip", "Restart", "Quit", "Quit Server"]
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

    def connect_terminal(self):
        self.terminal.connect_to_server()
    def host_game(self):
        self.terminal.send_command_api("host")
    def check_host(self):
        self.terminal.send_command_api("checkhost")
    def config_host(self):
        self.terminal.send_command_api("config")
    def start_game(self):
        self.terminal.send_command_api("start")
    def skip_game(self):
        self.terminal.send_command_api("skip")
    def restart_game(self):
        self.terminal.send_command_api("restart")
    def quit_game(self):
        self.terminal.send_command_api("quit")
    def quit_server(self):
        self.terminal.send_command_api("exitapp")
    def clear_console(self):
        self.terminal.clear()

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
        
        self.socket_worker = SocketWorker()
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
        self.socket_worker.connect_socket()

    def send_command_api(self, command:str, auto=False):
        # Avoid repeated auto command
        if auto and self.auto_command:
            return
        self.auto_command = auto
        self.socket_worker.send_command(command)
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
        self.check1 = QCheckBox("Enable Feature X")
        self.check2 = QCheckBox("Auto-refresh")
        check_layout = QHBoxLayout()
        check_layout.addWidget(self.check1)
        check_layout.addWidget(self.check2)
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
        self.check2.stateChanged.connect(self._toggle_auto_refresh)

        # Initial display
        self.update_display("States")

    def _toggle_auto_refresh(self, state):
        if state == Qt.CheckState.Checked.value:  # PyQt6
            self.auto_refresh_timer.start(1000)  # 1 second
        else:
            self.auto_refresh_timer.stop()

    def _auto_refresh_display(self):
        # Determine current mode based on checked button
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
        global serverReplyProcess
        global terminal
        terminalAvail = (not terminal is None) and terminal.socket_worker.running
        # Generate content based on mode
        if mode == "States":
            mem = self.stats.memory
            content = (
                f"Performance stats:\n"
                f"    - 总内存: {mem.total / (1024**3):.2f} GB\n"
                f"    - 已用内存: {mem.used / (1024**3):.2f} GB\n"
                f"    - 可用内存: {mem.available / (1024**3):.2f} GB\n"
                f"    - 内存使用率: {mem.percent}%\n"
                f"Last replied state change:\n"
                f"    - {serverReplyProcess.lastState}"
            )
        elif mode == "Player List":
            content = "Player List\n" + "\n".join(serverReplyProcess.players)
            if terminalAvail:
                terminal.send_command_api("player", auto=True)
        elif mode == "Actor List":
            content = "Actor List\n" + "\n".join([str(u) for u in serverReplyProcess.actors])
            if terminalAvail:
                terminal.send_command_api("list", auto=True)
        elif mode == "Flight Logs":
            content = "Flight Logs\n" + "\n".join(serverReplyProcess.logs)
        else:
            content = "Unknown mode"

        # Replace tabs with spaces for consistent display
        content = content.replace("\t", "    ")
        scrollbarpos = self.display_area.verticalScrollBar().value()
        self.display_area.setText(content)
        self.display_area.verticalScrollBar().setValue(scrollbarpos)


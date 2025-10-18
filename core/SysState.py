import os
import psutil
import threading
import time
from PyQt6.QtCore import QObject

class SysState(QObject):
    def __init__(self):
        super().__init__()
        self._stop_event = threading.Event()
        self.memory = psutil.virtual_memory()
        self.game_process = psutil.Process(os.getpid())
        self.GUI_process = psutil.Process(os.getpid())  # 实际上和 game_process 是同一个进程

        # 启动后台刷新线程
        self._refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._refresh_thread.start()

    def _refresh_loop(self):
        while not self._stop_event.is_set():
            try:
                self.memory = psutil.virtual_memory()
                # 如果 game_process 或 GUI_process 可能退出，建议加异常处理
                # 但当前它们都是当前进程，一般不会失效
            except psutil.NoSuchProcess:
                pass  # 可根据需要处理
            time.sleep(1)  # 每秒刷新一次

    def stop(self):
        """可选：提供停止线程的方法（虽然 daemon 线程会随主程序退出）"""
        self._stop_event.set()
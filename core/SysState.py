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
        # self.game_process = psutil.Process(os.getpid())
        self.GUI_process = psutil.Process(os.getpid())  # 实际上和 game_process 是同一个进程

        # 启动后台刷新线程
        self._refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._refresh_thread.start()

    def findMemUsageByPID(self, pid:int):
        if pid:
            try:
                P = psutil.Process(pid)
                mem = P.memory_info()
                rss = mem.rss
                vms = mem.vms
                rss_mb = rss / (1024 * 1024)
                vms_mb = vms / (1024 * 1024)
                mem_percent = P.memory_percent()
                return {
                    "pid": pid,
                    "rss_mb": round(rss_mb, 2),
                    "vms_mb": round(vms_mb, 2),
                    "memory_percent": round(mem_percent, 2)
                }
            except psutil.NoSuchProcess:
                return {"error": f"Process with PID {pid} not found"}
            except psutil.AccessDenied:
                return {"error": f"Access denied to process {pid}"}
        return "1"
    def find_pid_by_name(self,process_name:str):
        #根据进程名字查找id
        pids = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] == process_name:
                    pids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # 进程可能在遍历时已退出，跳过
                continue
        return pids
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
        #手动终止进程
        self._stop_event.set()
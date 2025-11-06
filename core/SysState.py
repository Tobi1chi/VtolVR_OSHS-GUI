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
        self.GUI_process = psutil.Process(os.getpid())  # Actually the same process as game_process

        # Start background refresh thread
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
    def find_pid_by_name(self,process_name:str)->int:
        # Find process ID by process name
        pids = 0
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] == process_name:
                    pids = proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Process might have exited during iteration, skip it
                continue
        return pids
    def _refresh_loop(self):
        while not self._stop_event.is_set():
            try:
                self.memory = psutil.virtual_memory()
                # If game_process or GUI_process might exit, add exception handling
                # But currently they are the current process, usually won't fail
            except psutil.NoSuchProcess:
                pass  # Handle as needed
            time.sleep(1)  # Refresh every second

    def stop(self):
        # Manually stop the process
        self._stop_event.set()
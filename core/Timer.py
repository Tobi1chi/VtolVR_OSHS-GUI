from PyQt6.QtCore import QTimer, QObject, QDateTime
from typing import Callable, Dict, Optional


class TimerManager(QObject):
    """
    统一管理 PyQt 中的所有 QTimer 实例。
    所有操作必须在主线程（GUI 线程）中调用。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timers = {}  # name -> QTimer
        self._timer_start_times = {}  # name -> start_time_ms (用于计时功能)

    def start_timer(self, name: str, interval_ms: int, callback: Callable, single_shot: bool = False):
        """
        启动一个命名定时器。
        如果同名定时器已存在，会先停止并替换。
        """
        if name in self._timers:
            self.stop_timer(name)

        timer = QTimer(self)
        timer.setSingleShot(single_shot)
        timer.timeout.connect(callback)
        timer.start(interval_ms)
        self._timers[name] = timer

    def start_stopwatch(self, name: str) -> bool:
        """
        启动一个秒表（用于计时，不触发回调）。
        
        Args:
            name: 秒表名称
            
        Returns:
            是否成功启动
        """
        if name in self._timers:
            return False  # 已存在同名计时器
        
        self._timer_start_times[name] = QDateTime.currentMSecsSinceEpoch()
        return True

    def get_elapsed_time(self, name: str) -> Optional[int]:
        """
        获取秒表的经过时间（毫秒）。
        
        Args:
            name: 秒表名称
            
        Returns:
            经过的毫秒数，如果秒表不存在返回 None
        """
        if name not in self._timer_start_times:
            return None
        
        start_time = self._timer_start_times[name]
        current_time = QDateTime.currentMSecsSinceEpoch()
        return current_time - start_time

    def stop_stopwatch(self, name: str) -> Optional[int]:
        """
        停止秒表并返回经过的时间。
        
        Args:
            name: 秒表名称
            
        Returns:
            经过的毫秒数，如果秒表不存在返回 None
        """
        elapsed = self.get_elapsed_time(name)
        if elapsed is not None:
            self._timer_start_times.pop(name, None)
        return elapsed

    def is_stopwatch_running(self, name: str) -> bool:
        """检查秒表是否正在运行"""
        return name in self._timer_start_times

    def stop_timer(self, name: str) -> bool:
        """停止并移除指定名称的定时器。返回是否成功停止。"""
        if name in self._timers:
            timer = self._timers.pop(name)
            timer.stop()
            timer.deleteLater()  # 安全释放资源
            return True
        return False

    def is_timer_active(self, name: str) -> bool:
        """检查指定名称的定时器是否正在运行。"""
        return name in self._timers and self._timers[name].isActive()

    def list_timers(self):
        """返回当前所有定时器的名称列表（调试用）"""
        return list(self._timers.keys())

    def stop_all_timers(self):
        """停止并清理所有定时器和秒表"""
        for name in list(self._timers.keys()):
            self.stop_timer(name)
        self._timer_start_times.clear()

from PyQt6.QtCore import QTimer, QObject, QDateTime
from typing import Callable, Dict, Optional


class TimerManager(QObject):
    """
    Centralized management of all QTimer instances in PyQt.
    All operations must be called in the main thread (GUI thread).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timers = {}  # name -> QTimer
        self._timer_start_times = {}  # name -> start_time_ms (for timing functionality)

    def start_timer(self, name: str, interval_ms: int, callback: Callable, single_shot: bool = False):
        """
        Start a named timer.
        If a timer with the same name exists, it will be stopped and replaced first.
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
        Start a stopwatch (for timing, does not trigger callbacks).
        
        Args:
            name: Stopwatch name
            
        Returns:
            Whether started successfully
        """
        if name in self._timers:
            return False  # Timer with same name already exists
        
        self._timer_start_times[name] = QDateTime.currentMSecsSinceEpoch()
        return True

    def get_elapsed_time(self, name: str) -> Optional[int]:
        """
        Get the elapsed time of the stopwatch (in milliseconds).
        
        Args:
            name: Stopwatch name
            
        Returns:
            Elapsed milliseconds, returns None if stopwatch doesn't exist
        """
        if name not in self._timer_start_times:
            return None
        
        start_time = self._timer_start_times[name]
        current_time = QDateTime.currentMSecsSinceEpoch()
        return current_time - start_time

    def stop_stopwatch(self, name: str) -> Optional[int]:
        """
        Stop the stopwatch and return the elapsed time.
        
        Args:
            name: Stopwatch name
            
        Returns:
            Elapsed milliseconds, returns None if stopwatch doesn't exist
        """
        elapsed = self.get_elapsed_time(name)
        if elapsed is not None:
            self._timer_start_times.pop(name, None)
        return elapsed

    def is_stopwatch_running(self, name: str) -> bool:
        """Check if the stopwatch is running"""
        return name in self._timer_start_times

    def stop_timer(self, name: str) -> bool:
        """Stop and remove the timer with the specified name. Returns whether successfully stopped."""
        if name in self._timers:
            timer = self._timers.pop(name)
            timer.stop()
            timer.deleteLater()  # Safely release resources
            return True
        return False

    def is_timer_active(self, name: str) -> bool:
        """Check if the timer with the specified name is running."""
        return name in self._timers and self._timers[name].isActive()

    def list_timers(self):
        """Return a list of names of all current timers (for debugging)"""
        return list(self._timers.keys())

    def stop_all_timers(self):
        """Stop and clean up all timers and stopwatches"""
        for name in list(self._timers.keys()):
            self.stop_timer(name)
        self._timer_start_times.clear()

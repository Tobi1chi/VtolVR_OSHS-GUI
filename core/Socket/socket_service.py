from PyQt6.QtCore import QObject
from core.Socket.SocketWorker import SocketWorker


class SocketService(QObject):
    """
    Unified Socket Service:
    - Internally holds a SocketWorker singleton for global components to share connection, signals, and sending capabilities.
    - Exposes worker for compatibility with existing TerminalWidget usage (e.g., reading running status).
    """

    def __init__(self, host: str = 'localhost', port: int = 23232):
        super().__init__()
        self._worker = SocketWorker(host=host, port=port)

    @property
    def worker(self) -> SocketWorker:
        return self._worker

    def connect(self) -> None:
        if not self._worker.running:
            self._worker.connect_socket()

    def is_connected(self) -> bool:
        return self._worker.running

    def send_command(self, cmd: str) -> None:
        self._worker.send_command(cmd)


# Module-level singleton
socket_service = SocketService()

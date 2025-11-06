from PyQt6.QtCore import QObject
from core.Socket.SocketWorker import SocketWorker


class SocketService(QObject):
    """
    统一的 Socket 服务：
    - 内部持有一个 SocketWorker 单例，供全局组件共享连接、信号与发送能力。
    - 暴露 worker 以兼容现有 TerminalWidget 用法（例如读取 running）。
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


# 模块级单例
socket_service = SocketService()

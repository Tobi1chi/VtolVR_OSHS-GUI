import socket
import threading
from PyQt6.QtCore import pyqtSignal, QObject
class SocketWorker(QObject):
    message_received = pyqtSignal(str)

    def __init__(self, host='localhost', port=23232):
        super().__init__()
        self.host = host
        self.port = port
        self.sock = None
        self.running = False

    def connect_socket(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.running = True
            threading.Thread(target=self._listen, daemon=True).start()
            return True
        except Exception as e:
            self.message_received.emit(f"[Error] {e}")
            return False

    def _listen(self):
        while self.running:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break
                msg = data.decode('utf-8', errors='replace')
                self.message_received.emit(msg)
            except Exception as e:
                self.message_received.emit(f"[Recv Error] {e}")
                break
        self.running = False

    def send_command(self, cmd: str):
        if self.sock and self.running:
            try:
                self.sock.sendall((cmd + '\n').encode('utf-8'))
            except Exception as e:
                self.message_received.emit(f"[Send Error] {e}")

    def close(self):
        self.running = False
        if self.sock:
            self.sock.close()

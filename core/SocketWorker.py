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
        binary_buffer = bytes()  # 使用二进制缓冲区存储未解码的数据
        while self.running:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break
                
                # 将新接收的二进制数据添加到缓冲区
                binary_buffer += data
                
                # 尝试解码缓冲区中的数据
                try:
                    # 尝试完整解码
                    text_buffer = binary_buffer.decode('utf-8')
                    
                    # 检查是否有完整消息（以换行符分隔）
                    if '\n' in text_buffer:
                        # 按换行符分割消息
                        messages = text_buffer.split('\n')
                        # 处理除最后一个可能不完整的消息外的所有消息
                        for i in range(len(messages) - 1):
                            if messages[i]:  # 避免发送空消息
                                self.message_received.emit(messages[i])
                        # 保留最后一个可能不完整的消息
                        # 如果最后一个字符是换行符，则不需要保留
                        if text_buffer.endswith('\n'):
                            binary_buffer = b""
                        else:
                            # 重新编码最后一个不完整的消息，放回二进制缓冲区
                            binary_buffer = messages[-1].encode('utf-8')
                except UnicodeDecodeError:
                    # 解码失败，可能是多字节字符被分割
                    # 尝试从缓冲区末尾逐步回退，找到有效的UTF-8边界
                    # 从缓冲区长度-1开始尝试，直到找到有效的解码点
                    for i in range(1, len(binary_buffer)):
                        try:
                            # 尝试解码除了最后i个字节外的所有数据
                            valid_part = binary_buffer[:-i].decode('utf-8')
                            
                            # 检查有效部分中是否有完整消息
                            if '\n' in valid_part:
                                messages = valid_part.split('\n')
                                for j in range(len(messages) - 1):
                                    if messages[j]:
                                        self.message_received.emit(messages[j])
                                # 重新编码最后一个不完整的消息
                                remaining_text = messages[-1] if not valid_part.endswith('\n') else ""
                                # 保留未解码的部分加上剩余文本的编码
                                binary_buffer = remaining_text.encode('utf-8') + binary_buffer[-i:]
                            else:
                                # 没有换行符，保留整个缓冲区
                                pass
                            break
                        except UnicodeDecodeError:
                            # 继续尝试更小的有效部分
                            continue
                    # 如果无法找到有效边界，保留整个缓冲区
                    # 下一次接收到数据时会再次尝试
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

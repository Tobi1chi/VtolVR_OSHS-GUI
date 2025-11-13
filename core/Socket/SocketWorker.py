import socket
import threading
import queue
from PyQt6.QtCore import pyqtSignal, QObject
class SocketWorker(QObject):
    message_received = pyqtSignal(str)
    debug_received = pyqtSignal(str)

    def __init__(self, host='localhost', port=23232):
        super().__init__()
        self.host = host
        self.port = port
        self.sock = None
        self.running = False
        self.queue = queue.Queue()  # Create queue once, reuse it
        self.listen_thread = None
        self._auto_reconnect = False  # Control auto-reconnect

    def connect_socket(self, auto_reconnect=False):
        """
        Connect to socket server
        
        Args:
            auto_reconnect: If True, enable auto-reconnect on disconnect
        """
        # Prevent multiple connection attempts
        if self.running or (self.listen_thread and self.listen_thread.is_alive()):
            self.debug_received.emit(f"[Warning] Connection already exists or thread still running")
            return
        
        self._auto_reconnect = auto_reconnect
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.sock.setblocking(False)
            self.running = True
            self.debug_received.emit(f"[Info] Connected to server {self.host}:{self.port}")
            # Don't create new queue, reuse existing one to preserve messages
            self.listen_thread = threading.Thread(target=self._listen, daemon=True)
            self.listen_thread.start()
        except Exception as e:
            self.debug_received.emit(f"[Error] Connection failed: {e}")
            self.running = False
            if self.sock:
                try:
                    self.sock.close()
                except Exception:
                    pass
                self.sock = None

    def _listen(self):
        binary_buffer = bytes()  # Use binary buffer to store undecoded data
        while self.running:
            # Check connection
            try:
                self.sock.getpeername()
            except:
                self.running = False
                break
            # Try receive data
            try:
                data = self.sock.recv(4096)
                if not data:
                    break
                
                # Add newly received binary data to buffer
                binary_buffer += data
                
                # Try to decode data in buffer
                try:
                    # Try full decode
                    text_buffer = binary_buffer.decode('utf-8')
                    
                    # Check if there are complete messages (separated by newlines)
                    if '\n' in text_buffer:
                        # Split messages by newline
                        messages = text_buffer.split('\n')
                        # Process all messages except the last potentially incomplete one
                        for i in range(len(messages) - 1):
                            if messages[i]:  # Avoid sending empty messages
                                self.message_received.emit(messages[i])
                        # Keep last potentially incomplete message
                        # If last character is newline, don't need to keep
                        if text_buffer.endswith('\n'):
                            binary_buffer = b""
                        else:
                            # Re-encode last incomplete message, put back to binary buffer
                            binary_buffer = messages[-1].encode('utf-8')
                except UnicodeDecodeError:
                    # Decode failed, possibly multi-byte character was split
                    # Try to step back from end of buffer to find valid UTF-8 boundary
                    # Try from buffer length-1 until finding valid decode point
                    for i in range(1, len(binary_buffer)):
                        try:
                            # Try to decode all data except last i bytes
                            valid_part = binary_buffer[:-i].decode('utf-8')
                            
                            # Check if valid part has complete messages
                            if '\n' in valid_part:
                                messages = valid_part.split('\n')
                                for j in range(len(messages) - 1):
                                    if messages[j]:
                                        self.message_received.emit(messages[j])
                                # Re-encode last incomplete message
                                remaining_text = messages[-1] if not valid_part.endswith('\n') else ""
                                # Keep undecoded part plus encoding of remaining text
                                binary_buffer = remaining_text.encode('utf-8') + binary_buffer[-i:]
                            else:
                                # No newline, keep entire buffer
                                pass
                            break
                        except UnicodeDecodeError:
                            # Continue trying smaller valid part
                            continue
                    # If unable to find valid boundary, keep entire buffer
                    # Will try again next time data is received
            except Exception as e:
                if type(e) is not BlockingIOError:
                    self.debug_received.emit(f"[Recv Error] {e}")
                    break
            # Try send data
            try:
                if self.sock is not None and not self.queue.empty():
                    # Get command from queue
                    cmd = self.queue.get_nowait()
                    try:
                        self.sock.sendall((cmd + '\n').encode('utf-8'))
                    except BlockingIOError:
                        # Send buffer full, put command back to queue
                        try:
                            self.queue.put_nowait(cmd)
                        except Exception:
                            pass
            except (OSError, AttributeError) as e:
                # Connection error during send
                self.debug_received.emit(f"[Send Error] {e}")
                break
            except Exception as e:
                # Skip BlockingIOError for queue operations
                if type(e) is not BlockingIOError:
                    self.debug_received.emit(f"[Send Error] {e}")
                    break
          
        self.debug_received.emit(f"[SocketWorker] {self.host}:{self.port} disconnected")
        
        # Close socket safely
        if self.sock is not None:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        
        # Set running to False
        self.running = False
        
        # Auto-reconnect if enabled
        if self._auto_reconnect:
            import time
            time.sleep(1)  # Wait 1 second before reconnecting to prevent rapid reconnection loops
            try:
                self.connect_socket(auto_reconnect=True)
            except Exception as e:
                self.debug_received.emit(f"[Reconnect Error] {e}")
    
    def send_command(self, cmd: str):
        if self.queue and self.running:
            try:
                self.queue.put_nowait(cmd)
            except Exception as e:
                self.debug_received.emit(f"[Send Error] {e}")

    def close(self):
        """
        Close socket connection and disable auto-reconnect
        """
        self._auto_reconnect = False  # Disable auto-reconnect when manually closed
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

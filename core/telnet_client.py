import telnetlib

class TelnetClient:
    def __init__(self, host="localhost", port=23232, debug=False):
        self.host = host
        self.port = port
        self.debug = debug
        self.connection = None

    def connect(self):
        if self.debug:
            print(f"[DEBUG] Connect to {self.host}:{self.port}")
            return True
        try:
            self.connection = telnetlib.Telnet(self.host, self.port, timeout=5)
            print(f"Connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def send(self, message: str):
        if self.debug:
            print(f"[DEBUG] >>> {message}")
        else:
            if self.connection:
                self.connection.write(message.encode("utf-8") + b"\n")

    def read(self):
        if self.debug:
            print("[DEBUG] <<< simulated response")
            return "OK"
        if self.connection:
            return self.connection.read_some().decode("utf-8")
        return ""

    def close(self):
        if self.connection:
            self.connection.close()
            print("Connection closed")
        elif self.debug:
            print("[DEBUG] Connection closed")


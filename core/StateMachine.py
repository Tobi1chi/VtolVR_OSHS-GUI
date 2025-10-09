from enum import Enum, auto

class State(Enum):
    IDLE = auto()
    SETHOST = auto()
    HOSTING = auto()
    READY = auto()
    RUNNING = auto()
    SKIP = auto()
    RESTART = auto()

class StateMachine:
    def __init__(self, telnet, command_obj):
        self.state = State.IDLE
        self.telnet = telnet
        self.command_obj = command_obj

        # future: inject timer/pref/logger
        self.logger = None
        self.timer = None
        self.preferences = None

    def transition(self, new_state):
        print(f"[STATE] {self.state.name} -> {new_state.name}")
        self.state = new_state

    def handle_command(self, cmd, *args):
        """根据输入的命令触发状态流转"""
        if self.state == State.IDLE and cmd == "sethost":
            self.command_obj.sethost(*args)
            self.transition(State.SETHOST)

        elif self.state == State.SETHOST and cmd == "host":
            self.command_obj.host()
            self.transition(State.HOSTING)

        elif self.state == State.HOSTING and cmd == "start":
            self.command_obj.start()
            self.transition(State.RUNNING)

        elif self.state == State.RUNNING and cmd == "skip":
            self.command_obj.skip()
            self.transition(State.SKIP)

        elif self.state == State.SKIP and cmd == "sethost":
            self.command_obj.sethost(*args)
            self.transition(State.RESTART)

        elif self.state == State.RESTART and cmd == "host":
            self.command_obj.host()
            self.transition(State.HOSTING)

        else:
            print(f"[WARN] Command '{cmd}' not valid in state {self.state.name}")

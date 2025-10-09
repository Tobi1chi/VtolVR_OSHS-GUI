class CommandObject:
    """
    封装上位机支持的命令集合。
    可通过 execute(cmd, *args) 动态调用，也可直接使用方法调用。
    """

    def __init__(self, telnet):
        self.telnet = telnet

        # command_name : (handler_function, description)
        self.commands = {
            "help": (self.show_help, "Show this help message"),
            "clear": (self.clear_console, "Clear the console"),
            "esp": (self.toggle_esp, "Toggle ESP on/off"),
            "list": (self.list_actors, "List actors (type: all/enemy/friendly/air/ground)"),
            "factor": (self.adjust_factor, "Adjust nearFactor or farFactor: factor [near/far] [value]"),
            "test": (self.test_command, "Run a test command"),
            "scene": (self.get_current_scene, "Get current scene name"),
            "readyroom": (self.goto_ready_room_mp, "Go to multiplayer ready room"),
            "flightlog": (self.get_flight_log, "Get flight log entries"),
            "sethost": (self.set_host, "Set host parameters: sethost [name|password|uniticon|campaign|mission] <value>"),
            "checkhost": (self.check_host, "Check current host settings"),
            "host": (self.host_game, "Host a multiplayer game"),
            "start": (self.start_game, "Start the multiplayer game"),
            "skip": (self.skip_mission, "Skip current missions"),
            "quit": (self.quit_game, "Quit the multiplayer game"),
            "restart": (self.restart_game, "Restart the multiplayer game"),
            "sendlog": (self.send_log, "Send a log message to the game: sendlog [message]"),
            "player": (self.list_player, "List connected players"),
            "listscene": (self.list_scene, "List available scenes"),
            "getstage": (self.get_stage, "Get current mission stage"),
        }

    # -------------------------------------------------------
    # 🔹 通用执行接口
    # -------------------------------------------------------
    def execute(self, command_name, *args):
        if command_name not in self.commands:
            print(f"[ERROR] Unknown command: {command_name}")
            return
        func, _ = self.commands[command_name]
        func(*args)

    # -------------------------------------------------------
    # 🔹 命令实现区（每个命令对应上位机逻辑）
    # -------------------------------------------------------
    def show_help(self, *args):
        for cmd, (_, desc) in self.commands.items():
            print(f"{cmd:<10} - {desc}")

    def clear_console(self, *args):
        self.telnet.send("CLEAR")

    def toggle_esp(self, *args):
        self.telnet.send("ESP")

    def list_actors(self, *args):
        actor_type = args[0] if args else "all"
        self.telnet.send(f"LIST {actor_type}")

    def adjust_factor(self, *args):
        if len(args) != 2:
            print("Usage: factor [near/far] [value]")
            return
        self.telnet.send(f"FACTOR {args[0]} {args[1]}")

    def test_command(self, *args):
        self.telnet.send("TEST")

    def get_current_scene(self, *args):
        self.telnet.send("SCENE")

    def goto_ready_room_mp(self, *args):
        self.telnet.send("READYROOM")

    def get_flight_log(self, *args):
        self.telnet.send("FLIGHTLOG")

    def set_host(self, *args):
        if len(args) < 2:
            print("Usage: sethost [name|password|uniticon|campaign|mission] <value>")
            return
        key, value = args[0], args[1]
        self.telnet.send(f"SETHOST {key} {value}")

    def check_host(self, *args):
        self.telnet.send("CHECKHOST")

    def host_game(self, *args):
        self.telnet.send("HOST")

    def start_game(self, *args):
        self.telnet.send("START")

    def skip_mission(self, *args):
        self.telnet.send("SKIP")

    def quit_game(self, *args):
        self.telnet.send("QUIT")

    def restart_game(self, *args):
        self.telnet.send("RESTART")

    def send_log(self, *args):
        if not args:
            print("Usage: sendlog [message]")
            return
        message = " ".join(args)
        self.telnet.send(f"SENDLOG {message}")

    def list_player(self, *args):
        self.telnet.send("PLAYER")

    def list_scene(self, *args):
        self.telnet.send("LISTSCENE")

    def get_stage(self, *args):
        self.telnet.send("GETSTAGE"+' '+args)

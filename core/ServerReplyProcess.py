from core.Socket import socket_service


class ServerReplyProcess:
    def __init__(self):
        self.logs = []
        self.players = []
        self.actors = []
        self.stage = ""
        self.lastState = ""
        self.flightlog = []  # 存储当前局的 flightlog
        self.debuglog = []   # 预留：存储当前局的 debuglog
        
        self.processDict = {
            'OnChatMsg': self.processChatMessage,
            'ListActors': self.processListActors,
            'ListPlayer': self.processListPlayer,
            'GetStage' : self.processGetStage,
            'GetFlightLog': self.processGetFlightLog
        }
        
        # 命令映射：将状态类型映射到对应的 socket 命令
        self.commandMap = {
            'actors': 'list all',      # 获取所有 Actor
            'players': 'player',        # 获取玩家列表
            'stage': 'getstage',        # 获取当前阶段
            'flightlog': 'flightlog',   # 获取飞行日志
        }

    def processChatMessage(self, msg):
        self.logs.append(f"[{msg['time']:6.0f}] |{msg['name']}|: {msg['msg']}")

    def processListActors(self, msg):
        self.actors = [u for u in msg]
        self.actors.sort(key=lambda x: int(x['id']))

    def processListPlayer(self, msg):
        self.players = [u for u in msg]
    
    def processGetStage(self, msg):
        self.stage = msg
    
    def processGetFlightLog(self, msg):
        """
        处理 GetFlightLog 响应
        
        Args:
            msg: flightlog 消息列表，格式如 ["[0:03:59] pingas mustard has connected.", ...]
        """
        if isinstance(msg, list):
            self.flightlog = msg.copy()
        else:
            self.flightlog = []
    
    def add_debug_log(self, message: str):
        """
        预留接口：添加 debug 日志
        
        Args:
            message: debug 日志消息
        """
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.debuglog.append(f"[{timestamp}] {message}")
    
    def clear_session_logs(self):
        """
        清除当前会话的日志（开始新一局时调用）
        """
        self.flightlog = []
        self.debuglog = []

    def request_states(self, state_types: list):
        """
        批量请求多种状态
        
        Args:
            state_types: 要请求的状态类型列表，可选值：'actors', 'players', 'stage'
        
        Example:
            serverReplyProcess.request_states(['actors', 'players', 'stage'])
            serverReplyProcess.request_states(['stage', 'players'])
        """
        if not socket_service.is_connected():
            print("[ServerReplyProcess] 警告: Socket 未连接，无法发送请求")
            return
        
        for state_type in state_types:
            if state_type in self.commandMap:
                command = self.commandMap[state_type]
                socket_service.send_command(command)
            else:
                print(f"[ServerReplyProcess] 警告: 未知的状态类型 '{state_type}'，已跳过")
    
    def request_all_states(self):
        """
        请求所有可用的状态（actors, players, stage）
        """
        self.request_states(['actors', 'players', 'stage'])

    def process(self, reply):
        if reply['type'] == 'd' or reply['type'] == 'r':
            # Data or Response
            if reply['src'] in self.processDict:
                self.processDict[reply['src']](reply['msg'])
        elif reply['type'] == 's':
            # State
            if reply['msg'] == '':
                self.lastState = reply['src']
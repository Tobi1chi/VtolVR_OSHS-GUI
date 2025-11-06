from core.Socket import socket_service


class ServerReplyProcess:
    def __init__(self):
        self.logs = []
        self.players = []
        self.actors = []
        self.stage = ""
        self.lastState = ""
        self.flightlog = []  # Store current session's flightlog
        self.debuglog = []   # Reserved: Store current session's debuglog
        
        self.processDict = {
            'OnChatMsg': self.processChatMessage,
            'ListActors': self.processListActors,
            'ListPlayer': self.processListPlayer,
            'GetStage' : self.processGetStage,
            'GetFlightLog': self.processGetFlightLog
        }
        
        # Command mapping: Map state types to corresponding socket commands
        self.commandMap = {
            'actors': 'list all',      # Get all Actors
            'players': 'player',        # Get player list
            'stage': 'getstage',        # Get current stage
            'flightlog': 'flightlog',   # Get flight log
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
        Process GetFlightLog response
        
        Args:
            msg: flightlog message list, format like ["[0:03:59] pingas mustard has connected.", ...]
        """
        if isinstance(msg, list):
            self.flightlog = msg.copy()
        else:
            self.flightlog = []
    
    def add_debug_log(self, message: str):
        """
        Reserved interface: Add debug log
        
        Args:
            message: debug log message
        """
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.debuglog.append(f"[{timestamp}] {message}")
    
    def clear_session_logs(self):
        """
        Clear current session logs (called when starting a new game session)
        """
        self.flightlog = []
        self.debuglog = []

    def request_states(self, state_types: list):
        """
        Batch request multiple states
        
        Args:
            state_types: List of state types to request, valid values: 'actors', 'players', 'stage'
        
        Example:
            serverReplyProcess.request_states(['actors', 'players', 'stage'])
            serverReplyProcess.request_states(['stage', 'players'])
        """
        if not socket_service.is_connected():
            print("[ServerReplyProcess] Warning: Socket not connected, cannot send request")
            return
        
        for state_type in state_types:
            if state_type in self.commandMap:
                command = self.commandMap[state_type]
                socket_service.send_command(command)
            else:
                print(f"[ServerReplyProcess] Warning: Unknown state type '{state_type}', skipped")
    
    def request_all_states(self):
        """
        Request all available states (actors, players, stage)
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
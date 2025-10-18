
class ServerReplyProcess:
    def __init__(self):
        self.logs = []
        self.players = []
        self.actors = []
        self.lastState = ""
        
        self.processDict = {
            'OnChatMsg': self.processChatMessage,
            'ListActors': self.processListActors,
            'ListPlayer': self.processListPlayer
        }

    def processChatMessage(self, msg):
        self.logs.append(f"[{msg['time']:6.0f}] |{msg['name']}|: {msg['msg']}")

    def processListActors(self, msg):
        self.actors = [u for u in msg]
        self.actors.sort(key=lambda x: int(x['id']))

    def processListPlayer(self, msg):
        self.players = [u for u in msg]

    def process(self, reply):
        if reply['type'] == 'd' or reply['type'] == 'r':
            # Data or Response
            if reply['src'] in self.processDict:
                self.processDict[reply['src']](reply['msg'])
        elif reply['type'] == 's':
            # State
            if reply['msg'] == '':
                self.lastState = reply['src']
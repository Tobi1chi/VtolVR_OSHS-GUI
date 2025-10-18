import os
import psutil
import threading
import time
import os
import json
from PyQt6.QtCore import QObject

class JsonParser():
    def __init__(self, mode:str):
        self.dict_str = {}
        if mode == "Socket":
            self.mode = "socket"
        elif mode == "StateMachine":
            self.mode = "statemachine"

    def parse_json(self,json_str: str):
        if self.todict(json_str) != "":
            str_temp = self.socket_parser("src")


    def todict(self,json_str: str)->dict:
        if len(json_str) > 0 and json_str[0] == "{":
            try:
                self.dict_str = json.loads(json_str)
                return self.dict_str
            except json.JSONDecodeError:
                print(f"JSONDecodeError: {json_str}")
                return {}
        return {}

    def socket_parser(self,key:str)->str:
        if key in self.dict_str.keys():
            return self.dict_str[key]

        return ""



class CommandParser(QObject):
    def __init__(self):
        super().__init__()
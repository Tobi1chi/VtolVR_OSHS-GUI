
from core.FSM.fsm_functions_config import stage_equals
from core.Timer import TimerManager
from core.Socket.socket_service import socket_service

S2MS = 1000
MIN2MS = 60 * S2MS
H2MS = 60 * MIN2MS

tm = TimerManager()
FULL_LOAD = {
    "type": "d",
    "src": "OnChatMsg",
    "msg": {
        "id": {
            "Value": 76561198356726714,
            "AccountId": 396460986,
            "IsValid": True
        },
        "name": "origa3mi",
        "time": 0.3046191,
        "msg": "$log_Tobiichi Eigetsu has connected."
    }
}
FSM_Maps:dict = {
    "state1": {
        "campaign id": "2860956181",
        "mapname": "BVR Ocixem"
    },
    "state2": {
        "campaign id": "2852088319",
        "mapname": "3V3 F-26"
    }
}

def state1():
    tm.start_stopwatch("state1")
    print("state1")
    current_map = FSM_Maps["state1"]
    start(current_map)
    await
    if tm.get_elapsed_time("state1") > 6*MIN2MS:
        

def start(current_map:dict):
    socket_service.send_command(f"sethost campaign {current_map['campaign id']}")
    delay(300)
    socket_service.send_command(f"sethost mission {current_map['mapname']}")
    delay(300)
    socket_service.send_command("confighost")
    delay(8*1000)
    socket_service.send_command("checkhost")
    delay(300)
    socket_service.send_command("host")
    delay(300)
    if  socket.received_message["id"]["AccountId"] == FULL_LOAD["id"]["AccountId"]&&socket.received_message["msg"]["msg"] == FULL_LOAD["msg"]["msg"]:
        await
    else:
        socket_service.send_command("start")


def restart(target_map:dict):
    socket_service.send_command(f"sethost campaign {target_map['campaign id']}")
    delay(300)
    socket_service.send_command(f"sethost mission {target_map['mapname']}")
    delay(300)
    socket_service.send_command("restart")
    if  socket.received_message["id"]["AccountId"] == FULL_LOAD["id"]["AccountId"]&&socket.received_message["msg"]["msg"] == FULL_LOAD["msg"]["msg"]:
        await
    else:
        socket_service.send_command("start")
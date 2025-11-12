
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
    print("state1")
    current_map = FSM_Maps["state1"]


def start(current_map:dict):
    tm.start_stopwatch("state1")
    socket_service.send_command(f"sethost campaign {current_map['campaign id']}")
    delay(300)
    socket_service.send_command(f"sethost mission {current_map['mapname']}")
    delay(300)
    socket_service.send_command("config")
    delay(8*1000)
    socket_service.send_command("checkhost")
    delay(300)
    socket_service.send_command("host")
    delay(300)
    if 
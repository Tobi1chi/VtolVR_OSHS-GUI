from core.telnet_client import TelnetClient
from core.command import CommandObject
from core.StateMachine import StateMachine

def main():
    telnet = TelnetClient(debug=True)  # ← 调试时直接打印
    telnet.connect()

    command_obj = CommandObject(telnet)
    sm = StateMachine(telnet, command_obj)

    # 模拟执行流程
    sm.handle_command("sethost", "Room1")
    sm.handle_command("host")
    sm.handle_command("start")
    sm.handle_command("skip")
    sm.handle_command("sethost", "Room2")
    sm.handle_command("host")

    telnet.close()

if __name__ == "__main__":
    main()

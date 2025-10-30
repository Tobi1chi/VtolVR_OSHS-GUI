import datetime
from pathlib import Path
class replayPacker(object):
    def __init__(self):
        self.file_path = Path(__file__).resolve().parent

    def SaveFlightlog(self, log, filename:str):
        if filename is None:
            print("No path provided")
            return
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(log, encoding='utf-8')


class ReplayPackerTimer(replayPacker):
    def __init__(self):
        super().__init__()
        self.TimerEvent = []
    def StartTimer(self, name:str):
        Event = []
        Event.append(name)
        Event.append(datetime.datetime.now())
        Event.append(datetime.datetime.utcnow())
        self.TimerEvent.append(Event.copy())
        return Event.copy()
    # def StopTimer(self, name:str):
    #     self.TimerEvent.


def main():
    print("This is the main function for testing purposes!")
    hold_time = datetime.datetime.utcnow()
    print(f"HoldTime(UTC): {hold_time}\nTimezone: {hold_time.tzinfo}")
    rp = replayPacker()
    # rp.StartTimer
    return hold_time  # 返回时间对象，供后续使用


if __name__ == "__main__":
    hold_time = main()
    # 将时间格式化为合法的文件名（去掉冒号、空格等）
    filename = hold_time.strftime("%Y-%m-%d_%H-%M") + ".log"
    Event = []
    Event.append("123123")
    Event.append(datetime.datetime.now())
    Event.append(datetime.datetime.utcnow())
    print(Event)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(hold_time.strftime("%Y-%m-%d_%H-%M"))

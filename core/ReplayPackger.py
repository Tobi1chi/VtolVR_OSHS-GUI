import datetime
from pathlib import Path
import os

class replayPacker(object):
    def __init__(self):
        # 创建 logs 目录用于存储日志文件
        self.base_path = Path(__file__).resolve().parent.parent
        self.logs_dir = self.base_path / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def SaveFlightlog(self, log_lines, filename: str = None):
        """
        保存 flightlog 到文件
        
        Args:
            log_lines: 日志行列表或字符串
            filename: 文件名（可选），如果不提供则自动生成
        """
        if filename is None:
            # 自动生成文件名：使用当前时间戳
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"flightlog_{timestamp}.txt"
        
        # 确保文件名以 .txt 结尾
        if not filename.endswith('.txt'):
            filename += '.txt'
        
        file_path = self.logs_dir / filename
        
        # 将日志内容写入文件
        if isinstance(log_lines, list):
            content = '\n'.join(log_lines)
        else:
            content = str(log_lines)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[ReplayPacker] Flightlog 已保存到: {file_path}")
            return str(file_path)
        except Exception as e:
            print(f"[ReplayPacker] 保存 flightlog 失败: {e}")
            return None
    
    def SaveDebuglog(self, log_lines, filename: str = None):
        """
        预留接口：保存 debuglog 到文件
        
        Args:
            log_lines: 日志行列表或字符串
            filename: 文件名（可选），如果不提供则自动生成
        """
        if filename is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"debuglog_{timestamp}.txt"
        
        if not filename.endswith('.txt'):
            filename += '.txt'
        
        file_path = self.logs_dir / filename
        
        if isinstance(log_lines, list):
            content = '\n'.join(log_lines)
        else:
            content = str(log_lines)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[ReplayPacker] Debuglog 已保存到: {file_path}")
            return str(file_path)
        except Exception as e:
            print(f"[ReplayPacker] 保存 debuglog 失败: {e}")
            return None
    
    def get_logs_directory(self):
        """返回日志目录路径"""
        return str(self.logs_dir)


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

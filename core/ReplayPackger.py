import datetime
from pathlib import Path
import os

class replayPacker(object):
    def __init__(self):
        # Create logs directory for storing log files
        self.base_path = Path(__file__).resolve().parent.parent
        self.logs_dir = self.base_path / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def SaveFlightlog(self, log_lines, filename: str = None):
        """
        Save flightlog to file
        
        Args:
            log_lines: Log line list or string
            filename: Filename (optional), will be auto-generated if not provided
        """
        if filename is None:
            # Auto-generate filename: use current timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"flightlog_{timestamp}.txt"
        
        # Ensure filename ends with .txt
        if not filename.endswith('.txt'):
            filename += '.txt'
        
        file_path = self.logs_dir / filename
        
        # Write log content to file
        if isinstance(log_lines, list):
            content = '\n'.join(log_lines)
        else:
            content = str(log_lines)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[ReplayPacker] Flightlog saved to: {file_path}")
            return str(file_path)
        except Exception as e:
            print(f"[ReplayPacker] Failed to save flightlog: {e}")
            return None
    
    def SaveDebuglog(self, log_lines, filename: str = None):
        """
        Reserved interface: Save debuglog to file
        
        Args:
            log_lines: Log line list or string
            filename: Filename (optional), will be auto-generated if not provided
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
            print(f"[ReplayPacker] Debuglog saved to: {file_path}")
            return str(file_path)
        except Exception as e:
            print(f"[ReplayPacker] Failed to save debuglog: {e}")
            return None
    
    def get_logs_directory(self):
        """Return logs directory path"""
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



def main():
    print("This is the main function for testing purposes!")
    hold_time = datetime.datetime.utcnow()
    print(f"HoldTime(UTC): {hold_time}\nTimezone: {hold_time.tzinfo}")
    rp = replayPacker()
    # rp.StartTimer
    return hold_time  # Return time object for future use


if __name__ == "__main__":
    hold_time = main()
    # Format time to a valid filename (remove colons, spaces, etc.)
    filename = hold_time.strftime("%Y-%m-%d_%H-%M") + ".log"
    Event = []
    Event.append("123123")
    Event.append(datetime.datetime.now())
    Event.append(datetime.datetime.utcnow())
    print(Event)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(hold_time.strftime("%Y-%m-%d_%H-%M"))

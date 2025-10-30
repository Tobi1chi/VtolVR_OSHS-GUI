import json as js
from PyQt6.QtCore import QTimer, QObject
from typing import Callable, Optional
# def jsonTemplate(key:int, name, V1:str, V2:str, TimerMin:int):
#     T = {"key":key, "name":name, "V1":V1, "V2":V2,
#          "controls":{}
#          }
#     MapStruct = [8383838383,636363636]
#     T["controls"] = {"TimerMin":TimerMin,"MC_Result": MapStruct, "TE_Result": MapStruct, "TF_Result": MapStruct}
#     with open("test.json", "w", encoding="utf-8") as f:
#         f.write(js.dumps(T))
#     print(T)
#     return ""

class TimerManager(QObject):
    """
    统一管理 PyQt 中的所有 QTimer 实例。
    所有操作必须在主线程（GUI 线程）中调用。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timers = {}  # name -> QTimer

    def start_timer(self, name: str, interval_ms: int, callback: Callable, single_shot: bool = False):
        """
        启动一个命名定时器。
        如果同名定时器已存在，会先停止并替换。
        """
        if name in self._timers:
            self.stop_timer(name)

        timer = QTimer(self)
        timer.setSingleShot(single_shot)
        timer.timeout.connect(callback)
        timer.start(interval_ms)
        self._timers[name] = timer

    def stop_timer(self, name: str) -> bool:
        """停止并移除指定名称的定时器。返回是否成功停止。"""
        if name in self._timers:
            timer = self._timers.pop(name)
            timer.stop()
            timer.deleteLater()  # 安全释放资源
            return True
        return False

    def is_timer_active(self, name: str) -> bool:
        """检查指定名称的定时器是否正在运行。"""
        return name in self._timers and self._timers[name].isActive()

    def list_timers(self):
        """返回当前所有定时器的名称列表（调试用）"""
        return list(self._timers.keys())

    def stop_all_timers(self):
        """停止并清理所有定时器"""
        for name in list(self._timers.keys()):
            self.stop_timer(name)
    def TestFuncCB(self):
        print("CB successful")
    def TestFuncCB1(self):
        print("CB1 successful!")

class FSMActuator():
    def __init__(self):
        self.counter = 0
    def TestFuncFSM(self):
        self.counter += 1






def main():
    with open("state_machine1.json","r",encoding="utf-8") as f:
        jsFile = js.load(f)
        sm = jsFile["StateMachine"]
        FSMnum = len(sm)
        sm
        print(f"{len(sm)}"+"\n")
        for i in jsFile:
            print(type(i))
            print(i)
        
    pass
if __name__ == '__main__':
    main()
    pass
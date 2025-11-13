
"""
自动任务脚本：将原始伪代码整理为可由 PyQt 主程序导入执行的脚本。

PyQt 只需 import 后调用 state1()/state2()/state3() 或 run()。
不提供命令行入口。
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from GUI.MainPage import serverReplyProcess
from core.Socket.socket_service import socket_service

LOGGER = logging.getLogger(__name__)

S2MS = 1000
MIN2MS = 60 * S2MS
H2MS = 60 * MIN2MS

SERVER_NAME = "PvP Server-60min mapcycle"
SERVER_PASSWORD = "2025"
PUBLIC = True
FULL_LOAD_KEYWORD = "$log_Tobiichi Eigetsu has connected."
STATE_DURATION_MS = 60 * MIN2MS
FULL_LOAD_TIMEOUT = 90  # 秒
FLIGHTLOG_TIMEOUT = 15  # 秒
COMMAND_DELAY_MS = 500

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
global round_number
round_number = 0

@dataclass(frozen=True)
class MapConfig:
    campaign_id: str
    mapname: str


FSM_MAPS: Dict[str, MapConfig] = {
    "state1": MapConfig(campaign_id="2860956181", mapname="BVR Ethi5"),
    "state2": MapConfig(campaign_id="3355613749", mapname="MergeLarge"),
    "state3": MapConfig(campaign_id="2860956181", mapname="BVR Archipel"),
}

DEFAULT_SEQUENCE: Sequence[str] = ("state1", "state2", "state3")


def delay(milliseconds: int) -> None:
    if milliseconds > 0:
        time.sleep(milliseconds / 1000.0)


def _ensure_connection() -> None:
    if socket_service.is_connected():
        return
    LOGGER.info("Socket 未连接，尝试连接中...")
    socket_service.connect()
    delay(500)


def _send_common_prefix(config: MapConfig) -> None:
    socket_service.send_command(f"sethost campaign {config.campaign_id}")
    delay(COMMAND_DELAY_MS)
    socket_service.send_command(f"sethost mission {config.mapname}")
    delay(COMMAND_DELAY_MS)


def start(current_map: MapConfig) -> None:
    _ensure_connection()
    socket_service.send_command(f"sethost name {SERVER_NAME}")
    if PUBLIC:
        socket_service.send_command("sethost password")
    else:
        socket_service.send_command(f"sethost password {SERVER_PASSWORD}")
    _send_common_prefix(current_map)
    socket_service.send_command("config")
    delay(8 * S2MS)
    socket_service.send_command("checkhost")
    delay(COMMAND_DELAY_MS)
    socket_service.send_command("host")
    delay(1*MIN2MS)
    socket_service.send_command("start")


def restart(target_map: MapConfig) -> None:
    _ensure_connection()
    _send_common_prefix(target_map)
    socket_service.send_command("restart")
    delay(COMMAND_DELAY_MS)
    delay(1*MIN2MS)
    socket_service.send_command("start")




def _wait_for_full_load(timeout: int = FULL_LOAD_TIMEOUT) -> bool:
    last_state = serverReplyProcess.lastState
    if last_state == "LobbyReady":
        return True
    else:
        return False


def _snapshot_logs(start_index: int) -> List[str]:
    logs = serverReplyProcess.logs
    if start_index >= len(logs):
        return []
    return logs[start_index:]


def _wait_duration(state_name: str, duration_ms: int = STATE_DURATION_MS) -> None:
    LOGGER.info("状态 %s 等待 %.1f 分钟", state_name, duration_ms / MIN2MS)
    start = time.monotonic()
    last_report = 0
    while True:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        if elapsed_ms >= duration_ms:
            return
        minutes = elapsed_ms // MIN2MS
        if minutes > last_report:
            last_report = minutes
            LOGGER.info("状态 %s 已运行 %d 分钟", state_name, minutes)
        delay(1000)


def _dump_flightlog(state_name: str) -> Path:
    LOGGER.info("请求 flightlog 数据")
    serverReplyProcess.request_states(["flightlog"])
    deadline = time.monotonic() + FLIGHTLOG_TIMEOUT
    while time.monotonic() < deadline:
        if serverReplyProcess.flightlog:
            break
        delay(500)

    flightlog = serverReplyProcess.flightlog or []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = LOG_DIR / f"{state_name}_flightlog_{timestamp}.txt"
    with target.open("w", encoding="utf-8") as f:
        if not flightlog:
            f.write("[Info] No flightlog data returned.\n")
        else:
            f.write(f"# Flightlog captured after state {state_name}\n")
            for line in flightlog:
                f.write(f"{line}\n")
    LOGGER.info("flightlog 写入 %s", target)
    return target


def _run_state(state_name: str) -> None:
    global round_number
    if state_name not in FSM_MAPS:
        LOGGER.warning("未知状态 %s，跳过。", state_name)
        return

    config = FSM_MAPS[state_name]
    LOGGER.info("执行状态 %s", state_name)

    if round_number == 0:
        start(config)
        round_number += 1
    else:
        restart(config)

    # if not _wait_for_full_load():
    #     LOGGER.warning("未检测到 FULL_LOAD，手动发送 start。")
    #     socket_service.send_command("start")

    _wait_duration(state_name)
    _dump_flightlog(state_name)


def state1() -> None:
    _run_state("state1")


def state2() -> None:
    _run_state("state2")


def state3() -> None:
    _run_state("state3")


def run(
    *,
    state_sequence: Sequence[str] = DEFAULT_SEQUENCE,
    cycles: Optional[int] = None,
) -> None:
    loop = 0
    while True:
        for state_name in state_sequence:
            _run_state(state_name)
        loop += 1
        if cycles is not None and loop >= cycles:
            break


def run_once(state_sequence: Iterable[str]) -> None:
    for state_name in state_sequence:
        _run_state(state_name)
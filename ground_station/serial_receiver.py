from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

try:
    import serial
    from serial.tools import list_ports
except ModuleNotFoundError:  # mock mode는 pyserial 없이도 동작할 수 있습니다.
    serial = None
    list_ports = None

import config
from data_model import InvalidRow
from mock_data import MockDataGenerator
from shared.telemetry_sources import SerialSource


class ConnectionState(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    RECONNECTING = "RECONNECTING"
    CONNECTED = "CONNECTED"
    MOCK = "MOCK"


@dataclass(frozen=True)
class ReceiverEvent:
    kind: str
    value: Any


def available_ports() -> list[str]:
    if list_ports is None:
        raise RuntimeError(
            "pyserial이 설치되지 않았습니다: python -m pip install -r requirements.txt"
        )
    return [port.device for port in list_ports.comports()]


def probe_port(port: str, seconds: float | None = None) -> bool:
    """포트를 잠시 읽어 지원되는 v1/v2/v3 telemetry가 오는지 확인합니다."""
    if serial is None:
        raise RuntimeError(
            "pyserial이 설치되지 않았습니다: python -m pip install -r requirements.txt"
        )
    deadline = time.monotonic() + (seconds or config.AUTO_DETECT_SECONDS_PER_PORT)
    try:
        source = SerialSource(port, config.BAUD_RATE, config.SERIAL_READ_TIMEOUT_SECONDS)
        try:
            while time.monotonic() < deadline:
                try:
                    measurement = source.read()
                except (UnicodeDecodeError, InvalidRow):
                    continue
                if measurement is not None:
                    return True
        finally:
            source.close()
    except (OSError, serial.SerialException):
        return False
    return False


def auto_detect_port() -> Optional[str]:
    ports = available_ports()
    if ports:
        print("검색한 COM 포트:", ", ".join(ports))
    else:
        print("사용 가능한 COM 포트가 없습니다.")
    for port in ports:
        print(f"  {port} telemetry 확인 중...")
        if probe_port(port):
            print(f"  정상 telemetry 발견: {port}")
            return port
    return None


class SerialReceiver:
    def __init__(self, events: queue.Queue[ReceiverEvent], port: str | None) -> None:
        self.events = events
        self.preferred_port = port
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _state(self, state: ConnectionState) -> None:
        self.events.put(ReceiverEvent("state", state))

    def _candidate_ports(self) -> list[str]:
        ports = available_ports()
        if self.preferred_port:
            return [self.preferred_port] + [p for p in ports if p != self.preferred_port]
        return ports

    def _open_port(self) -> tuple[SerialSource, str] | None:
        for port in self._candidate_ports():
            if self._stop.is_set():
                return None
            # 사용자가 고른/이전에 성공한 포트는 즉시 열고, 대체 포트는
            # 지원되는 telemetry를 실제로 확인한 뒤 선택합니다.
            if port != self.preferred_port and not probe_port(port):
                continue
            try:
                source = SerialSource(port, config.BAUD_RATE,
                                      config.SERIAL_READ_TIMEOUT_SECONDS)
                self.preferred_port = port
                return source, port
            except (OSError, serial.SerialException) as exc:
                self.events.put(ReceiverEvent("error", f"{port}: {exc}"))
        return None

    def _run(self) -> None:
        while not self._stop.is_set():
            self._state(ConnectionState.RECONNECTING)
            opened = self._open_port()
            if opened is None:
                self._state(ConnectionState.DISCONNECTED)
                self._stop.wait(config.RECONNECT_INTERVAL_SECONDS)
                continue

            source, port = opened
            self.events.put(ReceiverEvent("port", port))
            self._state(ConnectionState.CONNECTED)
            try:
                while not self._stop.is_set():
                    try:
                        measurement = source.read()
                    except (UnicodeDecodeError, InvalidRow) as exc:
                        self.events.put(ReceiverEvent("invalid", str(exc)))
                        continue
                    if measurement is None:
                        continue
                    self.events.put(ReceiverEvent("measurement", measurement))
            except (OSError, serial.SerialException) as exc:
                self.events.put(ReceiverEvent("error", f"연결 끊김: {exc}"))
            finally:
                try:
                    source.close()
                except serial.SerialException:
                    pass
                self._state(ConnectionState.DISCONNECTED)
            self._stop.wait(config.RECONNECT_INTERVAL_SECONDS)


class MockReceiver:
    def __init__(self, events: queue.Queue[ReceiverEvent]) -> None:
        self.events = events
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.generator = MockDataGenerator(
            interval_ms=int(config.MOCK_INTERVAL_SECONDS * 1000)
        )

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        self.events.put(ReceiverEvent("state", ConnectionState.MOCK))
        self.events.put(ReceiverEvent("port", "SIMULATION"))
        while not self._stop.is_set():
            self.events.put(
                ReceiverEvent("measurement", self.generator.next_measurement())
            )
            self._stop.wait(config.MOCK_INTERVAL_SECONDS)

from __future__ import annotations

import queue
import threading

from shared.telemetry_sources import TelemetrySource

from serial_receiver import ConnectionState, ReceiverEvent


class SourceReceiver:
    """SimulationSource/CSVReplaySource를 기존 dashboard event로 바꿉니다."""

    def __init__(self, events: queue.Queue[ReceiverEvent], source: TelemetrySource,
                 label: str, stop_at_eof: bool = False) -> None:
        self.events = events
        self.source = source
        self.label = label
        self.stop_at_eof = stop_at_eof
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self.source.close()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        self.events.put(ReceiverEvent("port", self.label))
        self.events.put(ReceiverEvent("state", ConnectionState.CONNECTED))
        try:
            while not self._stop.is_set():
                measurement = self.source.read()
                if measurement is None:
                    if self.stop_at_eof:
                        break
                    continue
                self.events.put(ReceiverEvent("measurement", measurement))
        except Exception as exc:
            if not self._stop.is_set():
                self.events.put(ReceiverEvent("error", str(exc)))
        finally:
            self.events.put(ReceiverEvent("state", ConnectionState.DISCONNECTED))


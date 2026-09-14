from __future__ import annotations

import argparse
import queue
import sys
import time

import config
from data_logger import DataLogger
from data_model import SequenceTracker
from serial_receiver import (
    MockReceiver,
    ReceiverEvent,
    SerialReceiver,
    auto_detect_port,
    available_ports,
)


def choose_port() -> str | None:
    detected = auto_detect_port()
    if detected:
        return detected

    ports = available_ports()
    print("정상 telemetry 자동 탐색에 실패했습니다.")
    if not ports:
        print("프로그램은 실행을 계속하며 COM 포트를 주기적으로 다시 찾습니다.")
        return None
    for index, port in enumerate(ports, start=1):
        print(f"  {index}. {port}")
    if not sys.stdin.isatty():
        return None
    try:
        answer = input("사용할 번호를 입력하거나 Enter로 자동 재연결을 계속하세요: ").strip()
        if answer:
            selected = int(answer) - 1
            if 0 <= selected < len(ports):
                return ports[selected]
    except (ValueError, EOFError):
        pass
    return None


def run_headless(receiver, events: queue.Queue[ReceiverEvent], logger: DataLogger,
                 tracker: SequenceTracker, duration: float | None) -> None:
    started = time.monotonic()
    receiver.start()
    try:
        while duration is None or time.monotonic() - started < duration:
            try:
                event = events.get(timeout=0.5)
            except queue.Empty:
                continue
            if event.kind == "measurement":
                measurement = event.value
                missing = tracker.update(measurement.seq)
                logger.write(measurement)
                print(measurement.raw_line, flush=True)
                if missing:
                    print(f"WARNING: {missing} packet(s) missing", file=sys.stderr)
            elif event.kind in {"state", "port", "error", "invalid"}:
                print(f"[{event.kind}] {event.value}", file=sys.stderr)
    except KeyboardInterrupt:
        pass
    finally:
        receiver.stop()


def main() -> int:
    parser = argparse.ArgumentParser(description="공중 환경 측정 PC 지상국")
    parser.add_argument("--mock", action="store_true", help="하드웨어 없이 가상 데이터 사용")
    parser.add_argument("--port", help="자동 탐색 대신 사용할 COM 포트 (예: COM5)")
    parser.add_argument("--headless", action="store_true", help="GUI 없이 수신/저장")
    parser.add_argument("--duration", type=float, help="headless 실행 시간(초)")
    parser.add_argument("--list-ports", action="store_true", help="COM 포트 목록만 출력")
    args = parser.parse_args()

    if args.list_ports:
        print("\n".join(available_ports()) or "사용 가능한 COM 포트 없음")
        return 0
    if args.duration is not None and not args.headless:
        parser.error("--duration은 --headless와 함께 사용하세요")

    events: queue.Queue[ReceiverEvent] = queue.Queue()
    tracker = SequenceTracker()
    logger = DataLogger(config.DATA_DIRECTORY)
    print(f"PC CSV 저장 파일: {logger.path}")

    if args.mock:
        receiver = MockReceiver(events)
    else:
        receiver = SerialReceiver(events, args.port or choose_port())

    try:
        if args.headless:
            run_headless(receiver, events, logger, tracker, args.duration)
        else:
            import tkinter as tk
            from dashboard import Dashboard

            root = tk.Tk()

            def close_all() -> None:
                receiver.stop()
                logger.close()

            Dashboard(root, events, logger, tracker, close_all)
            receiver.start()
            root.mainloop()
    finally:
        receiver.stop()
        logger.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


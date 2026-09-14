from __future__ import annotations

import socket

from controller import Robot


def main() -> None:
    robot = Robot()
    step_ms = int(robot.getBasicTimeStep())
    receiver = robot.getDevice("ground receiver")
    receiver.enable(step_ms)
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        while robot.step(step_ms) != -1:
            while receiver.getQueueLength() > 0:
                payload = bytes(receiver.getData()).rstrip(b"\x00\r\n")
                if payload:
                    udp.sendto(payload, ("127.0.0.1", 19000))
                receiver.nextPacket()
    finally:
        udp.close()


if __name__ == "__main__":
    main()


"""Report external dependencies for the ArduPilot/Webots closed loop."""
from __future__ import annotations

import argparse
import importlib.util
import shutil
import socket
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, help="ArduPilot source checkout")
    parser.add_argument("--binary", type=Path, help="ArduCopter SITL executable")
    parser.add_argument("--json-port", type=int, default=9002)
    args = parser.parse_args()
    checks = []
    if args.source:
        checks.append(("ArduPilot source", args.source.is_dir(), str(args.source)))
        backend = args.source / "libraries" / "SITL" / "SIM_JSON.cpp"
        checks.append(("SIM_JSON backend", backend.is_file(), str(backend)))
    else:
        checks.append(("ArduPilot source", False, "not configured (external dependency)"))
    if args.binary:
        checks.append(("SITL executable", args.binary.is_file(), str(args.binary)))
    else:
        found = shutil.which("arducopter")
        checks.append(("SITL executable", bool(found), found or "not configured"))
    checks.append(("pymavlink", importlib.util.find_spec("pymavlink") is not None, "Python package"))
    candidates = (
        Path(r"C:\Program Files\Webots\webots.exe"),
        Path(r"C:\Program Files\Webots\msys64\mingw64\bin\webots.exe"),
    )
    webots = shutil.which("webots") or shutil.which("webots.exe")
    if not webots:
        webots = next((str(path) for path in candidates if path.is_file()), None)
    checks.append(("Webots", bool(webots), webots or "not on PATH"))
    port_ok = False
    detail = f"udp:0.0.0.0:{args.json_port}"
    if 1 <= args.json_port <= 65535:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.bind(("127.0.0.1", args.json_port)); port_ok = True
        except OSError as exc:
            detail = str(exc)
        finally:
            probe.close()
    checks.append(("JSON listen port", port_ok, detail))
    for name, passed, detail in checks:
        print(f"{'OK' if passed else 'MISSING'}  {name}: {detail}")
    required = [item for item in checks if item[0] in {"SITL executable", "Webots", "JSON listen port"}]
    return 0 if all(item[1] for item in required) else 1


if __name__ == "__main__":
    raise SystemExit(main())

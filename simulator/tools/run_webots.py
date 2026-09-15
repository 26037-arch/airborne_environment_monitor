"""Launch the Webots world with an explicit simulator configuration."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "simulator" / "default_config.json")
    parser.add_argument("--webots", default=None, help="Webots executable path")
    args = parser.parse_args()
    config = args.config.resolve()
    if not config.is_file():
        parser.error(f"configuration not found: {config}")
    executable = args.webots or shutil.which("webots") or shutil.which("webots.exe")
    if not executable:
        parser.error("Webots executable was not found; pass --webots")
    environment = os.environ.copy()
    environment["AEM_SIM_CONFIG"] = str(config)
    world = ROOT / "simulator" / "webots" / "worlds" / "earth_environment.wbt"
    return subprocess.run([executable, str(world)], env=environment, shell=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())

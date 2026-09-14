from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except ModuleNotFoundError:
        print("PySide6가 없습니다. python -m pip install -r simulator/requirements.txt", file=sys.stderr)
        return 2
    from simulator.gui.main_window import MainWindow
    app = QApplication(sys.argv)
    window = MainWindow(PROJECT_ROOT); window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())


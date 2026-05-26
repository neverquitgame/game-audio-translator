import sys

# ── PyInstaller + macOS multiprocessing fix ───────────────────────────────────
# On macOS, multiprocessing spawns subprocesses by re-launching the frozen
# executable with argv like: [exe, "-B", "-S", "-I", "-c", "<python code>"].
# The frozen bootloader ignores the -c flag and runs main() again, causing
# infinite app instances. We intercept this early, before any other import.
if getattr(sys, "frozen", False) and "-c" in sys.argv:
    _c_idx = sys.argv.index("-c")
    if _c_idx + 1 < len(sys.argv):
        exec(sys.argv[_c_idx + 1])  # noqa: S102
    sys.exit(0)

import multiprocessing
multiprocessing.freeze_support()  # also handles --multiprocessing-fork on Windows
# ─────────────────────────────────────────────────────────────────────────────

import logging
import signal

from PySide6.QtWidgets import QApplication

from src.app.bootstrap import Bootstrap

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


def main():
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("GameAudioTranslator")
    qt_app.setOrganizationName("GameAudioTranslator")
    qt_app.setQuitOnLastWindowClosed(False)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    Bootstrap(qt_app).run()


if __name__ == "__main__":
    main()

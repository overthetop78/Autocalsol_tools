from __future__ import annotations

import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from autocalsol_tools.gui.main_window import MainWindow


def test_background_worker_is_kept_alive_and_runs():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    completed: list[str] = []
    progress: list[str] = []

    window._start_worker(
        lambda report: (report("travail démarré"), "terminé")[1],
        completed.append,
        lambda error: completed.append(f"erreur: {error}"),
        progress=progress.append,
    )

    deadline = time.monotonic() + 3
    while not completed and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)

    assert progress == ["travail démarré"]
    assert completed == ["terminé"]

    deadline = time.monotonic() + 3
    while window._threads and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert not window._threads
    assert not window._workers
    window.close()

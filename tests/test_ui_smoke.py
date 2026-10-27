"""Headless smoke tests for the karaoke UI.

The original unit tests never constructed the window, so a startup crash
(mic_manager used before it existed) shipped unnoticed. These build the real UI
offscreen so that can't happen again.
"""
import os
import time
import importlib.machinery
import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("PyQt6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SCRIPT_PATH = Path(__file__).parent.parent / "stage-katoy" / "03-tools" / "files" / "katoy-karaoke"


@pytest.fixture(scope="module")
def kk():
    loader = importlib.machinery.SourceFileLoader("katoy_karaoke_ui", str(SCRIPT_PATH))
    spec = importlib.util.spec_from_loader("katoy_karaoke_ui", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def qapp(kk):
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    kk.apply_theme(app, 1080)
    return app


def _dispose(app, w):
    w.close()
    if w.net_watcher:
        w.net_watcher.wait(5000)
    w.deleteLater()
    _pump(app, 50)


def _pump(app, ms):
    end = time.time() + ms / 1000
    while time.time() < end:
        app.processEvents()


def test_window_constructs_and_survives_startup(kk, qapp):
    cfg = kk.load_config()
    cfg.update({"REMOTE_ENABLED": "0", "SONGS_DIR": "/nonexistent-usb", "FULLSCREEN": "0", "KIOSK": "1"})
    w = kk.KaraokeApp(cfg)
    w.resize(1280, 720)
    w.show()
    _pump(qapp, 400)  # runs _late_init
    assert w.stack.currentWidget() is w.no_usb_page
    w.grab()  # paint every widget once
    _dispose(qapp, w)


def test_kiosk_escape_never_quits(kk, qapp):
    cfg = kk.load_config()
    cfg.update({"REMOTE_ENABLED": "0", "SONGS_DIR": "/nonexistent-usb", "KIOSK": "1"})
    w = kk.KaraokeApp(cfg)
    w.show()
    w.stack.setCurrentWidget(w.library_page)
    w.on_escape_pressed()
    assert w.isVisible()
    _dispose(qapp, w)


def test_lyric_wipe_progresses_and_first_frame_is_correct(kk, qapp):
    from PyQt6.QtWidgets import QWidget
    host = QWidget()
    host.resize(1200, 200)
    line = kk.LyricLineWidget(70, "current", host)
    line.resize(1200, 130)
    host.show()
    line.set_syllables([("Hel", 1.0, 2.0), ("lo ", 2.0, 3.0), ("world", 3.0, 4.0)])
    line.set_elapsed(0.5)
    assert line._wipe == pytest.approx(line._edges[0][0])  # nothing sung yet
    line.set_elapsed(2.5)  # first call right after set_syllables must already work
    assert line._edges[1][0] < line._wipe < line._edges[1][1]
    line.set_elapsed(10)
    assert line._wipe == pytest.approx(line._edges[-1][1])


def test_long_line_shrinks_to_fit(kk, qapp):
    from PyQt6.QtWidgets import QWidget
    host = QWidget()
    host.resize(800, 200)
    line = kk.LyricLineWidget(78, "current", host)
    line.resize(800, 130)
    host.show()
    line.set_text("Isang napakahabang linya ng awit na hindi kasya sa isang hanay")
    line.grab()
    first, last = line._edges[0][0], line._edges[-1][1]
    assert first >= 0 and last <= 800

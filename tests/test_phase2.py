import tempfile
import shutil
from pathlib import Path

import pytest
import mido

# Load katoy-karaoke script module dynamically
SCRIPT_PATH = Path(__file__).parent.parent / "stage-katoy" / "03-tools" / "files" / "katoy-karaoke"

kk = {"__name__": "__test__", "__file__": str(SCRIPT_PATH)}
with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
    exec(f.read(), kk)


def test_cascading_config_loading():
    tmpdir = Path(tempfile.mkdtemp())
    try:
        # Create a mock USB config
        usb_conf = tmpdir / ".katoy-karaoke.conf"
        usb_conf.write_text("MIC_VOLUME=95\nSCORING_MODE=fun\n", encoding="utf-8")

        cfg = kk["load_config"](tmpdir)
        assert cfg["MIC_VOLUME"] == "95"
        assert cfg["SCORING_MODE"] == "fun"
        assert cfg["REMOTE_PORT"] == "8080"  # Retains system default
    finally:
        shutil.rmtree(tmpdir)


def test_calculate_real_score():
    score_fn = kk["calculate_real_score"]

    # Silent / empty samples
    score_silent = score_fn([], 10)
    assert 85 <= score_silent <= 92

    # Active singing samples (all above threshold 0.1)
    samples = [0.2, 0.5, 0.8, 0.4, 0.6]
    score_active = score_fn(samples, 5)
    assert score_active == 100

    # Half active samples
    samples_half = [0.2, 0.0, 0.5, 0.0]
    score_half = score_fn(samples_half, 4)
    assert score_half == 87


def test_generate_qr_matrix():
    qr_fn = kk["generate_qr_matrix"]
    url = "http://192.168.1.100:8080"
    matrix = qr_fn(url)

    assert len(matrix) >= 21
    assert len(matrix[0]) >= 21
    # Check finder patterns (top-left 7x7)
    assert matrix[0][0] is True
    assert matrix[0][6] is True
    assert matrix[6][0] is True

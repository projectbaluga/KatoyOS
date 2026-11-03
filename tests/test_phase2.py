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


def test_parse_nmcli_general_state():
    parse_fn = kk["parse_nmcli_general_state"]

    assert parse_fn("connected\n") == "connected"
    assert parse_fn("connected (local only)") == "limited"
    assert parse_fn("disconnected") == "disconnected"
    assert parse_fn("") == "unknown"


def test_parse_nmcli_wifi_list():
    parse_fn = kk["parse_nmcli_wifi_list"]

    raw_output = "MyHomeWiFi:80:WPA2\nOfficeWiFi:65:WPA2\n--:40:WPA2\nMyHomeWiFi:75:WPA2\n"
    ssids = parse_fn(raw_output)

    assert ssids == ["MyHomeWiFi", "OfficeWiFi"]
    assert parse_fn("") == []


def test_remote_settings_page_and_update():
    # Verify that RemoteRequestHandler serves /settings and applies config updates
    import io
    import json

    handler = kk["RemoteRequestHandler"]

    class MockApp:
        def __init__(self):
            self.config = {
                "HOTSPOT_SSID": "KaraOkePi",
                "HOTSPOT_PASSWORD": "katoyos123",
                "MIC_VOLUME": "80",
                "MUSIC_VOLUME": "100",
                "MIC_ENABLED": "1",
                "MIC_REVERB": "0",
                "SCORING_MODE": "real",
                "REMOTE_PIN": ""
            }
            self.mic_manager = None

    def create_mock_handler(target_path, client_addr=("10.0.0.42", 1234)):
        class DummyHandler(handler):
            def __init__(self, path):
                self.path = path
                self.wfile = io.BytesIO()
                self.rfile = io.BytesIO()
                self.headers = {}
                self.response_code = None
                self.app_instance = MockApp()
                self.bridge_signals = None
                self.client_address = client_addr
                self.pin = ""

            def send_response(self, code, message=None):
                self.response_code = code

            def send_header(self, keyword, value):
                pass

            def end_headers(self):
                pass

        return DummyHandler(target_path)

    h_settings = create_mock_handler("/settings")
    h_settings.do_GET()
    assert h_settings.response_code == 200
    assert b"KaraOkePi Settings" in h_settings.wfile.getvalue()
    assert b"HOTSPOT_SSID" in h_settings.wfile.getvalue()

    # Test updating settings
    h_update = create_mock_handler("/settings?HOTSPOT_SSID=NewParty&MIC_VOLUME=90")
    h_update.do_GET()
    assert h_update.response_code == 200
    res = json.loads(h_update.wfile.getvalue().decode("utf-8"))
    assert res.get("status") == "ok"
    assert h_update.app_instance.config["HOTSPOT_SSID"] == "NewParty"
    assert h_update.app_instance.config["MIC_VOLUME"] == "90"


def test_parse_systemd_analyze_output():
    parse_fn = kk["parse_systemd_analyze_output"]

    out = "Startup finished in 4.120s (kernel) + 17.340s (userspace) = 21.460s\ngraphical.target reached after 21.460s"
    parsed = parse_fn(out)
    assert parsed is not None
    assert "21.460s" in parsed
    assert "(kernel) + 17.340s (userspace)" in parsed
    assert "target ~25s" in parsed

    assert parse_fn("") is None

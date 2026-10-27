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


def test_wifi_setup_route_alias():
    # Verify that RemoteRequestHandler handles both /wifi and /setup routes
    import io

    handler = kk["RemoteRequestHandler"]

    def create_mock_handler(target_path):
        class DummyHandler(handler):
            def __init__(self, path):
                self.path = path
                self.wfile = io.BytesIO()
                self.rfile = io.BytesIO()
                self.response_code = None
                self.app_instance = None
                self.bridge_signals = None

            def send_response(self, code, message=None):
                self.response_code = code

            def send_header(self, keyword, value):
                pass

            def end_headers(self):
                pass

        return DummyHandler(target_path)

    h_wifi = create_mock_handler("/wifi")
    h_wifi.do_GET()
    assert h_wifi.response_code == 200
    assert b"KatoyOS Wi-Fi Setup" in h_wifi.wfile.getvalue()

    h_setup = create_mock_handler("/setup")
    h_setup.do_GET()
    assert h_setup.response_code == 200
    assert b"KatoyOS Wi-Fi Setup" in h_setup.wfile.getvalue()


def test_wifi_status_endpoint():
    # Verify that /wifi/status and /api/wifi-status serve persisted status or pending
    import io
    from pathlib import Path

    handler = kk["RemoteRequestHandler"]

    def create_mock_handler(target_path):
        class DummyHandler(handler):
            def __init__(self, path):
                self.path = path
                self.wfile = io.BytesIO()
                self.rfile = io.BytesIO()
                self.response_code = None
                self.app_instance = None
                self.bridge_signals = None

            def send_response(self, code, message=None):
                self.response_code = code

            def send_header(self, keyword, value):
                pass

            def end_headers(self):
                pass

        return DummyHandler(target_path)

    # Test when no status file exists
    status_file = Path("/tmp/katoy-wifi-status.json")
    if status_file.exists():
        status_file.unlink()

    h_pending = create_mock_handler("/wifi/status")
    h_pending.do_GET()
    assert h_pending.response_code == 200
    assert b"pending" in h_pending.wfile.getvalue()

    # Test when status file exists
    try:
        status_file.write_text('{"status":"ok","connected":true,"ssid":"TestNet"}', encoding="utf-8")
        h_ok = create_mock_handler("/api/wifi-status")
        h_ok.do_GET()
        assert h_ok.response_code == 200
        assert b"TestNet" in h_ok.wfile.getvalue()
    finally:
        if status_file.exists():
            status_file.unlink()


def test_parse_systemd_analyze_output():
    parse_fn = kk["parse_systemd_analyze_output"]

    out = "Startup finished in 4.120s (kernel) + 17.340s (userspace) = 21.460s\ngraphical.target reached after 21.460s"
    parsed = parse_fn(out)
    assert parsed is not None
    assert "21.460s" in parsed
    assert "(kernel) + 17.340s (userspace)" in parsed
    assert "target ~25s" in parsed

    assert parse_fn("") is None

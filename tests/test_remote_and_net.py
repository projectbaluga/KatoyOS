import tempfile
import threading
import shutil
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parent.parent / "stage-katoy" / "03-tools" / "files" / "katoy-karaoke"
kk = {"__name__": "__test__", "__file__": str(SCRIPT_PATH)}
with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
    exec(f.read(), kk)


def test_wifi_qr_payload_escapes_specials():
    f = kk["wifi_qr_payload"]
    assert f("KaraOkePi", "katoyos123") == "WIFI:T:WPA;S:KaraOkePi;P:katoyos123;;"
    assert f("a;b", 'p:"x,y\\') == 'WIFI:T:WPA;S:a\\;b;P:p\\:\\"x\\,y\\\\;;'


def test_database_is_usable_from_other_threads():
    """The phone remote queries from HTTP worker threads."""
    tmp = Path(tempfile.mkdtemp())
    db = kk["SongDatabase"](tmp / "t.db")
    with db.conn:
        db.conn.execute("INSERT INTO songs(code,title,artist,filepath,mtime) VALUES('00042','Harana','Parokya','/x.mid',0)")
    result = {}

    def worker():
        try:
            result["rows"] = db.search("harana")
            result["one"] = db.get_by_code("42")
        except Exception as e:  # sqlite3.ProgrammingError before the fix
            result["err"] = e

    th = threading.Thread(target=worker)
    th.start()
    th.join()
    assert "err" not in result, result.get("err")
    rows = result["rows"]["songs"] if isinstance(result["rows"], dict) else result["rows"]
    assert rows[0][0] == "00042"
    assert result["one"][1] == "Harana"


def test_api_search_clamping_and_validation():
    handler_class = kk["RemoteRequestHandler"]

    class MockApp:
        def __init__(self, db):
            self.db = db
            self.net_ap = False

    class MockServer:
        def __init__(self):
            self.sent_json = None
            self.sent_code = None

    tmp = Path(tempfile.mkdtemp())
    try:
        db_path = tmp / "search_test.db"
        db = kk["SongDatabase"](db_path)
        with db.conn:
            for i in range(1, 250):
                code = f"{i:05d}"
                db.conn.execute("INSERT INTO songs(code,title,artist,filepath,mtime) VALUES(?,?,?,?,0)",
                                (code, f"Song {i}", "Artist", f"/{code}.mid"))

        app = MockApp(db)
        handler_class.app_instance = app
        handler_class.pin = ""

        # Test valid search & limit clamping (max 200)
        req = handler_class.__new__(handler_class)
        req.path = "/api/search?q=&limit=500&offset=-10"
        json_resp = None
        status_code = None
        def mock_send_json(data, code=200):
            nonlocal json_resp, status_code
            json_resp = data
            status_code = code
        req.send_json = mock_send_json

        req.do_GET()
        assert status_code == 200
        assert len(json_resp["songs"]) == 200
        assert json_resp["total"] == 249

        # Test invalid offset -> 400
        req.path = "/api/search?offset=abc"
        req.do_GET()
        assert status_code == 400
        assert "Invalid offset parameter" in json_resp["error"]

        # Test invalid limit -> 400
        req.path = "/api/search?limit=xyz"
        req.do_GET()
        assert status_code == 400
        assert "Invalid limit parameter" in json_resp["error"]

        db.close()
    finally:
        shutil.rmtree(tmp)


def test_katoydata_fstab_and_expand_service_configuration():
    script_04 = SCRIPT_PATH.parent.parent.parent / "04-pi3" / "00-run.sh"
    content_04 = script_04.read_text(encoding="utf-8")
    assert "/media/katoy/KATOYDATA" in content_04
    assert "LABEL=KATOYDATA" in content_04
    assert "vfat" in content_04
    assert "nofail" in content_04
    assert "init_resize.sh" in content_04

    expand_svc = SCRIPT_PATH.parent / "katoy-expand-data.service"
    assert expand_svc.exists()
    svc_text = expand_svc.read_text(encoding="utf-8")
    assert "ExecStart=/usr/bin/katoy-expand-data" in svc_text
    assert "Before=katoy-karaoke.service" in svc_text

    expand_script = SCRIPT_PATH.parent / "katoy-expand-data"
    assert expand_script.exists()
    script_text = expand_script.read_text(encoding="utf-8")
    assert "fatresize" in script_text
    assert "parted" in script_text


def test_service_unit_has_no_ordering_cycle_and_a_login_session():
    unit = (SCRIPT_PATH.parent / "katoy-karaoke.service").read_text()
    assert "WantedBy=multi-user.target" in unit
    after = [l for l in unit.splitlines() if l.startswith("After=")]
    assert not any("graphical.target" in l for l in after)
    assert "PAMName=login" in unit
    assert "Conflicts=getty@tty1.service" in unit


def test_captive_portal_redirection_and_hotspot_routing():
    RemoteRequestHandler = kk["RemoteRequestHandler"]

    class MockApp:
        def __init__(self, is_ap=True):
            self.net_ap = is_ap
            self.net_ip = "10.0.0.1"
            self.config = {"REMOTE_PORT": "8080"}
            self.db = None
            self.reservation_queue = []
            self.is_playing = False
            self.is_paused = False
            self.current_song = None
            self.pitch_key = 0
            self.tempo_multiplier = 1.0

    class DummyHandler(RemoteRequestHandler):
        def __init__(self, path, headers=None, is_ap=True, client_addr=("10.0.0.42", 54321), pin=""):
            self.path = path
            self.headers = headers or {}
            self.client_address = client_addr
            self.app_instance = MockApp(is_ap)
            self.pin = pin
            self.responses = []
            self.header_list = {}
            self.wfile = io.BytesIO()
            self.do_GET()

        def send_response(self, code):
            self.responses.append(code)

        def send_header(self, k, v):
            self.header_list[k] = v

        def end_headers(self):
            pass

    import io

    # Test probe redirect points to http://<ip>:<port>/
    h = DummyHandler("/generate_204", {"Host": "connectivitycheck.gstatic.com"})
    assert 302 in h.responses
    assert h.header_list.get("Location") == "http://10.0.0.1:8080/"

    # Test iOS probe redirect
    h_ios = DummyHandler("/hotspot-detect.html", {"Host": "captive.apple.com"})
    assert 302 in h_ios.responses
    assert h_ios.header_list.get("Location") == "http://10.0.0.1:8080/"

    # Test unknown path redirect during hotspot mode
    h_unknown = DummyHandler("/some/random/url", {"Host": "example.com"})
    assert 302 in h_unknown.responses
    assert h_unknown.header_list.get("Location") == "http://10.0.0.1:8080/"

    # Test unknown path when hotspot is inactive and client is non-AP returns 404
    h_unknown_no_ap = DummyHandler("/some/random/url", {"Host": "example.com"}, is_ap=False, client_addr=("192.168.1.15", 54321))
    assert 404 in h_unknown_no_ap.responses

    # Test root during hotspot mode serves REMOTE_HTML (full remote UI with Settings link)
    h_root = DummyHandler("/")
    assert 200 in h_root.responses
    assert b"KaraOkePi Remote" in h_root.wfile.getvalue()
    assert b"/settings" in h_root.wfile.getvalue()

    # Test Settings page has link back to remote and form fields
    h_settings = DummyHandler("/settings")
    assert 200 in h_settings.responses
    assert b"KaraOkePi Settings" in h_settings.wfile.getvalue()
    assert b"Remote" in h_settings.wfile.getvalue()
    assert b"HOTSPOT_SSID" in h_settings.wfile.getvalue()

    # Test /api/* reachable on AP interface even if REMOTE_PIN is set
    h_api = DummyHandler("/api/state", client_addr=("10.0.0.5", 1234), pin="9999")
    assert 200 in h_api.responses
    assert b"playing" in h_api.wfile.getvalue()

    # Test non-AP client without PIN is blocked when REMOTE_PIN is set
    h_api_blocked = DummyHandler("/api/state", client_addr=("192.168.1.50", 1234), pin="9999", is_ap=False)
    assert 401 in h_api_blocked.responses


def test_hotspot_mode_behavior_and_watcher():
    NetworkWatcher = kk["NetworkWatcher"]

    cfg_always = {"HOTSPOT_MODE": "always", "HOTSPOT_SSID": "TestAP", "HOTSPOT_GRACE": "10"}
    w_always = NetworkWatcher(cfg_always)
    assert w_always.mode == "always"

    cfg_fallback = {"HOTSPOT_MODE": "fallback", "HOTSPOT_SSID": "TestAP", "HOTSPOT_GRACE": "30"}
    w_fallback = NetworkWatcher(cfg_fallback)
    assert w_fallback.mode == "fallback"
    assert w_fallback.grace == 30.0


def test_is_hotspot_active_detection_multi_criteria(monkeypatch):
    """Verify is_hotspot_active checks systemd units, iw/iwconfig, and 10.0.0.0/24 subnet."""
    is_hotspot_active = kk["is_hotspot_active"]

    # 1. Systemd unit active
    monkeypatch.setattr("subprocess.run", lambda args, **kwargs:
        type("Res", (), {"returncode": 0 if "katoy-ap.service" in args else 1, "stdout": "", "stderr": ""})())
    assert is_hotspot_active() is True

    # 2. iw dev reporting type AP
    def mock_iw(args, **kwargs):
        if args == ["iw", "dev"]:
            return type("Res", (), {"returncode": 0, "stdout": "Interface wlan0\n  type AP\n", "stderr": ""})()
        return type("Res", (), {"returncode": 1, "stdout": "", "stderr": ""})()
    monkeypatch.setattr("subprocess.run", mock_iw)
    assert is_hotspot_active() is True

    # 3. 10.0.0.0/24 interface IP assigned
    def mock_ip(args, **kwargs):
        if args == ["ip", "-o", "-4", "addr", "show"]:
            return type("Res", (), {"returncode": 0, "stdout": "2: wlan0 inet 10.0.0.1/24 brd 10.0.0.255 scope global wlan0\n", "stderr": ""})()
        return type("Res", (), {"returncode": 1, "stdout": "", "stderr": ""})()
    monkeypatch.setattr("subprocess.run", mock_ip)
    assert is_hotspot_active() is True

    # 4. Nothing active
    monkeypatch.setattr("subprocess.run", lambda args, **kwargs:
        type("Res", (), {"returncode": 1, "stdout": "", "stderr": ""})())
    assert is_hotspot_active() is False


def test_settings_lyric_offset_update():
    """Verify updating LYRIC_OFFSET via /settings is parsed, persisted, and live applied."""
    RemoteRequestHandler = kk["RemoteRequestHandler"]

    class MockApp:
        def __init__(self):
            self.config = {"LYRIC_OFFSET": "0.0"}
            self.lyric_offset = 0.0
            self.mic_manager = None
            self.songs_dir = ""

    handler = RemoteRequestHandler.__new__(RemoteRequestHandler)
    handler.app_instance = MockApp()
    sent_data = {}
    handler.send_json = lambda d, c=200: sent_data.update(d)

    handler._apply_settings_update({"LYRIC_OFFSET": ["0.5"]})
    assert handler.app_instance.config["LYRIC_OFFSET"] == "0.5"
    assert handler.app_instance.lyric_offset == 0.5
    assert sent_data.get("status") == "ok"


def test_expanded_captive_portal_probes():
    """Verify newly added probe endpoints redirect to captive portal."""
    RemoteRequestHandler = kk["RemoteRequestHandler"]

    class MockApp:
        def __init__(self):
            self.net_ap = True
            self.net_ip = "10.0.0.1"
            self.config = {"REMOTE_PORT": "8080"}

    class DummyHandler(RemoteRequestHandler):
        def __init__(self, path):
            self.path = path
            self.headers = {}
            self.client_address = ("10.0.0.55", 12345)
            self.app_instance = MockApp()
            self.pin = ""
            self.responses = []
            self.header_list = {}
            self.do_GET()

        def send_response(self, code):
            self.responses.append(code)

        def send_header(self, k, v):
            self.header_list[k] = v

        def end_headers(self):
            pass

    for probe in ("/canonical.html", "/check_network_status.txt", "/mobile/status.php", "/kindle-wifi/wifiredirect.html"):
        h = DummyHandler(probe)
        assert 302 in h.responses
        assert h.header_list.get("Location") == "http://10.0.0.1:8080/"

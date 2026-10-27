import tempfile
import threading
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parent.parent / "stage-katoy" / "03-tools" / "files" / "katoy-karaoke"
kk = {"__name__": "__test__", "__file__": str(SCRIPT_PATH)}
with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
    exec(f.read(), kk)


def test_wifi_qr_payload_escapes_specials():
    f = kk["wifi_qr_payload"]
    assert f("KatoyOS-Karaoke", "katoyos123") == "WIFI:T:WPA;S:KatoyOS-Karaoke;P:katoyos123;;"
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
    assert result["rows"][0][0] == "00042"
    assert result["one"][1] == "Harana"


def test_service_unit_has_no_ordering_cycle_and_a_login_session():
    unit = (SCRIPT_PATH.parent / "katoy-karaoke.service").read_text()
    assert "WantedBy=multi-user.target" in unit
    after = [l for l in unit.splitlines() if l.startswith("After=")]
    assert not any("graphical.target" in l for l in after)
    assert "PAMName=login" in unit
    assert "Conflicts=getty@tty1.service" in unit

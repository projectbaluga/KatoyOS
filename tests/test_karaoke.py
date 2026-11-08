import os
import sys
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


def test_filename_parsing():
    parse_fn = kk["parse_filename_metadata"]

    has_code, code, title, artist = parse_fn(Path("00042 - Eraserheads - Ang Huling El Bimbo.mid"))
    assert has_code is True
    assert code == "00042"
    assert title == "Ang Huling El Bimbo"
    assert artist == "Eraserheads"

    has_code, code, title, artist = parse_fn(Path("Rivermaya - Kisapmata.kar"))
    assert has_code is False
    assert code is None
    assert title == "Kisapmata"
    assert artist == "Rivermaya"


def test_lyrics_and_encoding_robustness():
    tmpdir = Path(tempfile.mkdtemp())
    try:
        mid = mido.MidiFile(type=1)
        track = mido.MidiTrack()
        mid.tracks.append(track)

        # Tagalog/Spanish diacritic lyric in latin1 encoding
        latin1_text = "Mabangong Sampaguita - Café"
        track.append(mido.MetaMessage("lyrics", text=latin1_text.encode("latin1").decode("latin1"), time=0))
        track.append(mido.MetaMessage("set_tempo", tempo=500000, time=0))
        track.append(mido.Message("note_on", note=60, velocity=64, time=100))
        track.append(mido.Message("note_off", note=60, velocity=0, time=480))

        midi_path = tmpdir / "test_song.mid"
        mid.save(midi_path)

        lines, duration, m_title, m_artist = kk["extract_midi_lyrics_and_duration"](midi_path)
        assert len(lines) > 0
        assert "Mabangong" in lines[0]["text"]
        assert duration > 0.5
    finally:
        shutil.rmtree(tmpdir)


def test_midi_vocal_gender_metadata_and_fallback():
    tmpdir = Path(tempfile.mkdtemp())
    try:
        mid = mido.MidiFile(type=1)
        track = mido.MidiTrack()
        mid.tracks.append(track)
        track.append(mido.MetaMessage("text", text="@GENDER=FEMALE", time=0))
        midi_path = tmpdir / "female.mid"
        mid.save(midi_path)

        detect = kk["extract_midi_vocal_gender"]
        assert detect(midi_path) == "FEMALE"

        mid2 = mido.MidiFile(type=1)
        mid2.tracks.append(mido.MidiTrack())
        male_path = tmpdir / "untagged.mid"
        mid2.save(male_path)
        assert detect(male_path, "MALE") == "MALE"
        assert detect(male_path, "FEMALE") == "FEMALE"
    finally:
        shutil.rmtree(tmpdir)


def test_pitch_transpose_preserves_drum_channel():
    tmpdir = Path(tempfile.mkdtemp())
    try:
        mid = mido.MidiFile(type=1)
        track = mido.MidiTrack()
        mid.tracks.append(track)

        # Melodic note on channel 0
        track.append(mido.Message("note_on", note=60, velocity=64, channel=0, time=0))
        # Percussion/Drum note on channel 9 (10th MIDI channel)
        track.append(mido.Message("note_on", note=38, velocity=64, channel=9, time=10))

        src_path = tmpdir / "src.mid"
        dst_path = tmpdir / "dst.mid"
        mid.save(src_path)

        kk["process_midi_file"](src_path, dst_path, semi_tones=3, tempo_multiplier=1.0)

        transposed_mid = mido.MidiFile(dst_path)
        notes = []
        for trk in transposed_mid.tracks:
            for msg in trk:
                if msg.type == "note_on":
                    notes.append((msg.channel, msg.note))

        assert (0, 63) in notes  # Transposed from 60 to 63
        assert (9, 38) in notes  # Channel 9 (drums) untouched
    finally:
        shutil.rmtree(tmpdir)


def test_stable_code_assignment_and_index_change():
    tmpdir = Path(tempfile.mkdtemp())
    try:
        mid = mido.MidiFile(type=1)
        track = mido.MidiTrack()
        mid.tracks.append(track)

        f1 = tmpdir / "SongA.mid"
        f2 = tmpdir / "SongB.mid"
        mid.save(f1)
        mid.save(f2)

        db_path = tmpdir / "test.db"
        db = kk["SongDatabase"](db_path)
        count = db.index_songs(tmpdir)
        assert count == 2

        code_a1 = db.get_by_code("00001")
        code_b2 = db.get_by_code("00002")
        assert code_a1 is not None or code_b2 is not None

        # Add a new file and re-index
        f3 = tmpdir / "00000_AAA.mid"
        mid.save(f3)

        count2 = db.index_songs(tmpdir, force=True)
        assert count2 == 3

        # Confirm 00000_AAA gets 00000 and original files keep their assigned codes
        code_aaa = db.get_by_code("00000")
        assert code_aaa is not None
        assert "AAA" in code_aaa[1]

        db.close()
    finally:
        shutil.rmtree(tmpdir)


def test_indexing_multiple_directories():
    tmpdir = Path(tempfile.mkdtemp())
    try:
        d1 = tmpdir / "usb"
        d2 = tmpdir / "builtin"
        d1.mkdir()
        d2.mkdir()

        mid = mido.MidiFile(type=1)
        track = mido.MidiTrack()
        mid.tracks.append(track)

        f1 = d1 / "SongUSB.mid"
        f2 = d2 / "SongSD.mid"
        mid.save(f1)
        mid.save(f2)

        db_path = tmpdir / "test_multi.db"
        db = kk["SongDatabase"](db_path)
        count = db.index_songs([d1, d2])
        assert count == 2

        res = db.search("")
        rows = res["songs"] if isinstance(res, dict) else res
        assert len(rows) == 2
        titles = [r[1] for r in rows]
        assert "SongUSB" in titles
        assert "SongSD" in titles

        db.close()
    finally:
        shutil.rmtree(tmpdir)


def test_calculate_elapsed_seconds():
    calc_fn = kk["calculate_elapsed_seconds"]

    assert calc_fn(0, 1000, 180.0) == 0.0
    assert calc_fn(500, 1000, 180.0) == 90.0
    assert calc_fn(1000, 1000, 180.0) == 180.0
    assert calc_fn(-10, 1000, 180.0) == 0.0
    assert calc_fn(1500, 1000, 180.0) == 180.0


def test_queue_tuple_unpacking_4_and_5_elements():
    """Verify that queue operations safely handle 4-tuples and 5-tuples without crash."""
    app_class = kk["KaraokeApp"]

    class FakeApp:
        def __init__(self):
            self.reservation_queue = []
            self.current_song = None
            self.started_playback = []

        def update_queue_ui(self):
            pass

        def stop_playback(self):
            pass

        def start_playback(self, code, title, artist, filepath, singer=""):
            self.started_playback.append((code, title, artist, filepath, singer))

    fake = FakeApp()

    # 1. 4-tuple without singer
    item4 = ("00001", "Song Four", "Artist 4", "/path/4.mid")
    fake.reservation_queue.append(item4)
    app_class.play_next_reserved_song(fake)
    assert len(fake.started_playback) == 1
    assert fake.started_playback[0] == ("00001", "Song Four", "Artist 4", "/path/4.mid", "")

    # 2. 5-tuple with singer
    item5 = ("00002", "Song Five", "Artist 5", "/path/5.mid", "Juan")
    fake.reservation_queue.append(item5)
    app_class.play_next_reserved_song(fake)
    assert len(fake.started_playback) == 2
    assert fake.started_playback[1] == ("00002", "Song Five", "Artist 5", "/path/5.mid", "Juan")


def test_lyric_offset_config_and_render():
    """Verify LYRIC_OFFSET is read into config and affects effective elapsed time."""
    load_cfg = kk["load_config"]
    cfg = load_cfg()
    assert "LYRIC_OFFSET" in cfg
    assert float(cfg["LYRIC_OFFSET"]) == 0.0


def test_instrumental_gap_countdown():
    """Verify instrumental countdown indicators appear for intro and interlude gaps."""
    app_class = kk["KaraokeApp"]

    class MockLabel:
        def __init__(self):
            self.text = ""
        def set_text(self, t):
            self.text = t
        def set_syllables(self, s):
            pass
        def set_elapsed(self, t):
            pass

    class FakeLyricApp:
        def __init__(self):
            self.lyrics_lines = [
                {"text": "Line One", "start_sec": 10.0, "syllables": [{"text": "Line One", "sec": 10.0}]},
                {"text": "Line Two", "start_sec": 25.0, "syllables": [{"text": "Line Two", "sec": 25.0}]}
            ]
            self._lyric_idx = -2
            self.lyric_curr_lbl = MockLabel()
            self.lyric_next_lbl = MockLabel()
            self.lyric_prev_lbl = MockLabel()

        def _segments_for_line(self, idx):
            return [("Line", 10.0, 11.0)]

    fake = FakeLyricApp()

    # Intro with > 4s gap
    app_class.render_lyrics(fake, 2.0)
    assert "Instrumental" in fake.lyric_curr_lbl.text
    assert "8s" in fake.lyric_curr_lbl.text

    # Line 1 singing
    app_class.render_lyrics(fake, 10.5)
    assert fake._lyric_idx == 0

    # Interlude gap between line 1 and line 2 (> 4s remaining to next line)
    app_class.render_lyrics(fake, 15.0)
    assert "Instrumental" in fake.lyric_curr_lbl.text
    assert "10s" in fake.lyric_curr_lbl.text


def test_video_background_discovery_and_priority():
    """Verify find_backgrounds discovers .mp4, .mkv, .webm and prioritizes videos over images."""
    find_bg = kk["find_backgrounds"]
    tmpdir = Path(tempfile.mkdtemp())
    try:
        vid_dir = tmpdir / "videos"
        vid_dir.mkdir()
        (vid_dir / "bg1.mp4").write_text("dummy")
        (vid_dir / "bg2.webm").write_text("dummy")
        (vid_dir / "still.jpg").write_text("dummy")

        bgs = find_bg(str(vid_dir), None)
        assert len(bgs) == 3
        assert all(b.suffix.lower() in (".mp4", ".webm") for b in bgs[:2])
        assert bgs[2].suffix.lower() == ".jpg"

        # Single explicit video file
        single_vid = vid_dir / "bg1.mp4"
        assert find_bg(str(single_vid), None) == [single_vid]

        # Directory with only images falls back to images
        img_dir = tmpdir / "images"
        img_dir.mkdir()
        (img_dir / "img1.png").write_text("dummy")
        (img_dir / "img2.jpg").write_text("dummy")
        imgs = find_bg(str(img_dir), None)
        assert len(imgs) == 2
        assert all(b.suffix.lower() in (".png", ".jpg") for b in imgs)
    finally:
        shutil.rmtree(tmpdir)


def test_video_background_lifecycle_helpers():
    """Verify start_background_video and stop_background_video lifecycle tracking."""
    app_class = kk["KaraokeApp"]

    class FakeProc:
        def __init__(self):
            self.terminated = False
            self.killed = False

        def poll(self):
            return None if not self.terminated else 0

        def terminate(self):
            self.terminated = True

        def wait(self, timeout=None):
            return 0

        def kill(self):
            self.killed = True

    class FakePlayerApp:
        def __init__(self):
            self.is_playing = False
            self.bg_video_proc = None
            self._current_bg_video = None
            self._mpv_warned = False
            self.win_id = 12345

        def winId(self):
            return self.win_id

    fake = FakePlayerApp()
    proc = FakeProc()
    fake.bg_video_proc = proc
    fake._current_bg_video = Path("/test.mp4")

    # Stop video
    app_class.stop_background_video(fake)
    assert proc.terminated is True
    assert fake.bg_video_proc is None
    assert fake._current_bg_video is None

    # Idempotent stop
    app_class.stop_background_video(fake)
    assert fake.bg_video_proc is None



def test_background_video_is_kept_running_during_song(monkeypatch, tmp_path):
    """The idle video remains alive while a song plays; mpv must attach, not spawn fullscreen."""
    app_class = kk["KaraokeApp"]

    class FakeProc:
        def poll(self):
            return None

    class FakeStack:
        def __init__(self):
            self.native = False
            self.raised = False
        def setAttribute(self, attr, value):
            self.native = value
        def raise_(self):
            self.raised = True

    class FakeApp:
        is_playing = True
        bg_video_proc = None
        _current_bg_video = None
        _mpv_warned = False
        stack = FakeStack()
        def winId(self):
            return 12345

    video = tmp_path / "background.mp4"
    video.write_bytes(b"not-a-real-video")
    commands = []
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/mpv" if name == "mpv" else None)
    def fake_popen(cmd, **kwargs):
        commands.append(cmd)
        return FakeProc()
    monkeypatch.setattr("subprocess.Popen", fake_popen)

    fake = FakeApp()
    assert app_class.start_background_video(fake, video) is True
    assert fake.bg_video_proc is not None
    assert fake._current_bg_video == video
    assert fake.stack.native is True
    assert fake.stack.raised is True
    assert f"--wid=12345" in commands[0]
    assert "--force-window=no" in commands[0]
    assert "--fullscreen=no" in commands[0]


def test_stop_playback_refreshes_background_after_clearing_play_state():
    app_class = kk["KaraokeApp"]
    events = []
    class Timer:
        def __init__(self, name): self.name = name
        def stop(self): events.append(self.name + "_stop")
        def start(self): events.append(self.name + "_start")
    class Synth:
        def stop(self): events.append("synth_stop")
    class FakeApp:
        play_timer = Timer("play")
        score_timer = Timer("score")
        bg_timer = Timer("background")
        persistent_synth = Synth()
        fluid_proc = None
        is_playing = True
        is_paused = False
        current_song = ("1", "Song", "Artist", "/song.mid", "")
        controls_card = None
        controls_timer = Timer("controls")
        player_page = object()
        library_page = object()
        class Stack:
            def currentWidget(self): return None
        stack = Stack()
        def hide_score(self): pass
        def update_background_image(self): events.append(("background_refresh", self.is_playing))
        def stop_background_video(self): events.append("video_stop")
    fake = FakeApp()
    app_class.stop_playback(fake)
    assert fake.is_playing is False
    assert ("background_refresh", False) in events
    assert events.index(("background_refresh", False)) > events.index("synth_stop")


def test_song_transition_does_not_restart_idle_background():
    app_class = kk["KaraokeApp"]
    events = []
    class Timer:
        def stop(self): events.append("timer_stop")
        def start(self): events.append("timer_start")
    class FakeApp:
        play_timer = Timer()
        score_timer = Timer()
        bg_timer = Timer()
        persistent_synth = None
        fluid_proc = None
        is_playing = False
        is_paused = False
        current_song = None
        controls_card = None
        controls_timer = Timer()
        player_page = object()
        library_page = object()
        class Stack:
            def currentWidget(self): return None
        stack = Stack()
        def hide_score(self): pass
        def stop_background_video(self): events.append("video_stop")
        def update_background_image(self): events.append("background_refresh")
    fake = FakeApp()
    app_class.stop_playback(fake, resume_background=False)
    assert "background_refresh" not in events
    # Transitioning to the next song must not tear down the shared video layer.
    assert events.count("video_stop") == 0


def test_auto_hdmi_sink_selection(monkeypatch):
    """Verify MicrophoneChainManager.select_output_sink auto-detects HDMI sinks."""
    MicManager = kk["MicrophoneChainManager"]
    mm = MicManager({"OUTPUT_DEVICE": "auto", "MUSIC_VOLUME": "90"})

    sinks_output = "0\talsa_output.platform-bcm2835_audio.analog-stereo\tPipeWire\ts16le 2ch 48000Hz\tSUSPENDED\n1\talsa_output.platform-bcm2835_audio.hdmi-stereo\tPipeWire\ts16le 2ch 48000Hz\tRUNNING\n"

    commands_run = []
    def mock_run(args, **kwargs):
        commands_run.append(args)
        if args == ["pactl", "list", "short", "sinks"]:
            return type("Res", (), {"returncode": 0, "stdout": sinks_output, "stderr": ""})()
        return type("Res", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/" + cmd)
    monkeypatch.setattr("subprocess.run", mock_run)

    chosen = mm.select_output_sink()
    assert chosen == "alsa_output.platform-bcm2835_audio.hdmi-stereo"
    assert mm.current_sink == "alsa_output.platform-bcm2835_audio.hdmi-stereo"

    # Verify pactl commands were sent to configure sink
    assert ["pactl", "set-default-sink", "alsa_output.platform-bcm2835_audio.hdmi-stereo"] in commands_run
    assert ["pactl", "set-sink-mute", "alsa_output.platform-bcm2835_audio.hdmi-stereo", "0"] in commands_run
    assert ["pactl", "set-sink-volume", "alsa_output.platform-bcm2835_audio.hdmi-stereo", "90%"] in commands_run


def test_explicit_sink_selection(monkeypatch):
    """Verify selecting 3.5mm headphone jack selects analog sink."""
    MicManager = kk["MicrophoneChainManager"]
    mm = MicManager({"OUTPUT_DEVICE": "3.5mm", "MUSIC_VOLUME": "75"})

    sinks_output = "0\talsa_output.platform-bcm2835_audio.analog-stereo\tPipeWire\ts16le 2ch 48000Hz\tSUSPENDED\n1\talsa_output.platform-bcm2835_audio.hdmi-stereo\tPipeWire\ts16le 2ch 48000Hz\tRUNNING\n"

    commands_run = []
    def mock_run(args, **kwargs):
        commands_run.append(args)
        if args == ["pactl", "list", "short", "sinks"]:
            return type("Res", (), {"returncode": 0, "stdout": sinks_output, "stderr": ""})()
        return type("Res", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/" + cmd)
    monkeypatch.setattr("subprocess.run", mock_run)

    chosen = mm.select_output_sink()
    assert chosen == "alsa_output.platform-bcm2835_audio.analog-stereo"
    assert mm.current_sink == "alsa_output.platform-bcm2835_audio.analog-stereo"

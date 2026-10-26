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

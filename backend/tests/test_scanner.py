"""Tests for scanner module: tag extraction, CUE parsing, FFmpeg commands."""

import os
import tempfile
import pytest

from app.scanner import parse_cue_file, extract_tags, _parse_track_number, _parse_year
from app.audio import build_ffmpeg_command, get_content_type


class TestParseTrackNumber:
    def test_simple_number(self):
        assert _parse_track_number("3") == 3

    def test_with_total(self):
        assert _parse_track_number("5/12") == 5

    def test_none(self):
        assert _parse_track_number(None) == 1

    def test_invalid(self):
        assert _parse_track_number("abc") == 1


class TestParseYear:
    def test_four_digit(self):
        assert _parse_year("1985") == 1985

    def test_date_string(self):
        assert _parse_year("2020-03-15") == 2020

    def test_none(self):
        assert _parse_year(None) is None


class TestParseCueFile:
    def test_parse_valid_cue(self):
        cue_content = '''FILE "album.flac" WAVE
TRACK 01 AUDIO
  TITLE "Allegro con brio"
  PERFORMER "Berlin Philharmonic"
  INDEX 01 00:00:00
TRACK 02 AUDIO
  TITLE "Andante con moto"
  INDEX 01 08:25:30
TRACK 03 AUDIO
  TITLE "Scherzo: Allegro"
  INDEX 01 17:42:50
TRACK 04 AUDIO
  TITLE "Allegro"
  INDEX 01 23:10:15
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cue', delete=False, encoding='utf-8') as f:
            f.write(cue_content)
            cue_path = f.name

        try:
            tracks = parse_cue_file(cue_path)
            assert len(tracks) == 4
            assert tracks[0]["track_number"] == 1
            assert tracks[0]["title"] == "Allegro con brio"
            assert tracks[0]["start_time_ms"] == 0
            assert tracks[1]["start_time_ms"] == (8 * 60 + 25) * 1000 + int(30 / 75 * 1000)
            assert tracks[1]["title"] == "Andante con moto"
        finally:
            os.unlink(cue_path)

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cue', delete=False, encoding='utf-8') as f:
            f.write("")
            cue_path = f.name

        try:
            tracks = parse_cue_file(cue_path)
            assert len(tracks) == 0
        finally:
            os.unlink(cue_path)


class TestBuildFfmpegCommand:
    def test_basic_command(self):
        cmd = build_ffmpeg_command("/music/test.flac", "mp3")
        assert "ffmpeg" in cmd[0] or cmd[0].endswith("ffmpeg")
        assert "-i" in cmd
        assert "/music/test.flac" in cmd
        assert "libmp3lame" in cmd
        assert "pipe:1" in cmd

    def test_with_time_range(self):
        cmd = build_ffmpeg_command("/music/test.flac", "flac", start_ms=5000, end_ms=60000)
        assert "-ss" in cmd
        idx = cmd.index("-ss")
        assert cmd[idx + 1] == "5.000"
        assert "-t" in cmd
        idx = cmd.index("-t")
        assert cmd[idx + 1] == "55.000"  # 60000 - 5000 = 55000ms

    def test_flac_output(self):
        cmd = build_ffmpeg_command("/test.flac", "flac")
        assert "flac" in cmd

    def test_wav_output(self):
        cmd = build_ffmpeg_command("/test.wav", "wav")
        assert "pcm_s16le" in cmd


class TestGetContentType:
    def test_flac(self):
        assert get_content_type("flac") == "audio/flac"

    def test_mp3(self):
        assert get_content_type("mp3") == "audio/mpeg"

    def test_default(self):
        assert get_content_type("unknown") == "audio/flac"

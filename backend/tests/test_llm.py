"""Tests for LLM prompt building, canonical string, and metadata extraction."""

import json
import pytest
from app.llm import build_extraction_prompt, build_canonical_string


class TestBuildExtractionPrompt:
    def test_builds_system_and_user_prompts(self):
        tags = {"title": "Symphony No. 5", "artist": "Beethoven"}
        system, user = build_extraction_prompt("/music/beethoven/sym5.flac", tags, "简体中文")

        assert "简体中文" in system
        assert "classical music metadata expert" in system
        assert "/music/beethoven/sym5.flac" in user
        assert "Symphony No. 5" in user

    def test_language_substitution(self):
        tags = {}
        system, _ = build_extraction_prompt("/test.mp3", tags, "English")
        assert "English" in system
        assert "简体中文" not in system

    def test_tags_included_as_json(self):
        tags = {"composer": "Mozart", "album": "Jupiter"}
        _, user = build_extraction_prompt("/test.flac", tags)
        # Tags should be JSON-formatted in the prompt
        assert "Mozart" in user
        assert "Jupiter" in user


class TestBuildCanonicalString:
    def test_full_metadata(self):
        metadata = {
            "composer": "路德维希·范·贝多芬",
            "work_title": "第五交响曲",
            "key": "C minor",
            "catalog_number": "Op. 67",
            "work_type": "交响曲",
            "era": "古典",
            "mood": "agitated",
        }
        result = build_canonical_string(metadata)
        assert "Composer: 路德维希·范·贝多芬" in result
        assert "Title: 第五交响曲 in C minor" in result
        assert "Catalog: Op. 67" in result
        assert "Type: 交响曲" in result
        assert "Era: 古典" in result
        assert "Mood: agitated" in result

    def test_partial_metadata(self):
        metadata = {"composer": "Bach", "work_title": "Mass in B minor"}
        result = build_canonical_string(metadata)
        assert "Composer: Bach" in result
        assert "Title: Mass in B minor" in result
        assert "Catalog" not in result

    def test_empty_metadata(self):
        result = build_canonical_string({})
        assert result == ""

    def test_key_appended_to_title(self):
        metadata = {"work_title": "Sonata", "key": "A major"}
        result = build_canonical_string(metadata)
        assert "Title: Sonata in A major" in result


class TestMetadataExtraction:
    """Tests for metadata validation patterns."""

    def test_valid_mood_values(self):
        valid_moods = ["joyful", "melancholic", "agitated", "calm", "mysterious", "solemn", "playful"]
        for mood in valid_moods:
            metadata = {"composer": "Test", "work_title": "Test", "mood": mood}
            canonical = build_canonical_string(metadata)
            assert f"Mood: {mood}" in canonical

    def test_valid_era_values(self):
        valid_eras = ["文艺复兴", "巴洛克", "古典", "浪漫", "民族主义", "印象主义", "现代", "后现代", "当代"]
        for era in valid_eras:
            metadata = {"composer": "Test", "work_title": "Test", "era": era}
            canonical = build_canonical_string(metadata)
            assert f"Era: {era}" in canonical

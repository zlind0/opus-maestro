"""Tests for LLM prompt building, canonical string, and metadata extraction."""

import json
import httpx
import pytest
from app import llm
from app.llm import build_extraction_prompt, build_canonical_string, build_chat_completion_payload


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


class TestBuildChatCompletionPayload:
    def test_think_disabled_by_default(self):
        original = llm.settings.llm_enable_think
        llm.settings.llm_enable_think = False
        try:
            payload = build_chat_completion_payload("system", "user")
        finally:
            llm.settings.llm_enable_think = original

        assert payload["model"] == llm.settings.openai_model
        # assert payload["response_format"] == {"type": "json_object"}
        assert "think" not in payload

    def test_think_enabled_adds_flag(self):
        original = llm.settings.llm_enable_think
        llm.settings.llm_enable_think = True
        try:
            payload = build_chat_completion_payload("system", "user", response_json=False)
        finally:
            llm.settings.llm_enable_think = original

        assert payload["think"] is True
        assert "response_format" not in payload


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
        valid_eras = ["文艺复兴", "巴洛克", "古典", "浪漫", "民族乐派", "印象主义", "现代", "后现代", "当代"]
        for era in valid_eras:
            metadata = {"composer": "Test", "work_title": "Test", "era": era}
            canonical = build_canonical_string(metadata)
            assert f"Era: {era}" in canonical


@pytest.mark.asyncio
async def test_get_embedding_returns_none_when_disabled(monkeypatch):
    original = llm.settings.enable_embeddings
    llm.settings.enable_embeddings = False

    async def fail_post(*args, **kwargs):
        raise AssertionError("embedding request should not be sent when disabled")

    monkeypatch.setattr(httpx.AsyncClient, "post", fail_post)
    try:
        result = await llm.get_embedding("test")
    finally:
        llm.settings.enable_embeddings = original

    assert result is None

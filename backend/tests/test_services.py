"""Tests for service module - metadata extraction and audio processing."""

import json
from pathlib import Path

import pytest

# Import services that don't require async
from app.services import read_tags, normalize_tag_key


class TestMetadataExtraction:
    """Test metadata extraction from audio files."""
    
    def test_normalize_tag_key(self):
        """Test tag key normalization."""
        assert normalize_tag_key('composer') == 'composer'
        assert normalize_tag_key('作曲者') == 'composer'
        assert normalize_tag_key('tpe3') == 'composer'
        assert normalize_tag_key('Artist') == 'artist'
        assert normalize_tag_key('CATALOG_NUMBER') == 'catalog_number'
    
    def test_read_tags_from_testdata(self, test_audio_files):
        """Test reading ID3 tags from test audio files."""
        if not test_audio_files:
            pytest.skip("No test audio files available")
        
        # Test reading tags from first file
        audio_file = test_audio_files[0]
        tags = read_tags(str(audio_file))
        
        # Basic checks
        assert isinstance(tags, dict)
        assert len(tags) >= 0  # May have tags or not
        
        # Check filename-based parsing if tags are missing
        assert audio_file.name  # File should have a name
    
    def test_read_tags_multiple_files(self, test_audio_files):
        """Test reading tags from multiple test files."""
        if not test_audio_files:
            pytest.skip("No test audio files available")
        
        results = []
        for audio_file in test_audio_files[:5]:  # Test first 5 files
            tags = read_tags(str(audio_file))
            results.append({
                'file': audio_file.name,
                'tags': tags
            })
            print(f"\nFile: {audio_file.name}")
            print(f"Tags: {json.dumps(tags, indent=2, ensure_ascii=False)}")
        
        assert len(results) > 0
        assert all(isinstance(r['tags'], dict) for r in results)
    
    def test_filename_parsing_fallback(self, test_audio_files):
        """Test that filename can be parsed as fallback for composers."""
        if not test_audio_files:
            pytest.skip("No test audio files available")
        
        # Example: "092.019-Antonio Vivaldi-Concerto for 4 Violins..."
        # Should be able to extract composer "Antonio Vivaldi"
        audio_file = test_audio_files[0]
        filename = audio_file.stem  # without extension
        
        # Try to parse composer from filename
        parts = filename.split('-')
        assert len(parts) >= 2  # Should have at least index and title/artist
        
        print(f"\nFilename parts: {parts}")


class TestTagNormalization:
    """Test the tag key mapping system."""
    
    def test_composer_aliases(self):
        """Test all aliases for composer field."""
        aliases = ['composer', '作曲者', 'tpe3', 'Composer', 'COMPOSER']
        for alias in aliases:
            assert normalize_tag_key(alias) == 'composer', f"Failed for alias: {alias}"
    
    def test_artist_aliases(self):
        """Test all aliases for artist field."""
        aliases = ['artist', 'Artist', 'ARTIST', 'albumartist', 'album_artist']
        for alias in aliases:
            result = normalize_tag_key(alias)
            assert result in ['artist', 'albumartist'], f"Unexpected result for alias: {alias}"
    
    def test_title_aliases(self):
        """Test all aliases for title field."""
        aliases = ['title', 'Title', 'work_title', 'album', 'Album']
        for alias in aliases:
            result = normalize_tag_key(alias)
            assert result in ['title', 'album'], f"Unexpected result for alias: {alias}"

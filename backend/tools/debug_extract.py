#!/usr/bin/env python3
"""
LLM Metadata Extraction Debug Tool

Usage:
    python -m tools.debug_extract /path/to/file.m4a [--output prompt.txt] [--language 简体中文]

Output includes:
    - Raw tags extracted from the file
    - Complete prompt sent to LLM
    - LLM response JSON
    - Standardized canonical_string
"""

import argparse
import asyncio
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.scanner import extract_tags
from app.llm import build_extraction_prompt, call_llm, build_canonical_string


async def debug_extract(file_path: str, output_file: str | None = None, language: str = "简体中文", dry_run: bool = False):
    """Run metadata extraction on a single file with debug output."""
    
    separator = "=" * 60
    lines = []

    def log(text: str = ""):
        lines.append(text)
        print(text)

    log(f"{separator}")
    log(f"🎵 Classical Music Metadata Extraction Debug")
    log(f"{separator}")
    log()

    # 1. Extract raw tags
    log(f"📁 File: {file_path}")
    log()
    
    if not os.path.exists(file_path):
        log(f"❌ Error: File not found: {file_path}")
        return

    tags = extract_tags(file_path)
    log(f"📋 Raw Tags:")
    log(json.dumps(tags, ensure_ascii=False, indent=2))
    log()

    # 2. Build prompt
    system_prompt, user_prompt = build_extraction_prompt(file_path, tags, language)
    log(f"{separator}")
    log(f"🤖 System Prompt:")
    log(system_prompt)
    log()
    log(f"📝 User Prompt:")
    log(user_prompt)
    log()

    if dry_run:
        log(f"{separator}")
        log("🔒 Dry run mode — LLM call skipped")
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            log(f"\n💾 Output saved to: {output_file}")
        return

    # 3. Call LLM
    log(f"{separator}")
    log(f"🔄 Calling LLM...")
    result = await call_llm(system_prompt, user_prompt)

    if result is None:
        log("❌ LLM call failed (check OPENAI_API_KEY and OPENAI_API_BASE)")
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        return

    log(f"✅ LLM Response:")
    try:
        parsed = json.loads(result)
        log(json.dumps(parsed, ensure_ascii=False, indent=2))
    except json.JSONDecodeError:
        log(f"⚠️  Raw (non-JSON) response:")
        log(result)
        parsed = {}

    # 4. Build canonical string
    log()
    log(f"{separator}")
    canonical = build_canonical_string(parsed)
    log(f"🔗 Canonical String:")
    log(canonical)
    log()

    # Save output
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        log(f"💾 Output saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Debug LLM metadata extraction for a single audio file")
    parser.add_argument("file_path", help="Path to the audio file")
    parser.add_argument("--output", "-o", help="Save debug output to file")
    parser.add_argument("--language", "-l", default="简体中文", help="Target language (default: 简体中文)")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Only show prompt, don't call LLM")
    args = parser.parse_args()

    asyncio.run(debug_extract(args.file_path, args.output, args.language, args.dry_run))


if __name__ == "__main__":
    main()

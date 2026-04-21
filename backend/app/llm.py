"""LLM integration module for metadata extraction and embeddings."""

import json
import logging
from typing import Optional

import httpx
import shlex

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

METADATA_EXTRACTION_SYSTEM_PROMPT = """You are a classical music metadata expert. Given an audio file's existing tags and file path information, extract structured metadata about the musical work.

You MUST respond with valid JSON only, no other text. Use the following schema:

{
  "composer": "作曲家全名(使用{language})",
  "work_title": "作品标题(使用{language})",
  "key": "调号 (e.g. G minor, D major)",
  "catalog_number": "目录编号 (e.g. K. 550, Op. 67, BWV 232)",
  "work_type": "作品类型(使用{language}, e.g. 交响曲, 协奏曲, 奏鸣曲, 室内乐, 歌剧, 合唱, 独奏曲)",
  "era": "创作年代(使用{language}, 文艺复兴/巴洛克/古典/浪漫/民族主义/印象主义/现代/后现代/当代)",
  "movement_number": 1,
  "movement_title": "乐章标题",
  "mood": "情绪 (joyful/melancholic/agitated/calm/mysterious/solemn/playful)",
  "conductor": "指挥(if available)",
  "ensemble": "乐团/演奏者(if available)",
  "soloists": "独奏家(if available)",
  "year": 2000,
  "label": "唱片厂牌(if available)",
  "description": "乐章简短描述(使用{language})",
  "work_summary": "作品简介(使用{language})"
}

Rules:
- Fill in as many fields as possible based on available information
- Use null for fields that cannot be determined
- For movement_number, if unclear, use 1
- Normalize composer names to their most recognized form in {language}
- Catalog numbers should follow standard conventions (K., Op., BWV, etc.)
- The mood field MUST be one of: joyful, melancholic, agitated, calm, mysterious, solemn, playful
- era MUST be one of: 文艺复兴, 巴洛克, 古典, 浪漫, 民族主义, 印象主义, 现代, 后现代, 当代
- work_type MUST be in {language}
"""

METADATA_EXTRACTION_USER_TEMPLATE = """Extract metadata from this audio file:

File path: {file_path}

Existing tags:
{tags_json}

Please extract structured metadata as JSON."""


def build_extraction_prompt(file_path: str, tags: dict, language: str = "简体中文") -> tuple[str, str]:
    """Build the system and user prompts for metadata extraction.
    
    Returns (system_prompt, user_prompt) tuple.
    """
    system = METADATA_EXTRACTION_SYSTEM_PROMPT.replace("{language}", language)
    user = METADATA_EXTRACTION_USER_TEMPLATE.format(
        file_path=file_path,
        tags_json=json.dumps(tags, ensure_ascii=False, indent=2),
    )
    return system, user


def build_chat_completion_payload(
    system_prompt: str, user_prompt: str, response_json: bool = True
) -> dict:
    """Build the chat completion payload for an OpenAI-compatible API."""
    payload = {
        "model": settings.openai_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
    }
    # if response_json:
    #     payload["response_format"] = {"type": "json_object"}
    if settings.llm_enable_think:
        payload["think"] = True
    return payload


def _log_curl_request(method: str, url: str, headers: dict, payload: object) -> None:
    """Log an HTTP request as a curl command for easy copy/paste debugging."""
    try:
        payload_str = json.dumps(payload, ensure_ascii=False)
    except Exception:
        payload_str = str(payload)

    quoted_url = shlex.quote(url)
    quoted_payload = shlex.quote(payload_str)

    header_parts = []
    for k, v in headers.items():
        header_parts.append(f"-H {shlex.quote(f'{k}: {v}')}")

    headers_str = "  ".join(header_parts) if header_parts else ""

    curl_cmd = f"curl -X {method} {quoted_url}  {headers_str}  -d {quoted_payload}"

    logger.info("LLM request as curl:\n%s", curl_cmd)


async def call_llm(system_prompt: str, user_prompt: str, response_json: bool = True) -> Optional[str]:
    """Call OpenAI-compatible API."""
    try:
        url = f"{settings.openai_api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = build_chat_completion_payload(system_prompt, user_prompt, response_json=response_json)
        _log_curl_request("POST", url, headers, payload)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return None


async def extract_metadata(file_path: str, tags: dict, language: str = "简体中文") -> Optional[dict]:
    """Extract structured metadata from audio file tags using LLM."""
    system, user = build_extraction_prompt(file_path, tags, language)
    result = await call_llm(system, user)
    if result is None:
        return None
    try:
        if result.startswith("```json") and result.endswith("```"):
            result = result[7:-3].strip()
        return json.loads(result)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse LLM response as JSON: {result}")
        return None


async def get_embedding(text: str) -> Optional[list[float]]:
    """Get embedding vector for text using OpenAI-compatible API."""
    if not settings.enable_embeddings:
        logger.info("Embeddings are disabled; skipping embedding request")
        return None

    try:
        url = f"{settings.openai_api_base}/embeddings"
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": settings.openai_embedding_model, "input": text}
        _log_curl_request("POST", url, headers, payload)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
    except Exception as e:
        logger.error(f"Embedding call failed: {e}")
        return None


def build_canonical_string(metadata: dict) -> str:
    """Build canonical string from extracted metadata for embedding."""
    parts = []
    if metadata.get("composer"):
        parts.append(f"Composer: {metadata['composer']}")
    if metadata.get("work_title"):
        title = metadata["work_title"]
        if metadata.get("key"):
            title += f" in {metadata['key']}"
        parts.append(f"Title: {title}")
    if metadata.get("catalog_number"):
        parts.append(f"Catalog: {metadata['catalog_number']}")
    if metadata.get("work_type"):
        parts.append(f"Type: {metadata['work_type']}")
    if metadata.get("era"):
        parts.append(f"Era: {metadata['era']}")
    if metadata.get("mood"):
        parts.append(f"Mood: {metadata['mood']}")
    return " | ".join(parts)


RECOMMENDATION_SYSTEM_PROMPT = """You are a classical music recommendation expert. Given information about a piece of music the user just listened to, suggest similar pieces they might enjoy.

Respond with valid JSON only:
{
  "recommendations": [
    {
      "composer": "作曲家",
      "work_title": "作品标题",
      "reason": "推荐理由"
    }
  ]
}

Consider: same era, similar mood, same composer's other works, same form/genre, complementary keys."""


async def get_recommendations(work_info: str, limit: int = 5) -> Optional[list[dict]]:
    """Get music recommendations based on current work."""
    user_prompt = f"Based on this piece, recommend {limit} similar works:\n\n{work_info}"
    result = await call_llm(RECOMMENDATION_SYSTEM_PROMPT, user_prompt)
    if result is None:
        return None
    try:
        data = json.loads(result)
        return data.get("recommendations", [])
    except json.JSONDecodeError:
        return None

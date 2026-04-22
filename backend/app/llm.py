"""LLM integration module for metadata extraction and embeddings."""

import json
import logging
import re
import asyncio
from typing import Optional

import httpx
import shlex

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Validation rules
ALLOWED_ERAS = ['文艺复兴', '巴洛克', '古典', '浪漫', '民族乐派', '印象主义', '现代', '后现代', '当代']


def _contains_chinese(s: str) -> bool:
    if not s or not isinstance(s, str):
        return False
    return bool(re.search(r"[\u4e00-\u9fff]", s))


def _validate_metadata_item(metadata: dict) -> bool:
    """Return True if metadata satisfies basic validation rules.

    Rules enforced:
    - If `era` is provided and not null, it must be one of `ALLOWED_ERAS`.
    - `work_title` or `movement_title` should contain at least one Chinese character when provided.
    """
    if not isinstance(metadata, dict):
        return False

    era = metadata.get("era")
    if era is not None:
        try:
            era_str = str(era).strip()
        except Exception:
            return False
        if era_str and era_str not in ALLOWED_ERAS:
            logger.debug(f"Invalid era: {era_str}")
            return False

    # Prefer movement_title to be Chinese, fall back to work_title when movement missing
    mv_title = metadata.get("movement_title")
    wk_title = metadata.get("work_title")
    # If either present, at least one should contain Chinese characters
    if mv_title:
        if not _contains_chinese(mv_title):
            logger.debug(f"Movement title lacks Chinese characters: {mv_title}")
            return False
    elif wk_title:
        if not _contains_chinese(wk_title):
            logger.debug(f"Work title lacks Chinese characters: {wk_title}")
            return False

    return True

METADATA_EXTRACTION_SYSTEM_PROMPT = """You are a classical music metadata expert. Given an audio file's existing tags and file path information, extract structured metadata about the musical work.

You MUST respond with valid JSON only, no other text. Use the following schema:

{
  "composer": "作曲家为人熟知的简名(使用{language})，示例：巴赫，莫扎特，贝多芬，肖邦，德彪西，约翰·威廉姆斯，勃拉姆斯，柴可夫斯基，李斯特，拉赫玛尼诺夫，斯特拉文斯基，马勒，布鲁克纳，门德尔松，舒曼，维瓦尔第，亨德尔，普契尼，威尔第，理查德·施特劳斯，斯特劳斯，格里格，拉威尔，福雷，布拉姆斯，舒伯特，门德尔松，德沃夏克，西贝柳斯，埃尔加，巴托克，肖斯塔科维奇，普罗科菲耶夫"),",
  "work_title": "作品标题(使用{language}，构成为[题材+编号+标题]，不含作品编号（Op BWV K. 等等都不要出现）。示例：交响曲第5号《命运》，钢琴协奏曲第1号，G大调小提琴奏鸣曲，D大调前奏曲，A大调夜曲，C小调弦乐四重奏，钢琴奏鸣曲第14号《月光》",
  "key": "调号 (e.g. G小调, D大调)",
  "catalog_number": "作品编号 (e.g. K. 550, Op. 67, BWV 232)",
  "work_type": "作品类型(使用{language}, e.g. 交响曲, 协奏曲, 奏鸣曲, 室内乐, 歌剧, 合唱, 独奏曲)",
  "era": "创作年代(使用{language}, ['文艺复兴', '巴洛克', '古典', '浪漫', '民族乐派', '印象主义', '现代', '后现代', '当代']中选择一个最合适的，不要脱离这个范围)",
  "movement_number": "乐章编号 (如果不清楚，使用null)",
  "movement_title": "乐章标题，尽量要使用中文",
  "mood": "情绪 (喜悦的/忧郁的/激动的/平静的/神秘的/庄严的/顽皮的/愤怒的/惊恐的)",
  "conductor": "指挥(if available)",
  "ensemble": "乐团/演奏者(if available)",
  "soloists": "独奏家(if available)",
  "year": "唱片录制年份(if available)",
  "label": "唱片厂牌(if available)",
  "description": "乐章简短描述(使用{language})",
  "work_summary": "作品简介(使用{language})"
}

- 字段使用 {language}
"""

METADATA_EXTRACTION_USER_TEMPLATE = """从此音频文件中提取元数据：

路径: {file_path}

现有标签:
{tags_json}

请以JSON格式提取结构化元数据。如果某个字段不清楚或不存在，请使用null。不要添加任何额外的文本或解释，只返回JSON，对于不确定和不知道的东西，你最好保持沉默。"""

METADATA_EXTRACTION_BATCH_SYSTEM_PROMPT = """You are a classical music metadata expert. Given a list of audio files that are different movements of the same musical work, extract structured metadata for each movement.

You MUST respond with a JSON ARRAY only, no other text. The array must contain one object per provided file, in the same order as the input. Use the following schema for each object:

{
  "composer": "作曲家为人熟知的简名(使用{language})，示例：巴赫，莫扎特，贝多芬，肖邦，德彪西，约翰·威廉姆斯，勃拉姆斯，柴可夫斯基，李斯特，拉赫玛尼诺夫，斯特拉文斯基，马勒，布鲁克纳，门德尔松，舒曼，维瓦尔第，亨德尔，普契尼，威尔第，理查德·施特劳斯，斯特劳斯，格里格，拉威尔，福雷，布拉姆斯，舒伯特，门德尔松，德沃夏克，西贝柳斯，埃尔加，巴托克，肖斯塔科维奇，普罗科菲耶夫"),",
  "work_title": "作品标题(使用{language}，构成为[题材+编号+标题]，不含作品编号（Op BWV K. 等等都不要出现）。示例：交响曲第5号《命运》，钢琴协奏曲第1号，G大调小提琴奏鸣曲，D大调前奏曲，A大调夜曲，C小调弦乐四重奏，钢琴奏鸣曲第14号《月光》",
  "key": "调号 (e.g. G小调, D大调)",
  "catalog_number": "作品编号 (e.g. K. 550, Op. 67, BWV 232)",
  "work_type": "作品类型(使用{language}, e.g. 交响曲, 协奏曲, 奏鸣曲, 室内乐, 歌剧, 合唱, 独奏曲)",
  "era": "创作年代(使用{language}, ['文艺复兴', '巴洛克', '古典', '浪漫', '民族乐派', '印象主义', '现代', '后现代', '当代']中选择一个最合适的，不要脱离这个范围)",
  "movement_number": "乐章编号 (如果不清楚，使用null)",
  "movement_title": "乐章标题，尽量要使用中文",
  "mood": "情绪 (喜悦的/忧郁的/激动的/平静的/神秘的/庄严的/顽皮的/愤怒的/惊恐的)",
  "conductor": "指挥(if available)",
  "ensemble": "乐团/演奏者(if available)",
  "soloists": "独奏家(if available)",
  "year": "唱片录制年份(if available)",
  "label": "唱片厂牌(if available)",
  "description": "乐章简短描述(使用{language})",
  "work_summary": "作品简介(使用{language})"
}

IMPORTANT: All objects in the array MUST have identical values for these work-level fields: composer, work_title, key, catalog_number, work_type, era, conductor, ensemble, soloists, year, label, work_summary.
Each object should have its own unique values for movement-level fields: movement_number, movement_title, mood, description.
- 字段使用 {language}
"""

METADATA_EXTRACTION_BATCH_USER_TEMPLATE = """以下音频文件属于同一作品的不同乐章，请提取元数据并以JSON数组格式返回（共{n}个对象，与输入文件顺序对应）：

{files_section}

所有对象中的作品级字段（composer, work_title, key, catalog_number, work_type, era, conductor, ensemble, soloists, year, label, work_summary）必须完全一致。乐章级字段（movement_number, movement_title, mood, description）各自独立。
只返回JSON数组，不要添加任何额外的文本或解释。"""


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

        async with httpx.AsyncClient(timeout=300.0) as client:
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
    max_retries = getattr(settings, "llm_max_retries", 3) or 3
    for attempt in range(1, max_retries + 1):
        result = await call_llm(system, user)
        if result is None:
            logger.debug(f"LLM returned no result (attempt {attempt}/{max_retries})")
            if attempt < max_retries:
                await asyncio.sleep(attempt)
                continue
            return None
        try:
            s = result.strip()
            if s.startswith("```json") and s.endswith("```"):
                s = s[7:-3].strip()
            parsed = json.loads(s)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM response as JSON (attempt {attempt}): {result}")
            if attempt < max_retries:
                await asyncio.sleep(attempt)
                continue
            return None

        # Validate parsed metadata; if invalid, retry up to max_retries
        if _validate_metadata_item(parsed):
            return parsed
        else:
            logger.info(f"LLM metadata validation failed (attempt {attempt}/{max_retries}): {file_path}")
            if attempt < max_retries:
                await asyncio.sleep(attempt)
                continue
            # Give up and return None so caller falls back to tags
            return None


def build_extraction_prompt_batch(
    file_paths: list[str], tags_list: list[dict], language: str = "简体中文"
) -> tuple[str, str]:
    """Build system and user prompts for batch (multi-movement) metadata extraction."""
    system = METADATA_EXTRACTION_BATCH_SYSTEM_PROMPT.replace("{language}", language)
    files_parts = []
    for i, (fp, tags) in enumerate(zip(file_paths, tags_list)):
        files_parts.append(
            f"文件 {i + 1}:\n路径: {fp}\n现有标签:\n{json.dumps(tags, ensure_ascii=False, indent=2)}"
        )
    files_section = "\n\n".join(files_parts)
    user = METADATA_EXTRACTION_BATCH_USER_TEMPLATE.format(
        n=len(file_paths), files_section=files_section
    )
    return system, user


async def extract_metadata_batch(
    file_paths: list[str], tags_list: list[dict], language: str = "简体中文"
) -> list[Optional[dict]]:
    """Extract metadata for multiple movements of the same work in a single LLM call.

    Returns a list of dicts (one per file) in the same order as the inputs.
    Falls back to None entries if the LLM call or parsing fails.
    """
    n = len(file_paths)
    if n == 1:
        result = await extract_metadata(file_paths[0], tags_list[0], language)
        return [result]

    system, user = build_extraction_prompt_batch(file_paths, tags_list, language)
    max_retries = getattr(settings, "llm_max_retries", 3) or 3
    for attempt in range(1, max_retries + 1):
        result_str = await call_llm(system, user)
        if result_str is None:
            logger.debug(f"Batch LLM returned no result (attempt {attempt}/{max_retries})")
            if attempt < max_retries:
                await asyncio.sleep(attempt)
                continue
            return [None] * n

        try:
            s = result_str.strip()
            if s.startswith("```json"):
                s = s[7:]
            elif s.startswith("```"):
                s = s[3:]
            if s.endswith("```"):
                s = s[:-3]
            s = s.strip()
            parsed = json.loads(s)
            if not isinstance(parsed, list):
                logger.error(f"Batch LLM response is not a JSON array (attempt {attempt}): {result_str[:200]}")
                if attempt < max_retries:
                    await asyncio.sleep(attempt)
                    continue
                return [None] * n

            # Validate each parsed item. If any item fails validation, retry.
            valid_flags = []
            for item in parsed:
                if isinstance(item, dict) and _validate_metadata_item(item):
                    valid_flags.append(True)
                else:
                    valid_flags.append(False)

            if all(valid_flags) and len(parsed) >= n:
                # Normalize to exactly n items
                results: list[Optional[dict]] = []
                for i in range(n):
                    if i < len(parsed) and isinstance(parsed[i], dict):
                        results.append(parsed[i])
                    else:
                        results.append(None)
                return results
            else:
                logger.info(f"Batch metadata validation failed (attempt {attempt}/{max_retries})")
                if attempt < max_retries:
                    await asyncio.sleep(attempt)
                    continue
                # On final attempt, return parsed results but replace invalid items with None
                results = []
                for i in range(n):
                    if i < len(parsed) and isinstance(parsed[i], dict) and _validate_metadata_item(parsed[i]):
                        results.append(parsed[i])
                    else:
                        results.append(None)
                return results
        except json.JSONDecodeError:
            logger.error(f"Failed to parse batch LLM response as JSON (attempt {attempt}): {result_str[:200]}")
            if attempt < max_retries:
                await asyncio.sleep(attempt)
                continue
            return [None] * n


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

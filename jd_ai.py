"""
ROIN WORLD FZE — Gemini AI for JD text improvement
====================================================
Model  : gemini-2.0-flash
Key    : gemini_key.txt (local) or GEMINI_KEY env var (Railway)
All functions are async and degrade gracefully if the key is not set.

RULE: All AI in this bot uses Google Gemini — never Claude/Anthropic.
"""

import os, re, asyncio

SYSTEM_PROMPT = (
    "You are a professional HR document editor for ROIN WORLD FZE, a catering company "
    "at El Dabaa Nuclear Power Plant, Egypt. 30,000 meals/day, 600 employees.\n\n"
    "Your job: improve the given text to be more professional, specific, and action-oriented.\n\n"
    "Rules:\n"
    "- Make sentences clearer and more concise\n"
    "- Use strong action verbs (manage, coordinate, supervise, ensure, implement)\n"
    "- Add measurable KPIs where possible (e.g. 'within 2 hours', '100% compliance')\n"
    "- Keep the same meaning — do not invent new responsibilities\n"
    "- Keep the same language (if Arabic input, output Arabic. If Russian, output Russian. If English, output English)\n"
    "- Output ONLY the improved text. No explanations, no preamble, no markdown."
)

RETRY_SUFFIX = "\n\nRewrite and significantly improve this text. Do NOT return the same text."


def _key() -> str:
    from config import GEMINI_KEY
    return GEMINI_KEY


MODELS = ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-2.5-flash"]


def _call(system: str, user: str) -> str:
    """Try each model in order until one succeeds."""
    key = _key()
    if not key:
        raise RuntimeError("No Gemini API key")
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=key)
    last_err = None
    for model in MODELS:
        try:
            response = client.models.generate_content(
                model=model,
                contents=user,
                config=types.GenerateContentConfig(system_instruction=system),
            )
            return response.text.strip()
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"All Gemini models failed. Last error: {last_err}")


def _is_same(a: str, b: str) -> bool:
    """True if two strings are effectively identical (ignoring whitespace/case)."""
    return a.strip().lower() == b.strip().lower()


def _strip_nums(text: str) -> list:
    return [re.sub(r"^\d+[\.\)]\s*", "", l.strip())
            for l in text.split("\n") if l.strip()]


def ai_available() -> bool:
    return bool(_key())


# ── Core improve function with retry ──────────────────────────────────────────

def _improve_text(original: str) -> str:
    """Call Gemini. If result is identical to original, retry once with stronger instruction."""
    user_prompt = f"Improve this text professionally:\n\n{original}"
    result = _call(SYSTEM_PROMPT, user_prompt)

    if _is_same(result, original):
        # Retry with stronger instruction
        result = _call(SYSTEM_PROMPT, user_prompt + RETRY_SUFFIX)

    # Final fallback: if still identical, return original
    return result if not _is_same(result, original) else original


def _improve_tasks_text(tasks_text: str, n: int) -> str:
    """Improve a numbered task list. Retries if identical."""
    user_prompt = (
        f"Improve this numbered list of {n} job responsibilities professionally. "
        f"Keep exactly {n} items. Output ONLY a numbered list, one per line:\n\n{tasks_text}"
    )
    result = _call(SYSTEM_PROMPT, user_prompt)

    if _is_same(result, tasks_text):
        result = _call(SYSTEM_PROMPT, user_prompt + RETRY_SUFFIX)

    return result if not _is_same(result, tasks_text) else tasks_text


# ── Public async API ───────────────────────────────────────────────────────────

async def improve_summary(text: str, job_title: str) -> tuple[str, str | None]:
    """Returns (result, error_msg). error_msg is None on success."""
    try:
        result = await asyncio.to_thread(_improve_text, text)
        return result, None
    except Exception as e:
        return text, str(e)


async def improve_tasks(tasks: list, job_title: str) -> tuple[list, str | None]:
    """Returns (result_list, error_msg). error_msg is None on success."""
    n = len(tasks)
    joined = "\n".join(f"{i+1}. {t}" for i, t in enumerate(tasks))
    try:
        raw = await asyncio.to_thread(_improve_tasks_text, joined, n)
        improved = _strip_nums(raw)
        if len(improved) >= n:
            return improved[:n], None
        return (improved + tasks[len(improved):])[:n], None
    except Exception as e:
        return tasks, str(e)


async def improve_qualifications(text: str, job_title: str) -> tuple[str, str | None]:
    """Returns (result, error_msg). error_msg is None on success."""
    try:
        result = await asyncio.to_thread(_improve_text, text)
        return result, None
    except Exception as e:
        return text, str(e)


async def improve_section(section: str, content, job_title: str) -> tuple:
    """Generic dispatcher used by the HR editing flow. Returns (result, error_msg)."""
    if section == "summary":
        return await improve_summary(str(content), job_title)
    elif section == "tasks":
        if isinstance(content, list):
            return await improve_tasks(content, job_title)
        return content, None
    elif section == "qualifications":
        return await improve_qualifications(str(content), job_title)
    return content, None  # title / working_conditions: no AI improvement

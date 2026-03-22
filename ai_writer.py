"""
ROIN WORLD FZE — Universal AI Writing Assistant
================================================
Uses Google Gemini (same pattern as jd_ai.py).
NEVER uses Claude/Anthropic.

Functions:
  async improve_text(text, context, lang) -> (result, error)
  async improve_with_instruction(text, instruction, lang) -> (result, error)
  async translate_text(text, from_lang, to_lang) -> (result, error)
"""

import os, asyncio

MODELS = ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-2.5-flash"]


def _key() -> str:
    from config import GEMINI_KEY
    return GEMINI_KEY


def _call(system: str, user: str) -> str:
    key = _key()
    if not key:
        raise RuntimeError("No Gemini API key configured.")
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
    raise RuntimeError(f"All Gemini models failed. Last: {last_err}")


def _is_same(a: str, b: str) -> bool:
    return a.strip().lower() == b.strip().lower()


# ── System prompts per context ─────────────────────────────────────────────────

_SYSTEM_MEMO = (
    "You are a professional workplace communication writer for ROIN WORLD FZE, "
    "a catering company at El Dabaa Nuclear Power Plant, Egypt.\n"
    "Improve this internal memo to be clear, professional, and persuasive.\n"
    "Maintain the same meaning and key facts. Use formal business language.\n"
    "Output ONLY the improved text. No explanations, no preamble, no markdown."
)

_SYSTEM_ANNOUNCEMENT = (
    "You are writing an official company announcement for ROIN WORLD FZE.\n"
    "Make it clear, concise, and professional. Appropriate for all employees.\n"
    "Output ONLY the improved text. No explanations, no preamble, no markdown."
)

_SYSTEM_GENERAL = (
    "You are a professional business writer for ROIN WORLD FZE.\n"
    "Improve the given text to be clear, professional, and effective.\n"
    "Output ONLY the improved text. No explanations, no preamble, no markdown."
)

_CONTEXTS = {
    "memo": _SYSTEM_MEMO,
    "announcement": _SYSTEM_ANNOUNCEMENT,
    "general": _SYSTEM_GENERAL,
}


def _improve_sync(text: str, system: str, lang: str) -> str:
    lang_note = f"\nLanguage: Write the output in {lang}." if lang and lang != "EN" else ""
    user_prompt = f"Improve this text professionally:{lang_note}\n\n{text}"
    result = _call(system, user_prompt)
    if _is_same(result, text):
        result = _call(system, user_prompt + "\n\nRewrite significantly. Do NOT return the same text.")
    return result if not _is_same(result, text) else text


def _instruct_sync(text: str, instruction: str, lang: str) -> str:
    lang_note = f" Write the output in {lang}." if lang and lang != "EN" else ""
    system = (
        "You are improving text for ROIN WORLD FZE internal documents.\n"
        "Apply the specific change requested by the user.\n"
        "Output ONLY the modified text. Do not add explanations."
    )
    user_prompt = (
        f"Apply this specific change:{lang_note} {instruction}\n\n"
        f"Original text:\n{text}"
    )
    return _call(system, user_prompt)


def _translate_sync(text: str, from_lang: str, to_lang: str) -> str:
    system = (
        "You are a professional translator for ROIN WORLD FZE business documents.\n"
        "Translate accurately and maintain formal business tone.\n"
        "Output ONLY the translated text."
    )
    user_prompt = f"Translate from {from_lang} to {to_lang}:\n\n{text}"
    return _call(system, user_prompt)


# ── Public async API ───────────────────────────────────────────────────────────

async def improve_text(text: str, context: str = "memo", lang: str = "EN") -> tuple:
    """
    Returns (improved_text, error_msg). error_msg is None on success.
    context: "memo", "announcement", "general"
    lang: "EN", "RU", "AR", etc.
    """
    system = _CONTEXTS.get(context, _SYSTEM_GENERAL)
    try:
        result = await asyncio.to_thread(_improve_sync, text, system, lang)
        return result, None
    except Exception as e:
        return text, str(e)


async def improve_with_instruction(text: str, instruction: str, lang: str = "EN") -> tuple:
    """
    Returns (modified_text, error_msg). error_msg is None on success.
    Applies user's specific instruction to the text.
    """
    try:
        result = await asyncio.to_thread(_instruct_sync, text, instruction, lang)
        return result, None
    except Exception as e:
        return text, str(e)


async def translate_text(text: str, from_lang: str = "RU", to_lang: str = "EN") -> tuple:
    """
    Returns (translated_text, error_msg). error_msg is None on success.
    """
    try:
        result = await asyncio.to_thread(_translate_sync, text, from_lang, to_lang)
        return result, None
    except Exception as e:
        return text, str(e)


def ai_available() -> bool:
    return bool(_key())


# ── Recruitment AI ─────────────────────────────────────────────────────────────

def _social_posts_sync(title: str, dept: str, requirements: str,
                       benefits: str, phone: str, lang: str) -> dict:
    lang_note = {"AR": "Arabic", "RU": "Russian", "EN": "English"}.get(lang, "English")
    system = (
        "You are a social media copywriter for ROIN WORLD FZE, a catering company "
        "at El Dabaa Nuclear Power Plant, Egypt.\n"
        "Generate 3 distinct, engaging job post variations for social media (Facebook/WhatsApp groups).\n"
        "Each must have: catchy opening, job title, location (El Dabaa), key requirements, benefits, "
        "how to apply (phone number), company name.\n"
        "Format output EXACTLY as:\n"
        "POST_1:\n[text]\n\nPOST_2:\n[text]\n\nPOST_3:\n[text]"
    )
    user = (
        f"Language: {lang_note}\n"
        f"Job Title: {title}\nDepartment: {dept}\n"
        f"Requirements: {requirements}\nBenefits: {benefits}\nPhone: {phone}"
    )
    raw = _call(system, user)
    posts = {"post_1": "", "post_2": "", "post_3": ""}
    for key, marker in [("post_1", "POST_1:"), ("post_2", "POST_2:"), ("post_3", "POST_3:")]:
        if marker in raw:
            after = raw.split(marker, 1)[1]
            next_markers = [m for m in ["POST_1:", "POST_2:", "POST_3:"] if m != marker and m in after]
            if next_markers:
                after = after.split(next_markers[0], 1)[0]
            posts[key] = after.strip()
    if not any(posts.values()):
        posts["post_1"] = raw.strip()
    return posts


def _screen_candidate_sync(candidate: str, requirements: str) -> str:
    system = (
        "You are an expert HR screening assistant for ROIN WORLD FZE.\n"
        "Analyze the candidate profile against job requirements.\n"
        "Output format (strictly follow this):\n"
        "MATCH_SCORE: X%\n"
        "STRENGTHS:\n- [bullet points]\n"
        "GAPS:\n- [bullet points]\n"
        "RECOMMENDATION: [Recommend / Maybe / Do Not Recommend]\n"
        "SUMMARY: [2-3 sentences]"
    )
    user = f"Job Requirements:\n{requirements}\n\nCandidate Profile:\n{candidate}"
    return _call(system, user)


def _interview_questions_sync(job_title: str, requirements: str) -> str:
    system = (
        "You are an HR expert generating interview questions for ROIN WORLD FZE.\n"
        "Generate exactly 10 interview questions for the given role.\n"
        "Mix: technical (4), behavioral (3), situational (2), culture fit (1).\n"
        "Format: numbered list 1-10. No preamble, no explanations after questions."
    )
    user = f"Job Title: {job_title}\nRequirements: {requirements}"
    return _call(system, user)


async def generate_social_posts(title: str, dept: str, requirements: str,
                                 benefits: str, phone: str, lang: str = "EN") -> tuple:
    """Returns (dict of post_1/post_2/post_3, error_msg)."""
    try:
        result = await asyncio.to_thread(_social_posts_sync, title, dept, requirements, benefits, phone, lang)
        return result, None
    except Exception as e:
        return {"post_1": "", "post_2": "", "post_3": ""}, str(e)


async def screen_candidate(candidate: str, requirements: str) -> tuple:
    """Returns (screening_text, error_msg)."""
    try:
        result = await asyncio.to_thread(_screen_candidate_sync, candidate, requirements)
        return result, None
    except Exception as e:
        return "", str(e)


async def generate_interview_questions(job_title: str, requirements: str) -> tuple:
    """Returns (questions_text, error_msg)."""
    try:
        result = await asyncio.to_thread(_interview_questions_sync, job_title, requirements)
        return result, None
    except Exception as e:
        return "", str(e)


async def improve_job_description(text: str, lang: str = "EN") -> tuple:
    """Returns (improved_text, error_msg). Improves a job posting description."""
    system = (
        "You are a professional HR copywriter for ROIN WORLD FZE.\n"
        "Improve this job posting to be clear, attractive, and professional.\n"
        "Keep all factual information. Output ONLY the improved text."
    )
    try:
        result = await asyncio.to_thread(_improve_sync, text, system, lang)
        return result, None
    except Exception as e:
        return text, str(e)

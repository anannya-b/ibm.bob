"""
translator.py – Multilingual Translation Support
================================================
Provides language detection and translation for the FinLit AI agent,
supporting major Indian languages via deep-translator (Google Translate).
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supported languages
# ---------------------------------------------------------------------------
SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "English",
    "hi": "Hindi",
    "bn": "Bengali",
    "ta": "Tamil",
    "te": "Telugu",
    "mr": "Marathi",
    "gu": "Gujarati",
}

# Languages that can be reliably detected by langdetect
DETECTABLE_LANGUAGES = set(SUPPORTED_LANGUAGES.keys())


def detect_language(text: str) -> str:
    """
    Detect the language of the given text using langdetect.
    Falls back to "en" if detection fails or the detected language is not
    in the supported language set.

    Args:
        text: Input text whose language needs to be detected.

    Returns:
        str: BCP-47 language code (e.g. "en", "hi", "ta").
             Returns "en" as default if detection is uncertain.
    """
    if not text or not text.strip():
        return "en"

    try:
        from langdetect import detect, DetectorFactory
        # Make detection deterministic
        DetectorFactory.seed = 42

        detected = detect(text.strip())

        # Normalize: langdetect may return "zh-cn" etc; take base code
        base_code = detected.split("-")[0].lower()

        if base_code in DETECTABLE_LANGUAGES:
            logger.debug("Detected language: %s for text: '%s…'", base_code, text[:30])
            return base_code

        logger.debug(
            "Detected '%s' is not in supported languages; defaulting to 'en'",
            detected,
        )
        return "en"

    except Exception as exc:
        logger.warning("Language detection failed: %s — defaulting to 'en'", exc)
        return "en"


def translate_to_english(text: str, src_lang: str) -> str:
    """
    Translate text from the source language to English.
    If the source language is already English, returns the text unchanged.

    Args:
        text:     The text to translate.
        src_lang: Source language code (e.g. "hi", "ta").

    Returns:
        str: Translated English text, or the original text if translation fails
             or is unnecessary.
    """
    if not text or not text.strip():
        return text

    if src_lang == "en":
        return text

    if src_lang not in SUPPORTED_LANGUAGES:
        logger.warning(
            "Unsupported source language '%s'; returning original text", src_lang
        )
        return text

    try:
        from deep_translator import GoogleTranslator

        translator = GoogleTranslator(source=src_lang, target="en")
        translated = translator.translate(text.strip())

        if not translated:
            logger.warning("Translation returned empty result; using original text")
            return text

        logger.info(
            "Translated [%s → en]: '%s…' → '%s…'",
            src_lang,
            text[:30],
            translated[:30],
        )
        return translated

    except Exception as exc:
        logger.error("Translation to English failed: %s", exc)
        return text  # Graceful degradation: return original text


def translate_from_english(text: str, tgt_lang: str) -> str:
    """
    Translate text from English to the target language.
    If the target language is English, returns the text unchanged.

    Args:
        text:     English text to translate.
        tgt_lang: Target language code (e.g. "hi", "bn").

    Returns:
        str: Translated text in the target language, or the original English
             text if translation fails or is unnecessary.
    """
    if not text or not text.strip():
        return text

    if tgt_lang == "en":
        return text

    if tgt_lang not in SUPPORTED_LANGUAGES:
        logger.warning(
            "Unsupported target language '%s'; returning English text", tgt_lang
        )
        return text

    try:
        from deep_translator import GoogleTranslator

        # Google Translate has a character limit per request (~5000 chars)
        # Split long texts into chunks if necessary
        max_chars = 4500
        if len(text) <= max_chars:
            translator = GoogleTranslator(source="en", target=tgt_lang)
            translated = translator.translate(text.strip())
        else:
            # Chunk and translate
            translated = _translate_long_text(text, tgt_lang, max_chars)

        if not translated:
            logger.warning("Translation returned empty result; using English text")
            return text

        logger.info(
            "Translated [en → %s]: '%s…' → '%s…'",
            tgt_lang,
            text[:30],
            translated[:30],
        )
        return translated

    except Exception as exc:
        logger.error("Translation from English failed: %s", exc)
        return text  # Graceful degradation: return English text


def _translate_long_text(text: str, tgt_lang: str, max_chars: int) -> str:
    """
    Translate a long text by splitting it into sentence-respecting chunks.

    Args:
        text:      The full English text.
        tgt_lang:  Target language code.
        max_chars: Maximum characters per translation request.

    Returns:
        str: Fully translated text.
    """
    from deep_translator import GoogleTranslator

    # Split on paragraph boundaries first, then sentences
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= max_chars:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para + "\n\n"

    if current_chunk:
        chunks.append(current_chunk.strip())

    translated_chunks = []
    translator = GoogleTranslator(source="en", target=tgt_lang)

    for chunk in chunks:
        try:
            result = translator.translate(chunk)
            translated_chunks.append(result or chunk)
        except Exception as exc:
            logger.warning("Chunk translation failed: %s — using original", exc)
            translated_chunks.append(chunk)

    return "\n\n".join(translated_chunks)


def get_language_name(lang_code: str) -> str:
    """
    Get the human-readable language name for a given language code.

    Args:
        lang_code: BCP-47 language code (e.g. "hi").

    Returns:
        str: Language name (e.g. "Hindi"), or the code itself if not found.
    """
    return SUPPORTED_LANGUAGES.get(lang_code, lang_code)


def is_supported_language(lang_code: str) -> bool:
    """
    Check whether a given language code is supported by the translator.

    Args:
        lang_code: BCP-47 language code to check.

    Returns:
        bool: True if the language is supported.
    """
    return lang_code in SUPPORTED_LANGUAGES

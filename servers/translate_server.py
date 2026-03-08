"""
Translation MCP Server
Uses deep_translator (Google backend, free, no API key needed).
Install: pip install deep-translator
"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Translation")

# ─── Language Map ──────────────────────────────────────────────────────────────
# Maps common names (what users type) → Google language codes
LANGUAGE_MAP: dict[str, str] = {
    # Indian languages
    "hindi":      "hi",
    "gujarati":   "gu",
    "marathi":    "mr",
    "tamil":      "ta",
    "telugu":     "te",
    "kannada":    "kn",
    "malayalam":  "ml",
    "punjabi":    "pa",
    "bengali":    "bn",
    "urdu":       "ur",
    "odia":       "or",
    "assamese":   "as",
    # European
    "spanish":    "es",
    "french":     "fr",
    "german":     "de",
    "italian":    "it",
    "portuguese": "pt",
    "dutch":      "nl",
    "russian":    "ru",
    "polish":     "pl",
    "ukrainian":  "uk",
    "greek":      "el",
    "swedish":    "sv",
    "norwegian":  "no",
    "danish":     "da",
    "finnish":    "fi",
    # Middle Eastern / African
    "arabic":     "ar",
    "turkish":    "tr",
    "persian":    "fa",
    "farsi":      "fa",
    "hebrew":     "iw",
    "swahili":    "sw",
    # Asian
    "japanese":   "ja",
    "korean":     "ko",
    "chinese":    "zh-CN",
    "mandarin":   "zh-CN",
    "traditional chinese": "zh-TW",
    "thai":       "th",
    "vietnamese": "vi",
    "indonesian": "id",
    "malay":      "ms",
    # Others
    "english":    "en",
    "latin":      "la",
}


def _resolve_language(lang_input: str) -> tuple[str, str]:
    """
    Resolve a user-typed language name or code to a (code, display_name) tuple.
    Returns ("", "") if unknown.
    """
    raw = lang_input.strip().lower()
    # Direct code match (e.g. "hi", "zh-CN")
    all_codes = set(LANGUAGE_MAP.values())
    if raw in all_codes:
        display = next((k for k, v in LANGUAGE_MAP.items() if v == raw), raw)
        return raw, display.title()
    # Name match
    if raw in LANGUAGE_MAP:
        code = LANGUAGE_MAP[raw]
        return code, raw.title()
    # Partial match
    for name, code in LANGUAGE_MAP.items():
        if raw in name or name in raw:
            return code, name.title()
    return "", ""


# ─── Tools ────────────────────────────────────────────────────────────────────

@mcp.tool()
def translate_text(
    text: str,
    target_language: str,
    source_language: str = "auto",
) -> str:
    """
    Translate text into any target language.
    Use this as the FINAL step when a user requests output in a specific language.

    text            : the English text to translate (get this from other tools first)
    target_language : language name or code, e.g. "hindi", "gujarati", "japanese",
                      "spanish", "turkish", "korean", "hi", "gu", "ja"
    source_language : source language (default "auto" = auto-detect)

    Examples:
        translate_text("Hello, how are you?", "hindi")
        translate_text("Stock price is ₹2450", "gujarati")
        translate_text("It is raining today", "japanese")
    """
    if not text.strip():
        return "Error: text cannot be empty."
    if not target_language.strip():
        return "Error: target_language is required."

    try:
        from deep_translator import GoogleTranslator
    except ImportError:
        return "Error: deep-translator not installed. Run: pip install deep-translator"

    # Resolve target
    target_code, target_name = _resolve_language(target_language)
    if not target_code:
        supported = ", ".join(sorted(LANGUAGE_MAP.keys()))
        return (
            f"Error: Unknown language '{target_language}'.\n"
            f"Supported: {supported}"
        )

    # Resolve source
    if source_language.strip().lower() in ("auto", ""):
        source_code = "auto"
    else:
        source_code, _ = _resolve_language(source_language)
        if not source_code:
            source_code = "auto"

    try:
        translator = GoogleTranslator(source=source_code, target=target_code)
        # GoogleTranslator has a ~5000 char limit per call; chunk if needed
        MAX_CHARS = 4500
        if len(text) <= MAX_CHARS:
            translated = translator.translate(text)
        else:
            # Split into chunks and translate each
            chunks = [text[i:i+MAX_CHARS] for i in range(0, len(text), MAX_CHARS)]
            translated = " ".join(translator.translate(chunk) for chunk in chunks)

        return (
            f"🌐 Translation → {target_name} ({target_code})\n\n"
            f"Original  : {text[:200]}{'...' if len(text) > 200 else ''}\n"
            f"Translated: {translated}"
        )
    except Exception as e:
        return f"Error during translation: {e}"


@mcp.tool()
def detect_language(text: str) -> str:
    """
    Detect the language of a given text.
    Returns the detected language name and confidence.
    Example: detect_language("Namaste, aap kaise hain?")
    """
    if not text.strip():
        return "Error: text cannot be empty."
    try:
        from deep_translator import GoogleTranslator
        # Use a translate-to-english trick to get detected language
        translator = GoogleTranslator(source="auto", target="en")
        result = translator.translate(text[:200])
        # deep_translator doesn't expose detected lang directly, use langdetect fallback
        try:
            from langdetect import detect, DetectorFactory
            DetectorFactory.seed = 0
            lang_code = detect(text)
            lang_name = next(
                (name.title() for name, code in LANGUAGE_MAP.items() if code == lang_code),
                lang_code
            )
            return f"Detected Language: {lang_name} (code: {lang_code})"
        except ImportError:
            return (
                f"Detected (approximate): text appears translatable. "
                f"Install langdetect for precise detection: pip install langdetect"
            )
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def list_supported_languages() -> str:
    """
    List all languages supported by the translation tool.
    Includes the language name and its code.
    """
    lines = ["🌐 Supported Translation Languages\n"]
    for name, code in sorted(LANGUAGE_MAP.items()):
        lines.append(f"  {name.title():<22} → {code}")
    lines.append(
        "\nUsage: translate_text('your text here', 'hindi')"
    )
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run(transport="stdio")
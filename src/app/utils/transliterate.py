"""Uzbek Latin to Cyrillic transliteration."""


# Multi-character mappings (must be processed first)
MULTI_CHAR_MAP = {
    "sh": "ш",
    "ch": "ч",
    "g'": "ғ",
    "o'": "ў",
    "ng": "нг",
}

# Single character mappings
SINGLE_CHAR_MAP = {
    "a": "а",
    "b": "б",
    "d": "д",
    "e": "е",
    "f": "ф",
    "g": "г",
    "h": "ҳ",
    "i": "и",
    "j": "ж",
    "k": "к",
    "l": "л",
    "m": "м",
    "n": "н",
    "o": "о",
    "p": "п",
    "q": "қ",
    "r": "р",
    "s": "с",
    "t": "т",
    "u": "у",
    "v": "в",
    "x": "х",
    "y": "й",
    "z": "з",
    "'": "ъ",
}


def latin_to_cyrillic(text: str) -> str:
    """Convert Uzbek Latin text to Cyrillic.

    Args:
        text: Text in Uzbek Latin script

    Returns:
        Text converted to Cyrillic script
    """
    result = text

    # Process multi-character mappings first (case-insensitive)
    for latin, cyrillic in MULTI_CHAR_MAP.items():
        # Handle lowercase
        result = result.replace(latin, cyrillic)
        # Handle uppercase (first letter)
        result = result.replace(latin.capitalize(), cyrillic.upper() if len(cyrillic) == 1 else cyrillic[0].upper() + cyrillic[1:])
        # Handle all uppercase
        result = result.replace(latin.upper(), cyrillic.upper())

    # Process single character mappings
    for latin, cyrillic in SINGLE_CHAR_MAP.items():
        result = result.replace(latin, cyrillic)
        result = result.replace(latin.upper(), cyrillic.upper())

    return result


def is_latin(text: str) -> bool:
    """Check if text contains Latin Uzbek characters.

    Args:
        text: Text to check

    Returns:
        True if text appears to be Latin Uzbek
    """
    latin_chars = set("abcdefghijklmnopqrstuvwxyz'")
    text_lower = text.lower()
    latin_count = sum(1 for c in text_lower if c in latin_chars)
    return latin_count > len(text) * 0.3  # More than 30% Latin chars

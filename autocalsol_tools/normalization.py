from __future__ import annotations

import re
import unicodedata


def normalized_text(value: object) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = text.casefold().strip()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def safe_filename(value: object, fallback: str = "inconnu") -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("._-")
    return text[:80] or fallback


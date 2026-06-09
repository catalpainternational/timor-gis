"""Name normalisation for matching geographic features across providers.

Timor-Leste place names are spelled inconsistently between data providers and
across time: accents come and go, double consonants collapse, ``c``/``k``/``qu``
are interchangeable, ``u``/``o`` and ``f``/``w`` swap in Tetum transliterations,
and ordinals appear as either roman numerals or digits (``Lore II`` / ``Lore 2``).

Two keys are produced:

``normalize`` -- a conservative key (accents, case, punctuation, ordinals). Safe
to treat equal-keys as the same place.

``phonetic_key`` -- an aggressive key that folds the orthographic equivalence
classes above. Used only to *score* candidates, never to assert equality on its
own; residual matches are confirmed in the reviewed crosswalk.
"""

from __future__ import annotations

import re
import unicodedata

__all__ = ["strip_accents", "normalize", "phonetic_key"]

_ROMAN = {
    "i": "1",
    "ii": "2",
    "iii": "3",
    "iv": "4",
    "v": "5",
    "vi": "6",
}


def strip_accents(value: str) -> str:
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")


def _replace_trailing_roman(value: str) -> str:
    """``lospalos ii`` -> ``lospalos 2`` (only a trailing standalone numeral)."""
    parts = value.split()
    if parts and parts[-1] in _ROMAN:
        parts[-1] = _ROMAN[parts[-1]]
    return " ".join(parts)


def normalize(name: str) -> str:
    """Conservative key: equal keys are confidently the same place."""
    value = strip_accents(name or "").lower().strip()
    value = value.replace("'", "").replace("`", "")
    value = re.sub(r"[\-/]", " ", value)
    value = re.sub(r"[^a-z0-9 ]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    value = _replace_trailing_roman(value)
    return value.replace(" ", "")


def phonetic_key(name: str) -> str:
    """Aggressive key folding Timor-Leste orthographic equivalence classes.

    Lossy by design -- only ever used to rank fuzzy candidates for review.
    """
    value = strip_accents(name or "").lower()
    value = re.sub(r"[^a-z0-9]", "", _replace_trailing_roman(re.sub(r"[\-/']", " ", value)))

    # ordinal-aware digits kept; fold consonant/vowel classes
    value = value.replace("ph", "f")
    value = value.replace("qu", "k").replace("q", "k")
    value = value.replace("c", "k")  # c -> k (caraic/karaik)
    value = value.replace("x", "s").replace("z", "s")
    value = value.replace("y", "i")
    value = value.replace("w", "u").replace("f", "u")  # f <-> w <-> u family (fatu/watu/uatu)
    value = value.replace("o", "u")  # o <-> u
    value = value.replace("h", "")  # silent/inconsistent h
    value = re.sub(r"(.)\1+", r"\1", value)  # collapse doubled letters (ss->s)
    return value

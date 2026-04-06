"""Combinatorial analysis: cipher + gematria + cross-language matching.

Chains operations: cipher(word) → gematria(result) → match against other words.
Finds connections like:
  - בגד → Atbash → שרק (recognized word!)
  - מת → Atbash → יא (gematria = 11 = Ioan 11!)
  - פסח → Atbash → וחס (recognized word: "și a cruțat")
  - דוד Atbash-gematria = 280 = עיר standard gematria
"""

from hebrew import GematriaTypes, Hebrew
from .gematria import isopsephy
from .ciphers import atbash_hebrew, albam, avgad

# Available ciphers
_CIPHERS = {
    'ATBASH': atbash_hebrew,
    'ALBAM': albam,
    'AVGAD': avgad,
}


def cipher_then_gematria(word: str, cipher: str = 'ATBASH') -> dict:
    """Apply a cipher to a Hebrew word, then calculate all 23 gematria methods on the result.

    Returns dict with keys: original, cipher_name, cipher_result, gematria (dict of method→value).
    """
    cipher_fn = _CIPHERS.get(cipher.upper())
    if not cipher_fn:
        raise ValueError(f"Unknown cipher: {cipher}. Available: {list(_CIPHERS.keys())}")

    result = cipher_fn(word)
    h = Hebrew(result)
    gematria_vals = {}
    for gt in GematriaTypes:
        try:
            gematria_vals[gt.name] = h.gematria(gt)
        except Exception:
            pass

    return {
        'original': word,
        'cipher_name': cipher,
        'cipher_result': result,
        'gematria': gematria_vals,
    }


def cipher_word_match(hebrew_words: dict, known_words: dict = None) -> list:
    """Apply all ciphers to each Hebrew word and check if the result is a known word.

    Args:
        hebrew_words: dict of {word: meaning} to transform
        known_words: dict of {word: meaning} to match against (if None, matches against hebrew_words)

    Returns list of (word, meaning, cipher, result, result_meaning) tuples.
    """
    if known_words is None:
        known_words = hebrew_words

    matches = []
    for word, meaning in hebrew_words.items():
        for cipher_name, cipher_fn in _CIPHERS.items():
            result = cipher_fn(word)
            if result in known_words:
                matches.append((word, meaning, cipher_name, result, known_words[result]))
    return matches


def cipher_cross_language(hebrew_words: dict, greek_words: dict, min_value: int = 5) -> list:
    """Apply all ciphers to Hebrew words, then match gematria of cipher result against Greek isopsephy.

    Finds connections like: word → cipher → result, gematria(result) = isopsephy(greek_word).

    Returns list of dicts with keys:
        hebrew, hebrew_meaning, cipher, cipher_result,
        method, value, greek, greek_meaning
    """
    # Pre-compute Greek isopsephy values
    greek_vals = {}
    for gw, gm in greek_words.items():
        gv = isopsephy(gw)
        if gv >= min_value:
            greek_vals.setdefault(gv, []).append((gw, gm))

    results = []
    for hw, hm in hebrew_words.items():
        for cipher_name, cipher_fn in _CIPHERS.items():
            cipher_result = cipher_fn(hw)
            h = Hebrew(cipher_result)
            for gt in GematriaTypes:
                try:
                    hv = h.gematria(gt)
                    if hv in greek_vals:
                        for gw, gm in greek_vals[hv]:
                            results.append({
                                'hebrew': hw,
                                'hebrew_meaning': hm,
                                'cipher': cipher_name,
                                'cipher_result': cipher_result,
                                'method': gt.name,
                                'value': hv,
                                'greek': gw,
                                'greek_meaning': gm,
                            })
                except Exception:
                    pass
    return results


def full_combo_scan(hebrew_words: dict, greek_words: dict, min_value: int = 5) -> list:
    """Complete combinatorial scan: all ciphers × all 23 methods × cross-language.

    Combines:
    1. Direct: hebrew_gematria(word) = isopsephy(greek)  [23 methods]
    2. Cipher→match: cipher(word) → known Hebrew word?  [3 ciphers]
    3. Cipher→gematria→cross: cipher(word) → gematria(result) = isopsephy(greek)  [3×23 methods]

    Returns dict with keys: 'direct', 'cipher_words', 'cipher_cross'.
    """
    from .crosslang import cross_scan

    return {
        'direct': cross_scan(greek_words, hebrew_words, min_value),
        'cipher_words': cipher_word_match(hebrew_words),
        'cipher_cross': cipher_cross_language(hebrew_words, greek_words, min_value),
    }

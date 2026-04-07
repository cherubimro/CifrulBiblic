"""Cross-language matching: Greek isopsephy ↔ Hebrew gematria (all 23 methods)."""

from hebrew import GematriaTypes, Hebrew
from .gematria import isopsephy


def cross_match(greek_word: str, hebrew_word: str, min_value: int = 5) -> list:
    """Find all gematria methods where Greek isopsephy equals Hebrew gematria.

    Returns list of (method_name, value) tuples.
    """
    gv = isopsephy(greek_word)
    if gv < min_value:
        return []

    h = Hebrew(hebrew_word)
    matches = []
    for gt in GematriaTypes:
        try:
            hv = h.gematria(gt)
            if hv == gv:
                matches.append((gt.name, gv))
        except Exception:
            pass
    return matches


def cross_scan(greek_words: dict, hebrew_words: dict, min_value: int = 5) -> list:
    """Scan all Greek words against all Hebrew words using all 23 methods.

    Uses hash-table lookup: O(H×M) instead of O(G×H×M).

    Args:
        greek_words: dict of {word: meaning}
        hebrew_words: dict of {word: meaning}
        min_value: minimum value to report (skip trivial matches)

    Returns list of (greek_word, greek_meaning, value, hebrew_word, hebrew_meaning, method) tuples.
    """
    # Pre-compute Greek isopsephy values into reverse index
    greek_by_value = {}
    for gw, gm in greek_words.items():
        gv = isopsephy(gw)
        if gv >= min_value:
            greek_by_value.setdefault(gv, []).append((gw, gm))

    results = []
    for hw, hm in hebrew_words.items():
        h = Hebrew(hw)
        for gt in GematriaTypes:
            try:
                hv = h.gematria(gt)
                if hv in greek_by_value:
                    for gw, gm in greek_by_value[hv]:
                        results.append((gw, gm, hv, hw, hm, gt.name))
            except Exception:
                pass
    return results


def reverse_scan(hebrew_words: dict, greek_words: dict, min_value: int = 5) -> list:
    """Scan all Hebrew words (all 23 methods) against Greek isopsephy.

    Same as cross_scan but iterates Hebrew-first for different access patterns.
    """
    results = []
    # Pre-compute Greek values
    greek_vals = {}
    for gw, gm in greek_words.items():
        gv = isopsephy(gw)
        if gv >= min_value:
            greek_vals.setdefault(gv, []).append((gw, gm))

    for hw, hm in hebrew_words.items():
        h = Hebrew(hw)
        for gt in GematriaTypes:
            try:
                hv = h.gematria(gt)
                if hv in greek_vals:
                    for gw, gm in greek_vals[hv]:
                        results.append((hw, hm, hv, gw, gm, gt.name))
            except Exception:
                pass
    return results

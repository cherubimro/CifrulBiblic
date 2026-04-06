"""Hebrew gematria (23 methods via `hebrew` lib) and Greek isopsephy."""

import unicodedata
from hebrew import Hebrew, GematriaTypes

# Greek isopsephy values
_ISO = {
    'α':1,'β':2,'γ':3,'δ':4,'ε':5,'ζ':7,'η':8,'θ':9,
    'ι':10,'κ':20,'λ':30,'μ':40,'ν':50,'ξ':60,'ο':70,
    'π':80,'ρ':100,'σ':200,'ς':200,'τ':300,'υ':400,
    'φ':500,'χ':600,'ψ':700,'ω':800,
}

# Archaic Greek letters
_ISO_ARCHAIC = {**_ISO, 'ϝ': 6, 'ϟ': 90, 'ϡ': 900}


def isopsephy(word: str, archaic: bool = False) -> int:
    """Calculate Greek isopsephy for a word."""
    table = _ISO_ARCHAIC if archaic else _ISO
    total = 0
    for ch in word:
        base = unicodedata.normalize('NFD', ch)
        for c in base:
            if c in table:
                total += table[c]
                break
    return total


def hebrew_gematria(word: str, method: GematriaTypes = GematriaTypes.MISPAR_HECHRACHI) -> int:
    """Calculate Hebrew gematria using any of the 23 methods."""
    return Hebrew(word).gematria(method)


def all_hebrew_methods(word: str) -> dict:
    """Return all 23 gematria values for a Hebrew word."""
    h = Hebrew(word)
    results = {}
    for gt in GematriaTypes:
        try:
            results[gt.name] = h.gematria(gt)
        except Exception:
            results[gt.name] = None
    return results


def isopsephy_detail(word: str) -> list:
    """Return letter-by-letter isopsephy breakdown."""
    result = []
    for ch in word:
        base = unicodedata.normalize('NFD', ch)
        for c in base:
            if c in _ISO:
                result.append((ch, _ISO[c]))
                break
    return result


def factorize_theological(n: int) -> dict:
    """Check if n is divisible by theologically significant numbers."""
    factors = {}
    for name, val in [('YHWH', 26), ('David', 14), ('37', 37), ('7', 7),
                       ('17', 17), ('153', 153), ('12', 12), ('3', 3),
                       ('10', 10), ('40', 40), ('70', 70)]:
        if n % val == 0:
            factors[name] = n // val
    return factors

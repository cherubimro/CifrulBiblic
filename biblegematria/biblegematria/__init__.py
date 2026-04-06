"""biblegematria — Cross-language gematria, isopsephy, and cipher analysis for biblical texts."""

from .gematria import hebrew_gematria, isopsephy, all_hebrew_methods
from .ciphers import atbash_hebrew, albam, avgad, atbash_romanian
from .crosslang import cross_scan, cross_match
from .combo import cipher_then_gematria, cipher_word_match, cipher_cross_language, full_combo_scan
from .texts import load_sblgnt, load_masoretic, load_lxx

__version__ = "0.1.0"
__all__ = [
    "hebrew_gematria", "isopsephy", "all_hebrew_methods",
    "atbash_hebrew", "albam", "avgad", "atbash_romanian",
    "cross_scan", "cross_match",
    "load_sblgnt", "load_masoretic", "load_lxx",
]

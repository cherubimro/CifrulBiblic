#!/usr/bin/env python3
"""Full cross-language scan: all NT Greek words × all VT Hebrew words × all 23 methods × all ciphers.

Usage:
    python scan.py                        # full scan, output to stdout
    python scan.py -o results.tsv         # save to file
    python scan.py --book 64-Jn           # scan only Gospel of John
    python scan.py --top 50              # show top 50 results
    python scan.py -j 4                  # use 4 parallel workers
    python scan.py --book 64-Jn -j 8 -o john_scan.tsv
"""

import argparse
import sys
import re
from concurrent.futures import ProcessPoolExecutor, as_completed

from biblegematria import load_sblgnt, load_masoretic, isopsephy
from biblegematria.gematria import factorize_theological
from biblegematria.ciphers import atbash_hebrew, albam, avgad
from hebrew import Hebrew, GematriaTypes

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(it, **kw):
        total = kw.get('total', '?')
        desc = kw.get('desc', '')
        print(f"{desc} ({total} items)...", file=sys.stderr)
        return it

# NT book names (SBLGNT code → Romanian)
_NT_BOOKS = {
    'Mt': 'Matei', 'Mk': 'Marcu', 'Lk': 'Luca', 'Jn': 'Ioan', 'Ac': 'Fapte',
    'Ro': 'Romani', '1Co': '1Cor', '2Co': '2Cor', 'Ga': 'Galateni',
    'Eph': 'Efeseni', 'Php': 'Filipeni', 'Col': 'Coloseni',
    '1Th': '1Tes', '2Th': '2Tes', '1Ti': '1Tim', '2Ti': '2Tim',
    'Tit': 'Tit', 'Phm': 'Filimon', 'Heb': 'Evrei', 'Jas': 'Iacov',
    '1Pe': '1Petru', '2Pe': '2Petru', '1Jn': '1Ioan', '2Jn': '2Ioan',
    '3Jn': '3Ioan', 'Jud': 'Iuda', 'Re': 'Apocalipsa',
}

# VT book names (filename → Romanian)
_VT_BOOKS = {
    'Genesis': 'Facerea', 'Exodus': 'Ieșirea', 'Leviticus': 'Leviticul',
    'Numbers': 'Numeri', 'Deuteronomy': 'Deuteronom',
    'Joshua': 'Iosua', 'Judges': 'Judecători',
    'I_Samuel': '1Samuel', 'II_Samuel': '2Samuel',
    'I_Kings': '3Regi', 'II_Kings': '4Regi',
    'Isaiah': 'Isaia', 'Jeremiah': 'Ieremia', 'Ezekiel': 'Iezechiel',
    'Hosea': 'Osea', 'Joel': 'Ioel', 'Amos': 'Amos', 'Obadiah': 'Avdie',
    'Jonah': 'Iona', 'Micah': 'Miheia', 'Nahum': 'Naum',
    'Habakkuk': 'Avacum', 'Zephaniah': 'Sofonie',
    'Haggai': 'Agheu', 'Zechariah': 'Zaharia', 'Malachi': 'Maleahi',
    'Psalms': 'Psalmi', 'Proverbs': 'Proverbe', 'Job': 'Iov',
    'Song_of_Songs': 'Cânt', 'Ruth': 'Rut', 'Lamentations': 'Plângeri',
    'Ecclesiastes': 'Ecleziast', 'Esther': 'Estera', 'Daniel': 'Daniel',
    'Ezra': 'Ezdra', 'Nehemiah': 'Neemia',
    'I_Chronicles': '1Paralipomena', 'II_Chronicles': '2Paralipomena',
}

_ALL_METHODS = list(GematriaTypes)
_CIPHERS = {'ATBASH': atbash_hebrew, 'ALBAM': albam, 'AVGAD': avgad}


def extract_greek_vocabulary(book=None):
    """Extract unique Greek lemmas with first occurrence reference."""
    words = load_sblgnt(book=book)
    lemmas = {}  # {lemma: (isopsephy, "Carte cap:vs")}
    for w in words:
        lemma = w['lemma']
        if lemma and lemma not in lemmas:
            val = isopsephy(lemma)
            if val > 0:
                bk = _NT_BOOKS.get(w['book'], w['book'])
                ref = f"{bk} {w['chapter']}:{w['verse']}"
                lemmas[lemma] = (val, ref)
    return lemmas


def extract_hebrew_vocabulary(book=None):
    """Extract unique Hebrew words with first occurrence reference."""
    verses = load_masoretic(book=book)
    words = {}  # {word: (gematria, "Carte cap:vs")}
    for v in verses:
        for w in v['words']:
            clean = re.sub(r'[\u0591-\u05C7\u05F3\u05F4\u05BE]', '', w)
            if clean and len(clean) >= 2 and clean not in words:
                try:
                    val = Hebrew(clean).gematria(GematriaTypes.MISPAR_HECHRACHI)
                    if val > 0:
                        bk = _VT_BOOKS.get(v['book'], v['book'])
                        ref = f"{bk} {v['chapter']}:{v['verse']}"
                        words[clean] = (val, ref)
                except Exception:
                    pass
    return words


def _scan_one_hebrew(hw, hw_ref, greek_by_value, min_value):
    """Scan one Hebrew word against all Greek values. Called in parallel."""
    results = []
    h = Hebrew(hw)

    # Direct: all 23 methods
    for gt in _ALL_METHODS:
        try:
            hv = h.gematria(gt)
            if hv >= min_value and hv in greek_by_value:
                for gw, gref in greek_by_value[hv]:
                    results.append(('DIRECT', gw, gref, hv, hw, hw_ref, gt.name))
        except Exception:
            pass

    # Cipher → gematria → cross-language
    for cipher_name, cipher_fn in _CIPHERS.items():
        try:
            cipher_result = cipher_fn(hw)
            hc = Hebrew(cipher_result)
            for gt in _ALL_METHODS:
                try:
                    hv = hc.gematria(gt)
                    if hv >= min_value and hv in greek_by_value:
                        for gw, gref in greek_by_value[hv]:
                            results.append(('CIPHER', gw, gref, hv,
                                          f"{hw}→{cipher_name}→{cipher_result}",
                                          hw_ref, gt.name))
                except Exception:
                    pass
        except Exception:
            pass

    return results


def run_scan_parallel(greek_lemmas, hebrew_words, min_value=10, workers=4):
    """Run cross-language scan with parallel workers and progress bar."""

    # Build reverse index: value → [(greek_word, ref)]
    greek_by_value = {}
    for gw, (gv, gref) in greek_lemmas.items():
        if gv >= min_value:
            greek_by_value.setdefault(gv, []).append((gw, gref))

    hebrew_list = [(hw, info[1]) for hw, info in hebrew_words.items()]
    all_results = []

    # Cipher word matches
    cipher_word_results = []
    heb_set = set(hebrew_words.keys())
    for hw, (_, hw_ref) in hebrew_words.items():
        for cipher_name, cipher_fn in _CIPHERS.items():
            try:
                result = cipher_fn(hw)
                if result in heb_set and result != hw:
                    r_ref = hebrew_words[result][1]
                    cipher_word_results.append(
                        ('CIPHER_WORD', '', '', 0, hw, hw_ref,
                         f"{cipher_name}→{result} ({r_ref})"))
            except Exception:
                pass

    if workers <= 1:
        for hw, hw_ref in tqdm(hebrew_list, desc="Scanning", unit="words"):
            results = _scan_one_hebrew(hw, hw_ref, greek_by_value, min_value)
            all_results.extend(results)
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_scan_one_hebrew, hw, hw_ref, greek_by_value, min_value): hw
                for hw, hw_ref in hebrew_list
            }
            for future in tqdm(as_completed(futures), total=len(futures),
                             desc=f"Scanning ({workers} workers)", unit="words"):
                try:
                    results = future.result()
                    all_results.extend(results)
                except Exception:
                    pass

    return all_results, cipher_word_results


def format_results(direct_results, cipher_word_results, top=None):
    """Format and deduplicate results as TSV lines."""
    lines = []
    lines.append("TIP\tGREACĂ\tREF_NT\tVALOARE\tEBRAICĂ\tREF_VT\tMETODA\tFACTORI")

    seen = set()
    for rtype, gw, gref, val, hw, href, method in direct_results:
        key = f"{rtype}-{gw}-{hw}-{method}"
        if key in seen:
            continue
        seen.add(key)
        factors = factorize_theological(val) if val > 0 else {}
        fstr = ', '.join(f"{v}×{k}" for k, v in factors.items()) if factors else ''
        lines.append(f"{rtype}\t{gw}\t{gref}\t{val}\t{hw}\t{href}\t{method}\t{fstr}")

    for rtype, gw, gref, val, hw, href, method in cipher_word_results:
        key = f"{hw}-{method}"
        if key not in seen:
            seen.add(key)
            lines.append(f"{rtype}\t—\t—\t—\t{hw}\t{href}\t{method}\t—")

    if top:
        lines = lines[:1] + lines[1:top+1]

    return lines


def main():
    parser = argparse.ArgumentParser(
        description='Cross-language biblical gematria scanner')
    parser.add_argument('-o', '--output', help='Output file (TSV)')
    parser.add_argument('--book', help='SBLGNT book code (e.g., 64-Jn, 62-Mk)')
    parser.add_argument('--hebrew-book', help='Masoretic book (e.g., Genesis, Isaiah)')
    parser.add_argument('--top', type=int, help='Show only top N results')
    parser.add_argument('--min-value', type=int, default=10,
                        help='Minimum value to report (default: 10)')
    parser.add_argument('-j', '--workers', type=int, default=4,
                        help='Number of parallel workers (default: 4)')
    args = parser.parse_args()

    print(f"biblegematria scanner v0.1.0", file=sys.stderr)
    print(f"Workers: {args.workers}", file=sys.stderr)

    print("\n--- Loading texts ---", file=sys.stderr)
    greek = extract_greek_vocabulary(book=args.book)
    hebrew = extract_hebrew_vocabulary(book=args.hebrew_book)
    print(f"Greek lemmas: {len(greek)}, Hebrew words: {len(hebrew)}", file=sys.stderr)

    direct, cipher_words = run_scan_parallel(
        greek, hebrew, args.min_value, args.workers)

    print(f"\nResults: {len(direct)} direct/cipher-cross, "
          f"{len(cipher_words)} cipher-words", file=sys.stderr)

    lines = format_results(direct, cipher_words, top=args.top)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
        print(f"Saved to {args.output}", file=sys.stderr)
    else:
        for line in lines:
            print(line)


if __name__ == '__main__':
    main()

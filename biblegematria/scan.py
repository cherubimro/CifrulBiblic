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


# Pre-compute all GematriaTypes list
_ALL_METHODS = list(GematriaTypes)
_CIPHERS = {'ATBASH': atbash_hebrew, 'ALBAM': albam, 'AVGAD': avgad}


def extract_greek_vocabulary(book=None):
    """Extract unique Greek lemmas from SBLGNT."""
    words = load_sblgnt(book=book)
    lemmas = {}
    for w in words:
        lemma = w['lemma']
        if lemma and lemma not in lemmas:
            val = isopsephy(lemma)
            if val > 0:
                lemmas[lemma] = val
    return lemmas


def extract_hebrew_vocabulary(book=None):
    """Extract unique Hebrew words from Masoretic text."""
    verses = load_masoretic(book=book)
    words = {}
    for v in verses:
        for w in v['words']:
            clean = re.sub(r'[\u0591-\u05C7\u05F3\u05F4\u05BE]', '', w)
            if clean and len(clean) >= 2 and clean not in words:
                try:
                    val = Hebrew(clean).gematria(GematriaTypes.MISPAR_HECHRACHI)
                    if val > 0:
                        words[clean] = val
                except Exception:
                    pass
    return words


def _scan_one_hebrew(hw, greek_by_value, min_value):
    """Scan one Hebrew word against all Greek values using all 23 methods.
    Called in parallel workers.
    """
    results = []
    h = Hebrew(hw)

    # Direct: all 23 methods
    for gt in _ALL_METHODS:
        try:
            hv = h.gematria(gt)
            if hv >= min_value and hv in greek_by_value:
                for gw in greek_by_value[hv]:
                    results.append(('DIRECT', gw, hv, hw, gt.name))
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
                        for gw in greek_by_value[hv]:
                            results.append(('CIPHER', gw, hv,
                                          f"{hw}→{cipher_name}→{cipher_result}", gt.name))
                except Exception:
                    pass
        except Exception:
            pass

    return results


def run_scan_parallel(greek_lemmas, hebrew_words, min_value=10, workers=4):
    """Run cross-language scan with parallel workers and progress bar."""

    # Build reverse index: value → [greek_words]
    greek_by_value = {}
    for gw, gv in greek_lemmas.items():
        if gv >= min_value:
            greek_by_value.setdefault(gv, []).append(gw)

    hebrew_list = list(hebrew_words.keys())
    all_results = []

    # Cipher word matches (fast, no parallelization needed)
    cipher_word_results = []
    heb_set = set(hebrew_words.keys())
    for hw in hebrew_list:
        for cipher_name, cipher_fn in _CIPHERS.items():
            try:
                result = cipher_fn(hw)
                if result in heb_set and result != hw:
                    cipher_word_results.append(('CIPHER_WORD', '', 0, hw,
                                               f"{cipher_name}→{result}"))
            except Exception:
                pass

    if workers <= 1:
        # Sequential with progress bar
        for hw in tqdm(hebrew_list, desc="Scanning", unit="words"):
            results = _scan_one_hebrew(hw, greek_by_value, min_value)
            all_results.extend(results)
    else:
        # Parallel with progress bar
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_scan_one_hebrew, hw, greek_by_value, min_value): hw
                for hw in hebrew_list
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
    lines.append("TYPE\tGREEK\tVALUE\tHEBREW\tMETHOD\tFACTORS")

    seen = set()
    for rtype, gw, val, hw, method in direct_results:
        key = f"{rtype}-{gw}-{hw}-{method}"
        if key in seen:
            continue
        seen.add(key)
        factors = factorize_theological(val) if val > 0 else {}
        fstr = ', '.join(f"{v}×{k}" for k, v in factors.items()) if factors else ''
        lines.append(f"{rtype}\t{gw}\t{val}\t{hw}\t{method}\t{fstr}")

    for rtype, gw, val, hw, method in cipher_word_results:
        key = f"{hw}-{method}"
        if key not in seen:
            seen.add(key)
            lines.append(f"{rtype}\t—\t—\t{hw}\t{method}\t—")

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

    # Extract vocabularies
    print("\n--- Loading texts ---", file=sys.stderr)
    greek = extract_greek_vocabulary(book=args.book)
    hebrew = extract_hebrew_vocabulary(book=args.hebrew_book)
    print(f"Greek lemmas: {len(greek)}, Hebrew words: {len(hebrew)}", file=sys.stderr)
    total_comparisons = len(greek) * len(hebrew) * len(_ALL_METHODS)
    print(f"Comparisons: ~{total_comparisons:,} (direct) + cipher combos\n", file=sys.stderr)

    # Run scan
    direct, cipher_words = run_scan_parallel(
        greek, hebrew, args.min_value, args.workers)

    print(f"\nResults: {len(direct)} direct/cipher-cross, "
          f"{len(cipher_words)} cipher-words", file=sys.stderr)

    # Format output
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

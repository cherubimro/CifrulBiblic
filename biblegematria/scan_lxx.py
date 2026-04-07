#!/usr/bin/env python3
"""LXX ↔ Masoretic cross-language scan: did the Septuagint translators preserve gematria relationships?

Scans parallel verses: Greek isopsephy (LXX) vs Hebrew gematria (Masoretic), all 23 methods.

Usage:
    python scan_lxx.py                          # full scan
    python scan_lxx.py --book Gen               # only Genesis
    python scan_lxx.py --strict --top 50        # filtered results
    python scan_lxx.py -j 4 -o lxx_scan.tsv    # parallel, save to file
"""

import argparse
import os
import sys
import re
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from collections import Counter

from biblegematria.gematria import isopsephy, factorize_theological
from biblegematria.ciphers import atbash_hebrew, albam, avgad
from hebrew import Hebrew, GematriaTypes

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(it, **kw):
        return it

_ALL_METHODS = list(GematriaTypes)
_CIPHERS = {'ATBASH': atbash_hebrew, 'ALBAM': albam, 'AVGAD': avgad}

_STRICT_METHODS = {
    'MISPAR_HECHRACHI', 'MISPAR_GADOL', 'MISPAR_SIDURI',
    'MISPAR_KATAN', 'ATBASH', 'ALBAM', 'AVGAD',
}
_STRICT_FACTORS = {7, 14, 26, 37}

_LXX_BOOKS = {
    'Gen': 'Facerea', 'Exod': 'Ieșirea', 'Lev': 'Leviticul',
    'Num': 'Numeri', 'Deut': 'Deuteronom',
    'Isa': 'Isaia', 'Jer': 'Ieremia', 'Ezek': 'Iezechiel',
    'Ps': 'Psalmi', 'Dan': 'Daniel',
}

_LXX_TO_MAS = {
    'Gen': 'Genesis', 'Exod': 'Exodus', 'Lev': 'Leviticus',
    'Num': 'Numbers', 'Deut': 'Deuteronomy',
    'Isa': 'Isaiah', 'Jer': 'Jeremiah', 'Ezek': 'Ezekiel',
    'Ps': 'Psalms', 'Dan': 'Daniel',
}


def _clean_hebrew(word):
    """Strip vowels, cantillation, maqaf from Hebrew. Returns list of words."""
    w = word.replace('&nbsp;', ' ').replace('&thinsp;', ' ')
    w = w.replace('\u00a0', ' ').replace('\u2009', ' ')
    w = re.sub(r'&[a-z]+;', ' ', w)
    w = re.sub(r'\{[^}]*\}', '', w)
    w = w.replace('\u05BE', ' ')  # maqaf → split
    w = w.replace('׀', ' ')
    w = re.sub(r'[\u0591-\u05C7]', '', w)
    w = re.sub(r'[׃]', '', w)
    return [p.strip() for p in w.split() if p.strip() and len(p.strip()) >= 2]


def load_parallel_data(book=None):
    """Load LXX and Masoretic parallel verses.

    Returns dict: {ref: {'lxx_words': [...], 'mas_words': [...]}}
    """
    data_dir = os.path.join(os.path.expanduser('~'), '.biblegematria')
    lxx_dir = os.path.join(data_dir, 'lxx')
    mas_dir = os.path.join(data_dir, 'textul_masoretic')

    # Load LXX
    lxx_verses = {}
    for fname in sorted(os.listdir(lxx_dir)):
        if not fname.endswith('.js'):
            continue
        bk = fname.replace('.js', '')
        if book and bk != book:
            continue
        with open(os.path.join(lxx_dir, fname), 'r') as f:
            try:
                data = json.load(f)
                for ref, words in data.items():
                    lxx_verses[ref] = words
            except json.JSONDecodeError:
                pass

    # Load Masoretic
    mas_verses = {}
    for lxx_book, mas_book in _LXX_TO_MAS.items():
        if book and lxx_book != book:
            continue
        mas_file = os.path.join(mas_dir, f'{mas_book}.txt')
        if not os.path.exists(mas_file):
            continue
        with open(mas_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split('\t')
                if len(parts) >= 2:
                    ref_parts = parts[0].split(':')
                    if len(ref_parts) == 2:
                        ref = f"{lxx_book}.{ref_parts[0]}.{ref_parts[1]}"
                        mas_verses[ref] = parts[-1]

    # Build parallel data
    parallel = {}
    for ref in sorted(set(lxx_verses.keys()) & set(mas_verses.keys())):
        lxx_words = []
        for w in lxx_verses[ref]:
            lemma = w.get('lemma', '')
            if lemma and lemma not in ('ὁ', 'καί', 'δέ', 'ἐν', 'εἰς', 'ἐκ'):  # skip particles
                val = isopsephy(lemma)
                if val > 5:
                    lxx_words.append((lemma, val))

        mas_words = []
        for raw_w in mas_verses[ref].split():
            for clean_w in _clean_hebrew(raw_w):
                try:
                    val = Hebrew(clean_w).gematria(GematriaTypes.MISPAR_HECHRACHI)
                    if val > 5:
                        mas_words.append((clean_w, val))
                except:
                    pass

        if lxx_words and mas_words:
            parallel[ref] = {'lxx': lxx_words, 'mas': mas_words}

    return parallel


def scan_verse(ref, lxx_words, mas_words, strict=False):
    """Scan one parallel verse for cross-language matches."""
    results = []
    methods = [gt for gt in _ALL_METHODS if gt.name in _STRICT_METHODS] if strict else _ALL_METHODS

    # Build LXX value index
    lxx_by_value = {}
    for gw, gv in lxx_words:
        lxx_by_value.setdefault(gv, []).append(gw)

    for hw, hv_std in mas_words:
        h = Hebrew(hw)
        for gt in methods:
            try:
                hv = h.gematria(gt)
                if hv > 5 and hv in lxx_by_value:
                    if strict:
                        if not any(hv % f == 0 for f in _STRICT_FACTORS):
                            continue
                    for gw in lxx_by_value[hv]:
                        results.append((ref, gw, hv, hw, gt.name))
            except:
                pass

    return results


def main():
    parser = argparse.ArgumentParser(
        description='LXX ↔ Masoretic cross-language gematria scanner')
    parser.add_argument('-o', '--output', help='Output file')
    parser.add_argument('--book', help='LXX book (Gen, Exod, Isa, etc.)')
    parser.add_argument('--top', type=int, help='Show top N results')
    parser.add_argument('--strict', action='store_true',
                        help='Only strong methods + theological factors')
    parser.add_argument('-j', '--workers', type=int, default=4)
    args = parser.parse_args()

    print(f"LXX ↔ Masoretic scanner v0.1", file=sys.stderr)
    print(f"\n--- Loading parallel verses ---", file=sys.stderr)

    parallel = load_parallel_data(book=args.book)
    total_lxx = sum(len(v['lxx']) for v in parallel.values())
    total_mas = sum(len(v['mas']) for v in parallel.values())
    print(f"Versete paralele: {len(parallel):,}", file=sys.stderr)
    print(f"Cuvinte LXX: {total_lxx:,}, Masoretic: {total_mas:,}", file=sys.stderr)

    # Scan
    all_results = []
    refs = list(parallel.keys())

    if args.workers <= 1:
        for ref in tqdm(refs, desc="Scanning", unit="verses"):
            v = parallel[ref]
            results = scan_verse(ref, v['lxx'], v['mas'], args.strict)
            all_results.extend(results)
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(scan_verse, ref, parallel[ref]['lxx'],
                              parallel[ref]['mas'], args.strict): ref
                for ref in refs
            }
            for future in tqdm(as_completed(futures), total=len(futures),
                             desc=f"Scanning ({args.workers} workers)", unit="verses"):
                try:
                    all_results.extend(future.result())
                except:
                    pass

    print(f"\nPotriviri: {len(all_results):,}", file=sys.stderr)

    # Format
    lines = []
    lines.append(f"{'REF':<14} {'LXX (greacă)':<20} {'VAL':>5} "
                 f"{'MASORETIC (ebraică)':<20} {'METODA':<12} {'FACTORI'}")
    lines.append("─" * 100)

    seen = set()
    for ref, gw, val, hw, method in all_results:
        key = f"{ref}-{gw}-{hw}-{method}"
        if key in seen:
            continue
        seen.add(key)
        factors = factorize_theological(val)
        fstr = ', '.join(f"{v}×{k}" for k, v in factors.items()) if factors else ''
        mshort = method.replace('MISPAR_', '')
        bk_ch_vs = ref.replace('.', ' ', 1).replace('.', ':')
        lines.append(f"{bk_ch_vs:<14} {gw:<20} {val:>5} {hw:<20} {mshort:<12} {fstr}")

    if args.top:
        lines = lines[:2] + lines[2:args.top+2]

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
        print(f"Saved to {args.output}", file=sys.stderr)
    else:
        for line in lines:
            print(line)


if __name__ == '__main__':
    main()

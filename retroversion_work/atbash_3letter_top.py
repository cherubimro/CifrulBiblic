#!/usr/bin/env python3
"""Find the most theologically significant 3-letter-residue Atbash pairs
from atbash_pair_scan_v2.xlsx. Anchored on one side, rare + meaningful
residue word."""
import sys
import openpyxl
import unicodedata
from collections import defaultdict
from pathlib import Path

WORK = Path('/home/bu/Documents/Biblia/retroversion_work')


def strip_ac(w):
    w = unicodedata.normalize('NFD', w.lower())
    return ''.join(c for c in w if unicodedata.category(c) != 'Mn')


ANCHOR_ROOTS = [
    'ιησου', 'χριστ', 'πετρ', 'παυλ', 'πατερ', 'πατηρ', 'πατρ',
    'πνευμ', 'κυρι', 'μαθητ', 'σταυρ', 'αιμ', 'λυτρ', 'δουλ',
    'αναστ', 'γραφ', 'αρχιερε', 'ιερε', 'ναω', 'ναο', 'θυσι',
    'πασχ', 'βαπτ', 'προφητ', 'αποστολ', 'εκκλησ', 'βασιλει',
    'βασιλευ', 'σωτηρ', 'ηλι', 'μωυσ', 'ιωαν', 'μαρια', 'ιουδ',
    'αρνι', 'φως', 'ζω', 'αληθ', 'οδος', 'χαρ', 'ειρην', 'αγαπ',
    'ελπ', 'πιστ', 'μαρτυρ', 'δαυ', 'αβρα', 'μωσ', 'θεο',
]


def is_anchored(form):
    stripped = strip_ac(form)
    for root in ANCHOR_ROOTS:
        if stripped.startswith(root):
            return True
    return False


def main():
    path = WORK / 'atbash_pair_scan_v2.xlsx'
    wb = openpyxl.load_workbook(path)
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))

    # Keep only (3,3) residue pairs
    rows_3 = [r for r in rows if r[14] and r[15] and len(r[14]) == 3 and len(r[15]) == 3]
    print(f'Total (3,3)-residue pairs: {len(rows_3)}', file=sys.stderr)

    # Anchored subset
    anchored = [r for r in rows_3 if is_anchored(r[0]) or is_anchored(r[5])]
    print(f'Anchored: {len(anchored)}', file=sys.stderr)

    # Score: one side frequent (≥ 10), other rare, residue rare (≤ 30), and
    # the residue's NT iso match must be a content word of interest.
    def frequent_side(r):
        return max(r[2], r[7])

    filtered = []
    for r in anchored:
        max_ct = frequent_side(r)
        min_ct = min(r[2], r[7])
        res_freq = r[13] or 0
        if max_ct < 5:
            continue
        if res_freq > 40:
            continue
        # Skip if residue's NT match is a stopword-ish form
        iso_m = (r[16] or '').split(',')[0].strip()
        if not iso_m:
            continue
        filtered.append(r)

    # Rank by (max_ct desc, res_freq asc)
    def key(r):
        return (-frequent_side(r), r[13] or 999)
    filtered.sort(key=key)

    print(f'\n=== Top 50 (3,3)-residue anchored pairs ===\n')
    for r in filtered[:50]:
        iso_m = (r[16] or '-').split(',')[0].strip()
        print(f"  sum={r[10]:5}  "
              f"{r[0]:18}×{r[2]:<4} ↔ {r[5]:20}×{r[7]:<4}  "
              f"res={r[12]:5} ({r[14]}|{r[15]}) freq×{r[13] or 0:<3} → NT:{iso_m}")


if __name__ == '__main__':
    main()

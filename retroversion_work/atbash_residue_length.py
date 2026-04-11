#!/usr/bin/env python3
"""
Analyze the v2 Atbash-pair xlsx by RESIDUE-LENGTH:
  - Count pairs where residue_letters_A == 1 (and == B)
  - Count pairs where residue_letters_A == 2
  - Count pairs where residue_letters_A == 3+
For each length, show the top anchored pairs (at least one side is a
theologically major word).
"""
import sys
import openpyxl
import unicodedata
from collections import defaultdict, Counter
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

    # Columns: (see scan v2)
    # 0:A 1:A_lem 2:A_ct 3:A_iso 4:A_ref 5:B 6:B_lem 7:B_ct 8:B_iso 9:B_ref
    # 10:asum 11:csum 12:res 13:res_ct 14:resA 15:resB 16:iso_m 17:heb_m 18:score

    # Residue-length distribution
    by_length = defaultdict(list)
    for r in rows:
        lenA = len(r[14] or '')
        lenB = len(r[15] or '')
        by_length[(lenA, lenB)].append(r)

    total = sum(len(v) for v in by_length.values())
    print(f'Total pairs in v2 xlsx: {total}')
    print()
    print('Residue letter-count distribution (lenA, lenB): top 20')
    pairs_by_count = sorted(by_length.items(), key=lambda x: -len(x[1]))
    for (lA, lB), items in pairs_by_count[:20]:
        print(f'  ({lA},{lB}): {len(items):6} pairs')
    print()

    # Slice: residue has 1 letter on each side
    slice_1 = [r for (la, lb), rs in by_length.items() if la == 1 and lb == 1 for r in rs]
    slice_3 = [r for (la, lb), rs in by_length.items() if la == 3 and lb == 3 for r in rs]
    slice_4 = [r for (la, lb), rs in by_length.items() if la == 4 and lb == 4 for r in rs]

    print(f'Pairs with residue = 1 letter each: {len(slice_1)}')
    print(f'Pairs with residue = 3 letters each: {len(slice_3)}')
    print(f'Pairs with residue = 4 letters each: {len(slice_4)}')
    print()

    def top_anchored(slice_list, label, k=15):
        anchored = [r for r in slice_list if is_anchored(r[0]) or is_anchored(r[5])]
        # Rank by: at least one side frequent, other side rare, residue freq low
        def key(r):
            max_ct = max(r[2], r[7])
            min_ct = min(r[2], r[7])
            res_freq = r[13] or 9999
            return (-max_ct, min_ct, res_freq)
        anchored.sort(key=key)
        print(f'\n=== {label}: top {k} anchored (one side has a theological root) ===')
        for r in anchored[:k]:
            iso_m = (r[16] or '-').split(',')[0].strip()
            print(f"  sum={r[10]:5}  {r[0]:18}×{r[2]:<4} ↔ "
                  f"{r[5]:18}×{r[7]:<4}  "
                  f"residue={r[12]:5} ({r[14]}|{r[15]})  res_freq×{r[13] or 0:<3}  → NT:{iso_m}")

    top_anchored(slice_1, 'RESIDUE 1 LETTER EACH')
    top_anchored(slice_3, 'RESIDUE 3 LETTERS EACH')
    # 4 letters too noisy usually, but show a few
    top_anchored(slice_4, 'RESIDUE 4 LETTERS EACH', k=10)


if __name__ == '__main__':
    main()

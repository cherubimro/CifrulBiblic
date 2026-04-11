#!/usr/bin/env python3
"""
Focused analysis: for EACH theologically-meaningful value, show the top
matches ranked by rarity AND narrative weight.

Idea: rarity alone finds statistical outliers at random values. We want
rare matches AT ALREADY-MEANINGFUL values (666, 385, 613, 153, 276, ...).
"""
import json
import math
import sys
from collections import defaultdict, Counter
from pathlib import Path

sys.path.insert(0, '/home/bu/Documents/Biblia')
import openpyxl
from biblegematria.biblegematria import load_sblgnt, isopsephy

WORK = Path('/home/bu/Documents/Biblia/retroversion_work')

# Values we consider theologically meaningful
# (subset of base_values.json — the ones with real significance)
THEOLOGICAL_VALUES = {
    74:   "וחס (spared, Atbash of Pesach) / 2×37",
    103:  "Δανιηλ LXX (Daniel)",
    148:  "פסח (Pesach) / 4×37",
    153:  "John 21:11 fish / T(17)=H(9) / בני האלהים",
    206:  "דבר (Word) / בר אבא",
    207:  "אור (light)",
    214:  "רוח (ruach)",
    222:  "888-666 / 6×37 (our Thomas)",
    248:  "אברהם (Abraham) / 248 mitzvot",
    259:  "βασιλεία / 7×37",
    276:  "Acts 27:37 / T(23)=H(12) / רוע / עור",
    296:  "8×37",
    318:  "Barnabas (IH+T)",
    333:  "9×37",
    358:  "משיח (Messiah) / נחש",
    370:  "10×37 / שכן / שלם",
    385:  "שכינה (Shekinah) / σινδόνα",
    391:  "ישועה (yeshua'ah)",
    407:  "11×37",
    416:  "μαθητην / λεπτα",
    444:  "קרבן/מקדש / 12×37",
    481:  "13×37",
    518:  "14×37",
    555:  "15×37",
    592:  "1480-888 / 16×37",
    613:  "taryag mitzvot / γέγραφα",
    616:  "Rev 13:18 variant",
    629:  "17×37",
    666:  "Beast / Solomon / Nero Caesar / Lateinos",
    703:  "19×37",
    800:  "Ω (omega) / κύριος",
    848:  "βασιλεύς",
    888:  "Ἰησοῦς",
    911:  "ראשית / χάρις",
    913:  "בראשית",
    974:  "",
}


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def compute_rarity_map():
    """Per-value rarity score = -log10(P(NT,V) * P(OT,V))."""
    sblgnt = load_sblgnt()
    morph = load_json(WORK / 'morph_index.json')

    nt = Counter()
    for w in sblgnt:
        form = w['word'].strip('.,;·:()[]')
        v = isopsephy(form)
        if v > 0:
            nt[v] += 1

    ot = Counter()
    for vid, words in morph.items():
        for w in words:
            g = w['gematria_stem']
            if g > 0:
                ot[g] += 1

    nt_total = sum(nt.values())
    ot_total = sum(ot.values())

    rarity = {}
    for v in set(nt.keys()) & set(ot.keys()):
        p = (nt[v] / nt_total) * (ot[v] / ot_total)
        rarity[v] = (-math.log10(p), nt[v], ot[v])
    return rarity, nt, ot


def read_raw_cipher():
    wb = openpyxl.load_workbook(WORK / 'nt_ot_cipher.xlsx', read_only=True)
    ws = wb['NT↔OT Cipher']
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    cols = ['score', 'nt_form', 'iso', 'factor37', 'greek_lemma', 'ro',
            'nt_count', 'first_ref',
            'retroversion_stem', 'ot_hebrew_stem', 'ot_hebrew_strongs',
            'ot_occurrences', 'ot_first_verse']
    return [dict(zip(cols, r)) for r in rows]


def main():
    print('Computing rarity map...', file=sys.stderr)
    rarity, nt_counts, ot_counts = compute_rarity_map()

    matches = read_raw_cipher()
    by_iso = defaultdict(list)
    for m in matches:
        by_iso[m['iso']].append(m)

    print('\n' + '=' * 90)
    print('THEOLOGICAL VALUES — rarity + top NT forms + top OT words')
    print('=' * 90)

    for val, label in sorted(THEOLOGICAL_VALUES.items()):
        info = rarity.get(val)
        if info:
            r, nt_c, ot_c = info
        else:
            nt_c = nt_counts.get(val, 0)
            ot_c = ot_counts.get(val, 0)
            r = 0
        if nt_c == 0 or ot_c == 0:
            marker = '—'
        elif r >= 7.5:
            marker = '★★'  # very rare
        elif r >= 6.5:
            marker = '★'   # moderately rare
        else:
            marker = ' '    # common

        print(f'\n{marker} {val:>5} (r={r:>4.1f}, NT×{nt_c:>4}, OT×{ot_c:>4}) — {label}')

        ms = by_iso.get(val, [])
        if not ms:
            print('    NO MATCHES')
            continue

        # Top NT forms by count
        nt_forms_seen = {}
        for m in ms:
            f = m['nt_form']
            if f not in nt_forms_seen or (m['nt_count'] or 0) > (nt_forms_seen[f]['nt_count'] or 0):
                nt_forms_seen[f] = m
        top_nt = sorted(nt_forms_seen.values(), key=lambda x: -(x['nt_count'] or 0))[:5]

        # Top OT words by frequency
        ot_seen = {}
        for m in ms:
            w = m['ot_hebrew_stem']
            if w not in ot_seen:
                ot_seen[w] = m
        top_ot = sorted(ot_seen.values(), key=lambda x: -(x['ot_occurrences'] or 0))[:5]

        if top_nt:
            print('    NT forms: ' + '  •  '.join(
                f"{m['nt_form']} ×{m['nt_count']} ({(m['ro'] or '')[:16]})"
                for m in top_nt
            ))
        if top_ot:
            print('    OT words: ' + '  •  '.join(
                f"{m['ot_hebrew_stem']} (H{m['ot_hebrew_strongs']} ×{m['ot_occurrences']})"
                for m in top_ot
            ))


if __name__ == '__main__':
    main()

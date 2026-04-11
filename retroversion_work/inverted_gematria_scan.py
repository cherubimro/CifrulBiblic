#!/usr/bin/env python3
"""
Inverted-gematria scan.

"Inverted gematria" = value assignment where α↔ω, β↔ψ, γ↔χ, etc. — i.e.,
each letter gets the value of its Atbash mirror. Equivalently,
inverted_iso(W) = iso(atbash(W)).

Three tests:

  (1) TARGET HITS: find NT content words whose inverted gematria equals
      a known theological constant (888, 153, 666, 611, 613, 444, 318,
      276, 37×k, etc.)

  (2) MIRROR PAIRS: find pairs (A, B) where iso(A) = inverted_iso(B),
      i.e., standard isopsephy of one equals inverted isopsephy of the
      other. This is a new kind of cross-scheme identity.

  (3) PALINDROMIC: find words W with iso(W) = inverted_iso(W) — numerically
      invariant under Atbash re-valuation.
"""
import re
import sys
import unicodedata
from collections import defaultdict, Counter
from pathlib import Path

import openpyxl

sys.path.insert(0, '/home/bu/Documents/Biblia')
from biblegematria.biblegematria import load_sblgnt, isopsephy

WORK = Path('/home/bu/Documents/Biblia/retroversion_work')

GREEK_ALPHABET = 'αβγδεζηθικλμνξοπρστυφχψω'
ATBASH = {GREEK_ALPHABET[i]: GREEK_ALPHABET[23 - i] for i in range(24)}
ATBASH['ς'] = ATBASH['σ']

EDITORIAL_RE = re.compile(r'[⸀⸁⸂⸃⸄⸅⸆⸇⸈⸉⸊⸋⸌⸍⸎⸏⸐⸑⸒⸓⸔⸕⸖⸗]')

STOPWORD_LEMMAS = {
    'ὁ', 'ἡ', 'τό', 'αὐτός', 'ἐγώ', 'σύ', 'ἡμεῖς', 'ὑμεῖς', 'οὗτος', 'ἐκεῖνος',
    'ὅς', 'ὅστις', 'ὅδε', 'τις', 'τίς', 'ἄλλος', 'ἕτερος', 'ἑαυτοῦ',
    'καί', 'δέ', 'γάρ', 'οὖν', 'τε', 'ἀλλά', 'ἤ', 'μέν', 'μή',
    'οὐ', 'οὐχί', 'εἰ', 'ἐάν', 'ὅτι', 'ἵνα', 'ὡς', 'ὥστε', 'ὅταν',
    'ὅπως', 'ἄν', 'ἄρα', 'γε', 'ναί', 'οὐδέ', 'μηδέ', 'οὔτε', 'μήτε',
    'καθώς', 'πρίν', 'πλήν', 'πῶς', 'ποῦ', 'πότε', 'ὅπου', 'οὕτως',
    'ἐν', 'εἰς', 'ἐκ', 'ἐπί', 'πρός', 'ἀπό', 'διά', 'περί', 'ὑπό',
    'κατά', 'μετά', 'παρά', 'ὑπέρ', 'πρό', 'σύν',
    'εἰμί', 'γίνομαι', 'ἔχω', 'λέγω', 'ποιέω', 'δίδωμι', 'ὁράω',
    'ἔρχομαι', 'οἶδα', 'θέλω', 'δύναμαι',
    'πᾶς', 'πολύς', 'εἷς', 'μέγας', 'ἰδού', 'ἀμήν',
}

# Theological target values (Greek and Hebrew anchors)
TARGETS = {
    13: 'אחד/אהבה',
    17: 'T(17)=153',
    26: 'יהוה',
    37: 'Christ-factor (888/24)',
    74: 'וחס spared',
    86: 'אלהים',
    111: '3×37',
    148: 'פסח Pesaḥ',
    153: 'ΙΧΘΥΣ / בני האלהים',
    214: 'רוח',
    222: '6×37',
    246: 'גבריאל',
    276: 'רע/עור',
    318: 'חנוך Enoch / Gen 14:14',
    354: 'שנה year',
    385: 'שכינה',
    416: 'λεπτά',
    430: 'שקל',
    444: 'קדש',
    486: 'סכות',
    496: 'מלכות',
    532: 'וישמן',
    560: 'βουλήν',
    611: 'תורה',
    613: 'mitzvot',
    666: 'Beast',
    702: 'שבת',
    775: 'ירושלים',
    777: 'triple-7',
    800: 'ω',
    811: '(empty)',
    830: 'Φοῖνιξ/fruits',
    858: '33×26',
    888: 'Ἰησοῦς',
    911: 'ראשית',
    913: 'בראשית',
    999: 'near triple',
    1000: 'chiliad',
    1118: 'Shema',
    1209: '3×13×31',
    1260: 'Rev 12:6',
}


def clean_greek(word):
    w = EDITORIAL_RE.sub('', word)
    return w.strip('.,;·:()[]·\u0387')


def strip_accents(word):
    w = unicodedata.normalize('NFD', word.lower())
    return ''.join(c for c in w if unicodedata.category(c) != 'Mn')


def atbash_transform(word):
    w = strip_accents(word)
    return ''.join(ATBASH[c] for c in w if c in ATBASH)


def inverted_iso(word):
    """Inverted gematria = isopsephy of the Atbash transform."""
    at = atbash_transform(word)
    return isopsephy(at)


def main():
    sblgnt = load_sblgnt()

    forms = {}
    for w in sblgnt:
        orig = clean_greek(w['word'])
        if not orig:
            continue
        stripped = strip_accents(orig)
        if not stripped:
            continue
        if stripped not in forms:
            forms[stripped] = {
                'original': orig,
                'lemma': clean_greek(w['lemma']),
                'count': 0,
                'first_ref': f"{w['book']} {w['chapter']}:{w['verse']}",
                'iso': isopsephy(orig),
                'inv_iso': inverted_iso(orig),
            }
        forms[stripped]['count'] += 1

    def is_stopword(stripped):
        return forms[stripped]['lemma'] in STOPWORD_LEMMAS

    content = {k: v for k, v in forms.items() if not is_stopword(k)}
    print(f'Total NT forms: {len(forms)}', file=sys.stderr)
    print(f'Content forms: {len(content)}', file=sys.stderr)

    # =========================================================
    # TEST 1: inverted_iso hits on theological targets
    # =========================================================
    print('\n=== TEST 1: inverted_iso on theological target values ===\n')
    by_inv = defaultdict(list)
    for k, info in content.items():
        by_inv[info['inv_iso']].append(k)

    for target, name in sorted(TARGETS.items()):
        hits = by_inv.get(target, [])
        if not hits:
            continue
        # Rank by frequency
        hits_sorted = sorted(hits, key=lambda k: -content[k]['count'])
        top = hits_sorted[:5]
        top_str = ', '.join(
            f"{content[k]['original']}(×{content[k]['count']})" for k in top
        )
        print(f'  inverted = {target:4} ({name:30}): {len(hits):3} hits → {top_str}')

    # =========================================================
    # TEST 2: Mirror pairs — iso(A) = inverted_iso(B)
    # =========================================================
    print('\n=== TEST 2: mirror pairs iso(A) == inverted_iso(B) (both content, rare) ===\n')
    by_iso = defaultdict(list)
    for k, info in content.items():
        by_iso[info['iso']].append(k)

    anchor_roots = ['ιησου', 'χριστ', 'πετρ', 'παυλ', 'πατερ', 'πατηρ',
                    'πνευμ', 'κυρι', 'μαθητ', 'σταυρ', 'λυτρ', 'θεο',
                    'βαπτ', 'αμνο', 'αρνι', 'προφητ', 'αποστολ',
                    'βασιλει', 'σωτηρ', 'δαυ', 'αβρα', 'μωσ', 'μωυσ',
                    'αγαπ', 'πιστ', 'αληθ', 'μαρτυρ']

    def is_anchored(k):
        return any(k.startswith(r) for r in anchor_roots)

    mirror_hits = []
    for k, info in content.items():
        if not is_anchored(k):
            continue
        matches = by_iso.get(info['inv_iso'], [])
        for m in matches:
            if m == k:
                continue
            if is_stopword(m):
                continue
            if content[m]['lemma'] == info['lemma']:
                continue
            mirror_hits.append((k, m, info['iso'], info['inv_iso']))

    print(f'  Total anchored mirror pairs: {len(mirror_hits)}')
    # Rank by max frequency
    mirror_hits.sort(key=lambda t: -max(content[t[0]]['count'], content[t[1]]['count']))
    for k, m, isoA, invA in mirror_hits[:30]:
        cA = content[k]
        cB = content[m]
        print(f'  {cA["original"]:18}×{cA["count"]:<4} iso={isoA:4}, inv_iso={invA:4}  '
              f'→ {cB["original"]:18}×{cB["count"]:<4} iso={cB["iso"]:4}')

    # =========================================================
    # TEST 3: Palindromic (iso = inv_iso)
    # =========================================================
    print('\n=== TEST 3: palindromic forms (iso == inverted_iso) ===\n')
    palindromic = [k for k, info in content.items() if info['iso'] == info['inv_iso']]
    palindromic.sort(key=lambda k: -content[k]['count'])
    print(f'  Total palindromic content forms: {len(palindromic)}')
    for k in palindromic[:40]:
        info = content[k]
        print(f'  {info["original"]:20}×{info["count"]:<4} iso={info["iso"]:4} = inv_iso={info["inv_iso"]:4}  ({info["lemma"]}, {info["first_ref"]})')

    # Save main findings to xlsx
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Inverted gematria'
    ws.append(['Form', 'Lemma', 'Count', 'First ref', 'iso', 'inverted_iso',
               'atbash_form'])
    for k, info in sorted(content.items(), key=lambda x: -x[1]['count']):
        ws.append([info['original'], info['lemma'], info['count'],
                   info['first_ref'], info['iso'], info['inv_iso'],
                   atbash_transform(info['original'])])
    ws.freeze_panes = 'A2'
    wb.save(WORK / 'inverted_gematria.xlsx')


if __name__ == '__main__':
    main()

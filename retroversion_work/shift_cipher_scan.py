#!/usr/bin/env python3
"""
Unified Greek shift-cipher scanner. Runs any shift (1=Avgad, 12=Albam,
23=reverse-Avgad, etc.) on all NT content forms and reports:
  (1) Hits on theological target values
  (2) Literal pairs: Shift(A) = B (both NT words)
  (3) Mirror pairs: iso(A) = shift_iso(B) for anchored words
  (4) Self-mirror: iso(W) = shift_iso(W)

Usage:
    python shift_cipher_scan.py 1        # Avgad (shift +1)
    python shift_cipher_scan.py 23       # Reverse Avgad (shift -1 = +23)
    python shift_cipher_scan.py 12       # Albam (already done separately)
"""
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, '/home/bu/Documents/Biblia')
from biblegematria.biblegematria import load_sblgnt, isopsephy

GA = 'αβγδεζηθικλμνξοπρστυφχψω'
EDITORIAL_RE = re.compile(r'[⸀⸁⸂⸃⸄⸅⸆⸇⸈⸉⸊⸋⸌⸍⸎⸏⸐⸑⸒⸓⸔⸕⸖⸗]')

STOPWORD_LEMMAS = {
    'ὁ','ἡ','τό','αὐτός','ἐγώ','σύ','ἡμεῖς','ὑμεῖς','οὗτος','ἐκεῖνος',
    'ὅς','ὅστις','τις','τίς','ἄλλος','ἕτερος','ἑαυτοῦ',
    'καί','δέ','γάρ','οὖν','τε','ἀλλά','ἤ','μέν','μή',
    'οὐ','εἰ','ἐάν','ὅτι','ἵνα','ὡς','ἄν',
    'ἐν','εἰς','ἐκ','ἐπί','πρός','ἀπό','διά','περί','ὑπό',
    'κατά','μετά','παρά','ὑπέρ','πρό','σύν',
    'εἰμί','γίνομαι','ἔχω','λέγω','ποιέω','δίδωμι',
    'πᾶς','πολύς','εἷς','μέγας','ἰδού','ἀμήν',
}

TARGETS = {
    13:'אחד/אהבה', 26:'יהוה', 37:'Christ-factor', 74:'וחס',
    86:'אלהים', 111:'3×37', 148:'פסח', 153:'ΙΧΘΥΣ',
    214:'רוח', 222:'6×37', 276:'רע/עור', 318:'חנוך',
    354:'שנה', 385:'שכינה', 416:'λεπτά', 430:'שקל',
    444:'מקדש', 486:'סכות', 554:'πρόβατα', 560:'βουλήν',
    611:'תורה', 613:'mitzvot', 666:'Beast', 777:'triple-7',
    783:'Albam(שכינה)', 800:'ω', 888:'Ἰησοῦς',
    911:'ראשית', 913:'בראשית', 1000:'χίλιοι', 1118:'Shema',
    1209:'Gabriel/Atbash-sum', 1260:'Rev12:6',
}


def clean_greek(word):
    w = EDITORIAL_RE.sub('', word)
    return w.strip('.,;·:()[]·\u0387').replace('(','').replace(')','')

def strip_accents(word):
    w = unicodedata.normalize('NFD', word.lower())
    return ''.join(c for c in w if unicodedata.category(c) != 'Mn')

def make_shift(n):
    mapping = {}
    for i in range(24):
        mapping[GA[i]] = GA[(i + n) % 24]
    mapping['ς'] = mapping['σ']
    return mapping

def apply_shift(word, mapping):
    w = strip_accents(word)
    out = []
    for ch in w:
        if ch in mapping:
            out.append(mapping[ch])
        else:
            return None
    return ''.join(out)

def shift_iso(word, mapping):
    s = apply_shift(word, mapping)
    return isopsephy(s) if s else 0


def main():
    if len(sys.argv) < 2:
        print("Usage: python shift_cipher_scan.py <shift_amount> [shift_amount2 ...]")
        sys.exit(1)

    shifts = [int(x) for x in sys.argv[1:]]

    print('Loading SBLGNT...', file=sys.stderr)
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
            }
        forms[stripped]['count'] += 1

    content = {k: v for k, v in forms.items()
               if v['lemma'] not in STOPWORD_LEMMAS}
    print(f'  {len(content)} content forms', file=sys.stderr)

    by_iso = defaultdict(list)
    for k, v in content.items():
        by_iso[v['iso']].append(k)

    anchor_roots = ['ιησου','χριστ','πετρ','παυλ','κυρι','θεο',
                    'πνευμ','μαθητ','σταυρ','λυτρ','βασιλει',
                    'αγαπ','πιστ','αληθ','μαρτυρ','δαυ','αβρα',
                    'λογ','αρνι','δουλ','σωτηρ','ζω','φως']

    def is_anchored(k):
        return any(k.startswith(r) for r in anchor_roots)

    for shift_n in shifts:
        mapping = make_shift(shift_n)
        cipher_name = {1:'Avgad', 23:'Rev-Avgad', 12:'Albam'}.get(shift_n, f'Shift-{shift_n}')

        # Precompute shift_iso for all content forms
        for k, v in content.items():
            v[f's{shift_n}'] = shift_iso(v['original'], mapping)

        print(f'\n{"="*70}')
        print(f'  {cipher_name} (shift {shift_n})')
        print(f'{"="*70}')

        # TEST 1: target hits
        print(f'\n--- TEST 1: {cipher_name}-iso on theological targets ---\n')
        by_shift = defaultdict(list)
        for k, v in content.items():
            sv = v[f's{shift_n}']
            if sv:
                by_shift[sv].append(k)

        for target, name in sorted(TARGETS.items()):
            hits = by_shift.get(target, [])
            if not hits:
                continue
            hits_sorted = sorted(hits, key=lambda k: -content[k]['count'])[:5]
            top_str = ', '.join(f"{content[k]['original']}(×{content[k]['count']})" for k in hits_sorted)
            print(f'  {cipher_name}={target:5} ({name:28}): {len(hits):3} → {top_str}')

        # TEST 2: literal pairs
        print(f'\n--- TEST 2: {cipher_name}-literal pairs ---\n')
        literal = []
        for k, v in content.items():
            shifted = apply_shift(v['original'], mapping)
            if shifted and shifted != k and shifted in content:
                if content[shifted]['lemma'] != v['lemma'] and k < shifted:
                    literal.append((k, shifted))

        literal.sort(key=lambda p: -(content[p[0]]['count'] + content[p[1]]['count']))
        print(f'  {len(literal)} literal pairs. Top 15:')
        for A, B in literal[:15]:
            cA, cB = content[A], content[B]
            print(f"    {cA['original']:16}×{cA['count']:<3} ↔ {cB['original']:16}×{cB['count']:<3}")

        # TEST 3: mirror (anchored)
        print(f'\n--- TEST 3: {cipher_name} mirror iso(A)=shift_iso(B), anchored, top 20 ---\n')
        mirror = []
        for k, v in content.items():
            if not is_anchored(k):
                continue
            sv = v[f's{shift_n}']
            if not sv:
                continue
            matches = by_iso.get(sv, [])
            for m in matches:
                if m == k or content[m]['lemma'] == v['lemma']:
                    continue
                mirror.append((k, m, v['iso'], sv))

        mirror.sort(key=lambda t: -max(content[t[0]]['count'], content[t[1]]['count']))
        seen = set()
        shown = 0
        for k, m, isoA, shA in mirror:
            key = (k, m)
            if key in seen:
                continue
            seen.add(key)
            cA, cB = content[k], content[m]
            print(f"    {cA['original']:16}×{cA['count']:<4} iso={isoA:4} {cipher_name}={shA:4}  "
                  f"→ {cB['original']:16}×{cB['count']:<4} iso={cB['iso']:4}")
            shown += 1
            if shown >= 20:
                break

        # TEST 4: self-mirror
        print(f'\n--- TEST 4: {cipher_name} palindromic (iso = shift_iso) ---\n')
        palindromic = [(k, v) for k, v in content.items()
                       if v['iso'] == v[f's{shift_n}'] and v['iso'] > 0]
        palindromic.sort(key=lambda p: -p[1]['count'])
        print(f'  {len(palindromic)} palindromic forms. Top 15:')
        for k, v in palindromic[:15]:
            print(f"    {v['original']:20}×{v['count']:<4} iso={v['iso']:4}  ({v['lemma']}, {v['first_ref']})")


if __name__ == '__main__':
    main()

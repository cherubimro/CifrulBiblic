#!/usr/bin/env python3
"""
Albam cipher scan on NT Greek text + Hebrew retroversion.

Greek Albam: 24-letter alphabet split into 2×12, shift by 12 positions:
  α↔ν, β↔ξ, γ↔ο, δ↔π, ε↔ρ, ζ↔σ, η↔τ, θ↔υ, ι↔φ, κ↔χ, λ↔ψ, μ↔ω

Hebrew Albam: 22-letter alphabet split into 2×11, shift by 11 positions:
  א↔ל, ב↔מ, ג↔נ, ד↔ס, ה↔ע, ו↔פ, ז↔צ, ח↔ק, ט↔ר, י↔ש, כ↔ת

Tests:
  (1) NT content words whose Greek-Albam isopsephy hits a theological target
  (2) Albam-literal pairs: Albam(A) = B, both NT words
  (3) Mirror pairs: iso(A) = albam_iso(B)
  (4) Albam-sum identity: pairs with iso(A) + albam_iso(A) = iso(B) + albam_iso(B)
  (5) Hebrew Albam on retroversion: cross-language Albam matches
"""
import json
import re
import sys
import unicodedata
from collections import defaultdict, Counter
from pathlib import Path

sys.path.insert(0, '/home/bu/Documents/Biblia')
from biblegematria.biblegematria import load_sblgnt, isopsephy, hebrew_gematria
from biblegematria.ciphers import albam as hebrew_albam

WORK = Path('/home/bu/Documents/Biblia/retroversion_work')

# Greek Albam
GA = 'αβγδεζηθικλμνξοπρστυφχψω'
ALBAM_GR = {}
for i in range(12):
    ALBAM_GR[GA[i]] = GA[i + 12]
    ALBAM_GR[GA[i + 12]] = GA[i]
ALBAM_GR['ς'] = ALBAM_GR['σ']

EDITORIAL_RE = re.compile(r'[⸀⸁⸂⸃⸄⸅⸆⸇⸈⸉⸊⸋⸌⸍⸎⸏⸐⸑⸒⸓⸔⸕⸖⸗]')

STOPWORD_LEMMAS = {
    'ὁ', 'ἡ', 'τό', 'αὐτός', 'ἐγώ', 'σύ', 'ἡμεῖς', 'ὑμεῖς', 'οὗτος',
    'ἐκεῖνος', 'ὅς', 'ὅστις', 'τις', 'τίς', 'ἄλλος', 'ἕτερος', 'ἑαυτοῦ',
    'καί', 'δέ', 'γάρ', 'οὖν', 'τε', 'ἀλλά', 'ἤ', 'μέν', 'μή',
    'οὐ', 'εἰ', 'ἐάν', 'ὅτι', 'ἵνα', 'ὡς', 'ἄν',
    'ἐν', 'εἰς', 'ἐκ', 'ἐπί', 'πρός', 'ἀπό', 'διά', 'περί', 'ὑπό',
    'κατά', 'μετά', 'παρά', 'ὑπέρ', 'πρό', 'σύν',
    'εἰμί', 'γίνομαι', 'ἔχω', 'λέγω', 'ποιέω', 'δίδωμι',
    'πᾶς', 'πολύς', 'εἷς', 'μέγας', 'ἰδού', 'ἀμήν',
}

TARGETS = {
    13: 'אחד/אהבה', 26: 'יהוה', 37: 'Christ-factor',
    86: 'אלהים', 111: '3×37', 148: 'פסח', 153: 'ΙΧΘΥΣ',
    214: 'רוח', 276: 'רע/עור', 318: 'חנוך', 385: 'שכינה',
    416: 'λεπτά', 430: 'שקל', 444: 'מקדש', 486: 'סכות',
    554: 'πρόβατα=ἐγείρονται', 560: 'βουλήν',
    611: 'תורה', 613: 'mitzvot', 666: 'Beast',
    783: 'Albam(שכינה)', 800: 'ω', 888: 'Ἰησοῦς',
    911: 'ראשית', 1000: 'χίλιοι', 1118: 'Shema', 1209: 'Gabriel',
}


def clean_greek(word):
    w = EDITORIAL_RE.sub('', word)
    return w.strip('.,;·:()[]·\u0387').replace('(', '').replace(')', '')


def strip_accents(word):
    w = unicodedata.normalize('NFD', word.lower())
    return ''.join(c for c in w if unicodedata.category(c) != 'Mn')


def albam_transform_gr(word):
    w = strip_accents(word)
    out = []
    for ch in w:
        if ch in ALBAM_GR:
            out.append(ALBAM_GR[ch])
        else:
            return None
    return ''.join(out)


def albam_iso_gr(word):
    at = albam_transform_gr(word)
    if at is None:
        return 0
    return isopsephy(at)


def main():
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
            iso = isopsephy(orig)
            alb = albam_iso_gr(orig)
            forms[stripped] = {
                'original': orig,
                'lemma': clean_greek(w['lemma']),
                'count': 0,
                'first_ref': f"{w['book']} {w['chapter']}:{w['verse']}",
                'iso': iso,
                'albam_iso': alb,
                'albam_form': albam_transform_gr(orig) or '',
            }
        forms[stripped]['count'] += 1

    def is_stopword(k):
        return forms[k]['lemma'] in STOPWORD_LEMMAS

    content = {k: v for k, v in forms.items() if not is_stopword(k)}
    print(f'  {len(content)} content forms', file=sys.stderr)

    # ======== TEST 1: Albam-iso hits on theological targets ========
    print('\n=== TEST 1: Greek Albam-iso on theological targets ===\n')
    by_alb = defaultdict(list)
    for k, v in content.items():
        by_alb[v['albam_iso']].append(k)

    for target, name in sorted(TARGETS.items()):
        hits = by_alb.get(target, [])
        if not hits:
            continue
        hits_sorted = sorted(hits, key=lambda k: -content[k]['count'])
        top = hits_sorted[:5]
        top_str = ', '.join(f"{content[k]['original']}(×{content[k]['count']})" for k in top)
        print(f'  albam = {target:4} ({name:30}): {len(hits):3} hits → {top_str}')

    # ======== TEST 2: Albam-literal pairs ========
    print('\n=== TEST 2: Albam-literal pairs (Albam(A) = B, both NT content words) ===\n')
    literal_pairs = []
    for k, v in content.items():
        alb = v['albam_form']
        if not alb or alb == k:
            continue
        if alb in content and content[alb]['lemma'] != v['lemma']:
            if k < alb:  # avoid duplicates
                literal_pairs.append((k, alb))

    print(f'  Found {len(literal_pairs)} literal-Albam pairs:')
    for A, B in sorted(literal_pairs, key=lambda p: -(content[p[0]]['count'] + content[p[1]]['count'])):
        cA, cB = content[A], content[B]
        print(f"    {cA['original']:16}×{cA['count']:<3} (iso {cA['iso']}) ↔ "
              f"{cB['original']:16}×{cB['count']:<3} (iso {cB['iso']})")

    # ======== TEST 3: Mirror pairs iso(A) = albam_iso(B) ========
    print('\n=== TEST 3: Mirror pairs iso(A) = albam_iso(B), anchored ===\n')
    by_iso = defaultdict(list)
    for k, v in content.items():
        by_iso[v['iso']].append(k)

    anchor_roots = ['ιησου', 'χριστ', 'πετρ', 'παυλ', 'κυρι', 'θεο',
                    'πνευμ', 'μαθητ', 'σταυρ', 'λυτρ', 'βασιλει',
                    'αγαπ', 'πιστ', 'αληθ', 'μαρτυρ', 'δαυ', 'αβρα']

    def is_anchored(k):
        return any(k.startswith(r) for r in anchor_roots)

    mirror = []
    for k, v in content.items():
        if not is_anchored(k):
            continue
        matches = by_iso.get(v['albam_iso'], [])
        for m in matches:
            if m == k or content[m]['lemma'] == v['lemma']:
                continue
            mirror.append((k, m, v['iso'], v['albam_iso']))

    mirror.sort(key=lambda t: -max(content[t[0]]['count'], content[t[1]]['count']))
    print(f'  {len(mirror)} anchored mirror pairs. Top 25:')
    for k, m, isoA, albA in mirror[:25]:
        cA, cB = content[k], content[m]
        print(f"    {cA['original']:16}×{cA['count']:<4} iso={isoA:4} albam={albA:4}  "
              f"→ {cB['original']:16}×{cB['count']:<4} iso={cB['iso']:4}")

    # ======== TEST 5: Hebrew Albam on retroversion ========
    print('\n=== TEST 5: Hebrew Albam on retroversion canonical forms ===\n')
    retro_path = WORK / 'retroversion.json'
    if retro_path.exists():
        with open(retro_path, encoding='utf-8') as f:
            retro = json.load(f)

        heb_hits = []
        for lemma, entry in retro.items():
            can = entry.get('hebrew_canonical', {})
            stem = can.get('stem', '')
            gem = can.get('gematria', 0)
            if not stem or not gem:
                continue
            alb_stem = hebrew_albam(stem)
            alb_gem = hebrew_gematria(alb_stem)
            # Check if albam-gematria is interesting
            for target, name in TARGETS.items():
                if alb_gem == target:
                    heb_hits.append((lemma, stem, gem, alb_stem, alb_gem, name,
                                     entry.get('ro', '')))

        print(f'  {len(heb_hits)} Hebrew Albam hits on targets:')
        for lemma, stem, gem, alb_stem, alb_gem, name, ro in sorted(heb_hits, key=lambda x: x[4]):
            print(f"    {lemma:16} {stem:8}({gem}) → albam: {alb_stem:8}({alb_gem}) = {name:20} [{ro}]")


if __name__ == '__main__':
    main()

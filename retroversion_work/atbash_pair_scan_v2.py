#!/usr/bin/env python3
"""
Atbash-pair scan v2: look for pairs of NT Greek words with equal
atbash_sum and a residue that:
  (a) matches an NT word's isopsephy (non-stopword), AND
  (b) that residue value appears as isopsephy of a LOW-frequency NT word
      (a rare hit, not a frequent coincidence), AND
  (c) both A and B themselves are reasonably rare (so we don't get
      pairs dominated by function words or extremely common forms).

Unlike v1, this version does NOT privilege a theological-constants dict,
so the top results include residues beyond 416/613/1118.
"""
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl

sys.path.insert(0, '/home/bu/Documents/Biblia')
from biblegematria.biblegematria import load_sblgnt, isopsephy, hebrew_gematria

WORK = Path('/home/bu/Documents/Biblia/retroversion_work')

GREEK_ALPHABET = 'αβγδεζηθικλμνξοπρστυφχψω'
ATBASH = {GREEK_ALPHABET[i]: GREEK_ALPHABET[23 - i] for i in range(24)}
ATBASH['ς'] = ATBASH['σ']

EDITORIAL_RE = re.compile(r'[⸀⸁⸂⸃⸄⸅⸆⸇⸈⸉⸊⸋⸌⸍⸎⸏⸐⸑⸒⸓⸔⸕⸖⸗]')

STOPWORD_LEMMAS = {
    'ὁ', 'ἡ', 'τό',
    'αὐτός', 'ἐγώ', 'σύ', 'ἡμεῖς', 'ὑμεῖς', 'οὗτος', 'ἐκεῖνος',
    'ὅς', 'ὅστις', 'ὅδε', 'τις', 'τίς', 'ἄλλος', 'ἕτερος', 'ἑαυτοῦ',
    'καί', 'δέ', 'γάρ', 'οὖν', 'τε', 'ἀλλά', 'ἤ', 'μέν', 'μή',
    'οὐ', 'οὐχί', 'εἰ', 'ἐάν', 'ὅτι', 'ἵνα', 'ὡς', 'ὥστε', 'ὅταν',
    'ὅπως', 'ἄν', 'ἄρα', 'γε', 'ναί', 'οὐδέ', 'μηδέ', 'οὔτε', 'μήτε',
    'καθώς', 'πρίν', 'πλήν', 'πῶς', 'ποῦ', 'πότε', 'ὅπου', 'οὕτως',
    'ἐν', 'εἰς', 'ἐκ', 'ἐπί', 'πρός', 'ἀπό', 'διά', 'περί', 'ὑπό',
    'κατά', 'μετά', 'παρά', 'ὑπέρ', 'πρό', 'σύν', 'ἄνευ', 'ἄχρι',
    'ἕως', 'ἔμπροσθεν', 'ὀπίσω', 'ἐνώπιον',
    'εἰμί', 'γίνομαι', 'ἔχω', 'λέγω', 'ποιέω', 'δίδωμι', 'ὁράω',
    'ἔρχομαι', 'οἶδα', 'θέλω', 'δύναμαι',
    'πᾶς', 'πολύς', 'εἷς', 'μέγας', 'ἅγιος',
    'ἰδού', 'ἀμήν',
}


def clean_greek(word):
    w = EDITORIAL_RE.sub('', word)
    return w.strip('.,;·:()[]·\u0387')


def strip_accents(word):
    w = unicodedata.normalize('NFD', word.lower())
    return ''.join(c for c in w if unicodedata.category(c) != 'Mn')


def letter_contribution(ch):
    if ch not in ATBASH:
        return 0
    return isopsephy(ch) + isopsephy(ATBASH[ch])


def contribution_multiset(word):
    w = strip_accents(word)
    counter = Counter()
    for ch in w:
        c = letter_contribution(ch)
        if c > 0:
            counter[c] += 1
    return counter


def multiset_sum(m):
    return sum(k * v for k, v in m.items())


def common_multiset(m1, m2):
    keys = set(m1) & set(m2)
    return Counter({k: min(m1[k], m2[k]) for k in keys})


def residue_letters(word, common):
    w = strip_accents(word)
    remaining = Counter(common)
    residue = []
    for ch in w:
        c = letter_contribution(ch)
        if c <= 0:
            continue
        if remaining.get(c, 0) > 0:
            remaining[c] -= 1
        else:
            residue.append(ch)
    return residue


def main():
    print('Loading SBLGNT...', file=sys.stderr)
    sblgnt = load_sblgnt()

    forms = {}
    for w in sblgnt:
        form = clean_greek(w['word'])
        if not form:
            continue
        iso = isopsephy(form)
        if iso <= 0:
            continue
        if form not in forms:
            mset = contribution_multiset(form)
            forms[form] = {
                'lemma': clean_greek(w['lemma']),
                'count': 0,
                'first_ref': f"{w['book']} {w['chapter']}:{w['verse']}",
                'iso': iso,
                'atbash_sum': multiset_sum(mset),
                'multiset': mset,
            }
        forms[form]['count'] += 1

    print(f'  {len(forms)} unique forms', file=sys.stderr)

    def is_stopword(form):
        return forms[form]['lemma'] in STOPWORD_LEMMAS

    # Index: map each isopsephy value -> list of NT forms with that iso,
    # along with total NT frequency of the iso-value
    iso_to_forms = defaultdict(list)
    iso_total_count = defaultdict(int)
    for f, info in forms.items():
        if is_stopword(f):
            continue
        iso_to_forms[info['iso']].append(f)
        iso_total_count[info['iso']] += info['count']

    # Load Hebrew retroversion
    retro_by_gem = defaultdict(list)
    retro_path = WORK / 'retroversion.json'
    if retro_path.exists():
        with open(retro_path, encoding='utf-8') as fh:
            retro = json.load(fh)
        for lemma, entry in retro.items():
            can = entry.get('hebrew_canonical', {})
            g = can.get('gematria', 0)
            if g:
                retro_by_gem[g].append((lemma, can.get('stem', ''), entry.get('ro', '')))

    # Bucket content-word forms by atbash_sum
    buckets = defaultdict(list)
    for f, info in forms.items():
        if is_stopword(f):
            continue
        buckets[info['atbash_sum']].append(f)

    print(f'  {len(buckets)} atbash_sum buckets (content words only)', file=sys.stderr)

    # Scan
    results = []
    for asum, bucket in buckets.items():
        if len(bucket) < 2:
            continue
        if asum < 500:
            continue
        n = len(bucket)
        for i in range(n):
            A = bucket[i]
            mA = forms[A]['multiset']
            for j in range(i + 1, n):
                B = bucket[j]
                mB = forms[B]['multiset']
                common = common_multiset(mA, mB)
                common_sum = multiset_sum(common)
                residue = asum - common_sum

                if residue == 0:
                    continue
                if residue < 50:
                    continue
                # Require strong letter-level overlap (>=50% shared)
                if common_sum < asum * 0.5:
                    continue

                resA = residue_letters(A, common)
                resB = residue_letters(B, common)
                if not resA or not resB:
                    continue

                if forms[A]['lemma'] == forms[B]['lemma']:
                    continue

                # Residue must match the isopsephy of some NT content word
                iso_matches = [f for f in iso_to_forms.get(residue, [])
                               if f not in (A, B)]
                heb_matches = retro_by_gem.get(residue, [])
                if not iso_matches and not heb_matches:
                    continue

                results.append({
                    'A': A,
                    'B': B,
                    'A_lemma': forms[A]['lemma'],
                    'B_lemma': forms[B]['lemma'],
                    'A_count': forms[A]['count'],
                    'B_count': forms[B]['count'],
                    'A_iso': forms[A]['iso'],
                    'B_iso': forms[B]['iso'],
                    'A_ref': forms[A]['first_ref'],
                    'B_ref': forms[B]['first_ref'],
                    'asum': asum,
                    'common_sum': common_sum,
                    'residue': residue,
                    'res_letters_A': ''.join(resA),
                    'res_letters_B': ''.join(resB),
                    'iso_matches': iso_matches[:5],
                    'heb_matches': heb_matches[:3],
                    'residue_total_freq': iso_total_count.get(residue, 0),
                })

    print(f'  {len(results):,} candidate pairs', file=sys.stderr)

    # Summary of residue distribution
    res_dist = Counter(r['residue'] for r in results)
    print(f'  {len(res_dist)} distinct residue values', file=sys.stderr)
    print('\n=== Residue distribution: top 30 values by pair count ===', file=sys.stderr)
    for v, c in res_dist.most_common(30):
        sample_iso = iso_to_forms.get(v, [])
        sample = ', '.join(sample_iso[:3]) if sample_iso else '-'
        print(f'  residue={v:5}  {c:5} pairs  → NT samples: {sample}', file=sys.stderr)

    # Score each result:
    # significance = product of (1/A_count) × (1/B_count) × (1/residue_total_freq)
    # Higher = rarer pair + rarer residue
    import math
    for r in results:
        # Use log scoring
        score = (
            -math.log(max(r['A_count'], 1))
            - math.log(max(r['B_count'], 1))
            - math.log(max(r['residue_total_freq'], 1))
        )
        r['score'] = score

    # Sort by score descending
    results.sort(key=lambda r: -r['score'])

    # Write full results to xlsx
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'All Atbash pairs'
    ws.append([
        'Form A', 'A lemma', 'A ×', 'A iso', 'A ref',
        'Form B', 'B lemma', 'B ×', 'B iso', 'B ref',
        'Atbash sum', 'Common sum', 'Residue',
        'Res freq NT', 'Res letters A', 'Res letters B',
        'NT iso-matches', 'Hebrew retroversion', 'Score',
    ])
    for r in results:
        iso_m = ', '.join(r['iso_matches'][:5])
        heb_m = ', '.join(f"{h[0]}={h[1]} ({h[2]})" for h in r['heb_matches'][:3])
        ws.append([
            r['A'], r['A_lemma'], r['A_count'], r['A_iso'], r['A_ref'],
            r['B'], r['B_lemma'], r['B_count'], r['B_iso'], r['B_ref'],
            r['asum'], r['common_sum'], r['residue'],
            r['residue_total_freq'], r['res_letters_A'], r['res_letters_B'],
            iso_m, heb_m, round(r['score'], 2),
        ])
    ws.freeze_panes = 'A2'
    out = WORK / 'atbash_pair_scan_v2.xlsx'
    wb.save(out)
    print(f'\nWrote {out} ({len(results)} pairs total)', file=sys.stderr)

    # Print top results per non-(416/613/1118) residue
    print('\n=== Top-scored pair per residue value (skipping 416/613/1118) ===\n')
    seen_residues = set()
    exclude = {416, 613, 1118}
    shown = 0
    for r in results:
        if r['residue'] in exclude:
            continue
        if r['residue'] in seen_residues:
            continue
        seen_residues.add(r['residue'])
        iso_m = ', '.join(r['iso_matches'][:3]) if r['iso_matches'] else '-'
        heb_m = ', '.join(f"{h[0]}" for h in r['heb_matches'][:2]) if r['heb_matches'] else '-'
        print(f"  sum={r['asum']:5}  {r['A']:18}×{r['A_count']:<3} ↔ "
              f"{r['B']:18}×{r['B_count']:<3}  "
              f"residue={r['residue']:5} "
              f"(res_total×{r['residue_total_freq']:<3}) "
              f"→ NT:{iso_m} | HEB:{heb_m}")
        shown += 1
        if shown >= 60:
            break


if __name__ == '__main__':
    main()

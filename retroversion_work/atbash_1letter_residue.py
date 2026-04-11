#!/usr/bin/env python3
"""
Dedicated scan for pairs with EXACTLY 1-letter residue on each side.
No NT-iso-match filter: we just want to see what pairs exist, where two
NT forms differ by exactly one 'orphan' letter on each side.

Such pairs are the tightest possible Atbash-sum matches: they represent
two words that are nearly identical letter-for-letter, differing only in
one position where the two letters have the same (iso + atbash-iso)
contribution.
"""
import sys
import re
import unicodedata
from collections import Counter, defaultdict
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


def main():
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
                'multiset': mset,
                'atbash_sum': multiset_sum(mset),
                'n_letters': sum(mset.values()),
            }
        forms[form]['count'] += 1

    def is_stopword(form):
        return forms[form]['lemma'] in STOPWORD_LEMMAS

    # Bucket content words by atbash_sum
    buckets = defaultdict(list)
    for f, info in forms.items():
        if is_stopword(f):
            continue
        buckets[info['atbash_sum']].append(f)

    # Scan pairs: keep only 1-letter residue on each side
    results = []
    for asum, bucket in buckets.items():
        if len(bucket) < 2:
            continue
        for i in range(len(bucket)):
            A = bucket[i]
            mA = forms[A]['multiset']
            nA = forms[A]['n_letters']
            for j in range(i + 1, len(bucket)):
                B = bucket[j]
                mB = forms[B]['multiset']
                nB = forms[B]['n_letters']

                # Quick: to have 1-letter residue on each side, word lengths
                # must be equal (common_letters is a subset of both)
                if nA != nB:
                    continue

                # Compute common multiset
                common = Counter({k: min(mA[k], mB[k]) for k in set(mA) & set(mB)})
                common_count = sum(common.values())
                resA = nA - common_count
                resB = nB - common_count
                if resA != 1 or resB != 1:
                    continue

                # Exclude identical lemmas
                if forms[A]['lemma'] == forms[B]['lemma']:
                    continue

                residue_val = asum - multiset_sum(common)
                results.append({
                    'A': A, 'B': B,
                    'A_lemma': forms[A]['lemma'],
                    'B_lemma': forms[B]['lemma'],
                    'A_count': forms[A]['count'],
                    'B_count': forms[B]['count'],
                    'A_ref': forms[A]['first_ref'],
                    'B_ref': forms[B]['first_ref'],
                    'asum': asum,
                    'residue': residue_val,
                    'n_letters': nA,
                })

    print(f'Total 1-letter-residue pairs (equal length): {len(results)}')
    print()

    # Distribution of residue values
    res_dist = Counter(r['residue'] for r in results)
    print('Residue value distribution:')
    for v, c in res_dist.most_common():
        print(f'  residue={v:4}  {c:4} pairs (= contrib of letter value)')
    print()

    # Rank: prefer pairs where at least one side has count >= 5 and length >= 5
    def key(r):
        max_ct = max(r['A_count'], r['B_count'])
        min_ct = min(r['A_count'], r['B_count'])
        # prefer longer words (more meaningful) and frequent partner
        return (-max_ct, -r['n_letters'], min_ct)
    results.sort(key=key)

    # Top 40 — prefer frequent anchored pairs
    print('=== Top 40 1-letter-residue pairs (ranked by frequency of larger side) ===\n')
    for r in results[:40]:
        print(f"  sum={r['asum']:5}  len={r['n_letters']}  "
              f"{r['A']:18}×{r['A_count']:<4} ↔ {r['B']:18}×{r['B_count']:<4}  "
              f"residue={r['residue']}")

    # Also write xlsx
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '1-letter residue'
    ws.append(['A', 'A lemma', 'A×', 'A ref', 'B', 'B lemma', 'B×', 'B ref',
               'Atbash sum', 'Residue', 'N letters'])
    for r in results:
        ws.append([r['A'], r['A_lemma'], r['A_count'], r['A_ref'],
                   r['B'], r['B_lemma'], r['B_count'], r['B_ref'],
                   r['asum'], r['residue'], r['n_letters']])
    ws.freeze_panes = 'A2'
    wb.save(WORK / 'atbash_1letter_residue.xlsx')
    print(f'\nWrote atbash_1letter_residue.xlsx ({len(results)} pairs)')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Complete cipher scan on Delitzsch Hebrew NT — all methods that were
done on Greek SBLGNT but not yet on Hebrew.

Methods:
  1. Hebrew Atbash systematic (pairs, literal, multiset)
  2. Hebrew Albam systematic
  3. Hebrew Avgad + Reverse-Avgad
  4. Hebrew ordinal (א=1...ת=22)
  5. Hebrew Mispar Katan
  6. Hebrew Notarikon (first/last letters)
  7. Hebrew inverted gematria (= Atbash-gematria) + palindromic
"""
import json
import sys
import unicodedata
import re
from collections import defaultdict, Counter
from pathlib import Path

sys.path.insert(0, '/home/bu/Documents/Biblia')
from biblegematria.biblegematria import hebrew_gematria
from biblegematria.ciphers import atbash_hebrew, albam

WORK = Path('/home/bu/Documents/Biblia/retroversion_work')

HEB_ALPHA = 'אבגדהוזחטיכלמנסעפצקרשת'
HEB_VALS = {
    'א':1,'ב':2,'ג':3,'ד':4,'ה':5,'ו':6,'ז':7,'ח':8,'ט':9,
    'י':10,'כ':20,'ל':30,'מ':40,'נ':50,'ס':60,'ע':70,'פ':80,'צ':90,
    'ק':100,'ר':200,'ש':300,'ת':400,
    'ך':20,'ם':40,'ן':50,'ף':80,'ץ':90  # final forms
}

# Hebrew Atbash: א↔ת, ב↔ש, ג↔ר, ד↔ק, ה↔צ, ו↔פ, ז↔ע, ח↔ס, ט↔נ, י↔מ, כ↔ל
HEB_ATBASH = {}
for i in range(11):
    HEB_ATBASH[HEB_ALPHA[i]] = HEB_ALPHA[21-i]
    HEB_ATBASH[HEB_ALPHA[21-i]] = HEB_ALPHA[i]
# Final forms map to their regular Atbash
for final, regular in [('ך','כ'),('ם','מ'),('ן','נ'),('ף','פ'),('ץ','צ')]:
    HEB_ATBASH[final] = HEB_ATBASH[regular]

# Hebrew Albam: shift by 11 (half of 22)
HEB_ALBAM = {}
for i in range(11):
    HEB_ALBAM[HEB_ALPHA[i]] = HEB_ALPHA[i+11]
    HEB_ALBAM[HEB_ALPHA[i+11]] = HEB_ALPHA[i]
for final, regular in [('ך','כ'),('ם','מ'),('ן','נ'),('ף','פ'),('ץ','צ')]:
    HEB_ALBAM[final] = HEB_ALBAM[regular]

# Hebrew Avgad: shift +1
HEB_AVGAD = {}
for i in range(22):
    HEB_AVGAD[HEB_ALPHA[i]] = HEB_ALPHA[(i+1) % 22]
for final, regular in [('ך','כ'),('ם','מ'),('ן','נ'),('ף','פ'),('ץ','צ')]:
    HEB_AVGAD[final] = HEB_AVGAD[regular]

# Hebrew Reverse-Avgad: shift -1
HEB_RAVGAD = {}
for i in range(22):
    HEB_RAVGAD[HEB_ALPHA[i]] = HEB_ALPHA[(i-1) % 22]
for final, regular in [('ך','כ'),('ם','מ'),('ן','נ'),('ף','פ'),('ץ','צ')]:
    HEB_RAVGAD[final] = HEB_RAVGAD[regular]

# Hebrew ordinal: א=1, ב=2, ..., ת=22
HEB_ORD = {HEB_ALPHA[i]: i+1 for i in range(22)}
for final, regular in [('ך','כ'),('ם','מ'),('ן','נ'),('ף','פ'),('ץ','צ')]:
    HEB_ORD[final] = HEB_ORD[regular]

# Hebrew Mispar Katan: leading digit
HEB_MK = {}
for ch, val in HEB_VALS.items():
    v = val
    while v >= 10: v //= 10
    HEB_MK[ch] = v

TARGETS = {
    13:'אחד/אהבה', 14:'דוד', 26:'יהוה', 37:'factor-37', 74:'וחס',
    86:'אלהים', 111:'3×37', 148:'פסח', 153:'ΙΧΘΥΣ/בני האלהים',
    214:'רוח', 276:'עור', 318:'חנוך', 358:'משיח', 385:'שכינה',
    386:'ישוע', 400:'ת', 410:'שמע', 430:'שקל', 444:'מקדש',
    486:'סכות', 520:'Albam(יהוה)', 541:'ישראל', 611:'תורה',
    613:'mitzvot', 666:'Beast', 888:'Ἰησοῦς', 911:'ראשית',
    913:'בראשית', 1118:'Shema',
}


def strip_nikkud(w):
    return ''.join(c for c in w if unicodedata.category(c) not in ('Mn','Cf')
                   and c not in '־׃·\u05be\u05c3\u200f\u200e')


def gem(w):
    return hebrew_gematria(strip_nikkud(w))


def apply_cipher(word, mapping):
    s = strip_nikkud(word)
    out = []
    for ch in s:
        if ch in mapping:
            out.append(mapping[ch])
        elif ch.isalpha():
            return None  # unknown char
    return ''.join(out) if out else None


def cipher_gem(word, mapping):
    t = apply_cipher(word, mapping)
    return hebrew_gematria(t) if t else 0


def ordinal_sum(word):
    return sum(HEB_ORD.get(c, 0) for c in strip_nikkud(word))


def mk_sum(word):
    return sum(HEB_MK.get(c, 0) for c in strip_nikkud(word))


def digital_root(n):
    while n >= 10:
        n = sum(int(d) for d in str(n))
    return n


def main():
    # Load Delitzsch
    with open(WORK / 'delitzsch_verses.json') as f:
        deli = json.load(f)

    print(f'Loaded {len(deli)} Delitzsch verses', file=sys.stderr)

    # Tokenize all unique Hebrew words
    forms = {}
    verse_words = {}
    for ref, data in deli.items():
        words_raw = data.get('words_pointed', [])
        words_clean = []
        for w in words_raw:
            s = strip_nikkud(w)
            if not s or len(s) < 2:
                continue
            if s not in forms:
                g = gem(w)
                if g <= 0:
                    continue
                forms[s] = {
                    'pointed': w, 'gem': g, 'count': 0,
                    'atb_gem': cipher_gem(w, HEB_ATBASH),
                    'alb_gem': cipher_gem(w, HEB_ALBAM),
                    'avg_gem': cipher_gem(w, HEB_AVGAD),
                    'ravg_gem': cipher_gem(w, HEB_RAVGAD),
                    'ord': ordinal_sum(w),
                    'mk': mk_sum(w),
                    'dr': digital_root(mk_sum(w)),
                }
            forms[s]['count'] += 1
            words_clean.append(s)
        verse_words[ref] = words_clean

    print(f'{len(forms)} unique Hebrew word forms', file=sys.stderr)

    # ====== ATBASH targets ======
    print('\n=== HEBREW ATBASH-GEM ON TARGETS ===\n')
    for target, name in sorted(TARGETS.items()):
        hits = [(s, v) for s, v in forms.items() if v['atb_gem'] == target]
        if not hits: continue
        hits.sort(key=lambda x: -x[1]['count'])
        top = hits[:5]
        top_str = ', '.join(f"{v['pointed']}({v['gem']},×{v['count']})" for s,v in top)
        print(f"  Atbash={target:5} ({name:20}): {len(hits):3} → {top_str}")

    # ====== ALBAM targets ======
    print('\n=== HEBREW ALBAM-GEM ON TARGETS ===\n')
    for target, name in sorted(TARGETS.items()):
        hits = [(s, v) for s, v in forms.items() if v['alb_gem'] == target]
        if not hits: continue
        hits.sort(key=lambda x: -x[1]['count'])
        top = hits[:5]
        top_str = ', '.join(f"{v['pointed']}({v['gem']},×{v['count']})" for s,v in top)
        print(f"  Albam={target:5} ({name:20}): {len(hits):3} → {top_str}")

    # ====== AVGAD + REV-AVGAD targets ======
    for cipher_name, key in [('AVGAD', 'avg_gem'), ('REV-AVGAD', 'ravg_gem')]:
        print(f'\n=== HEBREW {cipher_name}-GEM ON TARGETS ===\n')
        for target, name in sorted(TARGETS.items()):
            hits = [(s, v) for s, v in forms.items() if v[key] == target]
            if not hits: continue
            hits.sort(key=lambda x: -x[1]['count'])
            top = hits[:5]
            top_str = ', '.join(f"{v['pointed']}({v['gem']},×{v['count']})" for s,v in top)
            print(f"  {cipher_name}={target:5} ({name:20}): {len(hits):3} → {top_str}")

    # ====== ORDINAL targets ======
    print('\n=== HEBREW ORDINAL ON BIBLICAL NUMBERS ===\n')
    ORD_TARGETS = {
        7:'completeness', 12:'tribes', 13:'אחד', 14:'דוד', 22:'Heb letters',
        26:'יהוה', 33:'age of Jesus', 37:'factor-37', 40:'testing',
        42:'3×14', 50:'Pentecost', 70:'nations', 77:'Lk gen', 84:'Fiul Omului',
    }
    by_ord = defaultdict(list)
    for s, v in forms.items():
        by_ord[v['ord']].append(s)

    for val, name in sorted(ORD_TARGETS.items()):
        hits = by_ord.get(val, [])
        if not hits: continue
        top = sorted(hits, key=lambda s: -forms[s]['count'])[:5]
        top_str = ', '.join(f"{forms[s]['pointed']}(×{forms[s]['count']})" for s in top)
        print(f"  ord={val:4} ({name:18}): {len(hits):3} → {top_str}")

    # ====== MISPAR KATAN ======
    print('\n=== HEBREW MISPAR KATAN (DIGITAL ROOT CLASSES) ===\n')
    by_dr = defaultdict(list)
    for s, v in forms.items():
        by_dr[v['dr']].append(s)
    for dr in range(1, 10):
        group = by_dr[dr]
        top = sorted(group, key=lambda s: -forms[s]['count'])[:6]
        total = sum(forms[s]['count'] for s in group)
        top_str = ', '.join(f"{forms[s]['pointed']}(×{forms[s]['count']})" for s in top)
        print(f"  DR={dr}: {len(group):4} forms, {total:5} tok → {top_str}")

    # ====== PALINDROMIC (gem = atbash_gem) ======
    print('\n=== HEBREW PALINDROMIC (gem = atbash_gem) ===\n')
    palindromic = [(s, v) for s, v in forms.items()
                   if v['gem'] == v['atb_gem'] and v['gem'] > 0 and v['count'] >= 2]
    palindromic.sort(key=lambda x: -x[1]['count'])
    print(f"  {len(palindromic)} palindromic forms (×≥2). Top 15:")
    for s, v in palindromic[:15]:
        print(f"    {v['pointed']:16}×{v['count']:<4} gem=atb={v['gem']:4}")

    # ====== NOTARIKON (first letters of consecutive words) ======
    print('\n=== HEBREW NOTARIKON (first letters) ===\n')

    def first_heb_letter(word):
        for ch in strip_nikkud(word):
            if ch in HEB_VALS:
                return ch
        return ''

    # Check key verses for meaningful acronyms
    key_refs = ['Matt.1.1', 'Matt.6.9', 'Matt.17.27', 'Matt.26.26', 'Matt.27.37',
                'John.1.1', 'John.1.14', 'John.3.16', 'John.8.58', 'John.19.19',
                'Mark.10.45', 'Luke.2.14', 'Rev.22.20']

    for ref in key_refs:
        if ref not in deli: continue
        words_raw = deli[ref].get('words_pointed', [])
        words = [w for w in words_raw if len(strip_nikkud(w)) >= 2]
        if len(words) < 3: continue
        fl = ''.join(first_heb_letter(w) for w in words)
        fl_gem = hebrew_gematria(fl) if fl else 0
        # Check if fl_gem hits a target
        note = ''
        if fl_gem in TARGETS:
            note = f' ← {TARGETS[fl_gem]}'
        for f in [37, 26, 13, 7]:
            if fl_gem > 0 and fl_gem % f == 0:
                note += f' [{fl_gem//f}×{f}]'
                break
        preview = deli[ref]['text'][:60]
        print(f"  {ref:14} fl={fl:12} gem={fl_gem:5}{note:20} {preview}")


if __name__ == '__main__':
    main()

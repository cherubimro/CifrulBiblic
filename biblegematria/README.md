# biblegematria

Cross-language gematria, isopsephy, and cipher analysis for biblical texts.

Software care acompaniază cartea [„Fiul Omului": de la Enoh și Daniel la Iisus Hristos — Teologia narativă descifrată](https://github.com/cherubimro/CifrulBiblic).

## Formă vs. Lemmă

Isopsefia clasică se calculează pe **forma exactă din manuscris** (nu pe lemma/forma de dicționar). Autorul antic a ales forma precisă tocmai pentru valoarea ei numerică:

| Forma (manuscris) | Isopsefie | Lemma (dicționar) | Isopsefie |
|---|---|---|---|
| **βαΐα** (pl. acuz.) | **14 = דוד (David)** | βάϊον | 133 |
| **λύσατε** (imp. aor.) | **936 = 36 × YHWH** | λύω | 830 |
| **σινδόνα** (acuz.) | **385 = שכינה** | σινδών | 1054 |

`biblegematria` folosește **forma din manuscris** pentru isopsefie (ce a codificat autorul) și **lemma** pentru traducere (ce găsim în dicționar). Textul SBLGNT/MorphGNT conține ambele.

NT local: **19,409 forme unice** → **5,461 lemme unice**. Traducere automată prin Strong's Concordance (1890, public domain): **88.6% acoperire** (restul sunt nume proprii).

## Features

- **23 Hebrew gematria methods** (via `hebrew` library): standard, gadol, katan, ordinal, atbash, albam, avgad, plenară, triunghiulară, pătratică, etc.
- **Greek isopsephy** (standard + archaic with digamma/koppa/sampi)
- **Substitution ciphers**: Atbash, Albam, Avgad, Atbach, Romanian Atbash (31 letters)
- **Cross-language scan**: Greek NT isopsephy ↔ Hebrew VT gematria (all 23 methods)
- **Combinatorial analysis**: cipher × 23 methods × cross-language (unique!)
- **Biblical text loaders**: SBLGNT (Greek NT), Masoretic Hebrew, LXX, Biblia Ortodoxă (română)
- **Lexicon**: Strong's Greek (5,512 lemme) + dicționar manual grec-român + ebraic-român

## Install

```bash
git clone https://github.com/cherubimro/CifrulBiblic.git
cd CifrulBiblic/biblegematria
pip install -e .
```

## Quick start

```python
from biblegematria import isopsephy, hebrew_gematria, cross_match
from biblegematria.ciphers import atbash_hebrew, atbash_romanian

# Greek isopsephy
isopsephy('Ἰησοῦς')  # 888

# Hebrew gematria (standard)
hebrew_gematria('דוד')  # 14

# All 23 methods
from biblegematria import all_hebrew_methods
all_hebrew_methods('יהוה')  # {'MISPAR_HECHRACHI': 26, 'ATBASH': 300, ...}

# Cross-language match
cross_match('δόξα', 'עניה')  # [('MISPAR_HECHRACHI', 135)] — glory = suffering!

# Atbash
atbash_hebrew('בגד')  # 'שרק' — garment = choice vine!
atbash_romanian('șpăgară')  # 'gjyșziy'

# Scan NT words against VT words (all 23 methods)
from biblegematria import cross_scan
results = cross_scan(
    {'Χριστός': 'Christ', 'δόξα': 'glory'},
    {'דוד': 'David', 'עניה': 'suffering'}
)
```

## Number index

Extract explicit numbers from biblical texts (153 fish, 318 servants, 666 beast, etc.):

```python
from biblegematria.numbers import build_number_index

idx = build_number_index(min_value=12)  # 281 distinct values

# Query: where does 153 appear?
idx[153]
# {'nt': [('Ioan 21:11', 'ἑκατὸν(100)+πεντήκοντα(50)+τριῶν(3)')],
#  'lxx': [], 'mas': []}

# Numbers in all three texts (NT + LXX + Masoretic)
all_three = {v: d for v, d in idx.items() if d['nt'] and d['lxx'] and d['mas']}
# → 22 numbers appear across all three corpora
```

## CLI Scripts

```bash
cd CifrulBiblic/biblegematria

# scan.py — NT ↔ VT cross-language scanner
python3 scan.py                                    # afișează usage + liste cărți
python3 scan.py --book 64-Jn --strict --top 50     # Ioan, filtrat, top 50
python3 scan.py --range 100-200 --book 64-Jn       # doar valori 100-200
python3 scan.py --single ATBASH --book 64-Jn       # doar metoda Atbash
python3 scan.py --single HECHRACHI --book 64-Jn    # doar standard (cel din carte)
python3 scan.py --numbers 100-200 --book 64-Jn     # doar valori = numere biblice, range
python3 scan.py --fullscan -j 8 -o full.tsv        # tot NT × tot VT

# numbers.py — index numere explicite (153, 666, 318 etc.)
python3 numbers.py                                 # sumar cu referințe + versete
python3 numbers.py --query 153                     # unde apare 153?
python3 numbers.py --significant                   # doar numere teologice
python3 numbers.py --all-three                     # numere în NT + LXX + Masoretic

# scan_lxx.py — LXX ↔ Masoretic parallel scanner
python3 scan_lxx.py --book Gen --strict --top 50   # Geneza
```

## v0.3.3 Features

- **Romanian stemmer** (PyStemmer) for verse word matching
- **RoWordNet synonyms** (2,351 words, 7,796 pairs) for better highlighting
- **--numbers** flag with range support (e.g., `--numbers 100-200`)
- **--range** filter by value (e.g., `--range 153-153`)
- **--single METHOD** — use only one method (e.g., `--single ATBASH`, `--single HECHRACHI`)
- **Deterministic output** — sorted results, same order on every run
- **ANSI colors** — green progress bar, yellow translations, magenta number refs
- **Lexicon 100%** — all 5,461 NT lemmas translated to Romanian

## License

CC0 1.0 Universal — Public Domain

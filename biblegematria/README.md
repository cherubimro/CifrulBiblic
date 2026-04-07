# biblegematria

Cross-language gematria, isopsephy, and cipher analysis for biblical texts.

Software care acompaniază cartea [„Fiul Omului": de la Enoh și Daniel la Iisus Hristos — Teologia narativă descifrată](https://github.com/cherubimro/CifrulBiblic).

## Install

```bash
git clone https://github.com/cherubimro/CifrulBiblic.git
cd CifrulBiblic/biblegematria
pip install -e .
```

## CLI Scripts

```bash
cd CifrulBiblic/biblegematria

# scan.py — NT ↔ VT cross-language scanner
python3 scan.py                                    # afișează usage + liste cărți
python3 scan.py --book 64-Jn --strict --top 50     # Ioan, filtrat, top 50
python3 scan.py --single HECHRACHI --book 64-Jn    # doar standard (cel din carte)
python3 scan.py --single ATBASH --book 64-Jn       # doar metoda Atbash
python3 scan.py --range 100-200 --book 64-Jn       # doar valori 100-200
python3 scan.py --numbers 100-200 --book 64-Jn     # doar valori = numere biblice, range
python3 scan.py --fullscan -j 8 -o full.tsv        # tot NT × tot VT

# numbers.py — index numere explicite (153, 666, 318 etc.)
python3 numbers.py                                 # sumar cu referințe + versete
python3 numbers.py --query 153                     # unde apare 153?
python3 numbers.py --query 666                     # unde apare 666?
python3 numbers.py --significant                   # doar numere teologice
python3 numbers.py --all-three                     # numere în NT + LXX + Masoretic

# scan_lxx.py — LXX ↔ Masoretic parallel scanner
python3 scan_lxx.py --book Gen --strict --top 50   # Geneza
```

## Formă vs. Lemmă

Isopsefia clasică se calculează pe **forma exactă din manuscris** (nu pe lemma/forma de dicționar):

| Forma (manuscris) | Isopsefie | Lemma (dicționar) | Isopsefie |
|---|---|---|---|
| **βαΐα** (pl. acuz.) | **14 = דוד (David)** | βάϊον | 133 |
| **λύσατε** (imp. aor.) | **936 = 36 × YHWH** | λύω | 830 |
| **σινδόνα** (acuz.) | **385 = שכינה** | σινδών | 1054 |

NT: **19,409 forme unice** → **5,461 lemme unice** (100% traduse în română).

## Features

- **23 Hebrew gematria methods** (via `hebrew` library)
- **Greek isopsephy** (standard + archaic)
- **Substitution ciphers**: Atbash, Albam, Avgad, Romanian Atbash (31 letters)
- **Cross-language scan**: Greek NT isopsephy ↔ Hebrew VT gematria (all 23 methods)
- **Number index**: 281 explicit biblical numbers across NT + LXX + Masoretic
- **Romanian stemmer** (PyStemmer) + **RoWordNet synonyms** for verse highlighting
- **Biblical texts**: SBLGNT (27 books), Masoretic (39 books), LXX Rahlfs 1935 (59 books), Biblia Ortodoxă
- **Lexicon**: 5,461 lemme grec→română + 2,351 cuvinte cu sinonime

## Python library

```python
from biblegematria import isopsephy, hebrew_gematria, cross_match, all_hebrew_methods
from biblegematria.ciphers import atbash_hebrew, atbash_romanian

isopsephy('Ἰησοῦς')                    # 888
hebrew_gematria('דוד')                  # 14
all_hebrew_methods('יהוה')              # {'MISPAR_HECHRACHI': 26, 'ATBASH': 300, ...}

cross_match('δόξα', 'עניה')             # [('MISPAR_HECHRACHI', 135)] — glory = suffering!

atbash_hebrew('בגד')                    # 'שרק' — garment = choice vine!
atbash_hebrew('פסח')                    # 'וחס' — Passover = spared!
atbash_romanian('șpăgară')              # 'gjyșziy'

from biblegematria.numbers import build_number_index
idx = build_number_index(min_value=12)
idx[153]    # {'nt': [('Ioan 21:11', ...)], 'lxx': [], 'mas': []}
idx[666]    # {'nt': [('Apocalipsa 13:18', ...)], 'lxx': [...], 'mas': []}
```

## License

CC0 1.0 Universal — Public Domain

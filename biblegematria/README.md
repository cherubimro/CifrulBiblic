# biblegematria

Cross-language gematria, isopsephy, and cipher analysis for biblical texts.

## Features

- **23 Hebrew gematria methods** (via `hebrew` library): standard, gadol, katan, ordinal, atbash, albam, avgad, plenară, triunghiulară, pătratică, etc.
- **Greek isopsephy** (standard + archaic with digamma/koppa/sampi)
- **Substitution ciphers**: Atbash, Albam, Avgad, Atbach, Romanian Atbash (31 letters)
- **Cross-language scan**: Greek NT isopsephy ↔ Hebrew VT gematria (all 23 methods)
- **Biblical text loaders**: SBLGNT (Greek NT), Masoretic Hebrew, LXX

## Install

```bash
pip install biblegematria
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

## License

CC0 1.0 Universal — Public Domain

# biblegematria — User Manual

## 1. Installation

```bash
git clone https://github.com/cherubimro/CifrulBiblic.git
cd CifrulBiblic/biblegematria
pip install -e .
```

Dependencies: `hebrew>=0.8.0` (installed automatically).

## 2. Formă vs. Lemmă — principiu fundamental

Isopsefia clasică se calculează pe **forma exactă din manuscris**, nu pe lemma (forma de dicționar). Autorul antic a ales forma precisă tocmai pentru valoarea ei numerică.

**Exemplu**: în Ioan 12:13, autorul scrie **βαΐα** (plural acuzativ al lui βάϊον):

| | Formă (manuscris) | Lemmă (dicționar) |
|---|---|---|
| Cuvânt | **βαΐα** | βάϊον |
| Isopsefie | β(2)+α(1)+ι(10)+α(1) = **14** | β(2)+α(1)+ι(10)+ο(70)+ν(50) = **133** |
| Semnificație | **14 = דוד (David)** — mulțimea strigă „Fiului lui David!" | Fără conexiune |

Dacă am calcula pe lemmă, am pierde exact ce a codificat autorul.

`biblegematria` folosește:
- **Forma din manuscris** → pentru isopsefie (ce a codificat autorul)
- **Lemma** → pentru traducere (ce găsim în dicționar/Strong's)

Textul SBLGNT/MorphGNT conține ambele:
```
041213 N- ----APN- βαΐα βαΐα βαΐα βάϊον
                   │              └── lemma (forma de dicționar)
                   └── forma din manuscris (pentru isopsefie)
```

NT local: **19,409 forme unice** → **5,461 lemme unice** → **5,512 intrări Strong's** (88.6% acoperire; restul sunt nume proprii).

## 3. Biblical texts

The package includes a bundled `data.zip` (3.6 MB) containing:
- **SBLGNT** — Greek New Testament (27 books, morphologically tagged)
- **Masoretic** — Hebrew Old Testament (39 books)
- **LXX** — Septuagint (Greek Old Testament)

On first use, texts are automatically extracted to `~/.biblegematria/`.
If `data.zip` is missing, the package downloads texts from GitHub/Sefaria.

### Check status

```python
from biblegematria import status
print(status())
# {'sblgnt': {'path': '/home/user/.biblegematria/sblgnt', 'books': 27},
#  'masoretic': {'path': '/home/user/.biblegematria/textul_masoretic', 'books': 39}}
```

## 4. Greek isopsephy

Calculate the numerical value of Greek words using the classical isopsephy system (α=1, β=2, ... ω=800).

```python
from biblegematria import isopsephy

isopsephy('Ἰησοῦς')      # 888 — Jesus
isopsephy('Χριστός')      # 880 — Christ
isopsephy('δόξα')          # 135 — glory
isopsephy('βαΐα')          # 14  — palm branches = David!
isopsephy('λύσατε')        # 936 = 36 × 26 (YHWH)
```

Handles uppercase, accents, breathing marks, and diacritics automatically.

### Letter-by-letter breakdown

```python
from biblegematria.gematria import isopsephy_detail

isopsephy_detail('δόξα')
# [('δ', 4), ('ό', 70), ('ξ', 60), ('α', 1)]
```

### Theological factorization

```python
from biblegematria.gematria import factorize_theological

factorize_theological(936)
# {'YHWH': 36, '12': 78, '3': 312}
# → 936 = 36 × YHWH
```

## 5. Hebrew gematria — 23 methods

All 23 methods from the `hebrew` library are available:

```python
from biblegematria import hebrew_gematria, all_hebrew_methods
from hebrew import GematriaTypes

# Standard gematria
hebrew_gematria('דוד')                                    # 14 — David
hebrew_gematria('יהוה')                                   # 26 — YHWH
hebrew_gematria('ישוע')                                   # 386 — Yeshua/Jesus

# Specific method
hebrew_gematria('דוד', GematriaTypes.ATBASH)              # 280 = mânz (עיר)!
hebrew_gematria('דוד', GematriaTypes.MISPAR_SHEMI_MILUI)  # 880 = Χριστός!

# All 23 methods at once
results = all_hebrew_methods('יהוה')
for method, value in results.items():
    print(f"  {method}: {value}")
```

### Available methods

| Method | Hebrew name | Description |
|--------|-------------|-------------|
| MISPAR_HECHRACHI | מספר הכרחי | Standard: א=1, ב=2 ... ת=400 |
| MISPAR_GADOL | מספר גדול | Large: final letters ך=500, ם=600, ן=700, ף=800, ץ=900 |
| MISPAR_KATAN | מספר קטן | Small/reduced: ignore zeros, single digit |
| MISPAR_SIDURI | מספר סידורי | Ordinal: position in alphabet (1-22) |
| MISPAR_PERATI | מספר פרטי | Squared: each letter = square of standard value |
| MISPAR_SHEMI_MILUI | מספר שמי | Plenary: spell out letter names, sum values |
| MISPAR_BONEEH | מספר בונה | Cumulative: running sum |
| MISPAR_KIDMI | מספר קדמי | Triangular: T(ordinal position) |
| MISPAR_MESHULASH | מספר משולש | Cubed: each letter = cube of standard value |
| MISPAR_MUSAFI | מספר מוספי | Standard + number of letters |
| MISPAR_KOLEL | מספר כולל | Standard + 1 |
| MISPAR_HAACHOR | מספר האחור | Reverse ordinal: ת=1, ש=2 ... א=22 |
| MISPAR_MISPARI | מספר מספרי | Spelled-out numbers summed |
| MISPAR_KATAN_MISPARI | | Reduced of MISPARI |
| MISPAR_HAMERUBAH_HAKLALI | | Square of standard total |
| MISPAR_NEELAM | מספר נעלם | Hidden: letter name minus the letter itself |
| ATBASH | אתב"ש | Atbash substitution value |
| ALBAM | אלב"ם | Albam substitution value |
| AVGAD | אבג"ד | Avgad (Caesar +1) value |
| REVERSE_AVGAD | | Reverse Avgad (Caesar -1) value |
| AYAK_BACHAR | אי"ק בכ"ר | Units/tens/hundreds equivalence |
| OFANIM | אופנים | Letter name spelled in full, recursively |
| ACHAS_BETA | אכ"ס בט"ע | Group substitution |

## 6. Substitution ciphers

### Atbash (Hebrew)

First letter ↔ last letter: א↔ת, ב↔ש, ג↔ר, ... Used by Jeremiah (25:26, 51:1).

```python
from biblegematria.ciphers import atbash_hebrew, atbash_detail

atbash_hebrew('בגד')    # 'שרק' — garment → choice vine!
atbash_hebrew('פסח')    # 'וחס' — Passover → "and he spared"!
atbash_hebrew('מת')     # 'יא'  — dead → 11 (John 11!)
atbash_hebrew('בבל')    # 'ששך' — Babylon → Sheshak (Jeremiah's cipher)

# Step-by-step breakdown
atbash_detail('בגד')
# [('ב', 2, 'ש', 21), ('ג', 3, 'ר', 20), ('ד', 4, 'ק', 19)]
```

### Albam (Hebrew)

First half ↔ second half: א↔ל, ב↔מ, ג↔נ, ...

```python
from biblegematria.ciphers import albam

albam('אלעזר')  # Elazar through Albam
```

### Avgad (Hebrew)

Caesar cipher +1: א→ב, ב→ג, ג→ד, ...

```python
from biblegematria.ciphers import avgad

avgad('דוד')  # David +1
```

### Atbash (Romanian)

31-letter Romanian alphabet, center at 'm':

```python
from biblegematria.ciphers import atbash_romanian

atbash_romanian('alin.anton')  # 'znrl.zlfkl'
atbash_romanian('upt.ro')     # 'djf.ik'
atbash_romanian('șpăgară')    # 'gjyșziy'
```

## 7. Cross-language matching (NT ↔ VT)

The unique feature: match Greek NT isopsephy against Hebrew VT gematria using all 23 methods.

### Single pair

```python
from biblegematria import cross_match

cross_match('δόξα', 'עניה')
# [('MISPAR_HECHRACHI', 135), ('MISPAR_GADOL', 135)]
# → glory (Greek) = suffering (Hebrew)!

cross_match('Χριστός', 'דוד')
# [('MISPAR_SHEMI_MILUI', 880)]
# → Christ = David (plenary gematria)!

cross_match('βαΐα', 'דוד')
# [('MISPAR_HECHRACHI', 14), ('MISPAR_GADOL', 14),
#  ('MISPAR_SIDURI', 14), ('MISPAR_KATAN', 14)]
# → palm branches = David (4 methods!)
```

### Bulk scan

```python
from biblegematria import cross_scan

greek_words = {
    'Χριστός': 'Christ', 'δόξα': 'glory', 'βαΐα': 'palms',
    'Ἰησοῦς': 'Jesus', 'λύσατε': 'unbind', 'ἀγάπη': 'love',
}
hebrew_words = {
    'דוד': 'David', 'יהוה': 'YHWH', 'עניה': 'suffering',
    'משיח': 'Messiah', 'שלום': 'peace', 'אלעזר': 'Eleazar',
}

results = cross_scan(greek_words, hebrew_words)
for gw, gm, val, hw, hm, method in results:
    print(f"  {gw} ({gm}) = {val} = {hw} ({hm}) [{method}]")
```

## 8. Combinatorial analysis (cipher × method × cross-language)

The most powerful feature: apply ciphers first, then match across languages.

### Cipher → known word

```python
from biblegematria import cipher_word_match

words = {
    'בגד': 'garment', 'שרק': 'choice vine', 'פסח': 'Passover',
    'בבל': 'Babylon', 'ששך': 'Sheshak', 'מת': 'dead', 'חי': 'alive',
}

matches = cipher_word_match(words)
for word, meaning, cipher, result, result_meaning in matches:
    print(f"  {word} ({meaning}) → {cipher} → {result} ({result_meaning})")
# בגד (garment) → ATBASH → שרק (choice vine)
# שרק (choice vine) → ATBASH → בגד (garment)
# ששך (Sheshak) → ATBASH → בבל (Babylon)
```

### Cipher → gematria → cross-language

```python
from biblegematria import cipher_cross_language

hebrew = {'דוד': 'David', 'עניה': 'suffering', 'כבוד': 'glory'}
greek = {'δόξα': 'glory', 'βαΐα': 'palms'}

results = cipher_cross_language(hebrew, greek)
for r in results:
    print(f"  {r['hebrew']}({r['hebrew_meaning']}) "
          f"→{r['cipher']}→ {r['cipher_result']} "
          f"[{r['method']}={r['value']}] = {r['greek']}({r['greek_meaning']})")
```

### Full combinatorial scan

```python
from biblegematria import full_combo_scan

full = full_combo_scan(hebrew_words, greek_words)
print(f"Direct matches: {len(full['direct'])}")
print(f"Cipher word matches: {len(full['cipher_words'])}")
print(f"Cipher cross-language: {len(full['cipher_cross'])}")
```

## 9. Loading biblical texts

### Greek NT (SBLGNT)

```python
from biblegematria import load_sblgnt, isopsephy

# Load specific verse
words = load_sblgnt(book='64-Jn', chapter=11, verse=25)
for w in words:
    print(f"  {w['word']} ({w['lemma']}) = {isopsephy(w['word'])}")

# Load entire book
mark = load_sblgnt(book='62-Mk')

# Book codes: 61-Mt, 62-Mk, 63-Lk, 64-Jn, 65-Ac, 66-Ro, ...
```

### Hebrew VT (Masoretic)

```python
from biblegematria import load_masoretic, hebrew_gematria

# Load specific book
genesis = load_masoretic(book='Genesis')
for v in genesis:
    if v['chapter'] == 1 and v['verse'] == 1:
        print(f"  {v['text']}")
        for w in v['words']:
            print(f"    {w} = {hebrew_gematria(w)}")

# Available: Genesis, Exodus, Leviticus, Numbers, Deuteronomy,
# Joshua, Judges, I_Samuel, II_Samuel, I_Kings, II_Kings,
# Isaiah, Jeremiah, Ezekiel, Psalms, Proverbs, Job, etc.
```

### Septuagint (LXX)

```python
from biblegematria import load_lxx

# Load specific book
gen_lxx = load_lxx(book='Gen')
for entry in gen_lxx[:10]:
    print(f"  {entry['ref']}: {entry['word']} ({entry['lemma']})")
```

## 10. Example: complete analysis of a passage

```python
from biblegematria import (
    load_sblgnt, isopsephy, hebrew_gematria, all_hebrew_methods,
    cross_match, full_combo_scan
)
from biblegematria.ciphers import atbash_hebrew
from biblegematria.gematria import factorize_theological

# 1. Load John 11:43 — "Lazarus, come forth!"
verse = load_sblgnt(book='64-Jn', chapter=11, verse=43)
print("Ioan 11:43:")
for w in verse:
    val = isopsephy(w['word'])
    factors = factorize_theological(val)
    fstr = f" = {factors}" if factors else ""
    print(f"  {w['word']:20s} iso={val:5d}{fstr}")

# 2. Cross-language on key words
print("\nCross-language:")
print(cross_match('δόξα', 'עניה'))        # glory = suffering
print(cross_match('Χριστός', 'דוד'))      # Christ = David

# 3. Atbash discoveries
print("\nAtbash:")
print(f"  בגד → {atbash_hebrew('בגד')}")   # garment → vine
print(f"  פסח → {atbash_hebrew('פסח')}")   # Passover → spared
print(f"  מת → {atbash_hebrew('מת')}")     # dead → 11

# 4. Full combo scan
greek = {'δόξα': 'glory', 'βαΐα': 'palms', 'Χριστός': 'Christ'}
hebrew = {'דוד': 'David', 'עניה': 'suffering', 'משיח': 'Messiah'}
full = full_combo_scan(hebrew, greek)
print(f"\nFull scan: {len(full['direct'])} direct, "
      f"{len(full['cipher_words'])} cipher-words, "
      f"{len(full['cipher_cross'])} cipher-cross")
```

## 11. Number index — explicit numbers in biblical texts

Ancient texts write numbers as words: ἑκατὸν πεντήκοντα τρεῖς = 153. The `numbers` module parses these composite numbers and builds an index across NT, LXX, and Masoretic.

### Build the index

```python
from biblegematria.numbers import build_number_index

idx = build_number_index(min_value=12)
# → 281 distinct values across all three corpora
```

### Query a number

```python
idx[153]
# {'nt': [('Ioan 21:11', 'ἑκατὸν(100)+πεντήκοντα(50)+τριῶν(3)')],
#  'lxx': [],
#  'mas': []}

idx[666]
# {'nt': [('Apocalipsa 13:18', 'ἑξακόσιοι(600)+ἑξήκοντα(60)+ἕξ(6)')],
#  'lxx': [('1Kgs 10:14', ...), ('2Chr 9:13', ...), ('2Esd 2:13', ...)],
#  'mas': []}

idx[318]
# {'nt': [],
#  'lxx': [('Gen 14:14', 'τριακοσίους(300)+δέκα(10)+ὀκτώ(8)')],
#  'mas': []}  # = gematria of אליעזר (Eliezer)!
```

### Extract per corpus

```python
from biblegematria.numbers import extract_nt_numbers, extract_lxx_numbers, extract_masoretic_numbers

nt = extract_nt_numbers(min_value=100)    # NT only
lxx = extract_lxx_numbers(min_value=100)  # LXX only
mas = extract_masoretic_numbers(min_value=100)  # Masoretic only
# Each returns: [(value, ref, components_str), ...]
```

### Find numbers shared across all three texts

```python
all_three = {v: d for v, d in idx.items() if d['nt'] and d['lxx'] and d['mas']}
# → 22 numbers appear in NT + LXX + Masoretic:
#   12 (tribes/apostles), 14 (David), 40 (testing), 70 (elders/nations),
#   120 (Moses' age), 1000 (millennium), etc.
```

### Use with gematria/isopsephy matching

If a word has isopsephy = 153, and 153 appears as an explicit number in John 21:11, that's a direct connection:

```python
from biblegematria import isopsephy
from biblegematria.numbers import build_number_index

val = isopsephy('ἰχθύες')  # "fish" — check value
if val in build_number_index():
    print(f"ἰχθύες = {val} appears as explicit number!")
```

## 12. CLI Scripts

### scan.py — NT ↔ VT cross-language scanner

```bash
python3 scan.py                                    # usage + liste cărți NT/VT
python3 scan.py --book 64-Jn --strict --top 50     # Ioan, strict, top 50
python3 scan.py --book 62-Mk --hebrew-book Isaiah  # Marcu × Isaia
python3 scan.py --range 100-200 --book 64-Jn       # doar valori 100-200
python3 scan.py --range 153-153 --book 64-Jn       # doar valoarea 153
python3 scan.py --single HECHRACHI --book 64-Jn    # doar standard (cel din carte.tex)
python3 scan.py --single ATBASH --book 64-Jn       # doar Atbash
python3 scan.py --single GADOL --book 62-Mk        # doar Gadol
python3 scan.py --numbers --book 64-Jn --strict    # doar valori = numere biblice
python3 scan.py --numbers 100-200 --book 64-Jn     # numere biblice, range 100-200
python3 scan.py --fullscan -j 8 -o full.tsv        # tot, 8 workeri, salvat
python3 scan.py --strict -j 8 -o rezultate.tsv     # tot NT × tot VT, strict

# Notă: --range și --numbers nu se pot combina (eroare dacă se încearcă)
```

### numbers.py — index numere explicite

```bash
python3 numbers.py                                 # sumar cu referințe + versete românești
python3 numbers.py --query 153                     # unde apare 153?
python3 numbers.py --query 666                     # unde apare 666?
python3 numbers.py --significant                   # doar numere teologice semnificative
python3 numbers.py --all-three                     # numere comune NT + LXX + Masoretic
python3 numbers.py --corpus nt --min 100           # doar NT, ≥100
python3 numbers.py --no-index                      # nu suprascrie numbers.txt
```

### scan_lxx.py — LXX ↔ Masoretic parallel scanner

```bash
python3 scan_lxx.py --book Gen --strict --top 50   # Geneza
python3 scan_lxx.py --strict -j 4 -o lxx.tsv       # tot LXX
```

## 13. Limitări cunoscute

### Evidențierea cuvântului românesc (~70-80% acuratețe)

Scanul evidențiază cuvântul românesc corespunzător din versetul Bibliei Ortodoxe folosind:
- **PyStemmer** (stemmer Snowball românesc) — reduce cuvintele la rădăcină
- **RoWordNet** (2,351 cuvinte, 7,796 perechi sinonime) — extinde căutarea cu sinonime

Funcționează bine când traducerea e directă sau prin sinonim:
- κρίσιν → „judecată" → stem „judec" → găsește „**judecata**" ✓
- ἤγαγεν → „a aduce" → stem „adu" → găsește „**adus**" ✓
- ἔλεγεν → „a zice" → sinonim „vorbi" → stem „vorb" → găsește „**vorbea**" ✓

Eșuează când Biblia Ortodoxă traduce liber:
- λαμβάνετε (a lua) → versetul zice „ceea ce știm grăim" ✗
- ἐάν (dacă) → versetul reformulează complet fără „dacă" ✗

Cauza: Biblia Ortodoxă este o traducere **literară** (nu interlineară). Această limitare nu poate fi rezolvată cu dicționar sau sinonime — necesită un NT interliniar grec-român digital.

Soluția ar necesita un NT interliniar grec-român digital (aliniere cuvânt-cu-cuvânt), care nu există în format liber.

## 13. License

CC0 1.0 Universal — Public Domain Dedication.

Biblical texts: SBLGNT (MorphGNT, public domain), Masoretic (Sefaria, CC-BY-NC),
LXX (OpenScriptures).

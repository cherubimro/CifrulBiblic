"""Biblical and Romanian substitution ciphers."""

# Hebrew alphabet (22 letters)
_HEB = 'אבגדהוזחטיכלמנסעפצקרשת'
_HEB_FINAL = {'ך': 'כ', 'ם': 'מ', 'ן': 'נ', 'ף': 'פ', 'ץ': 'צ'}

# Atbash mapping (first↔last)
_ATBASH_HEB = {}
for i in range(len(_HEB)):
    _ATBASH_HEB[_HEB[i]] = _HEB[len(_HEB) - 1 - i]
# Add final forms
for final, normal in _HEB_FINAL.items():
    if normal in _ATBASH_HEB:
        _ATBASH_HEB[final] = _ATBASH_HEB[normal]

# Albam mapping (first half↔second half)
_ALBAM_HEB = {}
half = len(_HEB) // 2  # 11
for i in range(half):
    _ALBAM_HEB[_HEB[i]] = _HEB[i + half]
    _ALBAM_HEB[_HEB[i + half]] = _HEB[i]

# Avgad mapping (shift +1, Caesar cipher)
_AVGAD_HEB = {}
for i in range(len(_HEB)):
    _AVGAD_HEB[_HEB[i]] = _HEB[(i + 1) % len(_HEB)]

# Romanian alphabet (31 letters)
_RO = 'aăâbcdefghiîjklmnopqrsștțuvwxyz'
_ATBASH_RO = {}
for i in range(len(_RO)):
    _ATBASH_RO[_RO[i]] = _RO[len(_RO) - 1 - i]
    _ATBASH_RO[_RO[i].upper()] = _RO[len(_RO) - 1 - i].upper()


def atbash_hebrew(word: str) -> str:
    """Apply Atbash cipher to a Hebrew word."""
    return ''.join(_ATBASH_HEB.get(c, c) for c in word)


def albam(word: str) -> str:
    """Apply Albam cipher to a Hebrew word."""
    return ''.join(_ALBAM_HEB.get(c, c) for c in word)


def avgad(word: str) -> str:
    """Apply Avgad cipher (Caesar +1) to a Hebrew word."""
    return ''.join(_AVGAD_HEB.get(c, c) for c in word)


def atbash_romanian(word: str) -> str:
    """Apply Atbash cipher using Romanian 31-letter alphabet."""
    return ''.join(_ATBASH_RO.get(c, c) for c in word)


def atbash_detail(word: str) -> list:
    """Return letter-by-letter Atbash breakdown for Hebrew."""
    result = []
    for c in word:
        if c in _ATBASH_HEB:
            pos = _HEB.index(c) + 1 if c in _HEB else '?'
            target = _ATBASH_HEB[c]
            tpos = _HEB.index(target) + 1 if target in _HEB else '?'
            result.append((c, pos, target, tpos))
    return result

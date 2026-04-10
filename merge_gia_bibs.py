#!/usr/bin/env python3
"""
Merge gia/missing.bib and gia/bibliography.bib into carte.bib.
Deduplicate by DOI (if present), then by (lowercased) title + first author surname.
Preserve existing carte.bib entries unchanged; append new ones at the end.
"""

import re
import sys
import unicodedata

CARTE_BIB = '/home/bu/Documents/Biblia/carte.bib'
GIA_FILES = [
    '/home/bu/Documents/Biblia/gia/bibliography.bib',
    '/home/bu/Documents/Biblia/gia/missing.bib',
]


def parse_bib(path):
    """Parse a BibTeX file into a list of entries."""
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    entries = []
    # Find all @type{key,...} blocks
    # Strategy: scan for @type{, then match balanced braces.
    i = 0
    while i < len(content):
        m = re.search(r'@(\w+)\s*\{', content[i:])
        if not m:
            break
        etype = m.group(1).lower()
        if etype in ('comment', 'preamble', 'string'):
            # skip
            i += m.end()
            continue

        start = i + m.end()
        # Find matching closing brace
        depth = 1
        j = start
        while j < len(content) and depth > 0:
            if content[j] == '{':
                depth += 1
            elif content[j] == '}':
                depth -= 1
            j += 1
        if depth != 0:
            print(f"Unbalanced braces at position {i} in {path}", file=sys.stderr)
            break

        body = content[start:j - 1]
        entry_text = content[i + m.start():j]

        # Extract key
        key_match = re.match(r'\s*([^,\s]+)\s*,', body)
        if not key_match:
            i = j
            continue
        key = key_match.group(1).strip()

        entries.append({
            'type': etype,
            'key': key,
            'body': body,
            'text': entry_text,
            'position': i + m.start(),
        })
        i = j
    return entries


def get_field(body, name):
    m = re.search(
        rf'\b{name}\s*=\s*[{{"]((?:[^{{}}]|\{{[^{{}}]*\}})*)[}}"]',
        body, re.IGNORECASE | re.DOTALL)
    if m:
        val = m.group(1).strip()
        val = re.sub(r'\s+', ' ', val)
        return val
    return None


def normalize_title(title):
    if not title:
        return ''
    t = title.lower()
    # Strip LaTeX braces and common escapes
    t = re.sub(r'[{}]', '', t)
    t = re.sub(r'\\[a-zA-Z]+', '', t)
    # Keep only alphanumerics
    t = unicodedata.normalize('NFKD', t)
    t = ''.join(c for c in t if c.isalnum())
    return t


def normalize_author_surname(author):
    if not author:
        return ''
    # Take first author
    first = author.split(' and ')[0]
    if ',' in first:
        surname = first.split(',')[0]
    else:
        parts = first.strip().split()
        surname = parts[-1] if parts else ''
    surname = re.sub(r'[{}]', '', surname)
    surname = unicodedata.normalize('NFKD', surname)
    surname = ''.join(c for c in surname.lower() if c.isalnum())
    return surname


def entry_fingerprint(entry):
    body = entry['body']
    doi = get_field(body, 'doi')
    if doi:
        return ('doi', doi.lower().strip())
    title = get_field(body, 'title')
    author = get_field(body, 'author')
    return ('title_author',
            normalize_title(title),
            normalize_author_surname(author))


def main():
    # Load carte.bib
    carte_entries = parse_bib(CARTE_BIB)
    print(f"carte.bib: {len(carte_entries)} entries", file=sys.stderr)

    # Build set of existing fingerprints
    existing = {}
    for e in carte_entries:
        fp = entry_fingerprint(e)
        existing[fp] = e['key']

    # Also index by existing keys to avoid key collisions
    existing_keys = {e['key'] for e in carte_entries}

    # Load gia bib files
    new_entries = []
    for path in GIA_FILES:
        entries = parse_bib(path)
        print(f"{path}: {len(entries)} entries", file=sys.stderr)
        for e in entries:
            fp = entry_fingerprint(e)
            if fp in existing:
                continue
            # Also dedupe against already-added new entries
            existing[fp] = e['key']
            # Handle key collision
            new_key = e['key']
            counter = 2
            while new_key in existing_keys:
                new_key = f"{e['key']}_{counter}"
                counter += 1
            existing_keys.add(new_key)
            if new_key != e['key']:
                # Replace the key in the text
                e['text'] = re.sub(
                    r'@(\w+)\s*\{\s*' + re.escape(e['key']),
                    f"@{e['type']}{{{new_key}",
                    e['text'], count=1)
                e['key'] = new_key
            new_entries.append(e)

    print(f"New unique entries to add: {len(new_entries)}", file=sys.stderr)

    if not new_entries:
        print("Nothing to merge.", file=sys.stderr)
        return

    # Append new entries to carte.bib
    with open(CARTE_BIB, 'r', encoding='utf-8') as f:
        content = f.read()

    # Ensure trailing newline
    if not content.endswith('\n'):
        content += '\n'

    addition = ('\n'
                '% ========================================\n'
                '% MERGED FROM gia/ — academic papers on\n'
                '% biblical gematria, isopsephy, and atbash\n'
                '% ========================================\n\n')
    addition += '\n\n'.join(e['text'] for e in new_entries) + '\n'

    with open(CARTE_BIB, 'w', encoding='utf-8') as f:
        f.write(content + addition)

    print(f"Appended {len(new_entries)} entries to {CARTE_BIB}", file=sys.stderr)


if __name__ == '__main__':
    main()

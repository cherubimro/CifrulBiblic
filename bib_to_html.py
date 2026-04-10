#!/usr/bin/env python3
"""
Extract all entries from carte.bib and generate HTML bibliography.
Replaces the Bibliografie section in carte.html with auto-generated content.
"""

import re
import sys

BIB_FILE = '/home/bu/Documents/Biblia/carte.bib'
HTML_FILE = '/home/bu/Documents/Biblia/carte.html'


def parse_bib(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    entries = []
    # Split on @type{key,
    pattern = re.compile(r'@(\w+)\{(\w+),', re.MULTILINE)
    positions = [(m.start(), m.group(1), m.group(2)) for m in pattern.finditer(content)]

    for i, (pos, etype, key) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(content)
        body = content[pos:end]

        # Extract fields
        def get_field(name):
            m = re.search(
                rf'{name}\s*=\s*\{{((?:[^{{}}]|\{{[^{{}}]*\}})*)\}}',
                body, re.IGNORECASE | re.DOTALL)
            if m:
                value = m.group(1).strip()
                # Clean LaTeX commands minimally
                value = re.sub(r'\\textit\{([^}]*)\}', r'\1', value)
                value = re.sub(r'\\textbf\{([^}]*)\}', r'\1', value)
                value = re.sub(r'\\emph\{([^}]*)\}', r'\1', value)
                value = value.replace('\\&', '&amp;')
                value = value.replace('\\$', '$')
                value = value.replace('\\%', '%')
                value = value.replace('~', ' ')
                # LaTeX dashes → Unicode
                value = value.replace('---', '—')
                value = value.replace('--', '–')
                value = value.replace("``", '"').replace("''", '"')
                value = value.replace('\\_', '_')
                value = value.replace("\\'e", 'é').replace("\\'a", 'á')
                value = value.replace("\\\"o", 'ö').replace("\\\"u", 'ü')
                value = re.sub(r'\s+', ' ', value)
                return value
            return None

        entries.append({
            'type': etype,
            'key': key,
            'author': get_field('author'),
            'title': get_field('title'),
            'year': get_field('year'),
            'journal': get_field('journal'),
            'booktitle': get_field('booktitle'),
            'publisher': get_field('publisher'),
            'address': get_field('address'),
            'volume': get_field('volume'),
            'number': get_field('number'),
            'pages': get_field('pages'),
            'series': get_field('series'),
            'edition': get_field('edition'),
            'doi': get_field('doi'),
            'url': get_field('url'),
            'isbn': get_field('isbn'),
            'note': get_field('note'),
        })
    return entries


def format_author_for_sort(author):
    if not author:
        return 'zzz'
    # Take first author's last name
    first = author.split(' and ')[0]
    if ',' in first:
        return first.split(',')[0].strip().lower()
    # Otherwise take last word
    words = first.strip().split()
    return words[-1].lower() if words else 'zzz'


def format_entry_html(e):
    parts = []

    # Author
    if e['author']:
        parts.append(f"<strong>{e['author']}</strong>")

    # Year
    if e['year']:
        parts.append(f"({e['year']})")

    # Title — article in « », book in <em>
    if e['title']:
        if e['type'] == 'article':
            parts.append(f"«{e['title']}»")
        else:
            parts.append(f"<em>{e['title']}</em>")

    # Journal / Booktitle
    if e['journal']:
        j = f"<em>{e['journal']}</em>"
        vol_parts = []
        if e['volume']:
            vol_parts.append(e['volume'])
        if e['number']:
            vol_parts.append(f"({e['number']})")
        if vol_parts:
            j += ' ' + ''.join(vol_parts)
        if e['pages']:
            j += f": {e['pages']}"
        parts.append(j)
    elif e['booktitle']:
        parts.append(f"în <em>{e['booktitle']}</em>")

    # Series
    if e['series']:
        s = e['series']
        if e['volume'] and not e['journal']:
            s += f" {e['volume']}"
        parts.append(s)

    # Edition
    if e['edition']:
        parts.append(f"Ed. {e['edition']}")

    # Publisher + address
    if e['publisher']:
        pub = e['publisher']
        if e['address']:
            pub += f", {e['address']}"
        parts.append(pub)

    # ISBN
    if e['isbn']:
        parts.append(f"ISBN {e['isbn']}")

    # DOI
    if e['doi']:
        doi_link = (f'DOI: <a href="https://doi.org/{e["doi"]}" '
                    f'target="_blank" rel="noopener">{e["doi"]}</a>')
        parts.append(doi_link)

    # URL (if no DOI)
    elif e['url']:
        parts.append(f'<a href="{e["url"]}" target="_blank" rel="noopener">'
                     f'{e["url"]}</a>')

    # Note
    if e['note']:
        parts.append(e['note'])

    return '. '.join(parts) + '.'


def main():
    entries = parse_bib(BIB_FILE)
    print(f"Parsed {len(entries)} entries from {BIB_FILE}", file=sys.stderr)

    # Sort by author then year
    entries.sort(key=lambda e: (format_author_for_sort(e['author']),
                                e['year'] or '0000'))

    # Generate HTML
    html_lines = []
    html_lines.append(
        '<h2 id="bibliografie" style="color:#8B0000; margin-top:30px;">'
        'Bibliografie</h2>')
    html_lines.append(
        '<p style="font-size:0.85em; color:#666;">Auto-generată din '
        '<code>carte.bib</code> (biblatex). Conține toate cele '
        f'{len(entries)} intrări folosite în carte.</p>')
    html_lines.append('<ol style="font-size:0.85em; line-height:1.6;">')

    for e in entries:
        html_lines.append(
            f'<li style="margin-bottom:6px;">{format_entry_html(e)}</li>')

    html_lines.append('</ol>')

    with open('/home/bu/Documents/Biblia/bibliografie_html.html', 'w',
              encoding='utf-8') as f:
        f.write('\n'.join(html_lines))
    print(f"Wrote {len(entries)} entries to bibliografie_html.html",
          file=sys.stderr)

    # Now replace in carte.html
    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Find the bibliography section start and end (to closing </ol> before the
    # footer/scripts)
    start_match = re.search(
        r'<h2 id="bibliografie"[^>]*>.*?</h2>', html_content, re.DOTALL)
    if not start_match:
        print("ERROR: Could not find <h2 id=\"bibliografie\"> in HTML",
              file=sys.stderr)
        sys.exit(1)

    start = start_match.start()

    # Find the footer div after bibliography
    footer_match = re.search(r'<div class="footer">', html_content[start:])
    if not footer_match:
        print("ERROR: Could not find footer div after bibliography",
              file=sys.stderr)
        sys.exit(1)

    end = start + footer_match.start()

    new_html = (html_content[:start] +
                '\n'.join(html_lines) + '\n\n' +
                html_content[end:])

    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(new_html)
    print(f"Replaced bibliography in {HTML_FILE}", file=sys.stderr)


if __name__ == '__main__':
    main()

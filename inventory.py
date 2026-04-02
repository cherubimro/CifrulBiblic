#!/usr/bin/env python3.11
"""Inventory HTML content for checksum verification after LaTeX conversion."""
from bs4 import BeautifulSoup
import hashlib, re, json

with open('fara_buton.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

for tag in soup.find_all(['script', 'style']):
    tag.decompose()

body = soup.find('body')
text = body.get_text(separator=' ', strip=True)
text = re.sub(r'\s+', ' ', text).strip()

words = text.split()
md5 = hashlib.md5(text.encode('utf-8')).hexdigest()

print(f'Total words: {len(words)}')
print(f'Total chars: {len(text)}')
print(f'MD5: {md5}')

# Structural inventory
tables = soup.find_all('table')
blockquotes = soup.find_all('blockquote')
lists_all = soup.find_all(['ul', 'ol'])
paragraphs = soup.find_all('p')
links = soup.find_all('a')
pre_blocks = soup.find_all('pre')
headings = soup.find_all(['h1', 'h2', 'h3', 'h4'])

print(f'\n--- Structural inventory ---')
print(f'Headings (h1-h4): {len(headings)}')
print(f'Tables: {len(tables)}')
print(f'Blockquotes: {len(blockquotes)}')
print(f'Lists (ul/ol): {len(lists_all)}')
print(f'Paragraphs: {len(paragraphs)}')
print(f'Links: {len(links)}')
print(f'Pre/code blocks: {len(pre_blocks)}')

# Per-section word counts
print(f'\n--- Per-section word counts ---')
section_data = []
for h in soup.find_all(['h1', 'h2', 'h3']):
    sec_id = h.get('id', '')
    title = h.get_text(strip=True)[:60]
    words_in_section = []
    for sib in h.next_siblings:
        if sib.name in ['h1', 'h2', 'h3']:
            break
        if hasattr(sib, 'get_text'):
            t = sib.get_text(separator=' ', strip=True)
            if t:
                words_in_section.extend(t.split())
    wc = len(words_in_section)
    section_data.append({'tag': h.name, 'id': sec_id, 'title': title, 'words': wc})
    print(f'  [{h.name}] {title:60s} | {wc:5d}w | id={sec_id}')

# Save inventory for later comparison
inventory = {
    'total_words': len(words),
    'total_chars': len(text),
    'md5': md5,
    'headings': len(headings),
    'tables': len(tables),
    'blockquotes': len(blockquotes),
    'lists': len(lists_all),
    'paragraphs': len(paragraphs),
    'links': len(links),
    'pre_blocks': len(pre_blocks),
    'sections': section_data,
}
with open('html_inventory.json', 'w', encoding='utf-8') as f:
    json.dump(inventory, f, ensure_ascii=False, indent=2)
print('\nSaved to html_inventory.json')

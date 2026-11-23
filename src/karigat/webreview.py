"""Cheap static evidence; browser behavior remains a separate check."""
from html.parser import HTMLParser
import re


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links, self.buttons, self.copy = set(), [], [], []
        self.form = 0
        self.hidden = False
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('id'): self.ids.add(a['id'])
        if tag == 'a': self.links.append(a.get('href') or '')
        if tag == 'form': self.form += 1
        if tag == 'button' and not (self.form or a.get('onclick') or a.get('form') or a.get('popovertarget') or 'disabled' in a): self.buttons.append(self.getpos()[0])
        if tag in ('style','script'): self.hidden = tag
        if tag == 'script' and a.get('src'): self.scripts.append(a['src'])

    def handle_endtag(self, tag):
        if tag == 'form': self.form = max(self.form-1,0)
        if tag == self.hidden: self.hidden = False

    def handle_data(self, text):
        if self.hidden == 'script': self.scripts.append(text)
        elif not self.hidden: self.copy.append((self.getpos()[0],text.strip()))


def inspect_html(source, brief):
    page = Page(); page.feed(source); page.close()
    findings = []
    for line,text in page.copy:
        if text in ('...', '…') or 'lorem ipsum' in text.lower(): findings.append(f'line {line}: unfinished copy')
        for fact in re.findall(r'[$₹£€]\s*\d[\d,.]*|\b555-\d{4}\b|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',text):
            if fact[0] in '$₹£€' and not re.search(r'[1-9]',fact):continue  # Empty balances aren't advertised prices.
            if fact not in brief: findings.append(f'line {line}: confirm or remove unsupplied business detail: {fact}')
    for link in page.links:
        if not link or (link.startswith('#') and link[1:] not in page.ids): findings.append(f'unresolved navigation: {link!r}')
    script=' '.join(page.scripts)
    # Obvious unwired buttons only; dynamic handlers need a real browser.
    selections = re.findall(r'''querySelector(?:All)?\(\s*['"]([^'"]+)['"]\s*\)''',script)
    link_only = selections and all(re.fullmatch(r'(?:[\w-]+\s+)*a', s) for s in selections) and not re.search(r'getElementById\([^)]*\)\s*\.addEventListener|(?:window|document)\.addEventListener',script)
    if not script.strip() or link_only:
        for line in page.buttons: findings.append(f'line {line}: button has no apparent action')
    return findings

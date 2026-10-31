"""Build exam.html from src/template.html + data/*.json.

Usage: python3 src/build.py
"""
import json, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORD_RE = re.compile(r"[A-Za-z]+(?:[-'’][A-Za-z]+)*")
SCHOOLS = {'서강대': 0, '성균관대': 1, '한양대': 2}


def strip(s):
    return re.sub(r'<[^>]+>', '', s or '')


def main():
    exams = [json.loads(p.read_text()) for p in sorted((ROOT / 'data').glob('*.json')) if p.name != 'vocab.json']
    exams.sort(key=lambda e: (SCHOOLS.get(e['school'], 9), -e['year']))

    # global form -> lemma (first exam wins, like the app's fallback table)
    forms = {}
    for e in exams:
        for lemma, g in e['glossary'].items():
            for f in {lemma, *g.get('forms', [])}:
                forms.setdefault(f.replace('’', "'"), lemma)

    # occurrences: distinct (exam, passage-or-question) units per lemma
    occ = {}
    for e in exams:
        local = {f.replace('’', "'"): l for l, g in e['glossary'].items() for f in {l, *g.get('forms', [])}}
        units = {p['id']: strip(p['text']) for p in e['passages']}
        for q in e['questions']:
            units[f"q{q['no']}"] = strip(' '.join([q.get('stem', ''), q.get('box', ''), *q['choices']]))
        for uid, text in units.items():
            low = text.lower().replace('’', "'")
            found = set()
            for w in WORD_RE.findall(low):
                l = local.get(w) or forms.get(w)
                if l:
                    found.add(l)
            for f, l in list(local.items()):
                if ' ' in f and re.search(r'\b' + re.escape(f) + r'\b', low):
                    found.add(l)
            for l in found:
                occ.setdefault(l, []).append(f"{e['id']}#{uid}")

    data = {'exams': exams, 'occ': occ}
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    html = (ROOT / 'src' / 'template.html').read_text().replace('__DATA__', payload)
    (ROOT / 'exam.html').write_text(html)
    nq = sum(len(e['questions']) for e in exams)
    print(f"exam.html: {len(exams)} exams, {nq} questions, {len(occ)} lemmas, {len(html) // 1024} KB")


main()

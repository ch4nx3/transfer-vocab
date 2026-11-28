"""Rank data/vocab.json by exam frequency + judged difficulty/academic use/편입 relevance.

Inputs : data/vocab.json (enriched words), data/vocab_ratings.json ({w: [level, academic, transfer]}),
         data/<exam>.json (past papers, used to count how often each word really appeared)
Output : data/vocab.json rewritten in curriculum order with lvl, aca, tr, exN, vq, ez, imp, score.

Usage: python3 src/rank_vocab.py
"""
import json, math, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORD_RE = re.compile(r"[a-z]+(?:[-'][a-z]+)*")
SYN_DIR = re.compile(r'closest (in )?meaning|similar in meaning|nearest in meaning|synonym|same meaning|밑줄 친 (단어|부분)의? ?(뜻|의미)|가장 가까운 의미', re.I)
LEVEL_BONUS = {0: -10, 1: -6, 2: -1, 3: 1.5, 4: 0}


def strip(s):
    return re.sub(r'<[^>]+>', ' ', s or '').lower().replace('’', "'")


def main():
    words = json.loads((ROOT / 'data' / 'vocab.json').read_text())
    ratings = json.loads((ROOT / 'data' / 'vocab_ratings.json').read_text())
    exams = [json.loads(p.read_text()) for p in sorted((ROOT / 'data').glob('*.json'))
             if p.name not in ('vocab.json', 'vocab_ratings.json')]

    # surface forms per headword: the word itself + every exam glossary form for that lemma
    forms = {w['w']: {w['w'].lower()} for w in words}
    for e in exams:
        for lemma, g in e['glossary'].items():
            if lemma in forms:
                forms[lemma] |= {f.replace('’', "'") for f in g.get('forms', [])}
    single = {}
    for w, fs in forms.items():
        for f in fs:
            if ' ' not in f:
                single.setdefault(f, set()).add(w)

    def found_in(text):
        toks = set(WORD_RE.findall(text))
        hit = {w for t in toks for w in single.get(t, ())}
        hit |= {w for w, fs in forms.items() if any(' ' in f and f in text for f in fs)}
        return hit

    ex_units, vocab_q = {}, set()
    for e in exams:
        dirs = e['directions']
        units = {p['id']: strip(p['text']) for p in e['passages']}
        for q in e['questions']:
            units[f"q{q['no']}"] = strip(' '.join([q.get('stem', ''), q.get('box', ''), *q['choices']]))
            d = next((d for d in dirs if d['from'] <= q['no'] <= d['to']), None)
            synonym = d and SYN_DIR.search(re.sub(r'<[^>]+>', '', d['text']))
            short_choices = all(len(c.split()) <= 3 for c in q['choices']) and not all(re.fullmatch(r'\W*[①-⑤ⒶⒷⒸⒹⒺ()A-E→\- ]*\W*', c) for c in q['choices'])
            if synonym or short_choices:   # vocabulary-type item: the underlined word and the choices are tested words
                tested = ' '.join(re.findall(r'<u>(.*?)</u>', q.get('stem', ''))) + ' ' + ' '.join(q['choices'])
                vocab_q |= found_in(strip(tested))
        for uid, text in units.items():
            for w in found_in(text):
                ex_units.setdefault(w, set()).add(f"{e['id']}#{uid}")

    for w in words:
        lvl, aca, tr = ratings.get(w['w'], [2, 2, 2])
        exn = len(ex_units.get(w['w'], ()))
        vq = w['w'] in vocab_q
        w.update(lvl=lvl, aca=aca, tr=tr, exN=exn)
        if vq: w['vq'] = 1
        else: w.pop('vq', None)
        # frequent-in-passages alone shouldn't lift plainer words (mean, span) over real 편입 words
        freq_w = 2.5 if lvl >= 3 else 1.2
        w['score'] = round(freq_w * math.log1p(exn) + 3 * vq + 1.0 * aca + 1.8 * tr + LEVEL_BONUS.get(lvl, 0), 2)
        # left out of the default curriculum: 수능-basic or easier, or plain words never tested in 편입
        if lvl <= 1 or (lvl == 2 and tr <= 1 and not vq): w['ez'] = 1
        else: w.pop('ez', None)

    words.sort(key=lambda w: (1 if w.get('ez') else 0, -w['score'], w['w']))
    core = [w for w in words if not w.get('ez')]
    for i, w in enumerate(words):
        r = i / max(1, len(core))
        w['imp'] = 3 if w.get('ez') else 1 if r < .3 else 2 if r < .7 else 3
    (ROOT / 'data' / 'vocab.json').write_text(json.dumps(words, ensure_ascii=False, separators=(',', ':')))
    print(f"{len(words)} words · core {len(core)} · easy/off-curriculum {len(words) - len(core)} · "
          f"seen in exams {sum(1 for w in words if w['exN'])} · tested in vocab items {sum(1 for w in words if w.get('vq'))}")
    print('top 40:', ' '.join(w['w'] for w in words[:40]))


main()

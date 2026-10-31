"""Build vocab.html from src/vocab_template.html + data/vocab.json.

Usage: python3 src/build_vocab.py
"""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main():
    words = json.loads((ROOT / 'data' / 'vocab.json').read_text())
    payload = json.dumps({'words': words}, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    html = (ROOT / 'src' / 'vocab_template.html').read_text().replace('__DATA__', payload)
    (ROOT / 'vocab.html').write_text(html)
    print(f"vocab.html: {len(words)} words, {len(html.encode()) // 1024} KB")


main()

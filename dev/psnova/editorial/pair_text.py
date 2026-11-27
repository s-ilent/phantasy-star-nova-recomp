#!/usr/bin/env python3
"""Pair explicitly selected language groups from structured game-text JSONL exports.
No game formats, installation discovery or private reference data are embedded.
Input fields: archive, member, category, group (int), key, text (str), optional locator.
"""
import argparse, collections, json, sys
from pathlib import Path
import l10n


def load(path, group):
    rows = collections.defaultdict(list)
    with Path(path).open(encoding='utf-8-sig') as stream:
        for n, line in enumerate(stream, 1):
            if not line.strip():
                continue
            r = json.loads(line)
            fields = ('archive', 'member', 'category', 'key', 'text')
            if not isinstance(r, dict) or any(not isinstance(r.get(k), str) for k in fields) or type(r.get('group')) is not int:
                raise ValueError(f'{path}:{n}: invalid record')
            if r['group'] != group:
                continue
            # Archive identity is explicitly normalized by exporter. Do not join by basename alone.
            key = tuple(r[k] for k in fields[:-1])
            if not all(key):
                raise ValueError(f'{path}:{n}: empty structural key')
            rows[key].append(r)
    return rows


def pair(jp, en):
    count = collections.Counter(); accepted = []; rejected = []
    for key in sorted(jp.keys() | en.keys()):
        j, e = jp.get(key, []), en.get(key, [])
        if len(j) > 1 or len(e) > 1:
            reason = 'ambiguous_duplicate'
        elif not j or not e:
            reason = 'missing_source' if not j else 'missing_target'
        elif not j[0]['text'].strip() or not e[0]['text'].strip():
            reason = 'blank'
        elif e[0]['text'].strip() in ('***', '＊＊＊'):
            reason = 'redacted'
        else:
            reason = None
        if reason:
            count[reason] += 1
            rejected.append({'key': key, 'reason': reason, 'source_count': len(j), 'target_count': len(e)})
            continue
        count['paired'] += 1
        if j[0]['text'] == e[0]['text']:
            count['identical'] += 1
        accepted.append({'archive': key[0], 'member': key[1], 'category': key[2], 'key': key[3], 'source': j[0]['text'], 'target': e[0]['text'], 'source_group': j[0]['group'], 'target_group': e[0]['group'], 'source_locator': j[0].get('locator'), 'target_locator': e[0].get('locator')})
    return accepted, rejected, dict(count)


def store(db, pairs, corpus, locale):
    l10n.init(db)
    rows = []
    for r in pairs:
        origin = json.dumps([r['archive'], r['member']], ensure_ascii=False, separators=(',', ':'))
        locator = json.dumps([r['category'], r['key']], ensure_ascii=False, separators=(',', ':'))
        notes = json.dumps({k:r[k] for k in ('source_group','target_group','source_locator','target_locator')}, ensure_ascii=False)
        rows.append((corpus, locale, r['source'], r['target'], origin, locator, r['key'], notes, 'released-file-paired', None, None))
    if db.execute('SELECT 1 FROM segment WHERE corpus=? LIMIT 1', (corpus,)).fetchone():
        raise ValueError('corpus already exists; choose a new versioned corpus ID')
    l10n.put(db, rows)
    l10n.rebuild(db)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('jp'); p.add_argument('en'); p.add_argument('--jp-group', type=int, required=True); p.add_argument('--en-group', type=int, required=True)
    p.add_argument('--out', required=True, help='new output directory'); p.add_argument('--db'); p.add_argument('--corpus'); p.add_argument('--locale', default='en-US')
    a = p.parse_args()
    if bool(a.db) != bool(a.corpus): p.error('--db and --corpus must be supplied together')
    if Path(a.jp).resolve() == Path(a.en).resolve() and a.jp_group == a.en_group: p.error('same input and group for both languages')
    j, e = load(a.jp, a.jp_group), load(a.en, a.en_group)
    if not j or not e: raise ValueError('empty selected language group; check export')
    accepted, rejected, counts = pair(j, e)
    if not accepted: raise ValueError('no unambiguous pairs')
    out = Path(a.out); out.mkdir(parents=True, exist_ok=False)
    for name, records in [('pairs.jsonl', accepted), ('unresolved.jsonl', rejected)]:
        with (out/name).open('w', encoding='utf-8') as f:
            for r in records: f.write(json.dumps(r, ensure_ascii=False)+'\n')
    (out/'report.json').write_text(json.dumps(counts, indent=2)+'\n', encoding='utf-8')
    if a.db:
        with l10n.connect(a.db) as db: store(db, accepted, a.corpus, a.locale)
    print(json.dumps(counts, indent=2))

if __name__ == '__main__':
    try: main()
    except (ValueError, OSError) as e: sys.exit(str(e))

"""Snapshot-bound editorial decisions, independent review and adjudication."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import assignments
import l10n


def require(condition, message):
    if not condition:
        raise ValueError(message)


def collect(paths):
    result = {}
    for path in paths:
        for mid, row in l10n.read_jsonl(path).items():
            require(mid not in result, f'{mid}: duplicate decision')
            result[mid] = row
    return result


def actor(row, mid):
    for key in ('actor', 'reason'):
        require(isinstance(row.get(key), str) and row[key].strip(), f'{mid}: missing {key}')
    return row['actor'].strip().casefold()


def replacement(old, decision, row, mid):
    require(decision in ('keep', 'revise'), f'{mid}: invalid final decision')
    if decision == 'keep':
        require('translation' not in row, f'{mid}: keep must not supply replacement')
        return old.get('translation')
    new = row.get('translation')
    require(new != old.get('translation'), f'{mid}: revision is unchanged')
    errors = l10n.lint(old, new)
    require(not errors, f'{mid}: {"; ".join(errors)}')
    return new


def evaluate(records, manifest, edits, reviews, resolutions):
    owners = assignments.load_manifest(manifest, records, l10n.digest, l10n.blocked)
    require(bool(owners), 'empty assignment manifest')
    require(set(edits) <= set(owners), 'editor decision outside assignment manifest')
    require(set(reviews) <= set(edits), 'review without editor decision')
    require(set(resolutions) <= set(reviews), 'resolution without independent review')
    entries = []
    counts = Counter()
    revised = {}
    for mid, owner in owners.items():
        old = records[mid]
        e, r, a = edits.get(mid), reviews.get(mid), resolutions.get(mid)
        entry = {'id': mid, 'assignment_id': owner, 'state': 'unreviewed'}
        if e is not None:
            require(e.get('assignment_id') == owner and e.get('base_sha256') == l10n.digest(old), f'{mid}: stale or wrong editor assignment')
            editor = actor(e, mid)
            decision = e.get('decision')
            require(decision in ('keep','revise','query'), f'{mid}: invalid editorial decision')
            require(e.get('severity') in ('none','minor','major','blocker','query'), f'{mid}: invalid severity')
            if decision == 'query':
                require('translation' not in e, f'{mid}: query must not supply replacement')
                new = None
            else:
                new = replacement(old, decision, e, mid)
            entry.update(state='awaiting-review', editor=e, editor_sha256=l10n.digest(e))
            if r is not None:
                reviewer = actor(r, mid)
                require(reviewer != editor, f'{mid}: self-review')
                require(r.get('editor_sha256') == l10n.digest(e), f'{mid}: stale reviewer decision')
                verdict = r.get('verdict')
                require(verdict in ('agree','disagree'), f'{mid}: invalid verdict')
                entry.update(reviewer=r, reviewer_sha256=l10n.digest(r), state='needs-resolution')
                final = None
                if verdict == 'agree' and decision != 'query':
                    require(a is None, f'{mid}: unnecessary resolution')
                    final = decision
                elif a is not None:
                    adjudicator = actor(a, mid)
                    require(adjudicator not in (editor, reviewer), f'{mid}: adjudicator must be distinct')
                    require(a.get('reviewer_sha256') == l10n.digest(r), f'{mid}: stale resolution')
                    final = a.get('decision')
                    new = replacement(old, final, a, mid)
                    entry['resolution'] = a
                if final is not None:
                    entry['state'] = 'approved-' + final
                    if final == 'revise':
                        revised[mid] = {**old, 'translation': new, 'review': {'status':'editorially-approved', 'ledger_sha256':l10n.digest(entry)}}
        counts[entry['state']] += 1
        entries.append(entry)
    report = {'assigned':len(owners), 'editor_reviewed':len(edits), 'independently_reviewed':len(reviews), 'disagreements':sum(r['verdict']=='disagree' for r in reviews.values()), 'resolved':len(resolutions), 'states':dict(counts), 'complete':counts['approved-keep']+counts['approved-revise']==len(owners)}
    return report, entries, revised


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('corpus'); p.add_argument('--assignments',required=True)
    for name in ('edits','reviews','resolutions'):
        p.add_argument('--'+name,nargs='+',default=[])
    p.add_argument('--out',required=True,help='new output directory')
    p.add_argument('--finalize',action='store_true',help='emit full revised corpus only if all assigned decisions are approved')
    a=p.parse_args(); records=l10n.read_jsonl(a.corpus)
    report, entries, revised=evaluate(records,a.assignments,collect(a.edits),collect(a.reviews),collect(a.resolutions))
    out=Path(a.out); out.mkdir(parents=True,exist_ok=False)
    l10n.write_jsonl(out/'ledger.jsonl',entries)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
    if a.finalize:
        require(report['complete'], 'incomplete review; no revised corpus emitted')
        l10n.write_jsonl(out/'revised.jsonl',(revised.get(mid,row) for mid,row in records.items()))


if __name__=='__main__':
    try: main()
    except (ValueError,OSError) as exc: sys.exit(str(exc))

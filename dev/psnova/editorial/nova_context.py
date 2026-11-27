"""Build/query a local conversation index and offline bilingual HTML browser."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import l10n
from nova_prepare import event_records, npc_records


def build_index(root, records):
    names, _ = npc_records(root)
    name_map = json.loads((root/'names.json').read_text(encoding='utf-8'))
    scenes = {}
    def add(table, group, kind, mid, order, **metadata):
        sid = f'{table}::{group}'
        scene = scenes.setdefault(sid, dict(id=sid, kind=kind, table=table, label=group, lines=[]))
        scene['lines'].append(dict(id=mid, order=order, **metadata))
    def speaker(sid):
        jp = names.get(sid, {}).get('jp')
        return (name_map.get(jp, {}).get('english') or jp) if jp else None
    # Table order is evidence, not proof that every row is executed in one path.
    for mid, refs in event_records(root).items():
        for r in refs:
            model = r.get('speaker_model') or ''
            match = re.search(r'np(\d{4})', model, re.I)
            add(r['table'], r['scene'], 'event-table', mid, r['order'],
                speaker=speaker(match[1]) if match else None, model=model, cue=r.get('cue'))
    # Keep base and patch, generic crew, and malformed continuations distinct.
    for p in sorted(root.glob('scan/*_csv/NpcTalkParameter.csv')):
        table = str(p.relative_to(root)); group = None; ordinal = 0; sid = None; crew = None; condition = None
        for i, line in enumerate(p.read_bytes().decode('cp932', 'replace').splitlines()):
            f = line.split(',')
            if len(f) <= 26 or not f[0].startswith('key'):
                group = None; ordinal = 0; continue
            step = int(f[25]) if f[25].isdigit() else 0
            if step == 1:
                group = f[0]+f'@{i}'; ordinal = 1; sid = f[1] if f[1].isdigit() and not f[2] else None
                crew = f[2] or None; condition = f[3:6]
            elif group and not f[1] and not f[2] and step == ordinal+1:
                ordinal = step
            else:
                group = None; ordinal = 0; sid = None; crew = None; condition = None
            mid = f[26].strip()
            if mid.isdigit():
                add(table, group or f'orphan@{i}', 'npc-table' if group else 'npc-unresolved', mid, i,
                    speaker=speaker(sid), speaker_id=sid, crew_group=crew, condition=condition,
                    step=step, cue=f[28] if len(f)>28 else None, voice_bank=f[27] if len(f)>27 else None)
    found = {line['id'] for scene in scenes.values() for line in scene['lines']}
    # Fallback groups are browsing aids only, never asserted conversations.
    for mid, row in records.items():
        if mid not in found:
            group = 'id:'+mid[:9] if len(mid)>=12 else 'bank:'+str(row.get('bank', 'unknown'))
            add('inferred', group, 'id-group' if len(mid)>=12 else 'bank-group', mid, int(mid), speaker=None)
    for scene in scenes.values():
        scene['lines'].sort(key=lambda r:r['order'])
    return {'version':1, 'corpus_sha256':l10n.assignments.snapshot(records,l10n.digest), 'scenes':sorted(scenes.values(),key=lambda s:s['id'])}


def load_index(path, records):
    index = json.loads(Path(path).read_text(encoding='utf-8'))
    if index.get('version') != 1 or index.get('corpus_sha256') != l10n.assignments.snapshot(records,l10n.digest):
        raise ValueError('index belongs to a different corpus snapshot')
    return index


def load_revision(path, records):
    if not path: return {}
    rows = l10n.read_jsonl(path)
    if rows.keys() != records.keys() or any(r.get('source') != records[mid].get('source') for mid,r in rows.items()):
        raise ValueError('revision does not preserve baseline IDs and source')
    return {mid:r.get('translation') for mid,r in rows.items() if r.get('translation') != records[mid].get('translation')}


def view(scene, records, revised, selected=None):
    return {**scene, 'lines':[{**r, 'selected':r['id']==selected, 'source':records.get(r['id'],{}).get('source'),
        'translation':records.get(r['id'],{}).get('translation'), 'revised':revised.get(r['id']),
        'issues':records.get(r['id'],{}).get('issues',[])} for r in scene['lines']]}


def search(index, records, query='', speakers=()):
    q=query.casefold(); wanted={s.casefold() for s in speakers}
    for scene in index['scenes']:
        present={(r.get('speaker') or '').casefold() for r in scene['lines']}
        if not wanted <= present: continue
        if q and q not in scene['id'].casefold() and not any(q in ' '.join(str(x or '') for x in (r['id'],r.get('speaker'),records.get(r['id'],{}).get('source'),records.get(r['id'],{}).get('translation'))).casefold() for r in scene['lines']): continue
        yield scene


HTML = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Nova local context browser</title>
<style>body{margin:0;background:#141a23;color:#e4e9f0;font:15px system-ui,sans-serif}header{padding:16px 22px;background:#202b39;position:sticky;top:0;z-index:1}h1{font-size:20px;margin:0 0 8px}input,select,button{font:inherit;color:inherit;background:#283647;border:1px solid #53657a;border-radius:5px;padding:7px}input{width:min(420px,90%)}main{display:grid;grid-template-columns:minmax(220px,29%) 1fr;gap:16px;padding:16px}aside{max-height:76vh;overflow:auto}aside button{display:block;text-align:left;width:100%;margin-bottom:5px;overflow-wrap:anywhere}aside button.active{background:#38516c}article{min-width:0}section{border:1px solid #3e4f63;border-radius:8px;padding:12px;margin-bottom:9px;background:#1c2633;scroll-margin-top:120px}section.selected{border:2px solid #8bc7ff}h2{font-size:17px;overflow-wrap:anywhere}h3{font-size:14px;margin:0 0 6px;color:#b4d3f0}p{white-space:pre-wrap;overflow-wrap:anywhere;margin:7px 0}.jp{color:#bbc8d7}.rev{color:#a2e0b7}small{color:#a4b5c8}label{display:block;margin:8px 0}@media(max-width:700px){main{grid-template-columns:1fr}aside{max-height:30vh}}</style>
<header><h1>Nova · local context browser</h1><input id="q" placeholder="Search ID, Japanese, English, speaker or scene"><select id="kind"><option value="">All groups</option><option>event-table</option><option>npc-table</option><option>npc-unresolved</option><option>id-group</option><option>bank-group</option></select><small id="count"></small></header><main><aside id="list"></aside><article id="detail"><p>Select a scene.</p></article></main>
<script id="data" type="application/json">__DATA__</script><script>
const data=JSON.parse(document.getElementById('data').textContent), q=document.getElementById('q'), kind=document.getElementById('kind'), list=document.getElementById('list'), detail=document.getElementById('detail');
const el=(tag,t,cls)=>{const e=document.createElement(tag);e.textContent=t??'';if(cls)e.className=cls;return e};
let active=null;const rowText=l=>[l.id,l.speaker,data.messages[l.id]?.source,data.messages[l.id]?.translation,data.messages[l.id]?.revised].join(' ').toLowerCase();
function show(s,needle){active=s.id;detail.replaceChildren(el('h2',s.label),el('small',s.table+' · '+s.kind+' · '+s.lines.length+' occurrences'),el('p',s.kind.endsWith('-group')?'Inferred ID grouping; not an established conversation.':'Source table order; branching and runtime execution not verified.'));let first=null;for(const l of s.lines){const r=data.messages[l.id]||{},hit=needle&&rowText(l).includes(needle);const a=el('section','',hit?'selected':'');if(hit&&!first)first=a;a.append(el('h3',(l.speaker||l.model|| (l.crew_group?'Crew '+l.crew_group:'Unknown speaker'))+' · '+l.id),el('small','Row '+l.order+(l.cue?' · cue '+l.cue:'')+(l.condition?' · condition '+l.condition.join(' / '):'')),el('p',r.source??'[missing RMD source]','jp'),el('p',r.translation??'[missing translation]'));if('revised'in r)a.append(el('p','Revised: '+(r.revised??'[empty]'),'rev'));if(r.issues?.length)a.append(el('small',r.issues.join(' · ')));const b=el('button','Other occurrences');b.onclick=()=>{q.value=l.id;kind.value='';refresh()};a.append(b);detail.append(a)}if(first)first.scrollIntoView({block:'nearest'});for(const b of list.children)b.classList.toggle('active',b.dataset.id===active)}
function refresh(){const needle=q.value.trim().toLowerCase();const hits=data.scenes.filter(s=>(!kind.value||s.kind===kind.value)&&(!needle||s.id.toLowerCase().includes(needle)||s.lines.some(l=>rowText(l).includes(needle))));list.replaceChildren();document.getElementById('count').textContent=' '+hits.length+' groups';for(const s of hits){const b=el('button',s.label+' · '+s.lines.length+' ['+s.table+']');b.dataset.id=s.id;b.onclick=()=>show(s,needle);list.append(b)}if(hits.length===1)show(hits[0],needle);else if(!hits.some(s=>s.id===active))detail.replaceChildren(el('p',hits.length?'Select a scene.':'No results.'))}q.oninput=refresh;kind.onchange=refresh;refresh();
</script></html>'''


def browse(index, records, revised, out):
    messages={mid:{'source':r.get('source'),'translation':r.get('translation'),'issues':r.get('issues',[]),**({'revised':revised[mid]} if mid in revised else {})} for mid,r in records.items()}
    payload=json.dumps({'scenes':index['scenes'],'messages':messages},ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    Path(out).write_text(HTML.replace('__DATA__',payload),encoding='utf-8')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('corpus',type=Path);p.add_argument('--index',required=True,type=Path);p.add_argument('--revised',type=Path)
    sp=p.add_subparsers(dest='cmd',required=True)
    s=sp.add_parser('build');s.add_argument('dataset',type=Path)
    s=sp.add_parser('message');s.add_argument('id');s.add_argument('--occurrences',action='store_true')
    s=sp.add_parser('scene');s.add_argument('id')
    s=sp.add_parser('search');s.add_argument('query',nargs='?',default='');s.add_argument('--speaker',action='append',default=[])
    s=sp.add_parser('browse');s.add_argument('--out',required=True,type=Path)
    a=p.parse_args(); records=l10n.read_jsonl(a.corpus)
    if a.cmd=='build':
        idx=build_index(a.dataset,records);a.index.write_text(json.dumps(idx,ensure_ascii=False),encoding='utf-8');print(len(idx['scenes']));return
    idx=load_index(a.index,records); revised=load_revision(a.revised,records)
    if a.cmd=='browse':browse(idx,records,revised,a.out);return
    if a.cmd=='scene':
        result=[view(s,records,revised) for s in idx['scenes'] if s['id']==a.id]
    elif a.cmd=='message':
        result=[({**s,'lines':[r for r in s['lines'] if r['id']==a.id]} if a.occurrences else view(s,records,revised,a.id)) for s in idx['scenes'] if any(r['id']==a.id for r in s['lines'])]
    else:result=[{**s,'lines':len(s['lines'])} for s in search(idx,records,a.query,a.speaker)]
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()

#!/usr/bin/env python3
"""Offline localization reference and editing utilities; Python 3.10+, SQLite FTS5."""
import argparse, collections, hashlib, json, re, sqlite3, sys, unicodedata
from pathlib import Path
import assignments
def connect(path):
    db=sqlite3.connect(path); db.row_factory=sqlite3.Row; return db
def init(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS segment(id INTEGER PRIMARY KEY, corpus TEXT, locale TEXT, source TEXT, target TEXT, origin TEXT, locator TEXT, label TEXT, notes TEXT, status TEXT, width TEXT, lines TEXT, UNIQUE(corpus,locale,origin,locator)); CREATE INDEX IF NOT EXISTS idx_source ON segment(source); CREATE VIRTUAL TABLE IF NOT EXISTS concordance USING fts5(source,target,content='segment',content_rowid='id',tokenize='trigram');''')
def norm(x): return unicodedata.normalize('NFC',str(x or '')).replace('\r\n','\n').strip()
def put(db,rows):
    db.executemany('INSERT OR REPLACE INTO segment(corpus,locale,source,target,origin,locator,label,notes,status,width,lines) VALUES(?,?,?,?,?,?,?,?,?,?,?)',rows)
def rebuild(db): db.execute("INSERT INTO concordance(concordance) VALUES('rebuild')"); db.commit()
def search(db,query,locale=None,limit=20,exact=False,corpus=None):
    q=norm(query); args=[]; where=[]
    if not q: raise ValueError('empty search')
    if exact: where.append('source=?'); args.append(q)
    else: where.append('(instr(source,?)>0 OR instr(lower(target),lower(?))>0)'); args.extend([q,q])
    if locale: where.append('locale=?'); args.append(locale)
    if corpus: where.append('corpus=?'); args.append(corpus)
    where.append("target<>''")
    if len(q)>=3 and not exact:
        where.append('id IN (SELECT rowid FROM concordance WHERE concordance MATCH ?)'); args.append('"'+q.replace('"','""')+'"')
    args.append(limit)
    return [dict(r) for r in db.execute('SELECT * FROM segment WHERE '+' AND '.join(where)+" ORDER BY CASE WHEN status='released-file-paired' THEN 0 WHEN status LIKE 'Confirmed%' THEN 1 ELSE 2 END, CASE locale WHEN 'en-US' THEN 0 ELSE 1 END,length(source),id LIMIT ?",args)]
def candidates(db,limit=100):
    rows=[dict(r) for r in db.execute("SELECT source,count(DISTINCT target) variants,group_concat(DISTINCT locale) locales,count(*) occurrences FROM segment WHERE target<>'' AND length(source) BETWEEN 2 AND 24 AND length(target)<=80 AND instr(source,char(10))=0 GROUP BY source HAVING variants>1 ORDER BY occurrences DESC,source LIMIT ?",(limit,))]
    for r in rows:
        r['choices']=[dict(v) for v in db.execute("SELECT locale,target,count(*) occurrences,sum(status LIKE 'Confirmed%') confirmed FROM segment WHERE source=? AND target<>'' GROUP BY locale,target ORDER BY confirmed DESC,occurrences DESC",(r['source'],))]
    return rows
def read_jsonl(path):
    out={}
    for n,line in enumerate(Path(path).read_text(encoding='utf-8-sig').splitlines(),1):
        if not line.strip(): continue
        r=json.loads(line)
        if not isinstance(r,dict): raise ValueError(f'{path}:{n}: expected an object')
        mid=r.get('id')
        if not isinstance(mid,str) or not mid or mid in out: raise ValueError(f'{path}:{n}: missing/nonstring/duplicate id')
        out[mid]=r
    return out
def digest(row): return hashlib.sha256(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def write_jsonl(path,rows):
    p=Path(path); tmp=p.with_suffix(p.suffix+'.tmp'); tmp.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows),encoding='utf-8'); tmp.replace(p)
TAG=re.compile(r'\{[^{}]+\}')
def fixed_tags(s): return collections.Counter(t for t in TAG.findall(s) if not (t.startswith('{ruby:') or t=='{/ruby}' or t.startswith('{8081:') or t in ('{/color}','{end}')))
def lint(old,new):
    errs=[]
    if not isinstance(new,str) or not new.strip(): return ['empty/nonstring target']
    if not isinstance(old.get('source',old.get('jp')),str): return ['missing source']
    if fixed_tags(old.get('source',old.get('jp',''))) != fixed_tags(new): errs.append('protected token mismatch')
    depth=0
    for t in TAG.findall(new):
        if t.startswith('{8081:'): depth+=1
        elif t in ('{/color}','{end}'): depth-=1
        if depth<0: errs.append('unbalanced color tags'); break
    if depth and 'unbalanced color tags' not in errs: errs.append('unbalanced color tags')
    if any(c in TAG.sub('',new) for c in '{}'): errs.append('malformed brace tags')
    if re.search(r'[\u3040-\u30ff\u3400-\u9fff]',TAG.sub('',new)): errs.append('Japanese characters in target (manual exception needed)')
    return errs
def blocked(row):
    return row.get('source_review')=='blocked-glyphs' or bool(re.search(r'〔#[0-9a-fA-F]+〕',row.get('source',row.get('jp','')) or ''))
def batch(corpus,out,size):
    if size<1: raise ValueError('size must be positive')
    records=read_jsonl(corpus); groups=collections.defaultdict(list)
    for r in records.values(): groups[r.get('scene') or r.get('category') or r.get('group') or 'unclassified'].append(r)
    p=Path(out); p.mkdir(parents=True,exist_ok=True)
    if any(p.iterdir()): raise ValueError('batch output directory must be empty')
    manifest={'version':1,'corpus_sha256':assignments.snapshot(records,digest),'assignments':{}}
    n=0
    for group,rows in groups.items():
        for start in range(0,len(rows),size):
            chunk=rows[start:start+size]
            items=[{**r,'base_sha256':digest(r)} for r in chunk if not blocked(r)]
            if not items: continue
            context=rows[max(0,start-2):start]+[r for r in chunk if blocked(r)]+rows[start+size:start+size+2]
            assignment_id=f'batch_{n:04d}'
            manifest['assignments'][assignment_id]={r['id']:r['base_sha256'] for r in items}
            (p/f'{assignment_id}.json').write_text(json.dumps({'assignment_id':assignment_id,'group':group,'items':items,'read_only_neighbors':context},ensure_ascii=False,indent=2),encoding='utf-8'); n+=1
    (p/'assignments.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    return n
def merge(corpus,patches,out,manifest):
    records=read_jsonl(corpus); seen=set(); errors=[]; changes={}
    owners=assignments.load_manifest(manifest,records,digest,blocked)
    for path in patches:
        proposals=read_jsonl(path)
        if len({str(r.get('assignment_id')) for r in proposals.values()})>1:
            errors.append(f'{path}: mixed assignments in one proposal file'); continue
        for mid,r in proposals.items():
            if mid in seen: errors.append(f'{mid}: duplicate edit'); continue
            seen.add(mid); old=records.get(mid)
            if not old or r.get('base_sha256')!=digest(old): errors.append(f'{mid}: unknown/stale base'); continue
            if blocked(old): errors.append(f'{mid}: blocked source glyphs'); continue
            if mid not in owners or r.get('assignment_id')!=owners[mid]: errors.append(f'{mid}: outside assigned ownership'); continue
            new=r.get('translation'); issues=lint(old,new)
            if issues: errors.extend(f'{mid}: {e}' for e in issues); continue
            if not isinstance(r.get('reason'),str) or not r['reason'].strip(): errors.append(f'{mid}: missing reason'); continue
            changes[mid]={**old,'translation':new,'review':{'status':'proposed','reason':r['reason'],'base_sha256':r['base_sha256'],'assignment_id':owners[mid]}}
    if errors: raise ValueError('\n'.join(errors))
    if Path(corpus).resolve()==Path(out).resolve(): raise ValueError('refusing to overwrite input corpus')
    write_jsonl(out,(changes.get(mid,r) for mid,r in records.items())); return len(changes)
def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--db',default='reference.sqlite'); sp=p.add_subparsers(dest='cmd',required=True)
    s=sp.add_parser('search'); s.add_argument('query'); s.add_argument('--locale'); s.add_argument('--limit',type=int,default=20); s.add_argument('--exact',action='store_true'); s.add_argument('--corpus')
    s=sp.add_parser('conflicts'); s.add_argument('--limit',type=int,default=100)
    sp.add_parser('stats')
    s=sp.add_parser('batch'); s.add_argument('corpus'); s.add_argument('out'); s.add_argument('--size',type=int,default=60)
    s=sp.add_parser('merge'); s.add_argument('corpus'); s.add_argument('out'); s.add_argument('patches',nargs='+'); s.add_argument('--assignments',required=True)
    a=p.parse_args()
    if a.cmd=='batch': result={'batches':batch(a.corpus,a.out,a.size)}
    elif a.cmd=='merge': result={'changed':merge(a.corpus,a.patches,a.out,a.assignments)}
    else:
        with connect(a.db) as db:
            if a.cmd=='search': result=search(db,a.query,a.locale,a.limit,a.exact,a.corpus)
            elif a.cmd=='conflicts': result=candidates(db,a.limit)
            else: result=[dict(r) for r in db.execute("SELECT corpus,locale,count(*) rows,sum(target<>'') populated,sum(status LIKE 'Confirmed%') confirmed FROM segment GROUP BY corpus,locale")]
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':
    try: main()
    except (ValueError, OSError, sqlite3.Error) as e: sys.exit(str(e))

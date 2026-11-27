"""Local editorial terminology and character evidence; never automatically rewrite text."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import unicodedata
import l10n

STATUSES = {'candidate', 'verified', 'canonical', 'exception', 'deprecated', 'disputed'}
ACTIVE = {'canonical', 'exception', 'deprecated'}
TAG = re.compile(r'\{[^{}]*\}')


def clean(text):
    return unicodedata.normalize('NFC', TAG.sub('', text or '')).strip()


def dump(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def load_glossary(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('terms'), list):
        raise ValueError('expected glossary version 1 with a terms list')
    seen = set()
    for t in data['terms']:
        if not isinstance(t, dict) or not all(isinstance(t.get(k), str) and t[k].strip() for k in ('id','source','status')):
            raise ValueError('invalid term record')
        if not clean(t['source']) or t['id'] in seen or t['status'] not in STATUSES or t.get('match','exact') not in ('exact','substring'):
            raise ValueError(f"{t['id']}: invalid or duplicate term")
        seen.add(t['id'])
        for k in ('categories','message_ids','allowed','deprecated'):
            if not isinstance(t.get(k,[]),list) or any(not isinstance(x,str) or not x.strip() for x in t.get(k,[])):
                raise ValueError(f"{t['id']}: invalid {k}")
        if t['status'] in ACTIVE:
            if not isinstance(t.get('reason'),str) or not t['reason'].strip() or not isinstance(t.get('evidence'),list) or not t['evidence']:
                raise ValueError(f"{t['id']}: active term requires reason and evidence")
            if t['status'] in ('canonical','exception') and not t.get('allowed'):
                raise ValueError(f"{t['id']}: missing approved forms")
            if t['status']=='exception' and not t.get('message_ids') and not t.get('categories'):
                raise ValueError(f"{t['id']}: exception must be scoped")
            if t['status']=='deprecated' and not t.get('deprecated'):
                raise ValueError(f"{t['id']}: missing deprecated forms")
    return data


def applies(t, row):
    if t.get('categories') and row.get('category') not in t['categories']: return False
    if t.get('message_ids') and row['id'] not in t['message_ids']: return False
    source, term = clean(row.get('source',row.get('jp',''))), clean(t['source'])
    return source == term if t.get('match','exact')=='exact' else term in source


def relevant(terms, row):
    found = [t for t in terms if applies(t,row)]
    # More specific approved forms replace general forms for the same Japanese source.
    def specificity(t): return (bool(t.get('message_ids')),bool(t.get('categories')),t.get('match','exact')=='exact')
    groups=defaultdict(list)
    for t in found:
        if t['status'] in ('canonical','exception'): groups[clean(t['source'])].append(t)
    winners={}
    for key, choices in groups.items():
        best=max(map(specificity,choices)); top=[t for t in choices if specificity(t)==best]
        if len(top)!=1: raise ValueError(f"{row['id']}: conflicting active terminology for {key}")
        winners[key]=top[0]
    return [t for t in found if t['status'] not in ('canonical','exception') or winners[clean(t['source'])] is t]


def has_form(text, form):
    # Literal word/phrase boundaries; inflections are explicitly listed in allowed forms.
    return bool(re.search(r'(?<!\w)'+re.escape(form)+r'(?!\w)', text, re.IGNORECASE))


def warnings(terms,row):
    if l10n.blocked(row) or not row.get('translation'): return []
    text = clean(row['translation']); result=[]
    for t in relevant(terms,row):
        if t['status'] in ('canonical','exception') and not any(has_form(text,x) for x in t['allowed']):
            result.append({'id':row['id'],'term_id':t['id'],'kind':'approved_form_missing','severity':'review'})
        if t['status'] in ACTIVE and any(has_form(text,x) for x in t.get('deprecated',[])):
            result.append({'id':row['id'],'term_id':t['id'],'kind':'deprecated_form_present','severity':'review'})
    return result


def seed(records):
    groups=defaultdict(lambda:defaultdict(list))
    for row in records.values():
        jp,en=row.get('source',''),row.get('translation','')
        if l10n.blocked(row) or not en or TAG.search(jp) or '\n' in jp or not 2<=len(jp)<=24: continue
        groups[clean(jp)][clean(en)].append(row['id'])
    terms=[]
    for jp,variants in sorted(groups.items()):
        if len(variants)<2: continue
        terms.append({'id':'candidate-'+hashlib.sha256(jp.encode()).hexdigest()[:16], 'source':jp,'status':'candidate','match':'exact',
                      'alternatives':[{'text':en,'count':len(ids),'message_ids':ids[:8]} for en,ids in sorted(variants.items(),key=lambda kv:(-len(kv[1]),kv[0]))]})
    return {'version':1,'terms':terms}


# Surface-form observations only. Japanese homographs, quotations and context need a reviewer.
PERSON = {'first_person': ['わたくし','わたし','あたし','ワタシ','アタシ','私','僕','ぼく','ボク','俺','オレ','おれ','わし','拙者','我輩','吾輩'],
          'second_person': ['あなた','貴方','貴女','お前','おまえ','あんた','アンタ','君','きみ','キミ','貴様','てめえ','そなた']}
RUBY_PAIR = re.compile(r'\{ruby:([^{}]+)\}([^{}]+)\{/ruby\}')
PARTICLE = r'(?=[はがをにのもとへでや、。！？!?\s]|$)'
ENDING = re.compile(r'(です|でした|ます|ました|ません|ございます|だよ|だね|だぞ|だぜ|かしら|なのよ|なのね|だろう|でしょう)(?=[。！？!?…\s]|$)')


def profiles(records):
    groups=defaultdict(list)
    for r in records.values():
        if r.get('speaker') and r.get('speaker_jp') and 'ambiguous_speaker' not in r.get('issues',[]): groups[r['speaker_jp']].append(r)
    result=[]
    for jp,rows in sorted(groups.items()):
        usable=[r for r in rows if not l10n.blocked(r) and r.get('event_alignment')!='different']
        hits=defaultdict(list); names=Counter(r['speaker'] for r in rows)
        for r in usable:
            text=clean(r['source'])
            for kind,forms in PERSON.items():
                for form in forms:
                    if re.search(re.escape(form)+PARTICLE,text): hits[(kind,form)].append(r['id'])
            for reading, base in sorted(set(RUBY_PAIR.findall(r['source']))):
                # Record explicit pronunciation separately from written surface forms.
                if any(base in forms or reading in forms for forms in PERSON.values()):
                    hits[('pronoun_ruby', base+'→'+reading)].append(r['id'])
            for form in sorted(set(ENDING.findall(text))): hits[('sentence_ending',form)].append(r['id'])
        observations=[{'kind':kind,'form':form,'message_count':len(ids),'message_ids':ids[:8]} for (kind,form),ids in sorted(hits.items(),key=lambda kv:(kv[0][0],-len(kv[1]),kv[0][1]))]
        # Pick representative lines from different scenes, rather than the longest speaker monologue.
        examples=[]; scenes=set()
        for r in usable:
            if r.get('scene') in scenes: continue
            scenes.add(r.get('scene')); examples.append(r['id'])
            if len(examples)>=20: break
        result.append({'id':'speaker-'+hashlib.sha256(jp.encode()).hexdigest()[:16],'name':names.most_common(1)[0][0],'name_ja':jp,'status':'provisional',
                       'candidate_speaker_ids':sorted({sid for r in rows for sid in r.get('candidate_speaker_ids',[])}),
                       'attributed_messages':len(rows),'usable_messages':len(usable),'name_variants':dict(names),'observations':observations,
                       'sample_message_ids':examples,'evidence':[{'message_id':o['message_ids'][0],'observation':o['kind']+': '+o['form']} for o in observations]})
    return {'version':1,'profiles':result,'note':'Surface-form counts, not confirmed pronouns, addressees, personalities or voice instructions; verify speaker and context.'}


def enrich(directory, glossary, profile_data=None):
    terms=glossary['terms']; prof={p['name_ja']:p for p in (profile_data or {}).get('profiles',[]) if p.get('name_ja')}
    for path in sorted(Path(directory).glob('batch_*.json')):
        b=json.loads(path.read_text(encoding='utf-8')); selected={}; speakers={}
        for row in b['items']:
            for t in relevant(terms,row): selected[t['id']]=t
            p=prof.get(row.get('speaker_jp'))
            if p:
                # Keep batch context compact; reviewers can consult the complete local profile.
                speakers[p['id']]={k:v for k,v in p.items() if k not in ('evidence','qualitative_evidence','sample_message_ids','observations')}
                speakers[p['id']]['observations']=[{k:v for k,v in o.items() if k!='message_ids'} for o in p.get('observations',[])]
        b['terminology']=[selected[k] for k in sorted(selected)]
        b['character_profiles']=[speakers[k] for k in sorted(speakers)]
        dump(path,b)


def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='cmd',required=True)
    for name in ('seed','profiles','lint'):
        s=sub.add_parser(name); s.add_argument('corpus'); s.add_argument('out')
        if name=='lint': s.add_argument('--glossary',required=True)
    s=sub.add_parser('enrich'); s.add_argument('batches'); s.add_argument('--glossary',required=True); s.add_argument('--profiles')
    a=p.parse_args()
    if a.cmd=='enrich':
        enrich(a.batches,load_glossary(a.glossary),json.loads(Path(a.profiles).read_text(encoding='utf-8')) if a.profiles else None); return
    if Path(a.corpus).resolve()==Path(a.out).resolve(): raise ValueError('refusing to overwrite corpus')
    records=l10n.read_jsonl(a.corpus)
    if a.cmd=='seed': data=seed(records)
    elif a.cmd=='profiles': data=profiles(records)
    else:
        terms=load_glossary(a.glossary)['terms']; data={'warnings':[w for r in records.values() for w in warnings(terms,r)]}
    dump(a.out,data)


if __name__=='__main__': main()

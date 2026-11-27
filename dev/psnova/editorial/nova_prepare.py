#!/usr/bin/env python3
"""Prepare a local Nova editorial corpus; never change the extracted originals."""
import argparse, collections as C, json, re, sqlite3
from pathlib import Path
from l10n import read_jsonl, write_jsonl, fixed_tags, norm
GLYPH=re.compile(r'〔#([0-9a-f]+)〕')
TAG=re.compile(r'\{[^{}]+\}')
# Initial grouping inferred from the source ID banks; not an authoritative game taxonomy.
BANKS={10000:'system',20000:'system',30000:'characters',50000:'skills',60000:'skills',90000:'weapons',100000:'weapons',110000:'cores',120000:'cores',130000:'attachments',140000:'attachments',150000:'affixes',160000:'system',170000:'system',180000:'enemies',200000:'tutorials',210000:'quests',230000:'quests',240000:'facilities',250000:'facilities',260000:'radio',280000:'quests',290000:'quests',300000:'quests',310000:'shields',320000:'shields',330000:'costumes',340000:'costumes',350000:'materials',360000:'materials',370000:'consumables',380000:'consumables',390000:'consumables',400000:'consumables',410000:'story_summaries',430000:'system',440000:'character_creation',500000:'character_creation',510000:'crew',520000:'crew',530000:'partner_dialogue',540000:'crew',550000:'food',560000:'gran_arts',570000:'gran_arts',580000:'techniques',590000:'techniques',600000:'lobby_actions',610000:'lobby_actions',620000:'radio',630000:'food',640000:'status',650000:'crew',660000:'classes',670000:'gigantes',680000:'gigantes',690000:'gigantes',700000:'search_team',710000:'search_team',730000:'search_team',740000:'facilities',750000:'credits',770000:'tutorials',780000:'tutorials',790000:'locations',800000:'tutorials',810000:'story_summaries',820000:'affixes',830000:'affixes'}

def visible(s): return re.sub(r'\s+','',TAG.sub('',s))
def event_records(root):
    # Files have CRLF record delimiters and LF within fields; standard CSV line splitting loses dialogue.
    events=C.defaultdict(list)
    for p in sorted(root.glob('scan/*_csv/*.csv')):
        raw=p.read_bytes()
        if b'MessageID,CueID,CharacterID,FacialID' not in raw: continue
        lines=raw.decode('cp932',errors='replace').split('\r\n')
        hdr=lines[1].split(','); col=hdr.index('Message_ja')
        for i,row in enumerate(lines[2:],2):
            f=row.split(',',col)
            if len(f)<=col or not re.fullmatch(r'\d{15}',f[0]):continue
            # Trailing columns are sometimes omitted; comma-bearing tails are not parsed as definitive text.
            events[f[0]].append({'table':str(p.relative_to(root)),'scene':p.stem,'order':i,'speaker_model':f[2] or None,'cue':f[1] or None,'text':f[col]})
    return events

def npc_records(root):
    names={}; refs=C.defaultdict(list)
    for bank in ('b','p'):
        p=root/f'scan/{bank}_csv/NpcBaseParameter.csv'
        if p.exists():
            for s in p.read_bytes().decode('cp932','replace').splitlines():
                f=s.split(',')
                if len(f)>27 and f[0].startswith('key') and f[1].isdigit():names[f[1]]={'jp':f[26],'model':f[4]}
        p=root/f'scan/{bank}_csv/NpcTalkParameter.csv'
        if p.exists():
            speaker=None; group=None; ordinal=0
            for i,s in enumerate(p.read_bytes().decode('cp932','replace').splitlines()):
                f=s.split(',')
                if len(f)<=26 or not f[0].startswith('key'):
                    speaker=None; group=None; ordinal=0; continue
                step=int(f[25]) if f[25].isdigit() else 0
                if step==1:
                    # Column 2 identifies generic crew groups, not a named NPC.
                    speaker=f[1] if f[1].isdigit() and not f[2] else None
                    group=f[0]; ordinal=1
                elif not f[1] and not f[2] and step>1 and step==ordinal+1:
                    ordinal=step
                else:
                    speaker=None; group=None; ordinal=0
                mid=f[26].strip()
                if mid.isdigit() and speaker and group:
                    refs[mid].append({'table':str(p.relative_to(root)),'scene':'npc:'+group,'speaker_id':speaker,'order':i,'speaker_jp':names.get(speaker,{}).get('jp')})
    return names,refs

def alignment(jp,other):
    a=visible(jp); b=visible(other)
    if a==b:return 'exact',[]
    # Replace placeholders with a single sentinel and compare all known characters.
    h=GLYPH.findall(a); mask=GLYPH.sub('\x00',a)
    if h and len(mask)==len(b) and all(x=='\x00' or x==y for x,y in zip(mask,b)):
        return 'wildcard',list(zip(h,[y for x,y in zip(mask,b) if x=='\x00']))
    return 'different',[]

def prepare(root,out,dbpath=None):
    src=read_jsonl(root/'messages.jsonl'); out.mkdir(parents=True,exist_ok=True)
    events=event_records(root); npc_names,npc=npc_records(root); name_map=json.loads((root/'names.json').read_text(encoding='utf-8'))
    glyphs=json.loads((root/'glyph_readings.json').read_text(encoding='utf-8')); prefixes=C.defaultdict(list)
    for h in glyphs:prefixes[h[:6]].append(h)
    votes=C.defaultdict(lambda:C.defaultdict(set)); alignments={}; aligncounts=C.Counter()
    for mid,refs in events.items():
        if mid not in src:continue
        # Use all versions for conflict detection, but never count duplicate rows as independent IDs.
        states=[]
        for ref in refs:
            state,pairs=alignment(src[mid]['japanese'],ref['text']);states.append(state)
            for short,ch in pairs:
                if len(prefixes[short])==1:votes[prefixes[short][0]][ch].add(mid)
        alignments[mid]='exact' if 'exact' in states else 'wildcard' if 'wildcard' in states else 'different';aligncounts[alignments[mid]]+=1
    proposed={}; evidence={}
    for h,choices in votes.items():
        prior=glyphs[h].get('candidate'); winner=next(iter(choices)) if len(choices)==1 else None
        # A conservative suggestion, never a verified reading. Reject contradictory earlier guesses.
        accepted=bool(winner and len(choices[winner])>=2 and (prior is None or prior==winner))
        if accepted:proposed[h[:6]]=winner
        evidence[h]={'choices':{c:sorted(ids) for c,ids in choices.items()},'previous_candidate':prior,'suggested':winner if accepted else None}
    records=[]; issues=C.Counter(); issue_rows=[]; cats=C.defaultdict(C.Counter); dup=C.defaultdict(lambda:C.defaultdict(list)); speaker_counts=C.Counter(); refs_by_speaker=C.defaultdict(list)
    for mid,r in src.items():
        jp=r['japanese']; en=r['english']; long=len(mid)>=12; bank=int(mid)//10000*10000 if not long else 'long:'+mid[0]
        category={'1':'story','2':'story_side','3':'npc_dialogue','4':'radio','5':'story_side'}.get(mid[0],'unclassified') if long else BANKS.get(bank,'unclassified')
        er=events.get(mid,[]); nr=npc.get(mid,[]); chosen=(er or nr or [None])[-1]; scene=chosen['scene'] if chosen else ('id:'+mid[:9] if long else None)
        # Use explicit model IDs and exact name mappings, never infer the player from a blank character field.
        speaker=None; speaker_jp=None; model=chosen.get('speaker_model') if chosen else None
        m=re.search(r'np(\d{4})',model or '',re.I)
        if m:speaker_jp=npc_names.get(m[1],{}).get('jp')
        elif chosen:speaker_jp=chosen.get('speaker_jp')
        if speaker_jp:speaker=name_map.get(speaker_jp,{}).get('english') or speaker_jp
        speaker_ids=set()
        for ref in er+nr:
            rm=re.search(r'np(\d{4})',ref.get('speaker_model') or '',re.I)
            sid=rm[1] if rm else ref.get('speaker_id')
            if sid:speaker_ids.add(sid)
        if len(speaker_ids)>1:speaker=None;speaker_jp=None
        flags=[]
        if len(speaker_ids)>1:flags.append('ambiguous_speaker')
        cats[category]['rows']+=1
        if not en:flags.append('missing_english')
        elif en.strip()==jp.strip():flags.append('identical_source_target')
        if GLYPH.search(jp):flags.append('unresolved_source_glyph')
        if en:
            if fixed_tags(jp)!=fixed_tags(en):flags.append('protected_token_difference')
            # Existing target may contain intentional Japanese; this is a review signal only.
            if re.search(r'[\u3040-\u30ff\u3400-\u9fff]',TAG.sub('',en)):flags.append('japanese_in_target')
        if alignments.get(mid)=='different':flags.append('event_source_differs')
        suggested=GLYPH.sub(lambda m:proposed.get(m[1],m[0]),jp)
        if suggested!=jp:flags.append('glyph_suggestions_available')
        if not GLYPH.search(jp) and en and 2<=len(visible(jp))<=24 and '\n' not in jp and not TAG.search(jp):dup[norm(jp)][norm(en)].append(mid)
        context=r.get('english_layout_context') or r.get('message_context'); constraints={'context':context,'protected_tokens':dict(fixed_tags(jp))}
        if context in ('dialogue','radio','caption'):constraints.update(width_px={'dialogue':483,'radio':462,'caption':483}[context],max_lines=2 if context=='caption' else 3)
        rec={'id':mid,'source':jp,'translation':en,'category':category,'bank':bank,'scene':scene,'speaker':speaker,'speaker_jp':speaker_jp,'context':context,'constraints':constraints,'source_archive':r['source_archive'],'source_path':r['source_path'],'provenance':'mixed-unresolved' if en else 'untranslated','source_review':'blocked-glyphs' if GLYPH.search(jp) else 'decoded-unreviewed','issues':flags}
        if speaker_ids:rec['candidate_speaker_ids']=sorted(speaker_ids)
        if chosen:rec['context_locator']={k:v for k,v in chosen.items() if k!='text'}
        if er:rec['event_alignment']=alignments.get(mid);rec['event_source_reference']=er[-1]['text']
        if suggested!=jp:rec['suggested_source_unverified']=suggested
        if speaker:speaker_counts[speaker]+=1;refs_by_speaker[speaker].append(mid)
        for f in flags:issues[f]+=1;cats[category][f]+=1
        if flags:issue_rows.append({'id':mid,'category':category,'issues':flags})
        records.append(rec)
    # Keep original source and tokens external; order editorial scenes by source table when known.
    records.sort(key=lambda r:(r['category'],r['scene'] or '',r.get('context_locator',{}).get('order',int(r['id'])),int(r['id'])))
    write_jsonl(out/'corpus.jsonl',records);write_jsonl(out/'issues.jsonl',issue_rows)
    def dump(n,obj):(out/n).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
    dump('glyph-evidence.json',evidence);dump('category-stats.json',cats)
    conflicts=[{'source':jp,'variants':v} for jp,v in dup.items() if len(v)>1];conflicts.sort(key=lambda x:-sum(map(len,x['variants'].values())))
    dump('nova-terminology-conflicts.json',conflicts)
    dump('speaker-index.json',[{'name':s,'message_ids':refs_by_speaker[s],'count':n} for s,n in speaker_counts.most_common()])
    matches=[]
    if dbpath:
        db=sqlite3.connect(dbpath);db.row_factory=sqlite3.Row
        for jp,variants in dup.items():
            rows=[dict(x) for x in db.execute("SELECT corpus,locale,target,status,count(*) occurrences FROM segment WHERE source=? AND target<>'' GROUP BY corpus,locale,target,status ORDER BY occurrences DESC",(jp,))]
            if rows:matches.append({'source':jp,'nova_variants':variants,'reference_candidates':rows})
        dump('reference-candidates.json',matches)
        db.close()
    stats={'messages':len(records),'english':sum(bool(r['translation']) for r in records),'issue_counts':issues,'event_ids':len(events),'event_alignment':aligncounts,'npc_ids':len(npc),'known_speaker_messages':sum(speaker_counts.values()),'known_speakers':len(speaker_counts),'glyph_evidence_count':len(evidence),'glyph_suggestions':len(proposed),'glyph_conflicts':sum(len(v)>1 for v in votes.values()),'fully_suggested_glyph_rows':sum('suggested_source_unverified' in r and not GLYPH.search(r['suggested_source_unverified']) for r in records),'short_source_variants':len(conflicts),'exact_reference_matches':len(matches),'reference_candidates_differ':sum(any(x['target'] not in m['nova_variants'] for x in m['reference_candidates']) for m in matches)}
    dump('stats.json',stats);return stats
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('dataset',type=Path);p.add_argument('out',type=Path);p.add_argument('--reference-db',type=Path);a=p.parse_args();print(json.dumps(prepare(a.dataset,a.out,a.reference_db),ensure_ascii=False,indent=2))

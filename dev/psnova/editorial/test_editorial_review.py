import json, tempfile, unittest
from pathlib import Path
import editorial_review as er
import l10n
from nova_prepare import npc_records


class ReviewTests(unittest.TestCase):
    def test_glossary_scope(self):
        base={'id':'general','source':'星','status':'canonical','allowed':['Star'],'reason':'test','evidence':['fixture']}
        special={**base,'id':'special','status':'exception','allowed':['Sun'],'message_ids':['2']}
        row={'id':'2','source':'星','translation':'Sun','category':'story'}
        self.assertEqual(er.warnings([base,special],row),[])
        self.assertEqual(er.warnings([special,base],{**row,'id':'3'})[0]['term_id'],'general')
        with self.assertRaises(ValueError): er.relevant([base,{**base,'id':'duplicate'}],row)
        self.assertFalse(er.has_form('Starlight','Star'))
        self.assertTrue(er.has_form('A star.','Star'))
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'terms.json'; er.dump(path,{'version':1,'terms':[base,special]})
            self.assertEqual(len(er.load_glossary(path)['terms']),2)
            er.dump(path,{'version':1,'terms':[{**special,'message_ids':[]}]})
            with self.assertRaises(ValueError): er.load_glossary(path)
    def test_profiles_seed_enrich(self):
        a={'id':'1','source':'私が星です。','translation':'A star.','speaker':'A','speaker_jp':'エー','scene':'a'}
        b={**a,'id':'2','source':'俺が星だぞ。','event_alignment':'different'}
        c={**a,'id':'3','source':'青星','translation':'Star'}
        d={**c,'id':'4','translation':'Sun'}
        rows={r['id']:r for r in (a,b,c,d)}
        p=er.profiles(rows)['profiles'][0]; self.assertEqual(p['usable_messages'],3)
        self.assertIn('私',[o['form'] for o in p['observations']]); self.assertNotIn('俺',[o['form'] for o in p['observations']])
        g=er.seed(rows); self.assertEqual(len(g['terms']),1)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td); l10n.write_jsonl(path/'corpus.jsonl',rows.values()); l10n.batch(path/'corpus.jsonl',path/'batches',10)
            manifest=path/'batches/assignments.json'; before=manifest.read_bytes()
            er.enrich(path/'batches',g,{'profiles':[p]})
            batch=json.loads((path/'batches/batch_0000.json').read_text()); self.assertEqual(len(batch['terminology']),1)
            self.assertEqual(before,manifest.read_bytes()); self.assertEqual(batch['items'][0]['base_sha256'],l10n.digest(a))
    def test_npc_continuation(self):
        def row(key,npc,crew,step,mid):
            a=['']*27; a[0]=key; a[1]=npc; a[2]=crew; a[25]=step; a[26]=mid; return ','.join(a)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'scan/p_csv'; p.mkdir(parents=True)
            (p/'NpcTalkParameter.csv').write_text('\n'.join([row('key1','5015','','1','1'),row('key2','','','2','2'),row('key3','','110','1','3'),row('key4','','','2','4'),row('key5','5001','','1','5'),row('key6','','','3','6')]))
            _,refs=npc_records(Path(td)); self.assertEqual(set(refs),{'1','2','5'})
    def test_ruby_and_katakana(self):
        a={'id':'1','source':'{ruby:わたくし}私{/ruby}は星です。','translation':'A star.','speaker':'A','speaker_jp':'エー','scene':'a'}
        b={**a,'id':'2','source':'ボクが星です。'}
        rows={r['id']:r for r in (a,b)}
        profile=er.profiles(rows)['profiles'][0]
        observed={(o['kind'],o['form']) for o in profile['observations']}
        self.assertIn(('pronoun_ruby','私→わたくし'),observed)
        self.assertIn(('first_person','ボク'),observed)
        profile['voice_guidance']='Use a calm register.'
        profile['qualitative_evidence']=[{'message_id':'1','observation':'fixture'}]
        with tempfile.TemporaryDirectory() as td:
            path=Path(td); l10n.write_jsonl(path/'corpus.jsonl',rows.values()); l10n.batch(path/'corpus.jsonl',path/'batches',10)
            er.enrich(path/'batches',{'terms':[]},{'profiles':[profile]})
            enriched=json.loads((path/'batches/batch_0000.json').read_text())['character_profiles'][0]
            self.assertEqual(enriched['voice_guidance'],profile['voice_guidance'])
            self.assertNotIn('qualitative_evidence',enriched)

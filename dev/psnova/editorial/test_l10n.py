import json, sqlite3, tempfile, unittest
from pathlib import Path
import l10n
class Test(unittest.TestCase):
    def test_search(self):
        db=l10n.connect(':memory:'); l10n.init(db)
        l10n.put(db,[('fixture','en-US','青い星','Blue star','a','1','x','','Confirmed',None,None),('fixture','en-SG','青い星','Azure star','a','1','x','','exported',None,None)])
        l10n.rebuild(db)
        self.assertEqual(len(l10n.search(db,'青い星')),2)
        self.assertEqual(len(l10n.search(db,'青い')),2)
        self.assertEqual(l10n.search(db,'STAR','en-US')[0]['target'],'Blue star')
        self.assertEqual(len(l10n.candidates(db)[0]['choices']),2)
    def test_tokens(self):
        r={'source':'使う{8099:01}{8094:0001}'}
        self.assertEqual(l10n.lint(r,'Use {8099:01} {8094:0001}'),[])
        self.assertTrue(l10n.lint(r,'Use {8099:01}'))
        self.assertTrue(l10n.lint(r,'{/color}Use {8099:01}{8094:0001}{8081:03}'))
        self.assertTrue(l10n.lint(r,'Use {8099:01}{8094:0001}{broken'))
    def test_batch_merge(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); corpus=p/'corpus.jsonl'; out=p/'out.jsonl'; patch=p/'patch.jsonl'
            r={'id':'001','source':'星','translation':'Star','scene':'s1'}
            l10n.write_jsonl(corpus,[r]); self.assertEqual(l10n.batch(corpus,p/'batches',1),1)
            h=json.loads((p/'batches/batch_0000.json').read_text())['items'][0]['base_sha256']
            l10n.write_jsonl(patch,[{'id':'001','translation':'A star','base_sha256':h,'assignment_id':'batch_0000','reason':'Context'}])
            self.assertEqual(l10n.merge(corpus,[patch],out,p/'batches/assignments.json'),1)
            self.assertEqual(l10n.read_jsonl(out)['001']['translation'],'A star')
            with self.assertRaises(ValueError): l10n.merge(corpus,[patch,patch],out,p/'batches/assignments.json')
            with self.assertRaises(ValueError): l10n.merge(out,[patch],p/'out2.jsonl',p/'batches/assignments.json')
            with self.assertRaises(ValueError): l10n.merge(corpus,[patch],corpus,p/'batches/assignments.json')
            self.assertEqual(l10n.read_jsonl(corpus)['001']['translation'],'Star')
    def test_blocked_source(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); corpus=p/'corpus.jsonl'; patch=p/'patch.jsonl'; out=p/'out.jsonl'
            a={'id':'1','source':'星〔#abcdef〕','translation':'Star','scene':'a'}
            b={'id':'2','source':'星','translation':'Star','scene':'a'}
            l10n.write_jsonl(corpus,[a,b]); self.assertEqual(l10n.batch(corpus,p/'batches',2),1)
            batch=json.loads((p/'batches/batch_0000.json').read_text())
            self.assertEqual([r['id'] for r in batch['items']],['2'])
            self.assertEqual([r['id'] for r in batch['read_only_neighbors']],['1'])
            l10n.write_jsonl(patch,[{'id':'1','base_sha256':l10n.digest(a),'translation':'Star','reason':'test'}])
            with self.assertRaisesRegex(ValueError,'blocked source'): l10n.merge(corpus,[patch],out,p/'batches/assignments.json')
            self.assertFalse(out.exists())
    def test_duplicate_id(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.jsonl'; l10n.write_jsonl(p,[{'id':'1'},{'id':'1'}])
            with self.assertRaises(ValueError): l10n.read_jsonl(p)
if __name__=='__main__': unittest.main()

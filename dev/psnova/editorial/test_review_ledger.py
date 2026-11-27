import tempfile
import unittest
from pathlib import Path
import l10n
import review_ledger as rl


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        p=Path(self.tmp.name); self.corpus=p/'corpus.jsonl'; self.manifest=p/'batches/assignments.json'
        self.old={'id':'1','source':'星','translation':'Star'}
        l10n.write_jsonl(self.corpus,[self.old]); l10n.batch(self.corpus,p/'batches',1)
        self.records=l10n.read_jsonl(self.corpus)
        self.edit={'id':'1','assignment_id':'batch_0000','base_sha256':l10n.digest(self.old),'actor':'editor','reason':'fixture','decision':'revise','severity':'minor','translation':'A star'}
        self.review={'id':'1','actor':'reviewer','reason':'fixture','verdict':'agree','editor_sha256':l10n.digest(self.edit)}

    def evaluate(self,e=None,r=None,a=None):
        return rl.evaluate(self.records,self.manifest,{'1':e} if e else {},{'1':r} if r else {},{'1':a} if a else {})

    def test_approval_and_partial(self):
        self.assertFalse(self.evaluate()[0]['complete'])
        self.assertFalse(self.evaluate(self.edit)[0]['complete'])
        report,ledger,revised=self.evaluate(self.edit,self.review)
        self.assertTrue(report['complete']); self.assertEqual(revised['1']['translation'],'A star')
        self.assertEqual(revised['1']['review']['ledger_sha256'],l10n.digest(ledger[0]))
        keep={k:v for k,v in self.edit.items() if k!='translation'}; keep.update(decision='keep',severity='none')
        report,_,revised=self.evaluate(keep,{**self.review,'editor_sha256':l10n.digest(keep)})
        self.assertEqual(report['states'],{'approved-keep':1}); self.assertFalse(revised)

    def test_disagreement_and_query(self):
        r={**self.review,'verdict':'disagree'}
        self.assertEqual(self.evaluate(self.edit,r)[0]['states'],{'needs-resolution':1})
        a={'id':'1','actor':'lead','reason':'fixture','decision':'keep','reviewer_sha256':l10n.digest(r)}
        self.assertTrue(self.evaluate(self.edit,r,a)[0]['complete'])
        query={k:v for k,v in self.edit.items() if k!='translation'}; query.update(decision='query',severity='query')
        agree={**self.review,'editor_sha256':l10n.digest(query)}
        self.assertFalse(self.evaluate(query,agree)[0]['complete'])
        self.assertTrue(self.evaluate(query,agree,{**a,'reviewer_sha256':l10n.digest(agree)})[0]['complete'])

    def test_rejections(self):
        for e,r in [(self.edit,{**self.review,'actor':' EDITOR '}),(self.edit,{**self.review,'editor_sha256':'bad'}),({**self.edit,'assignment_id':'wrong'},None),({**self.edit,'translation':'Star'},None),({**self.edit,'translation':'星'},None)]:
            with self.assertRaises(ValueError): self.evaluate(e,r)
        r={**self.review,'verdict':'disagree'}
        a={'id':'1','actor':'reviewer','reason':'fixture','decision':'keep','reviewer_sha256':l10n.digest(r)}
        with self.assertRaises(ValueError): self.evaluate(self.edit,r,a)
        with self.assertRaises(ValueError): self.evaluate(self.edit,r,{**a,'actor':'lead','reviewer_sha256':'bad'})
        with self.assertRaises(ValueError): self.evaluate(self.edit,self.review,{**a,'actor':'lead'})

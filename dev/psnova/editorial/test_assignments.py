import json, tempfile, unittest
from pathlib import Path
import l10n


class AssignmentTests(unittest.TestCase):
    def test_ownership_and_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); corpus=p/'corpus.jsonl'; patch=p/'patch.jsonl'; out=p/'out.jsonl'
            a={'id':'1','source':'星','translation':'Star','scene':'a'}
            b={'id':'2','source':'月','translation':'Moon','scene':'a'}
            l10n.write_jsonl(corpus,[a,b]); l10n.batch(corpus,p/'batches',1)
            manifest=p/'batches/assignments.json'
            def proposal(r,owner):
                return {'id':r['id'],'base_sha256':l10n.digest(r),'assignment_id':owner,'translation':'Test','reason':'Fixture'}
            l10n.write_jsonl(patch,[proposal(b,'batch_0000')])
            with self.assertRaisesRegex(ValueError,'outside assigned'): l10n.merge(corpus,[patch],out,manifest)
            l10n.write_jsonl(patch,[proposal(a,'batch_0000'),proposal(b,'batch_0001')])
            with self.assertRaisesRegex(ValueError,'mixed assignments'): l10n.merge(corpus,[patch],out,manifest)
            l10n.write_jsonl(patch,[proposal(a,'batch_0000')]); data=json.loads(manifest.read_text())
            data['assignments']['batch_0001']['1']=l10n.digest(a); manifest.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'duplicate assignment'): l10n.merge(corpus,[patch],out,manifest)
            self.assertFalse(out.exists())

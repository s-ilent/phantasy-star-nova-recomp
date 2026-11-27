import unittest, tempfile, json
from pathlib import Path
import pair_text, l10n

class PairTests(unittest.TestCase):
    def test_structure_and_duplicates(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'input.jsonl'
            def row(key,group,text,archive='a'):
                return dict(archive=archive, member='x.text', category='menu', key=key, group=group, text=text)
            rows=[row('ok',0,'例'),row('ok',1,'Example'),row('dupe',0,'A'),row('dupe',0,'B'),row('dupe',1,'C'),row('missing',0,'X'),row('ok',0,'別','b'),row('ok',1,'Other','b'),row('blank',0,'例'),row('blank',1,''),row('redacted',0,'例'),row('redacted',1,'***')]
            p.write_text('\n'.join(json.dumps(r) for r in rows),encoding='utf-8')
            yes,no,counts=pair_text.pair(pair_text.load(p,0),pair_text.load(p,1))
            self.assertEqual(counts,dict(paired=2,ambiguous_duplicate=1,missing_target=1,blank=1,redacted=1))
            with l10n.connect(Path(d)/'reference.sqlite') as db:
                pair_text.store(db,yes,'test-v1','en-US')
                self.assertEqual(l10n.search(db,'例',exact=True)[0]['target'],'Example')
                with self.assertRaises(ValueError): pair_text.store(db,yes,'test-v1','en-US')
                self.assertEqual(db.execute('pragma integrity_check').fetchone()[0],'ok')
    def test_bad_group(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.jsonl';p.write_text('{"group":"0"}')
            with self.assertRaises(ValueError): pair_text.load(p,0)

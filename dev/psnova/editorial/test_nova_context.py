import json, tempfile, unittest
from pathlib import Path
import nova_context as nc


class ContextTests(unittest.TestCase):
    def test_occurrences(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'names.json').write_text('{}')
            for bank in ('b','p'):
                path=p/'scan'/f'{bank}_csv'; path.mkdir(parents=True)
                (path/'Event.csv').write_bytes(('DataStart\r\nMessageID,CueID,CharacterID,FacialID,MouthOff,OrderID,MessageName,Message_ja,User_ja,Category,Option\r\n100000010010001,1,np5001a,0,,,,一\r\n100000010010001,2,np5001a,0,,,,二\r\n100000010010002,3,,0,,,,三\r\n').encode('cp932'))
            def npc(key,who,crew,step,mid):
                f=['']*29;f[0]=key;f[1]=who;f[2]=crew;f[25]=step;f[26]=mid;return ','.join(f)
            (p/'scan/p_csv/NpcTalkParameter.csv').write_text('\n'.join([npc('key1','','10','1','3'),npc('key2','','','2','4'),npc('key3','','','5','5')]))
            ids=['100000010010001','3','4','5','6']
            records={i:{'id':i,'source':'星','translation':'Star','bank':0} for i in ids}
            index=nc.build_index(p,records); scenes=index['scenes']
            event=[s for s in scenes if s['kind']=='event-table'];self.assertEqual(len(event),2)
            self.assertEqual([r['order'] for r in event[0]['lines']],[2,3,4])
            self.assertEqual(len(nc.view(event[0],records,{},ids[0])['lines']),3)
            self.assertIsNone(nc.view(event[0],records,{})['lines'][-1]['source'])
            npc_scene=next(s for s in scenes if s['kind']=='npc-table')
            self.assertEqual([r['crew_group'] for r in npc_scene['lines']],['10','10'])
            self.assertEqual(len([s for s in scenes if s['kind']=='npc-unresolved']),1)
            self.assertEqual(len([s for s in scenes if s['kind']=='bank-group']),1)
            self.assertEqual(len(list(nc.search(index,records,ids[0]))),2)
            out=p/'index.json';out.write_text(json.dumps(index));self.assertEqual(nc.load_index(out,records),index)
            records['6']['translation']='</script><script>bad()</script>'
            with self.assertRaises(ValueError):nc.load_index(out,records)
            nc.browse(index,records,{},p/'browser.html');html=(p/'browser.html').read_text()
            self.assertNotIn('</script><script>bad()',html);self.assertIn('\\u003c/script>',html)
    def test_revision_source_guard(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'revised.jsonl';r={'id':'1','source':'星','translation':'Star'}
            p.write_text(json.dumps({**r,'translation':'A star'}));self.assertEqual(nc.load_revision(p,{'1':r}),{'1':'A star'})
            p.write_text(json.dumps({**r,'source':'月'}))
            with self.assertRaises(ValueError):nc.load_revision(p,{'1':r})

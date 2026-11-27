import unittest,tempfile
from pathlib import Path
from nova_prepare import alignment,event_records
class NovaTests(unittest.TestCase):
    def test_alignment(self):
        self.assertEqual(alignment('原{ruby:ほん}本{/ruby}\n','原本'),('exact',[]))
        self.assertEqual(alignment('原〔#abcdef〕','原本'),('wildcard',[('abcdef','本')]))
        self.assertEqual(alignment('原〔#abcdef〕','変更'),('different',[]))
    def test_multiline_csv(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'scan/b_csv';p.mkdir(parents=True)
            (p/'TEST.csv').write_bytes('DataStart\r\nMessageID,CueID,CharacterID,FacialID,MouthOff,OrderID,MessageName,Message_ja,User_ja,Category,Option\r\n100000010010001,0,np5001a_test,0,,,,一行\n二行\r\n100000010020001,1,np5002a_test,0,,,,次\r\n'.encode('cp932'))
            r=event_records(Path(d));self.assertEqual(len(r),2);self.assertEqual(r['100000010010001'][0]['text'],'一行\n二行')
if __name__=='__main__':unittest.main()

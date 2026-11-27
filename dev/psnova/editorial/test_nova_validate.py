import tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
import l10n
from nova_validate import inspect_message, render, select_rows, validate_row

LOCAL=0x391

class FakeRmd:
    def __init__(self, tokens, mid=12, width=21):
        self.id=mid; self.W=128; self.atlas_width=256; self.atlas_height=128
        self.recs=[(width,10,0,0,0,21/128,21/64)]
        self._tokens=tokens
    def tokens(self): return self._tokens
    def glyph(self,i):
        import numpy as np
        return np.full((42,42),200,dtype=np.uint8)

class ValidationTests(unittest.TestCase):
    def test_metrics(self):
        basic=FakeRmd([])
        r=FakeRmd([('c',LOCAL),('ctl',0x8099,b'\x01'),('nl',),('c',0x81)])
        m=inspect_message(r,basic,'dialogue',LOCAL)
        self.assertEqual(m['widths_px'],[45,21]); self.assertEqual(m['glyphs'],2); self.assertFalse(m['errors'])
        self.assertEqual(inspect_message(r,basic,None,LOCAL)['layout_status'],'unknown-context')
        self.assertTrue(inspect_message(FakeRmd([('c',LOCAL)]*129),basic,None,LOCAL)['errors'])
        self.assertTrue(inspect_message(FakeRmd([('c',LOCAL)],width=10),basic,'caption',LOCAL)['errors'])
        with self.assertRaises(ValueError): inspect_message(FakeRmd([('c',LOCAL+9)]),basic,'dialogue',LOCAL)
    def test_preview(self):
        try: import PIL, numpy
        except ImportError: self.skipTest('preview dependencies unavailable')
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.png'; render(FakeRmd([('c',LOCAL),('ctl',0x8094,b'\x01\x00')]),FakeRmd([]),None,LOCAL,p)
            with Image.open(p) as im: self.assertEqual(im.size,(154,64))
    def test_selection(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); a=p/'a.jsonl'; b=p/'b.jsonl'; r={'id':'12','source':'星','translation':'Star'}
            l10n.write_jsonl(a,[r]); l10n.write_jsonl(b,[{**r,'translation':'A star'}]); self.assertEqual(len(select_rows(b,baseline=a)),1)
            self.assertEqual(select_rows(a,ids=['12']),[r])
            l10n.write_jsonl(b,[{**r,'source':'月'}]);
            with self.assertRaisesRegex(ValueError,'source changed'): select_rows(b,baseline=a)
    def test_encoder_adapter(self):
        original=FakeRmd([]); encoded=FakeRmd([('c',LOCAL),('ctl',0x8099,b'\x01')])
        archive=SimpleNamespace(has=lambda name:True,read=lambda name:b'original')
        class Encoder:
            def encode(self,mid,text,template,context):
                assert mid==12 and template==b'original' and context=='radio'; return b'encoded'
            def parse(self,text):return [('ctl',0x8099,'01')]
        row={'id':'12','source':'星{8099:01}','translation':'Star {8099:01}','context':'dialogue'}
        result=validate_row(row,Encoder(),{'base':archive,'patch':archive},{'12':['old','radio']},lambda data:original if data==b'original' else encoded,FakeRmd([]),LOCAL)
        self.assertEqual(result['context'],'radio'); self.assertFalse(result['errors'])
        encoded._tokens=[('c',LOCAL)]
        self.assertTrue(validate_row(row,Encoder(),{'base':archive,'patch':archive},{'12':['old','radio']},lambda data:original if data==b'original' else encoded,FakeRmd([]),LOCAL)['errors'])

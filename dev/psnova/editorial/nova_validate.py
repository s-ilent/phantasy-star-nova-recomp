"""Validate and preview Nova messages with the release RMD encoder, without building a CPK."""
import argparse
import hashlib
import json
import os
import re
import sys
from contextlib import ExitStack
from pathlib import Path
import l10n

PACK = Path(__file__).resolve().parents[3] / 'packs/PCSG00351/english'
WIDTHS = {'dialogue': 483, 'radio': 462, 'caption': 483}
CONTROL_WIDTHS = {0x8099: 24, 0x8094: 48}


def inspect_message(rmd, basic, context, local_base):
    """Measure the encoded records, not the unwrapped input string."""
    caption = context == 'caption'
    widths = [0]
    glyphs = 0
    controls = []
    errors = []
    for token in rmd.tokens():
        if token[0] == 'nl':
            widths.append(0)
        elif token[0] == 'c':
            glyphs += 1
            code = token[1]
            owner = rmd if code >= local_base else basic
            index = code - local_base if owner is rmd else ((code & 0x7f) | ((code >> 8) << 7)) - 1
            if not 0 <= index < len(owner.recs):
                raise ValueError(f'out-of-range glyph {code:#x}')
            rec = owner.recs[index]
            if caption and owner is rmd and (rec[0] != 21 or round((rec[5]-rec[3])*rmd.W) != 21):
                errors.append('caption cell would stretch')
            widths[-1] += 21 if caption else rec[0]
        elif token[0] == 'ctl':
            controls.append({'code': f'{token[1]:04x}', 'parameter': token[2].hex()})
            widths[-1] += CONTROL_WIDTHS.get(token[1], 0)
    if glyphs > 128:
        errors.append('exceeds 128-glyph draw limit')
    if context in WIDTHS:
        if max(widths) > WIDTHS[context]:
            errors.append('line width exceeds context limit')
        if len(widths) > (2 if caption else 3):
            errors.append('too many lines for context')
        if not caption and any(a <= b for a, b in zip(widths, widths[1:])):
            errors.append('dialogue widths are not strictly descending')
    return {'widths_px': widths, 'glyphs': glyphs, 'lines': len(widths), 'controls': controls,
            'atlas_px': [rmd.atlas_width, rmd.atlas_height], 'errors': sorted(set(errors)),
            'layout_status': 'failed' if errors else 'checked' if context in WIDTHS else 'unknown-context'}


def render(rmd, basic, context, local_base, output):
    """Glyph-atlas preview at logical pixel scale; placeholders are not actual in-game icons."""
    from PIL import Image, ImageDraw
    import numpy as np
    metrics = inspect_message(rmd, basic, context, local_base)
    width = max(max(metrics['widths_px']), WIDTHS.get(context, 0), 1)
    if width > 16384 or metrics['lines'] > 256:
        raise ValueError('preview dimensions exceed safety limit')
    im = Image.new('RGB', (width+8, 24*metrics['lines']+8), (20, 26, 34))
    x, y = 4, 4
    for token in rmd.tokens():
        if token[0] == 'nl':
            x, y = 4, y+24
        elif token[0] == 'c':
            code = token[1]
            owner = rmd if code >= local_base else basic
            index = code-local_base if owner is rmd else ((code & 0x7f) | ((code >> 8) << 7))-1
            rec = owner.recs[index]
            w = 21 if context == 'caption' else rec[0]
            g = owner.glyph(index)
            if w and g.size:
                glyph = Image.fromarray(np.asarray(g, dtype=np.uint8)).resize((w,21), Image.Resampling.LANCZOS)
                im.paste((242, 242, 242), (x,y,x+w,y+21), glyph)
            x += w
        elif token[0] == 'ctl' and token[1] in CONTROL_WIDTHS:
            w = CONTROL_WIDTHS[token[1]]
            draw = ImageDraw.Draw(im)
            draw.rectangle((x+1,y+2,x+w-2,y+18), outline=(135,160,180))
            draw.text((x+3,y+5),'BTN' if token[1]==0x8099 else 'VALUE', fill=(190,205,220))
            x += w
    im.resize((im.width*2, im.height*2), Image.Resampling.NEAREST).save(output)


def select_rows(corpus, ids=None, baseline=None, all_rows=False):
    records = l10n.read_jsonl(corpus)
    if sum(bool(x) for x in (ids, baseline, all_rows)) != 1:
        raise ValueError('select exactly one of --id, --changed-from, --all')
    if baseline:
        old = l10n.read_jsonl(baseline)
        if old.keys() != records.keys():
            raise ValueError('baseline and revised IDs differ')
        for mid, row in records.items():
            if row.get('source') != old[mid].get('source'):
                raise ValueError(f'{mid}: original source changed')
        return [row for mid,row in records.items() if row.get('translation') != old[mid].get('translation')]
    if all_rows:
        return [row for row in records.values() if row.get('translation')]
    if len(set(ids)) != len(ids) or any(mid not in records for mid in ids):
        raise ValueError('duplicate or unknown selected ID')
    return [records[mid] for mid in ids]


def validate_row(row, encoder, archives, recipes, rmd_type, basic, local_base, out=None):
    mid = row['id']
    if not re.fullmatch(r'0|[1-9][0-9]{0,19}', mid) or int(mid) >= 2**64:
        raise ValueError('invalid Nova message ID')
    if l10n.blocked(row):
        raise ValueError('unresolved Japanese glyphs')
    text = row.get('translation')
    errors = l10n.lint(row,text)
    if errors:
        raise ValueError('; '.join(errors))
    name = f'msg_{mid}.rmd'
    template = next((archives[k].read(name) for k in ('patch','base') if archives[k].has(name)),None)
    if template is None:
        raise ValueError('original RMD template missing')
    if rmd_type(template).id != int(mid):
        raise ValueError('original template ID mismatch')
    context = recipes[mid][1] if mid in recipes else row.get('context')
    data = encoder.encode(int(mid),text,template=template,context=context)
    rmd = rmd_type(data)
    if rmd.id != int(mid):
        raise ValueError('encoded ID mismatch')
    result = inspect_message(rmd,basic,context,local_base)
    # Compare emitted control tokens against the encoder's parsed input, including order.
    want = [(t[1],bytes.fromhex(t[2])) if t[0]=='ctl' else (0x8082,b'') for t in encoder.parse(text) if t[0] in ('ctl','end')]
    got = [(t[1],t[2]) for t in rmd.tokens() if t[0]=='ctl']
    if want != got:
        result['errors'].append('encoded controls differ from parsed translation')
        result['layout_status'] = 'failed'
    result.update(id=mid,context=context,context_source='release-recipe' if mid in recipes else 'corpus-unverified',encoded_bytes=len(data))
    if out is not None:
        render(rmd,basic,context,local_base,out/f'{mid}.png')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('corpus',type=Path); p.add_argument('--base',type=Path,required=True); p.add_argument('--update',type=Path,required=True)
    p.add_argument('--font',type=Path,default=PACK/'fonts/K2D-Medium.ttf'); p.add_argument('--fallback-font',type=Path,default=Path(os.environ.get('WINDIR',r'C:\Windows'))/'Fonts/segoeuib.ttf')
    s=p.add_mutually_exclusive_group(required=True); s.add_argument('--id',action='append'); s.add_argument('--changed-from',type=Path); s.add_argument('--all',action='store_true')
    p.add_argument('--out',type=Path,required=True); p.add_argument('--preview',action='store_true')
    a=p.parse_args(); rows=select_rows(a.corpus,a.id,a.changed_from,a.all)
    if not rows:
        raise ValueError('no messages selected')
    # Import the exact production implementation only when validating local game assets.
    sys.path.insert(0,str(PACK))
    import build_text as prod
    from rmdlib import LOCAL_BASE
    from localize import ORIGINALS, BASE, PATCH
    for path,expected in ((a.base,ORIGINALS['app0',BASE]),(a.update,ORIGINALS['patch0',PATCH])):
        with path.open('rb') as f:
            digest=hashlib.sha256()
            for block in iter(lambda:f.read(1024*1024),b''):
                digest.update(block)
            if digest.hexdigest()!=expected:
                raise ValueError(f'not the supported original archive: {path}')
    a.out.mkdir(parents=True,exist_ok=False)
    results=[]
    with ExitStack() as stack:
        archives={}
        for key,path in [('base',a.base),('patch',a.update)]:
            cpk=prod.Cpk(path); stack.callback(cpk.close); archives[key]=prod.Archive(cpk)
        codes,pictures,charset=prod.original_font_data(archives)
        encoder=prod.Encoder(str(a.font),str(a.fallback_font),prod.recipe('font-metrics'),codes,pictures,charset)
        basic=prod.Rmd(charset); recipes=prod.recipe('messages')
        for row in rows:
            try:
                results.append(validate_row(row,encoder,archives,recipes,prod.Rmd,basic,LOCAL_BASE,a.out if a.preview else None))
            except (ValueError,IndexError,KeyError) as exc:
                results.append({'id':row['id'],'errors':[str(exc)],'layout_status':'failed'})
    failures=sum(bool(r['errors']) for r in results)
    report={'selected':len(results),'failed':failures,'unknown_layout':sum(r['layout_status']=='unknown-context' for r in results),'messages':results}
    (a.out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='messages'}))
    return int(bool(failures))


if __name__=='__main__':
    try: sys.exit(main())
    except (ValueError,OSError) as exc: sys.exit(str(exc))

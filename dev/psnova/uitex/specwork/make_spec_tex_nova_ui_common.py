"""Write dump/psnova-l10n/uitex/specs/tex_nova_ui_common.json (common UI parts, update copy), 2026-11-19.

Three groups, 22 labels:
  * button guide column (x852-1023, y574-699): white with a dark outline on transparent; boxes = the Cast_Camera
    sprite cells of update ui_common.crbpj (docs/psnova/ui-textures-research.md), right-aligned like the Japanese.
  * orange touch buttons (two rows): orange text on a flat (24,24,24) rounded button; boxes = button interior minus
    2 px at the sides and the rounded rows (alpha runs measured on the texture), cleared with that flat colour.
  * small tags with a leader dot: yellow 装着/右装着/左装着/装備, cyan ステルス, red 装備不可; the tag body is an opaque
    gradient inside a bright frame, so the Japanese is inpainted; boxes stay inside the frame (its slanted corners
    included), measured on luma/alpha dumps.
Sizes: one size per group where the cells allow it (the guide rows keep a common size), set per language.
"""
import json, os
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))
OUT = os.path.join(ROOT, 'dump', 'psnova-l10n', 'uitex', 'specs', 'tex_nova_ui_common.json')

GUIDE = dict(clear='transparent', align='right', valign='center', color=[255, 255, 255], outline=[8, 0, 0],
             outline_px=2, size=None, size_en=15, size_ar=14)
GUIDE_NARROW = dict(GUIDE, size_en=11, size_ar=12)     # the 70/37-px cells of the bottom row
ORANGE = dict(clear='fill', fill_color=[24, 24, 24, 255], align='center', valign='center', color=[255, 161, 49],
              outline=None, outline_px=0, size=None, size_en=15, size_ar=15, pad=0)
TAG = dict(clear='inpaint', inpaint_mask='box', inpaint_radius=2, align='center', valign='center', outline=None,
           outline_px=0, size=None, size_en=12, size_ar=12, pad=0)
YELLOW = dict(TAG, color=[255, 246, 131], glow=[40, 40, 16], glow_px=1, glow_strength=3.0)
CYAN = dict(TAG, color=[148, 202, 222], glow=[16, 32, 52], glow_px=1, glow_strength=3.0)
RED = dict(TAG, color=[255, 44, 49], glow=[40, 20, 28], glow_px=1, glow_strength=3.0)


def L(box, jp, en, ar, base, **kw):
    d = dict(box=box, jp=jp, en=en, ar=ar)
    d.update(base)
    d.update(kw)
    return d


labels = [
    # ---- button guide column (cells from ui_common.crbpj, update)
    L([852, 574, 938, 595], 'パーツ移動', 'Move Part', 'نقل الجزء', GUIDE),
    L([938, 574, 1024, 595], 'パーツ拡大', 'Enlarge Part', 'تكبير الجزء', GUIDE),
    L([922, 595, 1024, 615], 'パーツ移動小', 'Move Part (Fine)', 'نقل الجزء بدقة', GUIDE),
    L([907, 615, 1024, 636], 'パーツ45度回転', 'Rotate Part 45 Deg', 'تدوير الجزء 45 درجة', GUIDE, size_ar=13),
    L([854, 636, 923, 657], '一括回収', 'Collect All', 'جمع الكل', GUIDE),
    L([925, 636, 1024, 657], 'カメラ初期化', 'Camera Reset', 'إعادة ضبط الكاميرا', GUIDE, size_ar=12),
    L([971, 657, 1024, 678], 'ズーム', 'Zoom', 'تكبير', GUIDE),
    L([917, 678, 987, 699], '武器回転', 'Rotate Weapon', 'تدوير السلاح', GUIDE_NARROW),
    L([987, 678, 1024, 699], '回転', 'Rotate', 'تدوير', GUIDE_NARROW),
    # ---- orange touch buttons, row 1 (buttons x609-658 / 660-709 / 711-760, y363-390)
    L([610, 366, 658, 388], 'カメラ', 'Camera', 'الكاميرا', ORANGE),
    L([661, 366, 709, 388], '回転', 'Rotate', 'تدوير', ORANGE),
    L([712, 366, 760, 388], '拡縮', 'Scale', 'تحجيم', ORANGE),
    # row 2 (buttons x354-403 / 405-454 / 456-505 / 507-556, y392-419; the fifth one, RESET, is English)
    L([355, 395, 403, 417], 'アタッチ', 'Attach', 'تركيب', ORANGE),
    L([406, 395, 454, 417], '決定', 'Accept', 'تأكيد', ORANGE),
    L([457, 395, 505, 417], '回転1', 'Rotate 1', 'تدوير 1', ORANGE),
    L([508, 395, 556, 417], '回転2', 'Rotate 2', 'تدوير 2', ORANGE),
    # ---- tags (frame x343-399 / x436-504; boxes inside the frame, off its slanted corners)
    L([349, 127, 378, 141], '装着', 'Fitted', 'مركّب', YELLOW),
    L([349, 155, 392, 169], '右装着', 'Fitted R', 'يمين', YELLOW),
    L([350, 183, 392, 198], '左装着', 'Fitted L', 'يسار', YELLOW),
    L([442, 434, 497, 447], 'ステルス', 'Hidden', 'مخفي', CYAN),
    L([442, 463, 501, 476], '装備不可', "Can't Equip", 'غير متاح', RED),
    L([442, 490, 471, 503], '装備', 'In Use', 'مجهّز', YELLOW),
]

spec = dict(
    texture='tex_nova_ui_common.aif',
    archive='patch',
    note=('Common UI parts (update copy, ID 0515fe): button guide column (Cast_Camera cells of update ui_common.crbpj, '
          'white + dark outline, right-aligned), orange touch buttons of the attachment editor (flat (24,24,24) '
          'button body refilled; boxes = the button interior inside its partly transparent edge columns), small tags with a leader dot (yellow 装着/右装着/左装着/装備, cyan ステルス, red '
          '装備不可; opaque gradient body, Japanese inpainted, boxes kept inside the frame). English terms from the '
          'text sheet where the same Japanese exists (カメラ初期化 Camera Reset 430060, 回転 Rotate 430005, 決定 Accept '
          '430001); 装着 = fitted to a weapon (sheet 780090), R/L = right/left weapon of a twin pair. The display font has no '
          'degree sign, so 45度 is "45 Deg" in English and «45 درجة» in Arabic (to_display puts a ° on the wrong side of the digits). Written by dev/psnova/uitex/specwork/'
          'make_spec_tex_nova_ui_common.py.'),
    labels=labels,
)

SIZES = {}   # filled below once measured: jp -> dict(size_en=..., size_ar=...)

if __name__ == '__main__':
    import sys
    sizes = json.load(open(sys.argv[1], encoding='utf-8')) if len(sys.argv) > 1 else {}
    for lab in labels:
        for k, v in sizes.get(lab['jp'] + '@%d,%d' % tuple(lab['box'][:2]), {}).items():
            lab[k] = v
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
    print('wrote', OUT, len(labels), 'labels')

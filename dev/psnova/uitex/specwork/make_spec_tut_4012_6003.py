"""make_spec_tut_4012_6003.py - writes the redraw specs (SPEC.md) of ten tutorial pictures (2026-11-19):
ui_tut_4012_0002, 4013_0001, 5004_0001 (red callouts over gameplay) and ui_tut_6002_0003/0004/0005,
6003_0001/0002/0003/0004 (screenshots of the multiplayer counter, guest crew and quest gate menus).

Boxes were read from 4x/6x grid zooms (dev/psnova/uitex/tut_zoom.py -> dump/psnova-l10n/uitex/crops/tut/).
Terms come from the text sheet (dump/psnova-l10n/sheet/psnova_text_v5.tsv): ids noted next to each label.

Patterns used:
- Callouts (red text, 2 px white outline): a tight clear-only label over the Japanese (inpaint, en/ar "") plus a
  wider draw-only label (clear "keep") so the longer English never needs a big inpaint box over the scene.
  align_ar "left" keeps the caption anchored where the Japanese was.
- Menu text (white, 1 px dark outline): the draw label clears nothing (clear "keep"); erase labels are computed
  from the source picture (add_erasers): tight box around the Japanese strokes, then row-band fills (clear "fill")
  on flat panels, inpaint elsewhere (median / telea; see erase_labels and the -v log). `ebox` = where to look for
  the Japanese when the row box also holds frames or highlights; `exact` = use that box as is; `tool` = force a
  clear method.
  Arabic is right-aligned (apply_spec flips "left") on single-text rows; label/value rows (a value or Lv. at the
  right of the same row, table cells) keep align_ar "left" so the Arabic does not run into the value.
- Sizes (finalize): one size per language, capped (English 12, 13 in tall rows; Arabic 10), shrunk only when the
  width needs it; box_en / box_ar grow 1 / 3 px up and down instead of clipping the display font's g or Arabic alef/hamza.
- ui_tut_6003_0004: the quest text panel is half hidden behind the start dialog. The visible part of each hidden
  line is computed from the same English/Arabic text as ui_tut_6003_0002 (whole words only), so it reads as the
  same text cut off by the dialog.

Checking: apply_spec.py <spec> en|ar dump/psnova-l10n/uitex/crops/tut/check/<lang>, then tut_ba.py (before / en /
ar zoom of a region); tut_clear_trial.py compares clear settings on a box.

usage: python -s make_spec_tut_4012_6003.py [-v]   (writes dump/psnova-l10n/uitex/specs/<name>.json; -v = erase log)
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'dev', 'psnova', 'uitex'))
sys.path.insert(0, os.path.join(ROOT, 'dev', 'psnova', 'rmdtext'))
import apply_spec  # noqa: E402  (font_for: the same fonts and layout engine as the redraw)
import arabic  # noqa: E402

OUT = os.path.join(ROOT, 'dump', 'psnova-l10n', 'uitex', 'specs')
RED, WHITE_O = [255, 8, 8], [255, 255, 255]
TXT, DARK = [240, 240, 240], [8, 12, 20]


def callout(clear_box, draw_box, jp, en, ar, size=22, align='left'):
    """Two labels: erase the red Japanese (tight box), then draw over the wider box without clearing."""
    return [
        dict(box=clear_box, jp=jp, en='', ar='', clear='inpaint', inpaint_polarity='any', inpaint_threshold=40,
             inpaint_shadow=2, inpaint_dilate=1, note='erase only (callout); text drawn by the next label'),
        dict(box=draw_box, jp=jp, en=en, ar=ar, clear='keep', align=align, align_ar=align, color=RED,
             outline=WHITE_O, outline_px=2, size=size, valign='center'),
    ]


def row(box, jp, en, ar, align='left', keep_left=False, color=None, size=None, src=None, ebox=None, bg='panel',
        **kw):
    lab = dict(box=box, jp=jp, en=en, ar=ar, clear='keep', _bg=bg, align=align,
               color=color or TXT, outline=DARK, outline_px=1, size=size, valign='center')
    if keep_left:
        lab['align_ar'] = 'left'
    if kw.pop('exact', False):
        lab['_exact'] = True
    if kw.get('tool'):
        lab['_tool'] = kw.pop('tool')
    if ebox:
        lab['_ebox'] = ebox          # where to look for the Japanese (row boxes that also hold frames/highlights)
    if src:
        lab['src'] = src
    lab.update(kw)
    return lab


def spec(name, note, labels):
    return dict(texture=name + '.aif', archive='base', note=note, labels=labels)


# ---------------------------------------------------------------------------------------------------------------
# HUD names over the party gauges (bottom left of the menu screenshots): over the scene -> telea inpaint
def hud(box, jp, en, ar, ebox=None):
    return dict(box=box, _ebox=ebox or [box[0], box[1], 60, box[3] + 2], jp=jp, en=en, ar=ar, clear='keep', _bg='scene', align='left', color=TXT, outline=DARK,
                outline_px=1, size=None, valign='center', src='player/party names (PSO-style default names)', cap=12)


RACAST = ('レイキャスト', 'RAcast', 'ريكاست')
HUMAR = ('ヒューマー', 'HUmar', 'هيومار')
FONEW = ('フォニュエール', 'FOnewearl', 'فونيويرل')
LUTINA = ('ルティナ', 'Lutina', 'لوتينا')          # 30001

specs = []

# ---- 4012_0002: Ring Field footholds (780059, 620152/620153)
specs.append(spec('ui_tut_4012_0002',
    'Ring Field footholds (tutorial 780059; foothold wording from 620152/620153, centre mark / outer edge from '
    '780059). Four red callouts with a 2 px white outline over gameplay: each is a tight inpaint label (erase only) '
    'plus a wider draw-only label so the English can be longer than the Japanese.',
    callout([8, 8, 164, 32], [6, 6, 252, 34], '足場から足場に登る', 'Climb to a Higher Foothold', 'الصعود إلى موطئ قدم أعلى') +
    callout([264, 8, 388, 31], [262, 6, 508, 34], '足場から降りる', 'Step Down from a Foothold', 'النزول عن موطئ القدم') +
    callout([442, 176, 498, 200], [404, 174, 510, 202], '外周部', 'Outer Edge', 'الحافة الخارجية', align='right') +
    callout([84, 228, 172, 252], [40, 228, 216, 256], '中央マーク', 'Center Mark', 'العلامة المركزية', align='center')))

# ---- 4013_0001: Pile striking / shooting (780060)
specs.append(spec('ui_tut_4013_0001',
    'Pile: striking and shooting (tutorial 780060 "striking and shooting traits"; Arabic الضرب والرمي as in '
    'قوة الضرب / قوة الرمي). Two red callouts, 2 px white outline, over gameplay.',
    callout([8, 8, 47, 32], [6, 6, 124, 34], '打撃', 'Strike', 'ضرب') +
    callout([264, 8, 303, 32], [262, 6, 380, 34], '射撃', 'Shoot', 'رمي')))

# ---- 5004_0001: Breaking parts (780064)
specs.append(spec('ui_tut_5004_0001',
    'Breaking parts (tutorial 780064 "Breaking Parts", Arabic تدمير). Two red callouts, 2 px white outline.',
    callout([7, 7, 64, 31], [6, 6, 200, 34], '破壊前', 'Before Break', 'قبل التدمير') +
    callout([263, 7, 320, 31], [262, 6, 450, 34], '破壊後', 'After Break', 'بعد التدمير')))

# ---- 6002_0003: Form Party / Join Party (780067; menu 21101-21108)
specs.append(spec('ui_tut_6002_0003',
    'Multiplayer counter (780067). Left: Form Party window, right: Join Party list. Menu terms from the sheet '
    '(21101 Form Party, 21102 Join Party, 21103 dialog, 21104 Member Selection, 21105 Disband Party, 21107 Party '
    'List, 21108 Update List; 10202 Ranger, 10403 Cast, 10501 Male). レイキャスト/ヒューマー are the PSO-style '
    'player names RAcast/HUmar. "Lv. 3" and the START icon stay.',
    [
        row([10, 3, 178, 18], 'パーティーを結成', 'Form Party', 'تكوين الفريق', ebox=[10, 4, 86, 17], bg='scene'),
        row([36, 89, 234, 112], 'メンバー決定を押すと\n現在のメンバーでパーティーを結成します。',
            'After selecting your members,\nyou will form a party.',
            'اختر «تحديد الأعضاء» لتكوين\nفريق بالأعضاء الحاليين.', valign='top', line_gap=0),
        row([64, 120, 185, 131], 'メンバー決定', 'Member Selection', 'تحديد الأعضاء', align='center', ebox=[92, 120, 158, 131]),
        row([64, 135, 185, 146], 'パーティー募集中止', 'Disband Party', 'حل الفريق', align='center', ebox=[80, 135, 168, 147]),
        hud([7, 180, 92, 191], *RACAST, [7, 180, 58, 191]),
        hud([7, 207, 92, 220], *HUMAR, [7, 206, 60, 220]),
        row([264, 3, 434, 18], 'パーティーへ参加', 'Join Party', 'الانضمام إلى الفريق', ebox=[264, 4, 344, 17], bg='scene'),
        row([267, 23, 352, 34], 'パーティーリスト', 'Party List', 'قائمة الفرق', align='center', ebox=[272, 23, 348, 34]),
        row([388, 23, 436, 34], 'リスト更新', 'Update List', 'تحديث', align='center'),
        row([268, 37, 420, 49], *RACAST, ebox=[268, 37, 330, 49]),
        row([281, 51, 384, 62], 'レンジャー', 'Ranger', 'رامي', keep_left=True),
        row([267, 64, 380, 76], 'キャスト', 'Cast', 'كاست', keep_left=True),
        row([396, 64, 436, 76], '男性', 'Male', 'ذكر', align='right'),
    ]))

# ---- 6002_0004 / 6002_0005 / 6003_0003: guest crew lists and crew info (780068/780069, 780097/780098)
def crew_info(page, extra_rows):
    """Crew Info panel rows shared by 6002_0004, 6002_0005, 6003_0003 (right half)."""
    return [
        row([292, 47, 400, 60], 'クルー情報', 'Crew Info', 'معلومات الطاقم', keep_left=True),   # 21019; "1/x" at right
        row([292, 62, 490, 75], 'スタイル', 'Style', 'نمط'),                                     # 10321
    ] + extra_rows


TRAIT_L = lambda y0, y1, jp, en, ar: row([304, y0, 396, y1], jp, en, ar, keep_left=True)
TRAIT_R = lambda y0, y1, jp, en, ar: row([406, y0, 490, y1], jp, en, ar, keep_left=True)

specs.append(spec('ui_tut_6002_0004',
    'Guest Crew list (780068) with the crew card and Crew Info of FOnewearl. Terms: 11012 Guest Crew, 10716 '
    'Recently Used, 10203 Force, 10402 Newman, 10502 Female, 21019 Crew Info, 10321 Style, 10322 Traits, 520015, '
    '520026 (shortened to fit). 他人 under the face icon: the sheet (10601) gives "Lv. 3" in English (the fan patch '
    'shows relationship levels as Lv.) and غريب in Arabic; written "Lv.3" to fit 21 px.',
    [
        row([112, 3, 265, 15], 'ゲストクルー', 'Guest Crew', 'طاقم الضيوف', align='center', ebox=[155, 3, 222, 15]),
        row([126, 18, 212, 30], *FONEW, keep_left=True, ebox=[126, 19, 190, 28]),
        row([126, 33, 212, 46], *RACAST, keep_left=True),
        hud([7, 156, 92, 168], *RACAST, [7, 156, 58, 166]),
        hud([7, 180, 92, 191], *FONEW, [7, 180, 66, 191]),
        hud([7, 206, 92, 220], *HUMAR, [7, 206, 60, 220]),
        row([112, 180, 205, 194], '最近プレーした順', 'Recently Used', 'المستخدمة حديثاً', align='center', cap=12,
            ebox=[123, 179, 196, 193], exact=True, bg='scene'),
        row([312, 3, 490, 16], *FONEW, ebox=[312, 3, 378, 16]),
        row([325, 17, 400, 29], 'フォース', 'Force', 'ساحر', keep_left=True),
        row([287, 25, 313, 37], '他人', 'Lv.3', 'غريب', align='center', color=[120, 200, 50]),
        row([312, 29, 400, 41], 'ニューマン', 'Newman', 'نيومان', keep_left=True),
        row([466, 29, 500, 41], '女性', 'Female', 'أنثى', align='right'),
    ] + crew_info(1, [
        row([292, 90, 490, 101], '特徴', 'Traits', 'السمات'),
        TRAIT_L(105, 118, 'ピンチに強い', 'Strong in a Bind', 'قوي عند الأزمات'),
        TRAIT_R(105, 118, '持久力に難あり', 'Poor Stamina', 'ضعيف التحمل'),
    ])))

specs.append(spec('ui_tut_6002_0005',
    'Recently played guest crew list (780069) over the field, with FOnewearl and RAcast name tags and Crew Info. '
    'Terms: 20402 header, 10716 Recently Used, 10202 Ranger, 10203 Force, 10402 Newman, 10403 Cast, 10501/10502, '
    '21019, 10321, 10322, 520038 (shortened to fit), 520063 Calm. レイ at the panel edge is the start of a RAcast '
    'name tag cut off by the panel.',
    [
        row([14, 2, 172, 14], '最近遊んだゲストクルー', 'Recently Used', 'طاقم الضيوف المستخدم حديثاً', align='center', ebox=[40, 2, 150, 14]),
        row([30, 18, 155, 30], *RACAST, ebox=[30, 19, 86, 29]),
        row([40, 31, 136, 43], 'レンジャー', 'Ranger', 'رامي', keep_left=True),
        row([30, 43, 138, 55], 'キャスト', 'Cast', 'كاست', keep_left=True),
        row([140, 43, 175, 55], '男性', 'Male', 'ذكر', align='right'),
        row([30, 60, 170, 72], *FONEW),
        row([40, 73, 136, 85], 'フォース', 'Force', 'ساحر', keep_left=True),
        row([30, 85, 138, 97], 'ニューマン', 'Newman', 'نيومان', keep_left=True),
        row([140, 85, 175, 97], '女性', 'Female', 'أنثى', align='right'),
        dict(box=[177, 99, 240, 111], jp='フォニュエール', en='FOnewearl', ar='فونيويرل', clear='keep', _bg='scene',
             align='center', color=TXT, outline=DARK, outline_px=1, size=None, valign='center',
             note='name tag over the character (scene background)'),
        dict(box=[270, 86, 288, 98], jp='レイ', en='RA', ar='ري', clear='keep', _bg='scene', align='left', align_ar='left',
             color=TXT, outline=DARK, outline_px=1, size=None, valign='center',
             note='start of the RAcast name tag, cut off by the Crew Info panel'),
        row([24, 230, 106, 242], '最近プレイした順', 'Recently Used', 'المستخدمة حديثاً', align='center'),
    ] + crew_info(1, [
        row([292, 90, 490, 101], '特徴', 'Traits', 'السمات'),
        TRAIT_L(105, 118, '団体行動が苦手', 'Poor at Teamwork', 'قليل التعاون'),
        TRAIT_R(105, 118, '冷静', 'Calm', 'هادئ'),
    ])))

specs.append(spec('ui_tut_6003_0003',
    'All Crew list with Lutina\'s card, Crew Info, traits and comment (780072 context). Terms: 21755 All Crew '
    'Members, 10716, 10203 Force, 10401 Human, 10502 Female, 21019, 10321, 510028 Battling Girl, 10322, 520002, '
    '520091 / 520016 (shortened to fit), 520054, 520065, 21711 Comment. 知人 under the face icon: sheet 10602 gives '
    '"Lv. 4" in English (fan patch) and معرفة in Arabic; written "Lv.4" to fit 21 px. The comment line is new '
    'translation (no sheet row).',
    [
        row([112, 3, 265, 15], 'すべてのクルー', 'All Crew Members', 'جميع أفراد الطاقم', align='center', ebox=[150, 3, 228, 15]),
        row([126, 18, 212, 30], *LUTINA, keep_left=True, ebox=[126, 19, 166, 28]),
        hud([7, 180, 92, 191], *LUTINA, [7, 180, 46, 191]),
        hud([7, 206, 92, 220], *HUMAR, [7, 206, 60, 220]),
        row([112, 180, 205, 194], '最近プレイした順', 'Recently Used', 'المستخدمة حديثاً', align='center', cap=12,
            ebox=[123, 179, 196, 193], exact=True, bg='scene'),
        row([287, 25, 313, 37], '知人', 'Lv.4', 'معرفة', align='center', color=[215, 215, 80]),
        row([347, 3, 490, 16], *LUTINA, ebox=[347, 3, 385, 16]),
        row([360, 17, 412, 29], 'フォース', 'Force', 'ساحر', keep_left=True),
        row([347, 29, 426, 41], 'ヒューマン', 'Human', 'بشري', keep_left=True),
        row([466, 29, 500, 41], '女性', 'Female', 'أنثى', align='right'),
    ] + crew_info(1, [
        row([292, 76, 490, 89], '格闘系ガール', 'Battling Girl', 'فتاة قتالية'),
        row([292, 90, 490, 101], '特徴', 'Traits', 'السمات'),
        TRAIT_L(105, 118, '一般アークス', 'Common ARKS', 'آركس عادي'),
        TRAIT_R(105, 118, '仲間思い', 'Sentimental', 'يهتم بالرفاق'),
        TRAIT_L(118, 131, '火事場の馬鹿力', 'Fight-or-Flight', 'قوة الطوارئ'),
        TRAIT_R(118, 131, 'ハンター好き', 'Prefers Hunters', 'يفضّل الصيادين'),
        TRAIT_L(131, 143, '話し上手', 'Smooth Talker', 'لبق'),
        row([292, 172, 490, 186], 'コメント', 'Comment', 'تعليق', ebox=[292, 173, 334, 186], tool='median'),
        row([292, 187, 490, 210], '相棒の回復役はあたしなんだから\nいつでも呼んでよね！',
            "Healing my partner is my job,\nso call me anytime!", 'علاج شريكي مهمتي،\nفاستدعني في أي وقت!',
            valign='top', line_gap=0),
    ])))

# ---- 6003_0001: Quest Gate menu (780070)
specs.append(spec('ui_tut_6003_0001',
    'Quest Gate menu over the planet map (780070). Terms: 21762 Story Summary, 21761 Delta Valiant. The red story '
    'quest marker is an icon and stays.',
    [
        row([8, 33, 124, 45], 'クエスト', 'Quest', 'مهمة', ebox=[9, 33, 48, 44]),
        row([8, 49, 124, 61], 'あらすじの確認', 'Story Summary', 'مراجعة الملخص', ebox=[9, 49, 74, 61]),
        row([222, 94, 290, 105], 'デルタ・ヴァリアント', 'Delta Valiant', 'دلتا فاليانت', align='center',
            color=[200, 200, 200]),
    ]))

# ---- 6003_0002 / 0004: quest details (230002 text, 21723-21728, 200102, 200500, 180110, 180210, 790032)
DESC_EN = ['Requester: Fildia',
           'Search the Steel Wastelands for the',
           'survivors of the advance team left behind.',
           "Darkers are swarming, and I can't tell what",
           'kinds will show up, but save the survivors!',
           "You're the only ones who can fight. Go!",
           '',
           'Recommended: Lutina']
DESC_AR = ['العميل: فيلديا',
           'ابحثوا في الأراضي القاحلة الفولاذية',
           'عن ناجي الفرقة المتقدمة العالقين هناك.',
           'الداركر في كل مكان ولا أعرف أي نوع سيظهر،',
           'لكن إنقاذ الناجين أمر لا بد منه!',
           'لا أحد غيركم يستطيع القتال الآن. أعتمد عليكم!',
           '',
           'المرافقون: لوتينا']
DESC_JP = ['依頼者：フィルディア', '鋼の荒野に取り残された先遣隊の生存者を', '捜索してくれ。',
           'ダーカーがウヨウヨいて、どんなタイプが出て来るか', 'オレにもわからんが、生存者の救出は絶対だ！',
           '今、戦えるのはお前たちしかいない。頼むぞ！', '', '同行者：ルティナ']
# one label per line (exact 10 px pitch as in the Japanese): line i occupies y LINE_Y(i) .. +13, text bottom-aligned
# (valign bottom keeps the baselines on the pitch); Arabic boxes reach 3 px higher for hamza/alef tops
DESC_SIZE, DESC_SIZE_AR, PITCH, X0, X1 = 11, 9, 10, 293, 503
LINE_Y = lambda i: 115 + PITCH * i


def desc_line(i, box_x0=X0, en=None, ar=None, note=None):
    y = LINE_Y(i)
    lab = row([box_x0, y, X1, y + 13], DESC_JP[i], DESC_EN[i] if en is None else en,
              DESC_AR[i] if ar is None else ar, valign='bottom', size=DESC_SIZE)
    lab['size_ar'] = DESC_SIZE_AR
    lab['box_ar'] = [lab['box'][0], y - 3, X1, y + 13]
    lab['fixed'] = True
    lab.pop('_bg')
    if note:
        lab['note'] = note
    return lab


def quest_table(with_normal):
    t = [
        row([294, 9, 349, 22], '場所', 'Location', 'الموقع', keep_left=True),
        row([350, 9, 500, 22], '鋼の荒野　1', 'Steel Wastelands 1', 'الأراضي القاحلة الفولاذية 1', keep_left=True),
        row([294, 22, 349, 35], 'クエスト名', 'Quest Name', 'اسم المهمة', keep_left=True),
        row([363, 22, 500, 35], '仲間の捜索', 'Searching for Comrades', 'البحث عن الرفاق', keep_left=True),
        row([294, 50, 349, 63], 'クリア目標', 'Objective', 'هدف الإنجاز', keep_left=True),
        row([350, 50, 500, 63], '先遣隊の救出', 'Rescue Advance Team', 'إنقاذ الفرقة المتقدمة', keep_left=True),
        row([294, 63, 349, 76], '失敗条件', 'Failure', 'شروط الفشل', keep_left=True),
        row([350, 63, 500, 76], 'なし', 'None', 'لا شيء', keep_left=True),
        row([350, 76, 500, 89], 'Ｇクラーダ', 'G-Krahda', 'G-كراهدا', keep_left=True),
        row([350, 89, 500, 102], 'Ｇダガン', 'G-Dagan', 'G-داغان', keep_left=True),
    ]
    if with_normal:
        t.insert(4, row([350, 36, 500, 49], 'ノーマル', 'Normal', 'عادي', keep_left=True))
    return t


DESC_NOTE = ('Quest text 230002: the sheet\'s English (fan patch) keeps only "Requester: Fildia" and "Recommended: '
             'Lutina"; the body lines are a new translation (EN/AR), Arabic terms from the glossary (داركر, '
             'الأراضي القاحلة الفولاذية 790032). One label per line on the original 10 px pitch, English size 11, '
             'Arabic size 9 (box_ar 3 px taller for alef/hamza tops).')

specs.append(spec('ui_tut_6003_0002',
    'Quest Gate: quest details of "Searching for Comrades" (780072). Left: area header and quest row; right: '
    'details panel (semi-transparent over the map). Table terms 21723-21728 (Enemies label: Arabic shortened to '
    'الأعداء to fit the label column). ' + DESC_NOTE,
    [
        row([12, 31, 128, 44], '鋼の荒野　1', 'Steel Wastelands 1', 'الأراضي القاحلة الفولاذية 1', align='center', ebox=[56, 31, 114, 44]),
        row([20, 48, 128, 61], '仲間の捜索', 'Searching for Comrades', 'البحث عن الرفاق'),
    ] + quest_table(False) + [
        row([294, 76, 350, 89], '出現エネミー', 'Enemies', 'الأعداء', keep_left=True),
        dict(box=[X0, 114, X1, 200], jp='\n'.join(DESC_JP), en='', ar='', clear='keep', _bg='panel'),
    ] + [desc_line(i) for i in range(8) if DESC_JP[i]]))


def visible_tail_en(line, cut_x):
    """English line drawn left-aligned from X0 (pad 1): the whole words that start at or right of cut_x (or, when
    no word does, the letters of the word under the cut that start right of it). Returns (x, text)."""
    f = apply_spec.font_for('en', DESC_SIZE)
    words = line.split(' ')
    for k in range(1, len(words)):
        pre = ' '.join(words[:k]) + ' '
        x = X0 + 1 + f.getlength(pre)
        if x >= cut_x:
            return int(round(x)) - 1, ' '.join(words[k:])
    for c in range(1, len(line)):
        x = X0 + 1 + f.getlength(line[:c])
        if x >= cut_x and line[c] != ' ':
            return int(round(x)) - 1, line[c:]
    return None, ''


def visible_head_ar(line, vis_w):
    """Arabic line drawn right-aligned at X1 (pad 1): the leading words (logical order) that fit in vis_w px."""
    f = apply_spec.font_for('ar', DESC_SIZE_AR)
    words = line.split(' ')
    best = ''
    for k in range(1, len(words) + 1):
        t = ' '.join(words[:k])
        b = f.getbbox(arabic.to_display(t), stroke_width=1)
        if b[2] - b[0] <= vis_w:
            best = t
        else:
            break
    return best


CUT = 340            # the start dialog (+ its shadow) covers x < 340 down to y 167 in ui_tut_6003_0004
hidden = []
for i in range(5):   # requester line + body lines 1-4 are cut by the dialog
    x, t = visible_tail_en(DESC_EN[i], CUT)
    if t:
        hidden.append(desc_line(i, x, en=t, ar='', note='visible end of the English line (rest hidden by the dialog)'))
    a = visible_head_ar(DESC_AR[i], X1 - 1 - CUT)
    if a:
        hidden.append(desc_line(i, CUT, en='', ar=a, note='visible start of the Arabic line (rest hidden by the dialog)'))

specs.append(spec('ui_tut_6003_0004',
    'Quest Gate: start-quest confirmation (780142) over the quest details. Left menu 21709 Party Members, 21708 '
    'Start Quest; dialog 21748 (one line in English as in the sheet), 10105 Yes, 10106 No; ノーマル 21703. The '
    'details panel is partly behind the dialog (x < 340, y < 168): the visible Japanese fragments are erased and the '
    'visible part of each line is drawn from the same English/Arabic text as ui_tut_6003_0002 (whole words). The '
    '出現エネミー label is almost fully hidden: its visible slivers are only erased. ' + DESC_NOTE,
    [
        row([8, 32, 124, 45], 'パーティーメンバー', 'Party Members', 'أعضاء الفريق', ebox=[9, 33, 90, 44]),
        row([8, 48, 124, 61], 'クエスト開始', 'Start Quest', 'بدء المهمة', ebox=[9, 49, 64, 60]),
        row([182, 86, 330, 111], 'このクエストを開始します。\nよろしいですか？', 'Start the current quest?',
            'هل تريد بدء هذه المهمة؟', align='center', ebox=[194, 88, 318, 112], exact=True, tool='boxmedian'),
        row([214, 120, 300, 132], 'はい', 'Yes', 'نعم', align='center', ebox=[238, 120, 274, 132]),
        row([214, 135, 300, 148], 'いいえ', 'No', 'لا', align='center'),
    ] + quest_table(True) + [
        dict(box=[294, 75, 336, 80], jp='出現エネミー', en='', ar='', clear='keep', _bg='scene', _exact=True,
             note='top sliver of the label above the dialog: erase only'),
        dict(box=[337, 76, 350, 89], jp='出現エネミー', en='', ar='', clear='keep', _bg='panel',
             note='end of the label right of the dialog: erase only'),
        dict(box=[CUT, 114, X1, 167], jp='\n'.join(DESC_JP[:5]), en='', ar='', clear='keep', _bg='panel',
             note='visible Japanese right of the dialog: erase; the lines are drawn below'),
        dict(box=[X0, 165, X1, 200], jp='\n'.join(DESC_JP[5:]), en='', ar='', clear='keep', _bg='panel'),
    ] + hidden + [desc_line(5), desc_line(7)]))


# ---------------------------------------------------------------------------------------------------------------
# font sizes: one size per language and label, capped so equal rows look alike, shrunk only when needed. When the
# text block is a little taller than the box (the display font's 'g' / the Arabic alef and hamza), the language's box
# (box_en / box_ar) grows by up to `grow` px above and below instead of clipping (apply_spec draws inside the box).
def _fit(lab, lang, cap, grow):
    text = lab.get(lang) or ''
    if not text:
        return None
    x0, y0, x1, y1 = lab['box']
    bw, bh = x1 - x0, y1 - y0
    stroke = int(lab.get('outline_px', 0)) if lab.get('outline') else 0
    lines = apply_spec._lines(text, lang)
    n = len(lines)
    for s in range(cap, 5, -1):
        f = apply_spec.font_for(lang, s)
        w, h, rows_ = apply_spec._measure(lines, f, stroke, 0)
        if w > bw - 2:
            continue
        lh = max(r[4] - r[3] for r in rows_)
        gap = 0
        if n > 1:
            gap = min(0, (bh + 2 * grow - n * lh) // (n - 1))
            if gap < -max(2, lh // 3):
                continue
        th = n * lh + (n - 1) * gap
        if th > bh + 2 * grow:
            continue
        g = max(0, th - bh)
        box = [x0, y0 - g // 2, x1, y1 - g // 2 + g] if g else None
        return s, gap, box
    return 6, 0, None


def finalize(s):
    for lab in s['labels']:
        fixed = lab.pop('fixed', False)
        cap_en = lab.pop('cap', None)
        cap_ar = lab.pop('cap_ar', None)
        if not (lab.get('en') or lab.get('ar')) or fixed:
            continue
        callout_ = lab.get('color') == RED
        bh = lab['box'][3] - lab['box'][1]
        caps = {'en': cap_en or (22 if callout_ else (13 if bh >= 14 else 12)),
                'ar': cap_ar or (22 if callout_ else 10)}
        grows = {'en': 0 if callout_ else 1, 'ar': 0 if callout_ else 3}
        for lang in ('en', 'ar'):
            r = _fit(lab, lang, caps[lang], grows[lang])
            if not r:
                continue
            size, gap, box = r
            sfx = '' if lang == 'en' else '_ar'
            lab['size' + sfx] = size
            if gap:
                lab['line_gap' + sfx] = gap
            elif 'line_gap' + sfx in lab:
                del lab['line_gap' + sfx]
            if box:
                lab['box_' + lang] = [int(v) for v in box]
    return s



# ---------------------------------------------------------------------------------------------------------------
# erasing: every drawn label clears nothing itself (clear "keep"); the Japanese is erased by labels computed here
# from the source picture. The text strokes inside the label box (apply_spec's own stroke mask: bright strokes +
# their dark outline) give a tight erase box. On flat UI panels (the colour left and right of the text agrees on
# every row) the erase box is filled row band by row band with that colour (clear "fill"): exact for the game's
# panels, which are flat across and shaded top to bottom. Otherwise: inpaint (median background on panels,
# telea on scene backgrounds).
_IMG = {}


def _img(name):
    if name not in _IMG:
        import aiftex
        d = open(os.path.join(ROOT, 'dump', 'psnova-l10n', 'scratch', 'research', 'base', name), 'rb').read()
        W, H, fmt, tid = aiftex.info(d)
        _IMG[name] = aiftex.decode(d[0x1e0:], W, H, fmt)
    return _IMG[name]


TOOLS = {
    'median': dict(clear='inpaint', inpaint_method='median', inpaint_window=61, inpaint_dilate=2),
    'boxmedian': dict(clear='inpaint', inpaint_mask='box', inpaint_method='median', inpaint_window=61),
    'telea': dict(clear='inpaint', inpaint_dilate=2),
}


def erase_labels(img, box, jp, bg, color=None, exact=False, grow=2, tool=None):
    """Erase labels for the Japanese inside `box`: the text core = pixels close to the text colour (white by
    default) in columns holding at least 2 of them; erase box = core bbox + 2 px left/right + 1 px above/below
    (the 1 px dark outline), clipped to `box`."""
    import numpy as np
    H, W = img.shape[:2]
    rgb = img[..., :3].astype(np.int32)
    col = np.array(color or TXT)
    if exact:
        t = TOOLS[tool or ('telea' if bg != 'panel' else 'median')]
        return [dict(box=list(box), jp=jp, en='', ar='', note='erase: given box', **t)], 'exact %s %s' % (tool, box)
    x0b, y0b, x1b, y1b = box
    sub = rgb[y0b:y1b, x0b:x1b]
    strokes = apply_spec._stroke_mask(img, box, 40, 'bright', 0)[y0b:y1b, x0b:x1b].astype(bool)
    if (color or TXT) == TXT:                               # white/grey text, not yellow/blue frame highlights
        core = strokes & ((sub * [299, 587, 114]).sum(-1) // 1000 >= 140) & ((sub.max(-1) - sub.min(-1)) <= 50)
    else:
        core = strokes & (np.abs(sub - col).sum(-1) <= 120)
    cols = np.nonzero(core.sum(0) >= 1)[0]
    if len(cols) == 0:
        return [], 'nothing found'
    rows = np.nonzero(core[:, cols].any(1))[0]
    x0, x1 = max(x0b - grow, 0, x0b + int(cols.min()) - 2), min(x1b + grow, W, x0b + int(cols.max()) + 3)
    y0, y1 = max(y0b, y0b + int(rows.min()) - 1), min(y1b, y0b + int(rows.max()) + 2)
    eb = [x0, y0, x1, y1]
    if tool:
        return [dict(box=eb, jp=jp, en='', ar='', note='erase: %s' % tool, **TOOLS[tool])], '%s %s' % (tool, eb)
    if bg == 'panel' and x0 >= 2 and x1 <= W - 2:
        bands, ok = [], True
        for y in range(y0, y1):
            L, R = rgb[y, max(0, x0 - 5):x0 - 1], rgb[y, x1 + 1:min(W, x1 + 5)]
            fl, fr = np.ptp(L, 0).sum() <= 24, np.ptp(R, 0).sum() <= 24     # (DXT blocks: small steps)
            if fl and fr:
                if np.abs(L.mean(0) - R.mean(0)).sum() > 9:
                    ok = False; break
            elif fr:
                L = R                                   # left side is a panel edge/bevel: the right side alone
            elif fl:
                R = L
            else:
                ok = False; break
            c = np.rint((L.mean(0) + R.mean(0)) / 2).astype(int)
            if bands and np.abs(np.array(bands[-1][2]) - c).max() <= 3:
                bands[-1][1] = y + 1
            else:
                bands.append([y, y + 1, c.tolist()])
        if ok:
            return [dict(box=[x0, a, x1, b], jp=jp, en='', ar='', clear='fill', fill_color=c + [255],
                         note='erase: panel row band') for a, b, c in bands], 'bands %d %s' % (len(bands), eb)
    if bg == 'panel':
        grad = 0
        if x0 >= 2 and x1 <= W - 2:
            grad = np.mean([np.abs(rgb[y, x0 - 2:x0].mean(0) - rgb[y, x1:x1 + 2].mean(0)).sum() for y in range(y0, y1)])
        if grad > 9:                                        # shaded left to right: grow the colours in (telea)
            return [dict(box=eb, jp=jp, en='', ar='', clear='inpaint', inpaint_dilate=2,
                         note='erase: panel shaded across')], 'telea-panel %s' % eb
        return [dict(box=eb, jp=jp, en='', ar='', clear='inpaint', inpaint_method='median', inpaint_window=61,
                     inpaint_dilate=2, note='erase: shaded panel')], 'median %s' % eb
    return [dict(box=eb, jp=jp, en='', ar='', clear='inpaint', note='erase: over the scene')], 'telea %s' % eb


def add_erasers(s, log=None):
    img = _img(s['texture'])
    erase, draw = [], []
    for lab in s['labels']:
        bg = lab.pop('_bg', None)
        if bg:
            given = lab.pop('_ebox', None)        # a given search box is final (no growing past it)
            labs, how = erase_labels(img, given or lab['box'], lab.get('jp', ''), bg, lab.get('color'),
                                     lab.pop('_exact', False), 0 if given else 2, lab.pop('_tool', None))
            erase += labs
            if log is not None:
                log.append('%s %s %s -> %s' % (s['texture'][:-4], lab.get('jp', '').replace('\n', '/')[:12], lab['box'], how))
            if lab.get('en') or lab.get('ar'):
                draw.append(lab)
        elif lab.get('en') or lab.get('ar'):
            draw.append(lab)
        else:
            erase.append(lab)
    s['labels'] = erase + draw
    return s


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    LOG = []
    for s in specs:
        p = os.path.join(OUT, s['texture'][:-4] + '.json')
        json.dump(add_erasers(finalize(s), LOG), open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        draw = sum(1 for l in s['labels'] if l.get('en') or l.get('ar'))
        print('%-22s labels %2d (drawn %2d)  %s' % (s['texture'][:-4], len(s['labels']), draw, p))
    if '-v' in sys.argv:
        sys.stdout.reconfigure(encoding='utf-8')
        print('\n'.join(LOG))

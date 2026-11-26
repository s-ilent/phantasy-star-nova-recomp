# Phantasy Star Nova: Japanese text outside the .rmd messages (research, 2026-11-19)

Read-only research: no game run, nothing in the build, pack, sheet or tools changed. Work files and helper scripts in
`dump/psnova-l10n/scratch/research/` (`aif2png.py` = .aif texture decoder, `asm.sh <fn>` = print one recompiled function's
ARM comments, `png/` = decoded textures and crops, `base/` + `patch/` = extracted UI layouts and textures).
Question: with English/Arabic selected, why does Japanese still show, e.g. the character-creation banner
`キャラクタークリエイト` and the button guide `SELECT カメラ初期化` / `L R ズーム`?

## Answer in short

1. **The button guide and the page-title banner are pictures, not text.** `カメラ初期化`, `ズーム` and
   `キャラクタークリエイト` are baked into two UI textures, `tex_nova_ui_common.aif` and `tex_nova_ui_Title.aif`. No
   message, CSV, Lua or the program holds them as text. The fan rePatch never redrew either texture, so they are Japanese
   in every build. **Fix: redraw these two textures per language and put them in the lang/en and lang/ar overlay archives.**
2. **The CSV strings the earlier search found are not on screen.** The game does convert Shift-JIS table strings to
   UTF-16 and can draw UTF-16 with BasicCharSet glyphs. But the `StringFix_Name*` names only fill "string slots" that no
   message uses, and the NPC names on screen come from **messages** (NpcBaseParameter's last column, e.g. 30004
   フィルディア). Those messages are already translated: the name plates show "Fildia" / "فيلديا" in tests 8 and 9.

## 1. The button guide and the banner are texture art

### Where the text is

- `tex_nova_ui_common.aif` (Sega's 1.05 update archive, entry id 39; 1,049,056 bytes; it is also in our overlay
  archives, carried over from the update). Layout as in the .rmd atlases: 0x1e0 bytes of GXM chunks (`FIA`, `FRap`,
  `Xgmi`, ...; width/height u16 at 0xa8 = 1024 x 1024), then **DXT5 (BC3) blocks in Morton order**, colour + alpha. Our
  decoder (`scratch/research/aif2png.py`, using `rmdlib._perm`) gives a clean image
  (`png/patch/tex_nova_ui_common_dxt5_onblack.png`).
  - A strip on the right, white bold gothic, right-aligned, about **x 852-1024, y 574-706** (rows about 22 px apart):
    `パーツ移動 パーツ拡大` / `パーツ移動小` / `パーツ45度回転` / `一括回収 カメラ初期化` / `ズーム` / `武器回転 回転`.
    That is the guide in the screenshot: the `SELECT` and `L` `R` button pictures sit elsewhere in the same texture
    (x ~310-370, y ~455-505, and x ~520-560, y ~450-465).
  - The 1.05 version only differs from the base one in three places (2,959 pixels): it adds `一括回収` ("collect all")
    and orange arrow pieces (`png/diff_base_vs_patch.png`).
  - More baked Japanese in the same texture: the orange touch labels `カメラ 回転 拡縮 アタッチ 決定 回転1 回転2`
    (around x 350-760, y 365-420), the yellow `装着 / 右装着 / 左装着` (x ~320-400, y 125-200), and
    `ステルス / 装備不可 / 装備` (x ~410-505, y 430-505).
- The UI project that places these pieces is `ui_common.crbpj` (CRI "CRBD", update archive id 37). Its cast list has
  a block `--------CameraOperation--------` with `obj_operation1` .. `obj_operation14` and `obj_DLC_operation1/2`
  (names at file offsets 0x26ab-0x27b5), next to `obj_buttonExplanation`, `obj_CommandHelp_Long/Short`. So the guide is
  sprites of this texture.
- `tex_nova_ui_Title.aif` (1.05 update, id 40; 1024 x 512, same format): every page-title banner as a picture, one row
  per title, 20 px high, white on alpha. `キャラクタークリエイト` is the row at **x 4-212, y 172-192**. Others: items,
  shop, costume, skill board, cold sleep, theatre, menu, tutorial, Gigantes battle, ... The small English sub-titles
  under each banner ("CHARACTER CREATE" etc.) are the small rows in the lower left (y ~350-510), already English.
- Not text anywhere else: `カメラ初期化`, `ズーム`, `キャラクタークリエイト` searched as Shift-JIS, UTF-8 and UTF-16LE
  in all 11,314 CSV and 6,179 Lua files of both archives (`dump/psnova-l10n/scan/`), in all 101+9 `.crbpj`/`.crttl`
  layouts and in `eboot.bin.elf`: not found (only `カメラ` alone, in unrelated rows). In the 25,484 messages,
  `カメラ初期化` is only message 430060 (now "Camera Reset"), and `ズーム` is in no message: 430060 is not what the guide
  draws.
- The fan rePatch: `dev/psnova/inventory/compare-patch105-vs-repatch.tsv` shows `tex_nova_ui_Title.aif` **same** as
  Sega's (never translated) and `tex_nova_ui_common.aif` only in Sega's update (the rePatch dropped it; our pipeline
  carries it over, `pipeline/cri/README.md`). The only texture the rePatch changed is `nova_ui_title.aif` (title screen).

### Other UI textures surveyed

| Texture | Baked text |
|---|---|
| `tex_nova_ui_common.aif` | guide strip, touch labels, equip labels (above) |
| `tex_nova_ui_Title.aif` | all page-title banners (Japanese) + small English sub-titles |
| `tex_Chapter.aif` (base, 1024x1024) | chapter title cards: Japanese words (滅び, 歴史, 約束, 惑星, ...) and English chapter names |
| `tex_nova_ui_emergency.aif`, `tex_nova_Result.aif`, `ui_field.aif`, `UI_ChainLink.aif`, `tex_nova_ui_Class.aif` | English/Latin only (CODE EMERGENCY, RANK, GRAN LINK, digits, MORTAL BLOW) |
| `ui_tut_*.aif` (134 + 5) | gameplay pictures, no text (two checked + `ui_tut_common`) |
| `Credit_*.aif` (71), `nova_ui_title.aif` | not looked at here (credits = known texture job; title screen = fan English exists) |

## 2. How table strings would reach the screen

### The program can draw Shift-JIS table strings, through UTF-16

- **Shift-JIS -> UTF-16 converter `fn_8157e7d0(src, dst, maxlen)`**: a byte < 0x7f -> `table[b]`; a lead byte 0x81-0x9f /
  0xe0-0xef with its trail byte -> `table[code - 0x8060]` (codes 0x813f-0xeaa4); table of u32 at guest **0x823a0a50**.
  Checked: ASCII maps to itself (0x41 -> U+0041); `フィルディア` -> U+30D5 30A3 30EB 30C7 30A3 30A2. It has 24 calling
  functions (e.g. 0x810b9898, 0x81475da2, 0x8159605a (16 calls), 0x8150940e, 0x81676236, 0x819521a8).
- **UTF-16 -> glyph code `fn_8194f90e(textmgr, u16)`**: looks the character up in a std::map at textmgr+0x286c. The
  character list behind it is the UTF-16 table at guest **0x824723fc**: `0-9 - . ' A-Z a-z`, hiragana, katakana, spaces,
  punctuation, full-width letters and digits, `☆★＠` (the BasicCharSet order). **No kanji, no Arabic.** A UTF-16 string
  can only show those characters, in the game's own BasicCharSet font.
- Two users of that mapping (`right-alignment-research.md` 2.2/2.3): the text-box request type 2
  (`TextBox` vtable 0x8241a0ac +0xac = `fn_81908d06`, "set u16 string" -> worker `fn_8195148e` -> `fn_8194f956`: player
  names and the like), and the message control code **0x8093 xx** = "insert string slot xx" in the message decoder
  `fn_817e65fc` (0x817e69d8-0x817e6a3c: slot pointer from `fn_819568f4`, wcslen, each u16 through `fn_8194f90e`).

### StringFix_Name*: string slots that no message uses

- The 15 key names `StringFix_NameRut` .. `StringFix_NameQue` are strings at guest 0x823b8350 .. 0x823b8468 (17-byte
  stride), right after `HalfWordSpace` (0x823b4db8) and before `msg_%llu.rmd` (0x823b847c): text-system code.
- They are used only by **`fn_819521a8`** (game_part43.c line 317805; an event handler, record at 0x824723f4 next to
  the layout names `parts` / `obj_BaseName1` / `open`; it acts on event type 10, id 0x26e). It builds the 15 keys as
  std::strings (0x819521ec-0x81952556), then for each (loop 0x81952568-0x819525ec): `fn_81595284` reads the key's string
  from the parameter-table manager `[0x82493f9c]` (= `uireferenceparameter.csv`), `fn_8157e7d0` converts it to UTF-16,
  `wcslen` (0x822eb704), and up to 31 characters are copied to **this + 0x8e4 + i * 0x40**.
- `fn_819568f4(textmgr, n)` returns string slot n (1..127) at **textmgr + 0x864 + n * 0x40**, so the names fill slots
  2..16 (Rut 2, Sai 3, Izu 4, Mag 5, Fir 6, Rev 7, Jun 8, Cal 9, Kis 10, Rit 11, Yom 12, Hyp 13, Orc 14, Sha 15, Que 16),
  assuming `this` is the text manager `[0x82493f10]` (same 0x40-byte slot layout and module; not traced at run time).
- **No message file contains 0x8093**: control codes counted in all jp_base, jp_patch and en_patch files: only 0x8081,
  0x8082, 0x8094 (14), 0x8099. So these names are not drawn by any shipped message. Low priority.
- If they ever matter: writing ASCII English into the overlay's `uireferenceparameter.csv` works (the converter passes
  ASCII, the map has A-Z a-z), but it would draw in the game's own BasicCharSet letters (not the supplied font), at most 31
  characters; Arabic cannot go this way without a hook (e.g. replace the UTF-16 path by rendering a picture).

### NpcBaseParameter.csv: the name on screen is a message id

Rows `key5001`..`key5017` (update archive): column 27 is a Shift-JIS label, column 28 the partner call-out line message,
the **last column the name message**:

| key | label (col 27) | col 28 | last col | message text |
|---|---|---|---|---|
| key5001 | ルティナ | 530001 | 30001 | ルティナ -> Lutina |
| key5004 | ユノ | 530443 | 30013 | ユノ -> Juno |
| key5005 | フィルディア | 530005 (おっしゃーオレも戦場に出るぜ！！…) | 30004 | フィルディア -> Fildia / فيلديا |
| key5007 | レイヴァン幼少期（欠番） | 530000 | (none) | label = "Raven as a child (unused number)": a developer note |

All 14 character rows (key5001-5006, 5008-5015) line up the same way (30001-30014), and labels like `（欠番）` show column 27 is for developers. The
game draws the name from message 3000x, already translated (sheet v4 and v5). Test 8 (Arabic) and test 9 (English)
screenshots show the speaker plates translated (`ingame_text9/shot_21300.png`: "Fildia"). The Japanese `フィルディア`
seen in the arena before (notes, test 7) is not reproduced in tests 8/9; if it shows again, take a screenshot of it:
the CSV label is not the source.

### The other tables

- `guide_message_parameter.csv`: rows give an NPC id (5015) and a message id (260079); the Japanese is only in the
  header row as column labels (`オペレータ5フィルディア`).
- `MainMenuHelp.csv`: each row has a message id (e.g. 800181) next to the Japanese source line; message 800181 holds the
  same text (translated). The CSV text is a source copy.
- `charactermake_resource_database_*.csv` (`ja_name`, `en_name`): the program contains the column name `en_name`
  (0x823aee4c) but no `ja_name`: the Japanese part names are not read. `en_name` values are internal ids
  (`fildia_long`).
- Dialogue CSVs (`MP*.csv`, `SP*.csv`, `PQ*.csv`, ...): `MessageID` column + Japanese source; drawn from the messages
  (85-100 % found as messages, `text-format.md`).

## 3. Recommendation (cheapest correct fix)

**Redraw the two textures per language** (`tex_nova_ui_common.aif` and `tex_nova_ui_Title.aif`, starting from Sega's 1.05
versions) and add them as replaced entries to `lang/en` and `lang/ar` `NOVA_FileList_Vita_patch.cpk` (the overlay
archives already carry both entries; `cpk_build.build(base, out, files)` replaces entries by name). No code change, no
hook. Steps:

1. Decode (`aif2png.py` logic: header 0x1e0, DXT5, Morton order via `rmdlib._perm`).
2. Clear the Japanese label pixels and draw the new label inside the same rectangle (the sprite rectangles are fixed in
   `ui_common.crbpj` / `ui_title.crbpj`; staying inside the old ink box is safe). Guide strip: right-aligned white bold
   text, ~20 px rows (English: "Move part", "Enlarge part", "Move part (fine)", "Rotate part 45°", "Collect all",
   "Reset camera", "Zoom", "Rotate weapon", "Rotate"; Arabic: shaped, right-to-left pictures; the strip is already
   right-aligned, so Arabic fits naturally). Title banners: 20 px rows; for English the small English sub-title is
   already there, so the big row could say the same in the supplied font or keep a short form.
3. Re-encode only the 4x4 blocks that changed (DXT5 encoder: alpha endpoints + colour endpoints per block); copy every
   other block byte for byte, and keep the 0x1e0 header unchanged (same texture ID at 0x91-0x93 - only one version is
   in each language's archive, so the game's texture cache is not confused).
4. Fonts from `dev/psnova/fonts.json` (game_english may be too thin for the bold guide; a bold font may read
   better; check in game).

Also worth doing in the same pass: the other labels in `tex_nova_ui_common.aif` (touch labels, equip labels) and the
chapter cards in `tex_Chapter.aif`. Leave `StringFix_*` and the CSV labels alone (not on screen).

Open: exact sprite rectangles of each `obj_operation*` cast (read from `ui_common.crbpj` before drawing, or test the
redraw in game); which screens use the touch/equip labels; the title screen texture `nova_ui_title.aif` in our build.

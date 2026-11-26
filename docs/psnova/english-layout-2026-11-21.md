# English text layout, 21 November 2026

This change uses the existing English sheet v7 and the supplied font. It changes the English presentation of translated text in the PCSG00351 1.05 recomp.

## Movies and warning

`dev/psnova/burn_subs.py` measures the English words at the configured font size. A cue that exceeds the available width wraps at a word boundary. If two rows still exceed that width, the renderer reduces the font size in both dimensions. All 138 cues across the eight current story videos fit on one row at 28 px with their complete word sequences. Each re-encode kept the original frame count. The installed English movie CPK contains all eight rebuilt videos plus the rebuilt `Attention.mp4`. Each of those nine entries was compared byte for byte with its source MP4 after installation.

`dev/psnova/redraw_attention.py` centers the boot notice as three lines, including the heading. On the 960 × 544 hold frame the three visible pixel bands span x=444–515, 93–865 and 290–669. Their centers are within half a pixel of the screen center. The whole group spans y=212–328. See `dump/psnova-l10n/movies_l10n/Attention_en_still.png`.

## In-engine text

`dev/psnova/rmdtext/english_layout.py` identifies event text from Lua calls, caption lists, event CSVs, operator transmission variants and NPC talk tables. Explicit choice-only entries keep their existing layout. The 15-digit NPC/battle message banks include variants absent from the literal call lists. For 14 unreferenced main-story cues, full cells were chosen so either the cinematic drawer or a proportional text box can display the results.

`encode_text.py` measures complete text runs in pixels and preserves the sequence of words and inline controls. The body casts in `ui_field.crbpj` set the width to 483 px for regular dialogue (record 0xf01c) and 462 px for portrait radio messages (0xdae4). The planner uses the fewest rows that fit with strictly descending widths, up to three. It favors a gentle taper and nearby punctuation so sentences stay together where space allows. If a long message needs smaller letters, it is rasterized at a smaller font size. In-engine cinematic captions allow at most two rows. Their text is drawn first and then cut into exact 21 × 21 pixel tiles. Padding occurs at the end of a run, so the cinematic drawer can place every tile in its fixed cell with the original letter proportions.

The installed English text archive contains 6,348 regular dialogue messages, 2,906 radio messages and 323 caption-format messages. Of those captions, 320 fit on one row and three use two rows. These totals cover translated rows. The sheet also contains a Japanese developer placeholder for MP00_010_050 that differs between columns only in whitespace. The incremental build keeps the installed copy of that placeholder.

The Advanced Personnel survey-team message (101010020140051) measures 371 and 318 px across its two rows. Kisara's Kuklonahda transmission (261211) splits at the sentence boundary into 236 and 231 px. The validator decodes the actual packaged RMDs and checks row order, bounds, glyph counts and caption tile widths.

Every multiline dialogue in the installed archive had strictly descending widths, with a smallest adjacent difference of 2 px. A separate comparison preserved every word and inline control and reproduced the encoded bytes for all 9,577 messages. A pixel comparison against the supplied font drawn directly from the sheet matched all 323 caption-format messages and both dialogue examples to within the archive's 4-bit alpha quantization. The installed patch archive is 804,970,984 bytes and its SHA-256 is `82d8d1d0e1d821b375dffbe296a4e03b3860081fafa954acc09f249bf11268fa`. Demuxed audio packet hashes matched the source on all eight story movies and the boot warning.

## Speaker names

`dev/psnova/center_dialogue_names.py` changes the two name casts in the English `ui_field.crbpj`. The NPC message window has a portrait cast named `Cast_NpcIcon` beside `TextBox__NpcName`. The other window uses `TextBox__PlayerName`. Both name boxes are 210 × 21 native pixels. The change appends parameter blocks containing the original `Priority=60` and native `Align=2`, then redirects only these two cast records. The names are measured by the game when drawn, including player-entered names. Running the patch on its own output gives identical bytes.

An isolated English new-game run used a copy of this nameplate asset and fresh test saves. At frame 17100 the game reported a 52 px name in a 210 px box starting at x=231, with native center alignment active. The name's center was x=336. Frame 18000 visibly shows Rietheia centered on the plate. Evidence is in `dump/psnova-l10n/english_layout_20261121/Rietheia-nameplate.png` and `nameplate-trace.txt`. This playthrough checked name placement. The revised body and cinematic line breaks were verified from the final installed archive. The test did not exercise a custom player-entered name or every story scene.

## Build and verify

From the project root, with the extracted game tables under `dump/psnova-l10n/scan`, rebuild against the current English overlay to preserve its translated UI textures, names and other assets. Stage on a volume with space for the output archive and encoded RMDs.

```powershell
$sheet = 'dump/psnova-l10n/sheet/psnova_text_v7.tsv'
$live = 'dump/decrypted/PCSG00351/lang/en/NOVA_FileList_Vita_patch.cpk'
$stage = 'dump/psnova-l10n/scratch/english-layout-build'
python dev/psnova/rmdtext/build_l10n.py $sheet en $stage --layout-base $live
python dev/psnova/rmdtext/verify_english_layout.py $sheet "$stage/overlay/NOVA_FileList_Vita_patch.cpk"
```

The builder compares all 27,819 stored entries after repacking. The runtime accesses the same English overlay through `recomp/fs/lang/en`. The dialogue text and nameplate assets share the patch archive. The story videos and boot notice use the separate movie archive.

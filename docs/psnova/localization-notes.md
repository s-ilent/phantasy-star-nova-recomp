# Phantasy Star Nova: localization notes (English + Arabic)

Living log, started 2026-11-18. Every step of the localization work goes here, with its strength:
**proven**, **single run**, **untested**. Scratch output is in `dump/psnova-l10n/` (not part of the project).

## Question 1: what language is the game?

- The game is the **Japanese release** (PCSG00351, JP0177 content id). Base text, voices and UI art are Japanese.
- The player's copy has a `rePatch` folder: the **Arks-Layer English fan translation** (replaces
  `NOVA_FileList_Vita_patch.cpk` and `_movie.cpk`; 2,257 translated files, 5,875 identical to 1.05).
  The recomp layers it on top (`app0_repatched`), so **the build we play shows English text with Japanese voices**
  (proven by the journal's test46/47 notes: "Japanese text" without the rePatch's files, "English" with the merged archive).
- `RECOMP_NO_REPATCH=1` at import plays the pure Japanese game.
- English therefore already exists as a "language" only because a fan patch overwrote Japanese. The game has no
  language switch of its own (single-language Japanese Vita release; no language-select code or per-language
  folders seen in the archive list).

## Where the text lives (archive survey, 2026-11-18, single run)

Tool: `pipeline/cri/cpk.py list|extract` (CRI CPK reader). Lists in `dump/psnova-l10n/{patch,base}.tsv`.

| Archive | Entries | Notes |
|---|---|---|
| `NOVA_FileList_Vita.cpk` (base, 2.8 GB) | 87,268 | 21,379 `.rmd`, 9,735 `.csv`, 5,756 `.lua`, 6,580 `.aif` (images), 18,759 `.aet`, 18,763 `.aai` |
| `NOVA_FileList_Vita_patch.cpk` (English merged) | 23,034 | 20,056 `.rmd`, 1,580 `.csv`, 423 `.lua`, 433 `.aif`, `novamessagedictionary.mdic` |

- **`msg_*.rmd`**: message files (dialogue/menus/etc.), the bulk of the text (about 20,000 files).
- **`novamessagedictionary.mdic`**: magic `BMVN`, UTF-16-looking strings (e.g. "ジャンクション") with ids: a word dictionary.
- **`.csv`** (Shift-JIS) hold tables, some with Japanese labels (e.g. `guide_message_parameter.csv`).
- **`.lua`** scripts (423 patched): may hold some text; not yet checked.
- **`.aif`**: texture/UI images. Text baked into pictures (titles, menu art) must be redrawn per language.

## The `.rmd` format (first look, single run)

Header magic `" DMR"` (bytes `20 44 4d 52`), producer string `FontConverterDll_1.0.1.3_rc6`.
Text is stored as **16-bit little-endian glyph indices, not Unicode**. The same sentence has different codes in the
Japanese file and the English file:

- JP `msg_100001.rmd` (25,072 bytes): codes like `0x019f 0x019e 0x01a6 ...`.
- EN `msg_100001.rmd` (25,200 bytes): codes like `0x008e 0x01e8 0x00a0 ...`, with **`0x01e8` = space**.
  Latin letters sit in a low range (about 0x8e to 0xc0), `0x8080` and `0x8002` are control/line codes.
- Header size field differs (0x2010 vs 0x2090): the EN file carries 128 more bytes.

So the glyph-index table is defined by a **font** (the FontConverter output), and the English fan patch likely ships
its own font + code mapping. **Open**: where that glyph table / font lives (probably a font texture `.aif` plus a map
inside an `.rmd`-adjacent file or the executable), and whether the game's renderer can draw right-to-left text.

## The font lives in `.rmd` files too (found 2026-11-18, single run)

`strings` on `eboot.bin.elf` shows `BasicCharSet.rmd`, `BasicRubySet.rmd`, `llu.rmd` and many `Cast_FontSizeNN` names.
`BasicCharSet.rmd` (270,320 bytes) and `BasicRubySet.rmd` (140,400) are **only in the base archive** (the English patch does
not touch them), so English and Japanese text use the **same glyph set**; the English patch only re-encodes each message
with the codes of Latin letters that already exist in it.

Layout seen in `BasicCharSet.rmd` (same header magic `" DMR"` and `FontConverterDll_1.0.1.3_rc6`):

- header of 0x1e10 bytes holding a **per-glyph table**: records of 16-bit flags + two corner pairs of **float UVs**
  (`0x3d28...`, `0x3e48...` = texture coordinates 0..1) in code order;
- after the header, about 262,000 bytes that look like an **8-bit 512 x 512 glyph bitmap** (the rendered font).
- A message `.rmd` has the same kind of header (0x2010 to 0x2090 bytes: UV records, then the 16-bit text codes at about +0x110).

So the game has **no TrueType font and no Unicode**: text is pre-rendered by a tool (Sega/tri-Ace's *FontConverter*) into
bitmap glyph pages plus code tables. Anything new (Arabic) must be added to these bitmap pages and code tables, and every
message re-encoded. **Not yet decoded** (next steps): the exact record layout, the mapping code -> character,
what `BasicRubySet` (furigana) holds, how the 512 x 512 page is sampled (format, palette), and how `Cast_FontSize*` picks sizes.

## "Native" English: the Japanese subtitles burned into the story movies (2026-11-18, single run)

I noticed the English subtitles appear **below the Japanese ones** and want English to be native (Japanese gone).
Cause, checked on frames: the subtitles in the story movies are **part of the video picture**. Sega's Japanese subtitle line
is burned in; the fan patch re-encoded the movies and burned its English line under it. Nothing can switch the Japanese off at
runtime, so the video itself must change.

- `NOVA_FileList_Vita_movie.cpk` (21 entries, 960x544, H.264 29.97 fps + AAC). The patch's copy differs from the
  base in **8 files**: `MP00_000_000`, `MP00_000_010`, `MP00_010_050`, `MP06_030_040`, `MP06_030_050`, `MP06_030_070`,
  `MP09_040_040`, `MP09_040_070` (plus `Attention.mp4`, the patch credit). The other 12 (`OpeningDemo`, `Trial_*`,
  `MP09_030_*`, `MP09_040_025/030`, `Logo_SEGA_triAce`) are identical to the base, i.e. untranslated.
- Frames of `MP00_000_000.mp4` (extracted to `dump/psnova-l10n/movies/`): Japanese line at about **y 465-505**, English
  line at about y 515-535 (both centred; Japanese is thin white with a dark outline).
- **Test, 3 frames (single run):** mask = near-white pixels in the band y 462-508, dilated 7 px, `cv2.inpaint` (Telea, radius 4)
  removed the Japanese line cleanly on a plain and a moving background (result image `dump/psnova-l10n/movies/inpaint_test.png`),
  leaving the English line untouched. Not yet tried on a whole movie (flicker between frames, bright backgrounds, subtitle
  lines that sit at another height).
- **Plan:** script per movie: decode with OpenCV, inpaint the band on frames where text is detected (white-pixel count in the
  band), re-encode H.264 960x544 with `libx264` + copy the AAC track, write a patched movie archive (`cpk_merge.py` style), run through
  the game's movie player (`runtime/media/video.c` decodes H.264). Optional later: move the English line down to the Japanese
  line's spot.
- Tools: OpenCV (system Python 4.13); ffmpeg with libx264 + mp4 muxer at
  `F:\Antigravity Proj\animation\node_modules\ffmpeg-static\ffmpeg.exe` (the one in `recomp library\metroidprimeport` has no
  H.264 encoder and no png/jpg muxer).
- **Other Japanese left over in the English build:** the "PSO2 Save Bonus Award" dialog on the title screen (progress picture
  panel 3) is still Japanese: a message the patch did not translate; find its `.rmd` or `.csv`. Texture art with baked Japanese
  (`.aif`, e.g. `tex_nova_ui_Title`) not surveyed yet.

### Removing the Japanese line from the 8 movies (run 2026-11-18, single run)

Scripts (all in `dev/psnova/`): `subs_rows.py` (which rows hold subtitle-like pixels), `remove_jp_subs.py` (the cleaner),
`run_remove_jp_subs.sh` (all 8, 4 at a time). Input `dump/psnova-l10n/movies/`, output `dump/psnova-l10n/movies_clean/`, log `dump/psnova-l10n/run_clean.log`.

- Row analysis (every 15th frame): Japanese line **y 473-493** in `MP00_000_000`, `MP06_030_040/050/070`, `MP09_040_070`; **468-487** in
  `MP09_040_040`; about 476-497 in `MP00_000_010` (its English line is bigger and starts at about y 503), `MP00_010_050` about 473-493
  (English from y 500). Other rows with white-outlined pixels (y 130-420 in `MP00_010_050`, `MP09_040_070`) are on-screen scene text
  and must not be touched, so each movie has its own band (bands in the run script).
- Method: per frame count thin strokes in the band (|gray - 9x9 median| > 28); frames over a threshold (700, 450 for the
  detailed `MP09_040_040`) hold text; smoothing in time (gaps up to 8 frames filled, runs under 10 frames dropped, 4 frames added each
  side for fades); `cv2.inpaint` (Telea) on strokes (threshold 12, dilated 9x9) **inside the band only**, then raw frames to ffmpeg
  libx264 (CRF 19, high profile level 4.0, 960x544) with the original AAC audio copied. Frame count in = frame count out is checked.
- Lessons: (1) inpainting must not read below the band, else the English line's black outline bleeds into the fill (dark specks;
  fixed by cropping at the band's bottom); (2) a 20-level stroke threshold left dark outline specks, 12 + 9x9 dilation did not;
  (3) bright, detailed backgrounds (`MP09_040_040` gold sparkle scenes) leave a soft smear where the text was: readable as "no text" but
  not perfect.
- **First full run (17:22) was kept only as a check, then redone:** all 8 files came out with the right frame counts, durations and
  AAC audio (`dev/psnova/verify_clean_movies.py`, sheets `verify_sheet*.png`), Japanese gone in every text frame, **but** frames with
  no subtitle were also smudged (moving scene detail counted as text; worst in `MP06_030_070` and `MP09_040_040`).
- **Fix: temporal persistence.** Burned-in text does not move, scene detail does. Frame detection now counts only strokes that also
  sit on strokes of the previous or next frame, and only those persistent strokes are inpainted. Thresholds (persistent
  stroke counts): 500 for the movies, 900 for `MP09_040_040` (background detail up to ~800). Moving-scene false positives became
  nearly invisible; a bright static shot can still lose a faint soft patch. Text frames on busy backgrounds keep a soft smear.
  Run script writes one log per movie (`run_clean_<name>.log`) since parallel appends to one file interleaved.
- **Second run (17:28) still smudged static no-subtitle shots** (`MP06_030_070`, `MP09_040_040`: slowly moving detail also
  "persists"). **Third fix: use the English line as the clock.** It is burned in at the same times as the Japanese one and is
  always white with a black outline, so it is easy to detect (counts 0, or 160+ per frame; a fade shows 20-40). A frame holds
  Japanese text only when the English-like pixels in the rows under the Japanese band persist (>= 20) **and** the Japanese band
  has persistent strokes (>= 150). The run script uses these defaults for all 8 (`--enthr 20`, `--thr 150`).
- **Third run (17:32, kept): all 8 done.** Frame counts and durations equal the sources, AAC audio kept
  (`verify_clean_movies.py`); text-frame shares 39-85 % per movie (`dump/psnova-l10n/run_clean.log`). The sheets now show the
  no-subtitle static shots untouched and the Japanese gone in every subtitle frame; on bright busy backgrounds a soft smear remains
  where the line was (worst: gold sparkle scenes in `MP09_040_040`, `MP00_000_000` text frames not eyeballed beyond the sampled pairs).
  Not yet watched as video, and not yet played in the game.
- **Patched movie archive built:** `dev/psnova/cpk_replace.py` (new; copies an uncompressed CPK, replaces named entries, lays the
  content out again at Align 512, rewrites TOC + header sizes, reads every entry back and compares). Command (from the project folder):
  `python -I dev/psnova/cpk_replace.py dump/decrypted/PCSG00351/app0_repatched/NOVA_FileList_Vita_movie.cpk
  dump/psnova-l10n/movie_cpk/NOVA_FileList_Vita_movie.cpk --replace MP00_000_000.mp4=dump/psnova-l10n/movies_clean/MP00_000_000.mp4 ...`
  Result `dump/psnova-l10n/movie_cpk/NOVA_FileList_Vita_movie.cpk` = 413,850,912 bytes (base 395,276,064), 21 entries, read back equal
  by `cpk.py`. **Not yet loaded by the game** (the CRI library in the game is the real judge; same layout style as the original: content
  from 2048, TOC then ETOC after it, Align 512).
- **Not installed.** The game still plays the old movie archive (`dump/decrypted/PCSG00351/app0_repatched/`, hard links into the
  rePatch folder: never write into those files). To install: `vitarecomp import` would need a setting that swaps this archive in
  (sibling of `REPATCH_KEEP`, e.g. `MOVIE_OVERRIDE`) or a copy placed over the hard link; decision and test run pending my go-ahead.
- **Test-run etiquette (from the recomp session, 2026-11-18):** it runs `RECOMP_BIN=dev vitarecomp test PCSG00351` (about 16 min each, same folder
  `dump/decrypted/PCSG00351/recomp/test_dev_win` and `game_dev.exe` every time). Ask it before any install or game run and wait for "machine free".
  A parallel run may use `RECOMP_BIN=l10n` (`game_l10n.exe`, `test_l10n_win`): this runtime's `plat_gpu_cache_private()` keeps the NVIDIA cache in
  `nvidia-cache\` beside the exe, so another exe name evicts nothing here (the shader-cache memory rule still applies to the OoT/Uncharted copies).
- Previews (before above, after below): `dump/psnova-l10n/movies/prev_000_010c.png`, `prev_040_040.png`.

## Plan for English and Arabic as options (not yet built)

1. **English/Japanese switch**: cheapest of all. Both sets of files already exist (base archive = Japanese,
   rePatch = English). Add a runtime/launcher setting that picks which archive layering the file layer serves
   (the `REPATCH` layer on or off, per run). Voices stay Japanese either way.
2. **Arabic**: needs three pieces
   - a text export of all ~20,000 `.rmd` (decode glyph indices -> Unicode using the font map; menus/short labels get a first-pass translation,
     I fill dialogue, as for Wonder; see `memory: every-recomp-standard`);
   - an Arabic **font** with joined/contextual forms (presentation forms) added to the game's font texture + glyph map;
   - **right-to-left layout** (reverse order, mirrored alignment) in the text drawing code, and a re-encoder that writes
     `.rmd` files back with the new glyph codes, then a patched archive (`cpk_merge.py` already copies/merges entries).
   - UI art with baked-in text (`.aif`) is Japanese/English only; Arabic versions would need redrawn textures.
3. **Selection at launch**: a `language = ja | en | ar` setting in the game's ini plus a launcher option.

Reusable reference: `Super Mario Bros Wonder\tools\arabic\README.md` (pipeline for the same job).

## Decisions and cost rule

- The rule (2026-11-18): **use scripts for repeatable work when possible**. So far everything was done by
  scripts (`cpk.py list/extract`, `xxd`, `grep -a`). Bulk work to come (decode ~20,000 messages, code tables, Arabic
  export workbook) is script work; spot-check and indexing results are verified before use.
- Document every step in this file (I asked, 2026-11-18).

## Log

- 2026-11-18 (evening): recomp session informed (it committed 527045b with the first notes; its REPATCH_KEEP layering is in `vitarecomp import`).
  Built `subs_rows.py`, `remove_jp_subs.py` (3 detection fixes), `run_remove_jp_subs.sh`, `verify_clean_movies.py`, `cpk_replace.py`;
  8 cleaned movies + patched movie archive in `dump/psnova-l10n/`. Not installed, not played.
- 2026-11-18 (later): I asked for "native" English; confirmed Japanese hard subtitles in the 8 patched story movies,
  inpaint test on 3 frames looked clean, found a libx264 ffmpeg. Nothing in the game or build changed.
- 2026-11-18: surveyed archives, extracted `msg_100001.rmd` (JP and EN), `novamessagedictionary.mdic`, `guide_message_parameter.csv`
  to `dump/psnova-l10n/sample/`; found the glyph-index text format. Nothing in the game or build was changed.

## Decision 2026-11-18 evening: Japanese-only base + our own overlay

My decision (relayed by the recomp session): the game runs only from the Japanese app0_patched (game + 1.05, no rePatch); burned-in movie subtitles are removed and English + Arabic are added by us.
- Import change (made by this session, uncommitted): `packs/PCSG00351/pack.toml` `REPATCH = "off"` (same as RECOMP_NO_REPATCH=1); `pipeline/vitarecomp.py` cmd_import also layers `$W/overlay0/` (same layout as app0, hard links, never writes into sources) into `app0_overlay` after any rePatch; `RECOMP_NO_OVERLAY=1` skips it. overlay0 does not exist yet: import now gives exactly app0_patched. I did not run `vitarecomp import` (recomp session re-points its tests).
- CONSEQUENCE for movies: the 8 cleaned movies in `dump/psnova-l10n/movies_clean/` were made from the rePatch movies (English burned in, Japanese removed). Under Japanese-only the source must be the ORIGINAL Japanese movies (base `NOVA_FileList_Vita_movie.cpk`) with the Japanese line removed; there is no English line to key detection on, so `remove_jp_subs.py` needs a new presence detector (Japanese strokes alone, persistence, etc.). The old output is only a stopgap (it would show the fan English line). Nothing goes into overlay0 until I say go and the recomp session says the machine is free.

## Survey of the 13 movies without a burned-in subtitle line (2026-11-18 evening, I asked "will all movies be subtitled?")

Goal restated by me: by the end, every movie must be correctly subtitled/localized in English and Arabic. Removing the Japanese line from the 8 story movies is only step 1; adding English/Arabic text is separate and not built. Tool: `dev/psnova/survey_other_movies.py` (audio per second + contact sheet every 3 s; outputs `dump/psnova-l10n/others/<name>_sheet.png`, `_audio.txt`). No speech model is installed, so "does it speak" is judged from the sheets; the audio numbers are weak (dialogue movies ~0.35 syllable-rate modulation, these 0.20-0.32).
- Silent (no audio at all): Attention, Logo_SEGA_triAce, Trial_005, Trial_Attention, Trial_End (Attention/Trial_Attention/Trial_End carry baked text: check what language; Trial_End has many text rows).
- MP09_030_030, MP09_040_030: pure CG (planet, no characters on screen). MP09_040_025: a few characters, a hologram figure; no subtitle line. Whether any of these has spoken lines is UNVERIFIED (needs listening or a speech model). They differ from the 8 story movies in that the fan patch left them untouched.
- OpeningDemo (140 s): in-universe decorative script (cyan glyphs in a fictional alphabet) shown as titles/narration lines; no Japanese subtitle line. Not obviously translatable; ask me whether it should be (does the voice speak these lines?).
- Trial_001..Trial_004 (25-47 s each): in-engine tutorial captures (HUD) with BAKED JAPANESE instruction text in a box at the bottom (y ~ 465-530) plus a Japanese title card (e.g. "(1) new weapon description"). These are a different localization job (translate + redraw a text box over gameplay footage), not a line removal. Unknown whether the game plays them (Trial = trial version content?).
- Credits are textures (Credit_0000.aif..), another localization item.
So "all movies subtitled" splits into: (a) 8 story movies (remove JP, add EN/AR subtitles from the line text), (b) Trial_001-004 (redraw instruction box), (c) possibly OpeningDemo / the 3 other MP09 CGs if they have speech. Open: which of these the game actually plays.

### Which movies does the game play? (data survey, 2026-11-18 evening; scratch: dump/psnova-l10n/scan/ = all .csv and .lua of base + patch archives)
- `MovieList.csv` (base archive) registers all 21 files as MovieNo0..MovieNo20 (order: the 11 MPxx story movies, Attention, Logo_SEGA_triAce, OpeningDemo, Trial_Attention, Trial_001..005, Trial_End). The eboot itself names only four movies as strings (Attention, Logo_SEGA_triAce, OpeningDemo, MP00_000_000); the rest come from data.
- Story movies: played by event scripts (`event_boot_parameter.csv` rows of type `Movie`, e.g. quest-clear event for MP09_040_025 -> `Movie,MP09_040_025.mp4`) and replayable from the Theatre (`TheatreEvent.csv`: chapter/event list, one row per cutscene, flags `<event>_ed`). So MP09_030_030 / 040_025 / 040_030 ARE normal story cutscenes (they have EventScriptList + lua), not leftovers.
- Trial movies: `Trial_End.mp4` is played by the event `Trial_Demo` (event_boot_parameter key73, id 3000030). The data also holds a whole trial-version game: `Trialgame.*` registries and quest ids 120010-120030 (all end in `Trial_Demo`), `region01.quest_registry.csv` quest 110010 also names `Trial_Demo`, and many `*_trial_*` enemy/boss parameter files. Trial_001..005 and Trial_Attention appear in no csv/lua except MovieList: they are chosen by number from code, i.e. the trial-version demo flow. UNVERIFIED whether a retail playthrough ever reaches them (needs a run with movie-open logging, or reading the eboot's caller of MovieNo14..19). Treat them as low priority until proven reachable.
- Open question for the recomp session: its scripted runs log file opens? A grep of the runs for `.mp4` would show which movies have actually been opened so far.

### The four silent movies with text (read 2026-11-18 evening, frames in dump/psnova-l10n/others/silent_text.png)
- `Attention.mp4` (5 s, named in the eboot, plays at boot): Japanese anti-piracy notice on black ("<Caution> Distributing the game software over the internet without the rights holder's permission, or downloading it knowing the distribution is illegal, is strictly forbidden by law. Thank you for your understanding and cooperation."). 4 lines of white text on pure black: the easiest redraw of all (render English / Arabic text on black, same layout, re-encode). A retail boot movie, so it should be localized.
- `Trial_Attention.mp4` (5 s): trial-version warning ("contents/specs of this trial version are in development and partly differ from the product; unforeseen malfunctions possible; support not provided"). Trial-version only.
- `Trial_End.mp4` (10 s): trial-version ending ad on gameplay art: "The early-game trial ends here; enjoy the rest in the product version", "on sale 27 Nov 2014, price 5,980 yen (excl. tax)". Trial-version only; text is part of a picture (needs redraw over artwork, or leave).
- `Trial_005.mp4` (5 s): title card "Trial tutorial" + "Gigantes battle demo 5: [Weak point (core)] explanation will be played". Same family as Trial_001..004 (tutorial text boxes).
Priority: Attention (retail boot, trivial redraw) > story movies (8) > Trial_* family (only if proven reachable).

### Movies actually played in the recomp session's scripted run (its message 2026-11-18 evening; test55, Japanese files, title -> arena, frame 25,000)
File opens show only NOVA_FileList_Vita_movie.cpk (the AvPlayer reads inside it), so names are inferred from the 5 'avPlayer Controller' threads started: (1) frames 0-300 boot = Attention (anti-piracy notice), (2) 300-600 = Logo_SEGA_triAce, (3) 600-900 = OpeningDemo (Start skips it), (4) ~1800-2100 after NEW GAME = MP00_000_000 (story intro), (5) ~13,500-13,800 after the character-creation save = warp cutscene with a burned-in line, probably MP00_000_010 (unconfirmed). No movie plays in the ship corridor / arena tutorial (in-engine scenes). Consequence: Attention is confirmed played at every boot (redraw first); MP00_000_000 and MP00_000_010 are the first two story movies a player meets. Exact names would need an AvPlayer source log (RECOMP_LOG_IMPORTS=sceAvPlayerAddSource plus printing the path): offered by the recomp session, not requested yet.

## Movies v2: the ORIGINAL Japanese movies cleaned (2026-11-18 evening, I said "yes, redo them")

Result: `dump/psnova-l10n/movies_clean_jp/*.mp4` (8 cleaned story movies) and `dump/psnova-l10n/movie_cpk_jp/NOVA_FileList_Vita_movie.cpk` (452,742,240 bytes, the game's own archive with those 8 entries replaced, all 21 entries read back equal). **NOT installed, NOT played in the game.** Install = put the file in `$W/overlay0/` (W = dump/decrypted/PCSG00351), run `vitarecomp import`; needs my go-ahead and the recomp session's "machine free". The older `movie_cpk/` archive (made from the rePatch movies, English line still in) is obsolete.

- Source: `movies_jp/` = all 21 entries extracted from app0_patched's NOVA_FileList_Vita_movie.cpk (395,112,448 bytes, Sony's own). The same 8 movies carry a Japanese line (rows ~464-499); the 13 others have none (see the survey sections below).
- Why v1 failed on originals: it keyed on the English line the fan patch added, and its "white fill + dark outline" test misses the text on bright backgrounds (the subtitle has only a soft shadow there). The old English-line mask was also unreliable (missed lines on bright backgrounds, e.g. MP06_030_050 frames 234-538).
- Detector (dev/psnova/remove_jp_subs_v2.py): top-hat (9x9) of the per-pixel MIN of B,G,R ("whiteness": golden/red glow lines are saturated, so they are not white), persistent in >= 8 of 11 frames, minus tall vertical structures (26-px vertical opening: legs, glow lines, edges; a glyph is <= ~22 px tall). A frame has text when the kept pixels > 350 (MP09_040_040: 700, a busy glow movie); smoothed in time (fill 8, drop runs < 12, pad 4). Union with the fan copy's English line (patched minus original in rows 495..535 > 150 px, aligned per frame over -1/0/+1; the fan encode has one frame more or less in 6 movies): the English line only exists when the Japanese one does, and diff noise elsewhere is ~0.
- Cleaning: mask = the same persistent pixels at threshold 30, dilated 9x9, clipped to the band; cv2 Telea inpaint on the crop y0-8..y1+8 (the original has no second line below); libx264 CRF 19 high level 4.0, audio stream copied. Cleaned movies are bigger than the originals (36 -> 49 MB, 88 -> 135 MB): CRF 19 re-encode; the archive grew by 57.6 MB.
- Dead ends this evening (do not repeat): plain top-hat on gray, the dark-outline test, band-vs-neighbour-rows ratio, a glyph-sized component filter (text merged with background was dropped, so text stayed), the English diff alone (some lines have no English at all: dots-only lines like "......", and lines the translators skipped).
- How it was checked: a hand-labelled set of 48 random frames of MP09_040_040 (29 text, 18 none): at the final settings no ordinary text frame is missed; 2 dots-only frames (3361, 7349) were missed at threshold 900; false positives (no text, treated as text) cost only a soft white patch because the mask holds only white thin pixels. verify_clean_jp.py: frame counts equal (all 8), durations equal, audio present; residue run of the detector on the cleaned movies: MP00_000_000 frames 2642-3051 (looked at: no text; the inpainted smear on a bright pattern still counts as white), MP09_040_040 frames 7555-7563 (looked at: no text). 64 random frames the cleaner left untouched (8 per movie) were looked at: no Japanese text. 16 cleaned vs original frames compared by eye (qa_clean.png): text gone everywhere.
- Known flaws: (1) a soft blur patch where the line was on busy backgrounds (worst MP09_040_040, MP00_010_050, MP00_000_000 on the bright blue pattern); (2) faint ghost marks of thin "!" strokes in some frames (MP06_030_070 frame ~494); (3) dots-only lines ("......") with weak pixels may stay in a few frames; (4) not yet watched as video, not yet played in the game; the CRI library's acceptance of the re-laid-out archive is unproven.
- Archive tool: dev/psnova/cpk_replace.py now also handles the game's own layout (TOC at 2048 BEFORE the content, scrambled tables, Align 8, ContentSize present, Enabled sizes = 2 x sum). Self-test: with no replacements it reproduces the original archive byte for byte (cmp identical); this also showed the tables are scrambled (flag 0), so the TOC and ETOC blobs are scrambled again when written.
- Scripts: remove_jp_subs_v2.py (cleaner), run_remove_jp_subs_v2.sh (all 8, 4 at a time, per-movie thresholds and bands), verify_clean_jp.py, cpk_replace.py. Experiments, superseded: jp_presence.py, jp_presence2.py. A stray enum.py in the system Temp folder shadows the standard library for scripts run from there: run helper scripts from the scratchpad directory.
- Still open for movies: the 13 other movies (survey: Trial_001..004 have baked Japanese instruction text and a title card = redraw job; three silent ones have text not yet read); whether the English line goes where the Japanese line was; native subtitle rendering (the game's own subtitle path, if any) vs burned-in English.

## Attention redraw (English + Arabic), 2026-11-18 night

`Attention.mp4` is the anti-piracy notice the game plays at every boot. I said go. It is redrawn, not cleaned,
because it is only text on black.

- Script: `dev/psnova/redraw_attention.py` (run `python dev/psnova/redraw_attention.py [en] [ar]`). It only reads
  `dump/psnova-l10n/movies_jp/Attention.mp4` and writes to `dump/psnova-l10n/movies_l10n/`:
  `Attention_en.mp4`, `Attention_ar.mp4`, a still of each (`_still.png`, at 2.5 s) and the line texts (`text/<lang>/`).
- Matches the original: 960x544, 29.97 fps, 149 frames, 5.01 s; H.264 High level 3.1, 3 refs, bt709 tv range; the
  original's silent AAC track copied as is. Fade in over frames 0-30, fade out over frames 119-148. Measured peak per frame
  agrees with the original within 4 levels (frames 0/15/30/75/119/134/148: original 0/132/255/255/255/136/10).
- Layout from the original: heading centred, 4 lines, row centres y = 153/201/249/296/344, margins x = 100..860. English
  is left-aligned (Segoe UI 24). Arabic is right-aligned at x = 860 (Segoe UI 26).
- Wording (translated from the Japanese 〈ご注意〉 text):
  - EN: "< Notice > / Distributing or sharing game software over the internet without / the permission of the rights
    holder, or downloading it while knowing / it was distributed illegally, is strictly prohibited by law. / Thank you
    for your understanding and cooperation."
  - AR: "< تنبيه > / يحظر القانون حظرا تاما توزيع برامج الألعاب أو نشرها عبر الإنترنت / دون إذن صاحب الحقوق، وكذلك تنزيلها
    مع العلم بأنها منشورة / عبر الإنترنت بصورة غير قانونية. / نشكركم على تفهمكم وتعاونكم."
- Arabic drawing lessons (ffmpeg-static 6.1 drawtext, `text_shaping=1`, harfbuzz + fribidi; PIL here has no raqm and
  arabic_reshaper is not installed):
  - Dubai drew several letters (ا ن و ز, final forms) as boxes. Tahoma put the tanween on the wrong letter
    ("تأما"). Segoe UI drew every letter, so it is used, without tashkeel.
  - drawtext lays a line out with a left-to-right base direction, so a final period landed on the right. An RLM
    (U+200F) after the period puts it on the left.
  - drawtext places each line by its own tallest glyph, so Arabic rows drifted by a few px. The script measures each
    Arabic line's baseline (the row with the most ink, which is the joining stroke) on a test render and puts the rows
    on a fixed grid. These lessons apply to the movie subtitles too, if they are drawn with drawtext.
- sha256: en bbe08cb2474d0b6f8169c990b692d0a0a84f1c3c172953d07945d1bb1fe3feb0, ar
  4ed59f8ae3aff7dce183fd05a1f68dc5d5fc2a8d470a31faaff8d58971ee1f41.
- NOT installed. The movie archive is one file for all languages, so selectable EN/AR movies need either one archive per
  language (chosen at import or launch) or a runtime choice of file. That is undecided and belongs to the language switch
  work. Archive building and overlay0 stay with the main localization session.
- Not checked in the game (no run was made). The H.264 settings match the original's, so the firmware AvPlayer should
  take it, but that is unverified until a run.

## Movies v2 installed and tested in the game (2026-11-18, 22:10-22:45, I said "Yes" to install and test)

- **Installed:** `dump/decrypted/PCSG00351/overlay0/NOVA_FileList_Vita_movie.cpk` (a copy of `movie_cpk_jp/`'s, 452,742,240 bytes). `vitarecomp import` layered it: `app0_overlay` = app0_patched's 78 files with only this one different (file lists compared, the archive compared with cmp), and `recomp/fs/app0` now points at `app0_overlay`. Undo: `RECOMP_NO_OVERLAY=1 vitarecomp import` (re-points app0 at app0_patched). All PS Nova sessions told.
- **Test runs** (separate exe, nothing of the recomp session's touched): `game_l10n.exe` = a copy of the 19:12 `game_host.exe`; `RECOMP_BIN=l10n ... vitarecomp test PCSG00351` (folder `recomp/test_l10n_win`, fresh save each run, so no save backup was needed).
  - Run 1: `TEST_INPUT="1300-1340:8,1700-1740:8" TEST_FRAMES=5700 SHOT_EVERY=150 EXTRA_ENV="RECOMP_GFX=gpu RECOMP_CLOCK=real"`. Stopped at the title menu: NEW GAME needs Circle (0x2000) at ~2000 (the proven script's third press, not a movie skip). Still useful: Attention, the SEGA and tri-Ace logos and OpeningDemo all played from the new archive (its TOC and offsets are new, so the CRI library accepts the re-laid-out archive). Shots: `dump/psnova-l10n/ingame_run1/`.
  - Run 2: `TEST_INPUT="1300-1340:8,1700-1740:8,2000-2015:2000" TEST_FRAMES=5800 SHOT_EVERY=100 EXTRA_ENV="RECOMP_GFX=gpu"` (fixed clock). MP00_000_000 played from frame ~2050 to ~5150 (the whole movie, 3,407 frames), then character creation. Shots, contact sheet, subtitle-band strips: `dump/psnova-l10n/ingame_run2/` (sheet.png, bands.png, game_vs_file.png).
- **The game shows exactly what the file holds:** each screenshot was matched to its frame of the cleaned movie (dev/psnova/match_game.py; e.g. game 2900 = movie frame 895); the game's band and the file's band are the same picture. So the decoder and the archive are fine and every flaw below is in the cleaning.
- **Flaws seen in the game (the cleaning is NOT good enough yet):**
  1. **Text left at line fades/changes.** Game 2900 = movie frame 895: about half of "全宇宙の平和を……』" is still there. c2_MP00_000_000.npz: kept pixels 4,003 at frame 892, 35 at 896, 0 at 900; the frame is marked "present" but the mask is nearly empty, because a pixel must be above the threshold in 8 of 11 frames and a fading line fails that. Fix: build one mask per LINE (from its full-strength frames) and apply it to every frame of the line, fades included.
  2. **Visible smears.** The mask (strokes dilated 9x9) joins a line's glyphs into one solid strip, and Telea fills it from the edges: blurred, streaky strips in game 2200, 2800, 3400 and worst in 4600-5000 (a near-still planet scene, where the smear is a plain horizontal band). Fix: a tighter mask, and fill from other frames (in still or slow scenes the true background is in frames before or after the line, or under the line in frames where the text has moved on); spatial inpaint only as a last resort. The best quality would be a video-inpainting model (ProPainter or E2FGVI: flow-guided, fills from neighbouring frames); that needs a model download (my decision).
- Scripts kept: dev/psnova/sheet_test.py (contact sheet of a test folder), band_test.py (subtitle-band strips), match_game.py (game shot -> movie frame, band comparison).

## The text sheet (2026-11-18 night, me: "Build the text sheet first")

**Result:** `dump/psnova-l10n/sheet/psnova_text_v1.xlsx` (sheet "messages": one row per message, sheet "tags": what the
{tags} mean), the same as UTF-8 `psnova_text_v1.tsv`, and `psnova_text_v1_tokens.json` (parsed codes per message, for the
re-encoder). 25,484 rows = every message of the Japanese game (base archive + Sega's 1.05 update). Columns: id, source,
text height px, JP lines, Japanese (original), English (fan rePatch, to revise), Arabic (empty), notes.

- English column: 17,131 rows translated by the fan patch, 2,924 rows the fan patch left in Japanese (note "fan patch left
  this in Japanese"), 5,429 rows without any English (messages only in the base archive, which the fan patch does not
  cover; some may be unused).
- Notes column: 374 rows "check kanji reading: X" (a kanji the reviewers were not fully sure of).
- Line breaks are real new lines inside the cells; furigana show as `{ruby:ほし}惑星{/ruby}`; control codes as `{8081:03}`.
- How it was decoded, the format and the checks: **docs/psnova/text-format.md** (new). Tools: `dev/psnova/rmdtext/`.
- Key finds: the message pictures are DXT3 in Morton order (not plain 8-bit), the text codes are one fixed character
  table, and Sega's `novamessagedictionary.mdic` holds the first line of most messages in Unicode (keyed by the next id),
  which served as the answer key. Kanji pictures: 1,743 from that key, 898 read by two independent model readers + a judge.
- Checks: no unknown code or unread picture left; 85 % of first lines equal a dictionary entry exactly; a spot check of 100 dictionary-vote kanji labels (two independent checkers) confirmed all 100.
- CSV/Lua: not added. The game shows text from the .rmd messages; the CSV dialogue/help lines are sources (85-100 % found as
  messages); the rest are developer labels. Exception to check later: the character-creation name tables
  (`charactermake_resource_database_*.csv`, which have ja_name and en_name columns).
- Movie lines: not in the sheet yet (they are only pixels in the 8 story movies; they need reading from the frames).

## The re-encoder: translated text back into the game (2026-11-18 night to 2026-11-19, me: "Build the re-encoder")

**Result: English and Arabic text from the sheet now reach the game.** Details, rules and proofs: docs/psnova/text-format.md
("Writing message files"). Tools: dev/psnova/rmdtext/rmdwrite.py, encode_text.py, arabic.py, build_l10n.py, roundtrip.py,
dev/psnova/cpk_build.py.

- Build: `python dev/psnova/rmdtext/build_l10n.py <sheet.tsv> en <out> [--arabic ar.json]` encodes a column into .rmd files
  and rebuilds Sega's 1.05 update archive with them (out/overlay/NOVA_FileList_Vita_patch.cpk). Test builds:
  dump/psnova-l10n/build/test1 (shared texture IDs, broken), test2 (good): the whole game in the fan English (17,131
  messages, rows the fan patch left in Japanese stay Japanese) plus 11 route messages in Arabic (ar_test1.json, placeholder
  Arabic).
- In-game tests ran on a separate copy (`app0_l10ntest` = app0_overlay + overlay_l10ntest), through a new generic option
  `TEST_APP0=<folder>` in pipeline/vitarecomp.py fresh_fs (uncommitted; recomp session told). The shared fs/app0 stays the
  Japanese game with the v2 movies.
- Test 1 found the texture ID (chunk bytes 0x91-0x93; the game caches textures by it): copied IDs made messages show each
  other's pictures. Test 2 with unique IDs: Arabic correct in menus, help lines, the name dialog, the speaker label and
  dialogue; English correct throughout the route.
- Code review (30 passes) confirmed 24 problems in the first version; all fixed before test 2.
- Arabic method: our own shaping (presentation forms) and bidi (arabic.py), drawn with Segoe UI Bold 16 px as each file's
  own glyph pictures (word pictures, or letter-form pieces when a message has too many words for a 256x128 atlas).
- Open: Arabic text for the sheet (first pass: menus/short labels; me: dialogue), a language choice (one overlay per
  language + a launcher/ini setting), very long Arabic help texts (more than ~85 pieces do not fit one atlas), the 8 movie
  lines, right alignment (lines start at the box's left edge; centred dialogs centre them).

## Arabic for menus and short labels (2026-11-19, me: "Arabic for menus")

**Result: sheet v2 (`dump/psnova-l10n/sheet/psnova_text_v2.xlsx` / `.tsv`) has Arabic in 8,581 rows** (8,201 different
texts): every short, one-line, non-dialogue message. The notes column marks them as Arabic menu pass 1.
Dialogue, long help texts, spoken one-liners and credits are left for me (rules in docs/psnova/arabic-style.md).

Steps and tools (all in `dev/psnova/rmdtext/`, work files in `dump/psnova-l10n/ar/`):
1. `sheet_groups.py` lists the sheet by id range (groups.json); `pick_short.py` picks the rows: id under 12 digits, one
   Japanese line, at most 24 characters, not a developer dummy (ダミー, 削除予定, 解説文, //..., 【number】...), and not in
   the spoken-line groups (260000, 530000, 620000, 730000) or the staff credits (750000) -> short_rows.json.
2. Style guide + core terms: `docs/psnova/arabic-style.md` (MSA, menus as nouns, no diacritics, Western digits, HP/PP/GP/EXP/Lv.
   and Roman numerals in Latin, names by sound from the katakana, tags kept). Names list: Arabic was written for
   the 1,141 English tokens used across several id groups (glossary_terms.json); I unified the "-hda" enemy names
   (كراهدا, وولغادا...; the first draft had used ذ) and made "Gun" a plain word. `make_glossary.py` -> glossary.json (1,163).
3. `make_batches.py` -> 36 batches of 230 texts, each with the glossary entries its lines use.
4. Workflow psnova-arabic-menus: per batch a translator (from the Japanese; fan English only as a helper), then a
   reviewer that checked every line against the Japanese and fixed it in place (logs in reviews/b_NN.json; 6 to
   73 changes per batch, mostly meanings copied from wrong fan English, name sounds, adjective agreement).
5. `check_arabic.py --encode`: tags, Japanese left over, letters the font/shaping cannot show, on-screen width (Segoe UI
   Bold 16 vs 21 px per Japanese character), glossary use, and that every line encodes. Result: no tag, Japanese or encode
   problem; 58 lines use · ◆ α β ∞ (drawn as pictures, fine).
6. Workflow psnova-arabic-fixes: 67 Japanese strings that had two Arabic versions were unified, 42 labels more than 1.3x
   wider than the original were shortened; a skeptical checker rejected 10 of the 112 changes and gave better lines
   (applied). I kept «موافق» for OK (the fixer wanted «تم» only for the width rule). Old versions in results_before_fix1/.
7. `merge_arabic.py` writes the Arabic column -> sheet v2; `ar/ar_menus.json` = the same lines for build_l10n.py --arabic.

Build: `build_l10n.py psnova_text_v2.tsv en dump/psnova-l10n/build/menus3 --arabic dump/psnova-l10n/ar/ar_menus.json`
(fan English for the rest of the game, Arabic for the menu rows): 17,505 messages, 0 failed, archive 378 MB, all entries
read back equal. Installed only in the test copy (overlay_l10ntest -> app0_l10ntest), game_l10n.exe re-copied from the
01:51 game_host.exe.

Known limits: 208 labels are still wider than the Japanese by the rough width rule (most by a few pixels; the real limit
is each menu's box, only the game shows it); kanji readings marked "check kanji reading" in the notes may have fed a
wrong meaning into a few lines; item names whose fan English is empty (unused development items, e.g. カラバリ cores)
were translated from the Japanese only.

### In-game tests 3 and 4 (2026-11-19 ~04:00-04:40, machine handed over by the recomp session each time)

- game_l10n.exe = copy of the 03:55 game_host.exe (renderer view-crash fix + RECOMP_PIPE_PREDICT=0). Same route as test 2
  (`TEST_APP0=$W/app0_l10ntest`, inputs/to-arena.txt, windowed, gpu). No crash in either run.
- **Test 3** (build menus3, shots `dump/psnova-l10n/ingame_text3/`, zooms z_menus.png, z_class.png, z_edit.png): Arabic shows
  in the character-creation menu, race/sex list, class list, help lines, the class box ("الأسلحة القابلة للتجهيز:" with the
  weapon names), the height slider label and the Yes/No buttons. Fan English in the long texts. Problems seen:
  1. «رامٍ» showed as «رام» (the tanween is not drawn) -> Ranger is now «رامي» everywhere (61 lines).
  2. Class was «الفئة» in the menu and «الصنف» in a help line -> «الفئة» for every クラス line (grammar fixed by hand:
     فئتك, التي ... إليها); クラスカウンター (a facility desk) was «عداد الفئة» (a number counter) -> «مكتب الفئات».
  3. Wide gaps between Arabic words: each word was its own picture with the game's wide space between.
- Fix for 3: new Arabic mode **'phrase'** in encode_text.py: words joined by single spaces become one picture drawn with
  the font's own space (split at spaces before 250 px); fallback phrase -> word -> form when an atlas is full. All 8,201
  lines fit in phrase mode. ar_menus.json now asks for 'phrase'. 'word' and 'form' are unchanged.
- **Test 4** (build menus4, 392 MB archive, 17,505 messages, 0 failed; shots `dump/psnova-l10n/ingame_text4/`, zoom
  z_menus_phrase.png): words now sit at normal Arabic spacing; «رامي» and «اختيار الفئة» correct.
- Still open (seen in both): text starts at the left edge of each box (Arabic should be right-aligned; needs the box
  width from the game's layout, not the message file); the game's 2-column race rows read «ذكر ... بشري» right to left.

## The language switch (2026-11-19, me: "Language switch then Right alignment")

**Design: per-language file overlays chosen at start, picked in the in-game menu.**
- `dump/decrypted/PCSG00351/lang/<code>/` holds files laid out as app0 that replace the game's own for that language, plus
  `language.txt` (the name the menu shows). Now: `en` (English text archive + cleaned movies), `ar` (Arabic menus over
  English + cleaned movies). Original (no language) = the Japanese game as released. README.md in that folder.
- `vitarecomp import` links each language folder into `recomp/fs/lang/<code>` (pipeline/vitarecomp.py cmd_import; links of
  removed languages are dropped). Tests: `fresh_fs` links `fs/lang` (or `TEST_LANG=<folder>`); pick a language with
  `EXTRA_ENV="RECOMP_LANGUAGE=<code>"`.
- Runtime (generic, any Nativ game; nothing changes without fs/lang):
  - runtime/core/io.c `host_lang()` reads the per-game setting `language` (env RECOMP_LANGUAGE over it) once, at the first
    file open (thread-safe); `host_path_lang()` swaps an app0 path for `<RECOMP_FS>/lang/<code>/<same path>` when that file
    exists (sceIo and FIOS paths, relative paths too). `guest_path_readonly()` protects fs/lang like app0.
  - runtime/core/settings.c: `language` is a per-game key (each game's own settings.ini).
  - runtime/ui/overlay.cpp page_game: a **Language** row (Original / English / Arabic, from the folders' language.txt), shown
    only when fs/lang has folders; "Applies the next time the game starts" (the game keeps its archives open).
- Built so far only into `game_l10n.exe` (RECOMP_BIN=l10n, 05:08); game_host.exe gets it at the recomp session's next build.
  The shared recomp/fs/ is not changed yet: re-import (which also links fs/lang) waits until the player exe has the code
  and I am not playing.
- Planned with it: the cleaned movie archive moves from overlay0 (all languages) into lang/en and lang/ar only (already
  hard-linked there), so Original plays Sega's movies with their Japanese subtitles; overlay0 then holds nothing.
- Limits: a folder listing of app0 still shows app0's own entries (overlays only replace existing files; fine for CPK
  games); the language is fixed for the session.
- Review (workflow psnova-langswitch-review, 3 lenses + verifiers): 9 confirmed minor issues, all fixed: the read-only
  check now also covers the active language folder resolved through its link (POSIX symlinks), its prefixes are worked
  out once (pthread_once); host_lang publishes with acquire/release atomics; "/app0/" is matched ignoring case; the menu
  lists up to 16 languages sorted by code; import links languages in both import branches; a wrong TEST_LANG stops the test.

## Right alignment (2026-11-19)

Research (read-only; full write-up docs/psnova/right-alignment-research.md): every UI text box has an alignment at
box+0x94 (0 left, 1 centre, 2 right) used by the line-placement routine fn_81905ae0 (read at 0x81905b10); it comes from
the UI project files (*.crbpj `Align`), most text boxes have none (= left). The .rmd has no alignment field.
Done (the recomp session agreed and paused its builds for the recompile):
- Encoder: every Arabic message starts with the no-op control code 0x8095 (bytes 95 80) unless its id is in
  dev/psnova/rmdtext/ltr_ids.txt (now 10801-10811, the weapon type names beside their icons in the class box).
  `export_arabic.py <sheet> <ar.json>` writes the build input with that flag.
- packs/PCSG00351/hooks.c psn_rtl_mark (entry hook on the message layouts 0x817e850e, 0x817e882e: remembers per text box
  whether its message starts with 95 80) and psn_rtl_align (instruction hook after 0x81905b10: a marked box's "left"
  becomes "right"); pack.toml HOOKS/IHOOKS. RECOMP_PSN_RTL_TRACE=1 logs the first 40 marked layouts. Recompiled 06:00.
- **Test 5** (2026-11-19 ~06:10, game_l10n.exe 06:02, `TEST_APP0=$W/app0_patched TEST_LANG=$W/lang`,
  `EXTRA_ENV="RECOMP_GFX=gpu RECOMP_LANGUAGE=ar RECOMP_PSN_RTL_TRACE=1"`, shots dump/psnova-l10n/ingame_text5/, zooms
  z_rtl.png, z_full.png, z_more.png): the log shows "language ar: files in lang/ar replace the game's own" and the hook
  marking boxes; the character-creation menu, class list, help lines, the class box header, the height label all sit at
  the right; the Yes/No buttons and the centred dialogs are unchanged (centre boxes are not touched). The weapon names in
  the class box moved away from their icons -> listed in ltr_ids.txt (archive rebuilt 06:16; not re-run yet).

## Reader/writer fixes from the research (2026-11-19)

- The game reads text byte by byte: a byte < 0x80 is a one-byte code; otherwise (b & 0x7f) | (next << 7); bit 0x4000 =
  control. rmdlib.tokens() now does exactly that (old copy: rmdlib_v1_before_8082fix.py).
- **0x8082 is "colour back to white", not end of text** (0x8081 xx = colour: 03 red, 06 cyan, 07 yellow). The old reader
  stopped there: 178 Japanese and 65 English messages had lost their text after it (e.g. msg_21756 「よろしいですか？」).
  Sheet **v3** (dump/psnova-l10n/sheet/psnova_text_v3.*) has it back; the tag is now `{/color}` (the encoder still takes
  `{end}`). No Arabic row was affected. The round trip of all 26,535 Japanese files is byte-identical including those bytes.
- Own glyph i is game code 401 + i written as (0x80 | low 7 bits, rest): the old u16 0x391 + i was wrong from i = 111
  (a 0x00 byte). The writer now encodes it correctly. Two kana codes the game cannot read as two bytes (ぢ 0x105, ぴ 0x10f)
  are no longer chosen by the encoder. 4 fan-English files contain such a code (the game shows 2 wrong glyphs there).
- The game lays out at most 128 glyphs per message; the encoder records the count (Encoder.last_drawn).

## Movies v3: no flash at line fades (2026-11-19, me: "the Japanese subtitles are showing for a split second before fading out")

New dev/psnova/remove_jp_subs_v3.py (one mask per line, applied to the whole line plus >= 8 fade frames each side)
and check_sub_residue.py; details and per-movie numbers docs/psnova/movie-cleaning-v3.md. Residue frames over the 8 movies:
v2 566 at line edges + 125 core + 191 other, v3 2 + 0 + 19 (the 21 are gold glow in MP09_040_040, no text). Smears not
fixed yet. Archive: `python -I dev/psnova/cpk_replace.py $W/app0_patched/NOVA_FileList_Vita_movie.cpk <out> --replace
<name>=dump/psnova-l10n/movies_clean_jp_v3/<name> ...` (452,248,432 bytes, 21 entries read back equal), now in lang/en and
lang/ar (hard links). Original (no language) plays Sega's own movies.

## Deployed to the play copy, English by default (2026-11-19 06:32, me: "Yes, start in English" / "but i should be able to set a default language easily")

- **Default language file:** `dump/decrypted/PCSG00351/lang/default.txt`, first word `en` (or `ar`, or `original` for the
  Japanese game). `vitarecomp import` copies it to `recomp/fs/lang/default.txt` (editing that copy works directly too).
  The runtime uses it whenever the player has not chosen in the menu (settings.ini has no `language` key); the menu's
  Language row shows the default in use, and choosing Original writes `language = original`. RECOMP_LANGUAGE overrides all.
- overlay0 removed (its v2 movie archive is still in dump/psnova-l10n/movie_cpk_jp/); `vitarecomp import` -> fs/app0 =
  app0_patched (Sony's 1.05 files), fs/lang/{en,ar} + default.txt. Saves and settings backed up first to
  dump/psnova-l10n/save_backups/*-20261119-0631. settings.ini left as it was (menu_hint_shown, frame_rate = 60).
- game_host.exe rebuilt 06:34 (runtime only; game C recompiled 06:00 with the psn_rtl hooks; includes the recomp session's
  renderer fixes, which it approved for me).
- Tests stay Japanese: fresh_fs links languages only with `TEST_LANG=<folder>` or `TEST_LANG=game` (the player's fs/lang).
- Checked 2026-11-19 ~07:05 (local tools, `RECOMP_BIN=l10n TEST_LANG=game`, no language set): the log says "language en:
  files in lang/en replace the game's own"; the character-creation menu is English and left-aligned (no Arabic mark);
  shot dump/psnova-l10n/ingame_default_en/z_menu.png.

## Separated from the Uncharted folder (2026-11-19 ~06:40-07:00, me: "only work in your folder (only work in Drive F) and separate your work from Uncharted cleanly")

Own repository, own Python (tools/python + .venv), own toolchain copy, own ffmpeg, scratch on F; Uncharted keeps the
psnova branch as an archive and lost only PS Nova's worktree registration. Full record, proofs and undo:
docs/psnova/separation-from-uncharted.md. From now on run Python as `.venv/Scripts/python.exe -s` from this folder.

## My report 2026-11-19 ~07:45: "The warning is still in Japanese, some tutorials are still not translated, and movies are not translated with subtitles!"

**1. Warning screen (Attention.mp4, every boot).** The English/Arabic redraws (movies_l10n/Attention_{en,ar}.mp4, made
2026-11-18 night) had never been put into an archive. Now each language has its own movie archive:
`movie_cpk_<lang>` = Sony's archive with Attention_<lang> + the 8 story movies (subtitled, below); in lang/en and lang/ar.

**2. Tutorials.** Cause: the fan English patch never translated the tutorial pages: 170 of the 181 pages of group
780000 (『ガード』『ジャストアタック』...) had no English, so every language showed Japanese there. Done: all 181 pages
translated from the Japanese into English and Arabic (workflow psnova-tutorials: a translator per batch of 30 with a
script self-check, then a reviewer; 7 batches, 81 review fixes). Tools: `dev/psnova/rmdtext/measure.py` (on-screen
width as the game draws it: the English font is fixed 10 px per letter; Arabic as our phrase pictures), `check_tut.py`
(icons {8099:xx} and value slots kept, colour spans closed, no Japanese left, lines <= Japanese + 1, English <= 470 px,
Arabic <= 440 px, encodes). Batches/results: dump/psnova-l10n/tut/. Merged with `merge_translations.py` -> **sheet v4**
(English column replaced for these 181 rows, Arabic set; noted as the EN+AR tutorial pass).
Still untranslated in English (no fan English, no translation pass), by group: 620000 navigator/hint chatter 2,496;
dialogue 2,050; 750000 staff credits 534; 530000 partner lines 493; item/facility descriptions 120000 373, 250000 370,
140000 252, 340000 449 (part developer dummies); ~7,600 in all. (The Arabic of everything except menus/tutorials is still
the English or the Japanese.)
- Encoder fix found on the way: colour spans ({8081:xx} ... {/color}) inside right-to-left text were drawn mirrored (the
  wrong words coloured); the two codes now trade places when the span is reversed, and icons/colour codes at a line start
  are no longer pinned to the left (encode_text.py _arabic).
- build_l10n.py: English rows are skipped only while they are identical to the Japanese (the old rule used the notes).

**3. Movie subtitles.** The 8 story movies only had the Japanese line removed. Now:
- `dev/psnova/make_sub_sheets.py`: per line (timing from the v3 cleaning's line tables) a picture of the Japanese line and
  of the fan release's burned-in English at the same frame (dump/psnova-l10n/subs/sheets/, lines.json).
- Workflow psnova-movie-subs: per movie a translator read the sheets (jp, fan_en) and wrote en and ar; a reviewer checked
  every line against the pictures (53 fixes). Result dump/psnova-l10n/subs/<movie>.json: 163 lines, 138 with text (25 rows
  of the line table had no text = detections of glow, not lines).
- `dev/psnova/burn_subs.py`: draws each line where the Japanese line was, white Segoe UI Semibold/Bold 24 px with a dark
  outline on a soft rounded 58 % black strip as wide as the text or the old Japanese line (+30 px), so it also hides the
  inpainting smears there (my "two birds" idea); 6-frame fades over the line's own time; Arabic shaped by
  arabic.py. `dev/psnova/run_burn_subs.sh` burns all 8 movies per language and builds movie_cpk_<lang>.
- Fonts now come from tools/fonts/ (local copies of Segoe UI Bold/Semibold). Licensing note from the recomp session:
  Segoe UI is Microsoft's; for a published translation an openly licensed (OFL) Arabic font would be safer (needs a
  download -> my OK).
- Installed 2026-11-19 08:09 in lang/en and lang/ar: text archives from sheet v4 (en 17,301 / ar 17,675 messages, 0
  failed) and the subtitled movie archives (8 story movies x 2 languages burned with run_burn_subs.sh, all frame counts
  equal; Attention_<lang> included). NOT yet tested in the game (usage limit reached before the run): next = one Arabic
  run of inputs/to-arena.txt (warning at boot, MP00_000_000 subtitles at frames ~2050-5150, tutorial pages in the arena).
- In-game checks (2026-11-19 ~08:30-09:15): the recomp session's runs (test90, game_dev.exe, ar and en to frame 4200)
  showed the English/Arabic warning screen at frame 300 and the burned-in subtitles in MP00_000_000 (its line over the
  white flash at frame ~3450 was hard to read). burn_subs.py now darkens the strip over bright frames (up to ~90 %), all
  16 movies re-burned and installed 08:54. Test 6/7 (game_l10n.exe = the 08:46 game_host, Arabic; test 7 with the
  full arena route make_arena_inputs.py to 28,800, shots dump/psnova-l10n/ingame_text7/): Arabic quest banners and
  objectives in the training arena (z_quest.png). The tutorial PAGES (780000) were not caught on screen (the route's
  jump taps close help windows at once); they are verified by the script checks only.
- Fixed from test 7: Japanese corner brackets 『』「」 inside Arabic text did not mirror (a quest banner showed them facing
  the wrong way); export_arabic.py now writes « » for them (166 Arabic rows), Arabic archive rebuilt 09:21.
- Still open: the arena's speaker name box shows 「フィルディア」 in Japanese although the name messages (30004, 330318,
  440079) have Arabic: that label comes from another source (a picture or another table), not found yet.
- Leads for the Japanese speaker name (from the recomp session, 2026-11-19; its search: dev/psn-logs/fildia-name-search.txt):
  the name is Shift-JIS text in CSV tables, not an .rmd message. Most likely sources: `uireferenceparameter.csv` (patch
  archive: `StringFix_NameRut,,,,ルティナ`, `StringFix_NameFir,,,,フィルディア`, ... a block of UI name strings) and
  `NpcBaseParameter.csv` (key5005: `...,フィルディア,530005,FD_fieldea,...`; 530005 may be the name's message id). Next:
  find how these CSV strings reach the font (an SJIS -> glyph code path) before choosing a fix (replace the CSV text with
  an English name, or route it to a message / our glyph pictures for Arabic).

## Full translation pass (2026-11-19 ~09:40-10:20, me: "Yes, translate them")

- `dev/psnova/rmdtext/make_batches_full.py` picked every message with Japanese text and no usable English (empty, same as
  the Japanese, or still Japanese), minus developer dummies and punctuation: **7,196 messages** (6,814 also without
  Arabic) in 96 batches (id order inside a group; dialogue by scene), each item with the 2 rows before/after it as
  context and the character-name table. Groups: 620000 operator/navigator lines 2,495; story dialogue 2,028; 750000 staff
  credits 532; 530000 partner lines 443; descriptions 340000 414, 250000 335, 120000 261, 140000 252, 110000 105; others.
- Workflow psnova-full-translation: per batch a translator (from the Japanese, fan English only as a reference,
  check_tut.py self-check until 0 problems) and a reviewer (logs in dump/psnova-l10n/full/results/f_NNN_review.json).
  All 96 batches end with "problems 0". check_tut.py now skips the Arabic check where the Arabic column already had a
  translation (need_ar false).
- Merged -> **sheet v5** (dump/psnova-l10n/sheet/psnova_text_v5.*): English set for 7,197 rows, Arabic for 6,817 more;
  notes mark the EN(+AR) full pass. Left without English: 614 rows of punctuation/symbols and developer dummies (on
  purpose). Arabic now in 15,577 of 25,484 messages; the ~9,900 messages the fan patch had translated (most dialogue)
  still have English only (Arabic mode shows the English there).
- Archives from sheet v5 installed 10:37 (lang/en 24,429 messages, lang/ar 24,481; 0 failed). **Test 8** (Arabic, full
  arena route to 28,800, game_l10n.exe = the 08:46 game_host; shots dump/psnova-l10n/ingame_text8/sheet.png): Arabic
  warning screen (300), Arabic movie subtitles (2600), Arabic menus, Arabic speaker name plates (ريتيا, فيلديا),
  Arabic quest banners and objectives in the arena; the story dialogue the fan patch had translated shows in English
  (no Arabic for it yet); nothing broken seen.

## English font replaced with the supplied display font (2026-11-19 ~12:00, me: "use the fonts in the folder to replace the English fonts")

My font (a thin serif display font, no `~ < >`) now draws all English:
in-game text (new: the encoder draws each English character as a glyph picture, 18 px, baseline 16; before, the game's
own fixed-width letters were used), the movie subtitles (28 px) and the warning screen (heading "Notice"). All fonts are
now set in one file, dev/psnova/fonts.json; how-to and limits in docs/psnova/fonts.md. Rebuilt and installed 12:15:
lang/en and lang/ar text archives (English rows in both), lang/en movie archive. Old Segoe English warning kept as
movies_l10n/Attention_en_segoe.mp4.
**Test 9** (English, arena route to 24,000; shots dump/psnova-l10n/ingame_text9/): the display font in the warning
screen, the movie subtitles, every menu row, the race/class lists and help boxes, Yes/No dialogs, dialogue boxes and
name plates, and the arena quest banner; readable at the game's size; nothing broken seen.

## My screenshots 2026-11-19 ~12:30-13:10: Japanese still visible, tutorial pages cut off

- **Tutorial pages cut off mid-sentence** ("Combine normal attacks a", "While you hold"): the game lays out at most 128
  glyphs per message, and since English letters became one picture each, every letter and space counted (595
  English and 44 Arabic messages were over 128, up to 288; `dev/psnova/rmdtext/count_glyphs.py`). Fix: English is now
  drawn as one picture per word with its trailing spaces (encode_text.py `_latin_words`), and the writer can use larger
  atlases (256x256, 512x256, 512x512): `rmdwrite.template_gxm` derives the size fields (u16 W/H at 0xa8/0xaa, W/4 and
  H/4 at 0xb2/0xb4, pitch W*4 at 0xb8, W*H at 0xbc/0x150/0x1a0, W*H+0xf0 at 0xf4), checked against the game's own
  1024x512 / 1024x1024 UI textures, which differ from the 256x128 template in nothing else. Now 0 messages over 128
  (a 294-character tutorial page = 40 pictures on a 256x256 atlas). The larger atlases are NOT yet seen in the game.
- **Brackets as "l...l"** in English titles: the display font's [ ] are thin bars; fonts.json game_english "fallback": "[]~<>"
  keeps the game's own letters for these.
- **Names in Japanese** (ルティナ / フィルディア over characters, in the party HUD and in the portrait message window): they
  are Shift-JIS table strings, not messages: `uireferenceparameter.csv` StringFix_Name* (15 names) and
  `NpcBaseParameter.csv` column 27 (22 character rows). `dev/psnova/rmdtext/make_name_tables.py` writes copies with the
  English names (ASCII, still Shift-JIS) into dump/psnova-l10n/name_tables/; `build_l10n.py --extra-dir` puts them into the
  archive. Both languages get the English names there (that table path has no Arabic letters; they draw in the game's
  own font, not the display font). Not yet seen in the game.
- **Japanese drawn inside pictures** (UI textures, research docs/psnova/ui-textures-research.md and ui-strings-research.md):
  menu banners (キャラクタークリエイト, 設定/ヘルプ: tex_nova_ui_Title.aif), the button guide (カメラ初期化, ズーム:
  tex_nova_ui_common.aif), chapter title cards (「惑星の洗礼」: tex_Chapter.aif), the title screen and a few more (9 core
  textures), plus 83 tutorial screenshots (ソード, パルチザン, 素手, メインパレット, the settings screen...). Not started:
  I was asked which font to use for pictures (I declined adding a UI picture font to fonts.json for now).
- Installed 13:08: lang/ar text archive (word pictures + larger atlases + name tables); lang/en installed after I closed
  the game (rebuilt with build_l10n.py --extra-dir dump/psnova-l10n/name_tables). Earlier note: lang/en could not be replaced
  while my game_host.exe was running; rebuilding it (dump/psnova-l10n/build/en8) to install after the game closes.

## Japanese inside pictures redrawn (2026-11-19 ~13:30-15:30, me: "the supplied font")

- Spec format and tools: `dev/psnova/uitex/SPEC.md`, `apply_spec.py` (decode .aif, clear the Japanese -- transparent /
  inpaint / fill / per-row fills --, draw the display font (English) or Segoe UI Bold with our Arabic shaping, re-encode DXT3 with
  colour, only changed blocks re-encoded, header and texture ID kept, round-trip checked), `apply_all.sh`,
  `make_sheets.py`; fonts.json `ui_english` (the display font) / `ui_arabic`.
- Workflow psnova-ui-textures (21 tasks): tool author; spec writers for the 9 core textures (tex_nova_ui_Title menu
  banners ~60, tex_nova_ui_common ~25 labels incl. the button guide, tex_Chapter chapter cards, load024 control diagram,
  nova_ui_title, ev_dlc_104 DLC cast card) and 83 tutorial pictures; an apply pass; 6 visual reviewers who fixed specs
  (smears from inpainting -> per-row fills, too-small English -> 12 px minimum, Arabic alignment, a tool bug that erased
  chapter subtitles when "en" was null -> worked around in the spec).
- Chapter cards: English = the Japanese word pieces made transparent (the existing English subtitle shows alone);
  Arabic = Japanese pieces transparent and the English subtitle sprites redrawn in Arabic.
- Specs: dump/psnova-l10n/uitex/specs/ (88); outputs dump/psnova-l10n/uitex/out/{en,ar}/*.aif with previews and contact
  sheets sheet_en.png / sheet_ar.png. Archives are built with `build_l10n.py ... --extra-dir dump/psnova-l10n/name_tables
  --extra-dir dump/psnova-l10n/uitex/out/<lang>`.
- Installed 15:09 (lang/en, lang/ar: text + name tables + 88 redrawn textures). **Test 10** (English, full arena route;
  shots dump/psnova-l10n/ingame_text10/, zoom z_ui.png): the character-creation banner reads "Character Creation" in
  the display font (over the original "CHARACTER CREATE"), the button guide "Camera Reset" / "Zoom", name plates in English
  (Rietheia, Fildia), quest banner and dialogue fine, no broken message boxes with the larger atlases on the route.
  Not reached by the route: tutorial pages with pictures, chapter title cards (checked only in the review previews).

## Text faults from my evening recordings (2026-11-19 ~18:00; found by the recomp session: docs/psnova/text-render-faults.md)

- **Shadow beside the letters / cutscene subtitles at mixed sizes:** the game draws each glyph's 4 shadow copies offset by
  5 % of the glyph's own width/height, and the cutscene subtitle drawer fits every glyph into a 21-px cell. Our word /
  phrase pictures (30-75 px) got shadows 2-4 px to the side and were squeezed in subtitles ("I" stretched to a block).
  Fix (encode_text.py `_slices`, `latin_run`): every English and Arabic run is drawn whole, then cut into slices of
  exactly **21 px** (the last padded), each a glyph with advance = width, so they join seamlessly and behave like the
  game's own glyphs. Wider slices (32/48/96/255) only when a message would pass 128 glyphs or not fit a 512x512 atlas;
  the longest tutorial pages come to 79-104 slices at 21 px. Copy of the encoder before: scratch/encode_text_before_slices.py.
- **® box** in "PlayStation®Vita": ® © ™ added to fonts.json game_english "fallback" (the game's own ® picture is used).
- Chapter card glow: my screenshot predates the redrawn tex_Chapter.aif (15:09), whose Japanese pieces are
  transparent; to confirm in a test.
- OpeningDemo subtitles (I asked the recomp session): the lines are in the game's fictional alphabet, no voice;
  asked me before decoding.
- Archives with the 21-px slices installed 20:08 (0 messages over 128). **Test 11** (English, game_l10n.exe = the 20:29
  game_host; shots dump/psnova-l10n/ingame_text11/, zoom z_slices.png): dialogue box, menu rows and the arena objective
  draw seamlessly from the slices with a tight shadow (no dark copy beside the words any more). Cutscene subtitles and
  the chapter card are not on the scripted route.

## Arabic recordings review (2026-11-19 ~21:30; recomp session's findings from my 6 recordings, Arabic mode)

- **Detached full stops / a lone bracket** ("تحقق الهدف . مسموح ..." , "قطعة غران ) (جليد"): the last 21-px slice of a
  picture was padded with empty columns, so a game-font full stop or bracket after it stood apart. Fixed: slices now
  have equal widths <= 21 px (no padding), and in Arabic lines everything between control codes -- Arabic, punctuation,
  brackets, digits, Latin -- is drawn as ONE picture in the Arabic font in display order, then sliced (encode_text.py;
  copy before: scratch/encode_text_before_segments.py). Checked with the new `dev/psnova/rmdtext/preview_msg.py`
  (draws a message as the game lays it out): «جمع «قطعة غران (جليد)», «تحقق الهدف. مسموح بالعودة إلى القاعدة.».
- **Name + fragment messages** (level-up "Nova ! ارتفع مستواه", relationship changes, item obtained): the game draws the
  name (or item) and then the fragment, left to right. 17 Arabic fragments reworded so they read right to left with the
  name on their left: «ارتفع مستوى» + name, «بلغت العلاقة [صديق مقرب] مع» + name, «تم الحصول على» + item, etc.
  (dump/psnova-l10n/fixes/ar_fragments.json -> **sheet v6**).
- Open: the mission-prep team panel's Japanese names (ルティナ, ヒューマー): no table or message holds ヒューマー; likely
  names stored in the save when crew joined (my save predates the English name tables) -- needs a screenshot /
  a new save to confirm. The enemy name beside the TARGET marker is still squeezed (a drawer that scales glyphs to a
  small fixed cell; to look at with a frame). Dialogue bodies and cutscene subtitles are English in Arabic mode (their
  Arabic is not written yet: ~9,900 messages). EXP / CHAIN / DAMAGE popups, QUEST CLEAR / EMERGENCY CODE / NOW LOADING
  are English artwork in the original game too.
- Installed 23:58: archives from sheet v6 with equal-width slices and whole-stretch Arabic pictures (0 failed, 0 over 128).
- **Test 12** (2026-11-20, Arabic, arena route; dump/psnova-l10n/ingame_text12/z_ar.png): «إنشاء الشخصية» banner,
  right-aligned menus, «بدأت المهمة.» with the full stop attached, objective «انتقل إلى مكان العلامة!». Found:
  (a) the enemy level "Lv.1" showed as ". Lv1": a line without any Arabic letter was still reordered right to left ->
  encode_text.py `_arabic` now keeps such lines as written; (b) the quest name showed in Japanese corner brackets: the
  game draws messages 10019 「 and 10020 」 on either side of a name (skipped as punctuation by the pickers) -> English
  [ ], Arabic « » (display order: the left one is «). **Sheet v7**; archives rebuilt from it.
- Installed 00:52 (2026-11-20): archives from sheet v7.

## English layout, 2026-11-21

The installed English archives center speaker names and the three-line boot notice, reflow dialogue and radio messages to their respective box widths, and preserve the font proportions in movie and in-engine subtitles. Build commands, measurements and the Rietheia test capture are in the [English layout handoff](english-layout-2026-11-21.md).

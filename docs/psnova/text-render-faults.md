# English text faults seen in my recordings (2026-11-19 evening)

Found by the recomp session while reviewing my nine recordings (`dump/user-videos-2026-11-19/`, review in
`review.txt` there; tools `dev/psnova/video_review.sh`, workflow psnova-video-review, 68 review tasks, each fault re-checked
on full frames). This is a report for the localization session: its tools were read, not changed.

## 1. Cutscene subtitles: words at different sizes, "I" as a block

Recording 8 at 0:32 (`frames/r8_32_sub.png`): "As it stands, / the little troops we have, will be / annihilated." with
"As it" large and wide, "stands," and "troops" small, "annihilated." tiny. Recording 7 at 0:12: "It's the least [I] can
do": the "I" is a wide grey block. Recording 8 at 1:04, recording 9 at 0:01 and 0:08: the same.

The message file is correct: `msg_101010070030004.rmd` in lang/en has 11 word pictures (21-75 px wide, 21 high) on a
128x128 atlas, advance = width. The original (Japanese) file has 22 glyphs, **all 21x21 in 25-px slots**.

What the screen shows fits one rule: **the cutscene subtitle drawer fits every glyph into the game's fixed 21-px cell.**
Narrow pictures are stretched (an "I" a few pixels wide becomes a block, "it" turns wide), and wide ones are squeezed down
("annihilated.", 75 px, drawn at about a quarter of its size). Dialogue boxes and tutorial pages use the real widths.

Fix direction (localization tools): pictures no wider than 21 px in the messages this drawer shows: one picture per letter
(or per pair of narrow letters) instead of per word. Subtitles are short, so the 128-glyph limit isn't reached there.
The target marker's enemy name (recording 2 at 0:02, illegible tiny text left of TARGET) looks like the same squeeze.

## 2. Dialogue and HUD text: the shadow is a dark copy beside the letters

Screenshots and recordings 1, 2, 6 (dialogue boxes, objective "Move to the arrows!", "Bare Hands", enemy name "Krahda"):
a dark copy of the letters about 2 game pixels (4 screen pixels at 2x) to the left and half a pixel down, with streaks under
some words. Tutorial pages have an even outline instead. Measured per word in the screenshots
(`dev/psnova` scratch script): -4 px x, +1 px y at 2x, the same along a line.

Packing difference: the game's own glyphs sit in 25-px slots (21-px picture, 4 px empty to the right and below); word
pictures are packed with only 2 px between them (rmdwrite.pack: width + 2). A shadow drawn from a slightly wider region
than the picture picks up the neighbour's edge (the streaks). Cause of the offset: see section 4 (capture).

## 3. Other text faults

- A missing-glyph box between "PlayStation" and "Vita" (recording 9 at 0:56): the ® / ™ sign is not in the supplied font, and is
  not in the fallback list ("[]~<>").
- Chapter card "The Battle for Survival Begins" (my screenshot): the blurred Japanese title glow still shows above the
  English line (the glow layer is a separate sprite or texture from the word pieces made transparent).
- Area banner ("Steel Wastelands 1 / Area 1") drawn over a dialogue box and a name tag (recording 6 at 2:54-2:56): may
  be the original game's layering; not checked against the Japanese.

## 4. Capture of a dialogue box: how the game draws the shadow

Capture: English route (`dev/psnova/inputs/to-arena.txt`, `TEST_LANG=game RECOMP_LANGUAGE=en`, gpu, fixed clock) at frame
17600, Rietheia's "Let's check to ensure that your memory / is in working order." (`captures/frame_17600.vfc`; draws
listed with `RECOMP_REPLAY_DUMP=1`, `dev/psnova/text_draws.py --list`, vertices with `RECOMP_REPLAY_VERTS=391`; output in
`dump/user-videos-2026-11-19/capture/`). The body text is one draw (391, the message's 128x128 atlas, 330 indices); the
speaker name another (390, 128x32).

**Every glyph is drawn as 5 quads: 4 black copies, then the white glyph.** The black copies are the glyph's own quad
(same size, same texture coordinates) moved diagonally by **5 % of the glyph's width and height**:

| glyph | picture | white quad x | black copies x | black copies y |
|---|---|---|---|---|
| "Let's" | 33 x 21 | 239-272 | +-1.65 | +-1.05 |
| "check" | 44 x 21 | 272-316 | +-2.20 | +-1.05 |
| "to" | 18 x 21 | 316-334 | +-0.90 | +-1.05 |

For the game's own 21x21 glyphs the copies sit +-1.05 px each way: an even one-pixel outline. A word picture is wider, so
its copies move further sideways: a 44-px word gets two dark copies 2.2 px left and right (4.4 px on a 2x window), which
is the "misaligned shadow". On the dark tutorial pages the copies are there too, but hard to see.

## 5. One fix for both: glyph pictures about as wide as the game's own (21 px)

Both faults come from glyph pictures much wider than the game's 21-px glyphs: the shadow offset scales with the width
(section 4), and the cutscene subtitle drawer squeezes everything into a 21-px cell (section 1). Pictures cut at letter
boundaries into pieces of at most ~21 px (drawn exactly as now, advance = width, so the pieces join seamlessly) give
shadows within +-1.05 px (like the original) and fit the subtitle cell.

Cost: more glyphs per message. About 2-3 letters per piece; the 128-glyph limit can still be exceeded by the longest
tutorial pages (a 294-character page is ~120 pieces), which could keep wider pieces (their shadow falls on a dark
background). Cutscene subtitle messages are group 10101... (e.g. 101010070030004), dialogue boxes 10001...

The recomp side could instead patch the game's shadow offset to use the glyph height for both directions (a hook in
the glyph quad builder), which fixes the shadows of wide pictures but not the subtitle squeeze; the piece change covers
both, so it is the one recommended. Not done yet: the localization session owns the encoder.

## 6. The opening movie has no subtitles (me, 2026-11-19 evening)

Update, 2026-11-21. A Japanese radio announcement was found around 00:12.75–00:24.08 and my English subtitles were installed. See [Opening preview subtitles](opening-announcement-2026-11-21.md).

`OpeningDemo.mp4` (2:20, plays after the logos, before the title) is byte-identical in lang/en and app0: the localization
left it out on purpose (localization-notes.md: "in-universe decorative script ... no Japanese subtitle line ... ask
me"). Checked: no spoken narration (music only, spectrogram `dump/user-videos-2026-11-19/opening/spectrum.png`); the
on-screen lines (from 0:10, e.g. the "Deka Valiant" line at 0:15, lines at 0:35, 0:40, 0:50, 1:05) are written in the
game's own fictional alphabet. Subtitles would mean reading those lines (the series' alphabet is probably a
letter-for-letter cipher of the Latin alphabet; not checked) and burning an English/Arabic line under each.
The story movies (MP00_000_000 etc.) carry the burned-in subtitles since 08:54.

## 7. Not text (recomp session's list)

- Recording 9 at 2:24 (`frames/r9_144.jpg`): two straight dark vertical bands from the crates down to the character's
  shadow, drawn over her: the "shadow when walking" seen before (frame-rate.md, open).
- Recording 6 at 4:56 (`frames/r6_296.jpg`): a glittering diamond-shaped patch of tiled dots in a cutscene sky, moving with
  the camera: a sprite or particle drawn with the wrong texture or blend.
- Recording 6 at 1:36: a hard straight diagonal dark edge over rock in one camera cut (shadow cascade edge?).
- Black screens of 2-6 s at scene changes before "NOW LOADING" (recordings 3, 5): not compared with the real Vita yet.
- The sound: fixed (docs/psnova/audio.md).

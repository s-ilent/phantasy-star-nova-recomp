# Phantasy Star Nova (PCSG00351): state of the recomp

The one state file for this game. Correct it in place when a finding changes; give every claim its strength:
**proven** (repeated, or seen by me), **single run**, or **untested**.

The journey behind it (what was tried, the dead ends, the techniques and the traps): [journal-2026-11-18.md](journal-2026-11-18.md).
Read that before debugging anything here.

**Last reconciled 2026-11-27** against the dated notes in this folder (the Status table and Open questions below; the
other sections are the 2026-11-18/19 record and are kept as history). When a dated note and this file disagree, the
newer one wins: correct this file.

2026-11-27: added the pack's second 1.05 build, the cartridge/update VPK dumps, which are that program re-linked
0x1700000 higher, and the `MAIN_BASE` setting that plays it; see "The two 1.05 builds" below.

2026-11-22: checked the launcher with dry-run copies (working, missing and non-running `.venv`;
no game launch), and corrected the name limit and HD-text test coverage against the linked reports.

## The game

| | |
|---|---|
| Title | ファンタシースター ノヴァ (Phantasy Star Nova), tri-Ace / SEGA, PS Vita, 2014 |
| Title id / content id | PCSG00351 / JP0177-PCSG00351_00-NOVAAPPLICATION0 (Japan) |
| Player's copy | `F:\RECOMP GAMES\Phantasy Star Nova (v1.05)`: `app` (1.00, encrypted, NoNpDrm `work.bin`), `patch` (1.05), `rePatch` (English fan translation: two CPK archives) |
| Main program | NovaMRom, `eboot.bin` (28.4 MB as ELF); 1.05 SHA-256 `abb45e17...edcf3`, 1.00 `f4b3a669...2542` |
| Builds the pack plays | `1.05` (the original NoNpDrm/PKG copy) and `1.05-maidump` (the cartridge and update VPK dumps this machine has: the same program re-linked 0x1700000 higher). See [The two 1.05 builds](#the-two-105-builds-2026-11-27) |
| System libraries it imports | 33 libraries, 500 functions: GXM, libc, kernel, NGS (sound), AvPlayer (movies), Fiber, SaveData/IME/NetCheck dialogs, NP Trophy, Net (offline) |
| Data | CRI CPK archives: `NOVA_FileList_Vita.cpk` (2.8 GB), `_movie.cpk` (395 MB), the update's `_patch.cpk` (155 MB) |
| Code size | 40,427 functions in the current analysis (count of 2026-11-22; 39,840 on 2026-11-18); 7.7 M instructions translated to 1.1 GB of C in 100 parts |

## The two 1.05 builds (2026-11-27)

The pack plays one program from two dumps, which differ only in the address it is linked at:

- **`1.05`** — an original NoNpDrm or PKG copy: `eboot.bin.elf` `abb45e17...edcf3`, the main program at `0x81000000`,
  with the addresses `pack.toml` lists (FUNCTION_SEEDS, HOOKS, IHOOKS).
- **`1.05-maidump`** — the Japanese cartridge and 1.05 update **VPK** dumps. Their `eboot.bin` starts `SCE\0`, is exactly
  0x1000 bytes longer than the ELF inside it, and their `sce_module` also holds `libc_m` and `libfios2_m`: the eboot is the
  1.05 program **re-linked 0x1700000 higher** (`eboot.bin.elf` `74e66d0b...6f1c`, text `0x82700000`..`0x83B6BF90`). Its
  data (`NOVA_FileList_Vita.cpk`, `_movie.cpk`, `_patch.cpk`, `disc1`) is byte-identical to the originals above. Neither
  dump needs a licence: both eboots are unencrypted wrappers, so `add` decrypts them with no `work.bin`.

`packconf`'s **`MAIN_BASE`** is the whole of the support: the second table lists the `1.05` addresses unchanged and names
its own base, and `load()` shifts every address the pack gives for the game itself by the difference. The loaded modules'
addresses (MOD_HOOKS/MOD_IHOOKS) are never shifted, and `vitarecomp` links the main program at `MAIN_BASE` when it
analyses a module.

Verified on the VPK dumps 2026-11-27 (single run each): all 8 FUNCTION_SEEDS and all 7 HOOKS/IHOOKS decode to the bytes
`pack.toml` describes at +0x1700000 — the varargs prologue at `0x83553e70` (`mov ip, sp; push.w {r0-r3}`), the three
`bx ip` thunks, the `vtable +0x24` load of `psn_input_slot`, and the carried-over `0x839b0d6c`, which the analyser takes
as ARM and which reads `cmp r1, #0; beq` exactly as the pack records for `0x822b0d6c`. The text segment is `0x146BF90`
bytes = `0x8246bf90 - 0x81000000`, the range `dev/psnova/even_pointers.py` scans. `import` reports 33 libraries and 500
functions; `analyze` reports SceLibc 1562 / SceGxm 470 / SceGpuEs4User 65 / SceMp4 273 / SceAvPlayer 299, the same
figures as the 2026-11-22 record.

Seen on the GPU path (the player's own run, `session.log`, 2026-11-27): the main program is loaded where this build links
it (`loaded 0x82700000 0x146bf90` -- the text size above), the modules load at 0x88000000 and up, frames hold at 30.0 fps
(33.3/34.2 ms avg/1%low; `gpu 6 scenes 11 draws`, render 0.8 ms, present 0.3 ms), the start-up movies decode and present
(`avPlayer` threads, `texture ... 960x544 ... re-uploaded (decoded)`), movie sound closes with 0 errors, and the front end
reaches `open savedata0:system.bin`. A headless `test` run of the same build (1200 frames, exit 0, the movies decoded,
~28 fps, 12,867 draws) shoots frame 1200 black: the *software* renderer (`RECOMP_GFX=soft`, the gate's) skips the movie
and UI draws there with "no position attribute", so the gate's frame is not a picture of this build's window.

## How it is built here

Everything runs from this folder, its own git repository since 2026-11-19, with its own Python (`tools/python` +
`.venv`) and toolchain (`toolchain/`), nothing borrowed from the Uncharted checkout (record and undo:
[separation-from-uncharted.md](separation-from-uncharted.md)):

```bash
bash dev/psn_build_all.sh                    # import -> analyze -> recompile -> build, logs in dev/psn-logs/
STAGES="build" bash dev/psn_build_all.sh     # one stage
```

The pipeline driver by hand: `.venv/Scripts/python.exe -s pipeline/vitarecomp.py <stage> PCSG00351` (the build finds
`toolchain/` by itself; `ATIV_WIN_TOOLCHAIN` only to use another one).

Stages as run on 2026-11-18 (single run each):

| Stage | Result |
|---|---|
| `add app` (decrypt 1.00 with `work.bin`) | 32 s, 6 programs decrypted, 0 failed (one `sce_sys/about/right.suprx` hash note, not game code) |
| `add patch` (1.05) + import | update decrypted, `app0_patched` = 98 hard links, version recognised as 1.05 |
| `analyze` | 248 s; main 39,840 functions; libc 1,562, libgxm 470, libgpu 65, SceMp4 273, SceAvPlayer 299 |
| `recompile` | 278 s; 5,541 of 7.7 M instructions "unsupported" (coprocessor/`svc` forms: data decoded as ARM in literal pools, judged harmless until a run reaches one) |
| `build` | ~6 min after a recompile, ~30 s after a runtime-only change; `game_host.exe` 164 MB |

## Changes made to Project Nativ on this branch

- `pipeline/vitarecomp.py`: **`repatch <title> <folder>`** copies a rePatch folder to
  `dump/decrypted/<title>/repatch0`; `import` layers it over the game and update into `app0_repatched` (hard links).
  `RECOMP_NO_REPATCH=1` at import plays without it. Untested at the time of writing.
- `recompiler/recomp.py`: **a function is never switched to ARM when its ARM decode has no instruction at its entry.**
  The first build failed in 3 of 100 parts (`goto L_8102e9dc` and two more with no label): analyze.py gives some entries
  chunks of a Thumb switch's shared tail that start *below* the entry; the junk test reads a literal pool there as
  coprocessor code, the function was re-decoded as ARM, and the ARM decode skipped the entry. Only functions that failed
  to compile change, so builds that worked before are unaffected. The recompile prints the functions it kept Thumb
  (one: 0x8102e9dc). With it, "unsupported" instructions fell from 5,541 to 842: far fewer data words decoded as code.
- `recompiler/recomp.py`: **an entry that falls inside an instruction of its own linear decode is decoded from the entry
  itself.** The other two failures: 0x819b2852 is the second half of a `bne.w`, 0x811cc1f6 the second half of a `movt`,
  inside ordinary Thumb code, so these entries come from data words that look like code pointers and are never jumped
  to. Again only functions that failed to compile change; the recompile prints them.
- `runtime/platform/platform_win32.c` `plat_gpu_cache_private()` (called first in `main()` and before the GPU device):
  **NVIDIA's shader cache goes to `nvidia-cache\` beside the program**, 4 GiB, unless `__GL_SHADER_DISK_CACHE_PATH` is
  set. Every Nativ program is `game_host.exe`, the same name as the Uncharted build; NVIDIA keeps one 1 GiB cache per
  exe name and deletes other names' caches when full (memory note `nvidia-shader-cache-limit`).
- `dev/psnova/check_labels.py`: checks the generated C for gotos without labels (23 s), before a build; part of
  `dev/psn_build_all.sh` after every recompile.
- `recompiler/analyze.py` `arm_pointer_targets()`: **ARM functions reached only through even words** (ARM code
  pointers) are found. The first boot stopped at `call to 0x8209d688: neither recompiled code nor an import`: a vtable
  slot (`ldr r2, [r1, #8]; blx r2`) holding an even address, i.e. an ARM method, in a 36-byte gap no body covered. The
  whole vtable is ARM methods. `dev/psnova/even_pointers.py` found 84 such uncovered, cleanly decoding ARM accessors
  (one rebuild instead of ~84 crash-and-reseed rounds of ~15 min), and showed that no existing function was decoded in
  the wrong mode (the 500 "Thumb" targets of even pointers that also decode as ARM are all import stubs).
- `runtime/core/main.c` `RECOMP_IMPORTS=1`: the report now scans the main program up to the modules (0x88000000); it
  stopped at 0x82000000 and missed most of this 20 MB program's imports (186 listed instead of 649).
- The run's own miss log recorded 0x8209d688 as `thumb` (its rule: Thumb when the caller is Thumb); a `blx` to an even
  address enters ARM. Corrected by hand in `dump/decrypted/PCSG00351/analysis/seeds.txt` (old file kept beside it).
- `runtime/core/kernel.c` **`sceKernelCancelEventFlag`** (was a stub): wakes every waiter with WAIT_CANCEL, sets the
  pattern, writes the count. The game hung after frame 1 without it: the Aska engine starts each worker thread by
  "cancelling" its flag with pattern 2 (the worker waits for bit 2, runs its job, exits when the job returns).
- `runtime/audio/ngs.c`: **the NGS voice definitions this game uses** (ATRAC9 voice = the Scream ATRAC9 player,
  Template1 = the PCM player, mixer/EQ/delay/distortion/pitch-shift busses passed through, said once each).
  `runtime/gfx/display.c` **`sceAudioOutReleasePort`** (frees the slot, keeps the host device for a same-format reopen).
- `runtime/core/sysmem.c`: **memory blocks aligned by type as on the console** (CDRAM 256 KiB, phycont 1 MiB, others 4 KiB;
  the log line shows the type). The AvPlayer carves its H.264 decoder's memory out of the game's block at 1 MiB
  alignment; at 4 KiB alignment it no longer fitted and every movie played sound over a black screen.
- `runtime/media/video.c` `sceAvcdecQueryDecoderMemSize`: **whole MiB** (was 256 KiB rounding): the AvPlayer sizes the
  block as library + this rounded up to MiB, which only fits the aligned carve when this is a whole MiB; the second
  movie (0x240000) lost its video otherwise. With both: all three start-up movies decode (150, 240 and the opening's
  pictures), proven by screenshots of each.
- `runtime/gfx/display.c` `RECOMP_CTRL_BACKTRACE=1`: the native stack of the first controller read per caller (the
  guest call chain, symbolised with llvm-nm on the program).
- `runtime/gfx/display.c` **`SceCtrlData` written as 0x20 bytes, not 64** (the fix that made buttons work): see "The
  button problem" below. Every Nativ game had this overflow; the Uncharted copies still do.
- `packs/PCSG00351/hooks.c` + pack `HOOKS`/`IHOOKS`: input-thread trace hooks (`RECOMP_PSN_INPUT_TRACE=1`, off by
  default), kept for the next input question.
- `recompiler/analyze.py` `arm_function_at`: the ARM rule only needs the *first* instruction unconditional and rejects
  text by its bytes; a run-recorded "thumb" miss that is 4-aligned, stored as an even pointer and an ARM function is
  taken as ARM. Fixed the character-creation crash (`0x822b0d6c`, `cmp r1, #0; beq ...`); 100 ARM functions found.
- `runtime/gfx/usse_spirv.c`: **loops in GPU shaders** (a dispatcher for programs with backward or unstructured
  branches). Character creation's skinned characters were drawn by the software path before (slow, broken).
- `runtime/core/apputil.c`: **`sceImeDialog*`** answers at once ("Nova", the game's initial text, or `RECOMP_IME_TEXT`).
- **Gameplay recorder**: `RECOMP_VIDEO_DIR=<dir>` (gfx_gpu.c frames, display.c audio) + `dev/psnova/make_video.py`
  (H.264 + AAC via the ffmpeg already on this PC).

## Game data (CPK archives)

`dev/psnova/cpk.py` (spot-checked: counts and the 1.05/rePatch comparison reproduced, a
message file extracted from both archives) lists and extracts CRI CPK archives, CRILAYLA included. Full inventory:
[dev/psnova/CPK-INVENTORY.md](../../dev/psnova/CPK-INVENTORY.md).

- All five archives are plain TOC archives with bare file names (no folders); base 87,268 files, 1.05 patch 8,133,
  rePatch patch 23,033 (20,056 of them `.rmd`).
- **Text is pre-rendered.** `msg_*.rmd` (magic ` DMR`) carry the string `FontConverterDll_1.0.1.3_rc6`: each message is
  text already drawn into glyph images by the developer's font converter, one file per message, indexed by
  `novamessagedictionary.mdic` (magic `BMVN`). The English rePatch changes 2,254 and adds 14,898 `.rmd` files, i.e. it
  redrew the messages. Consequence for Arabic (proven only as far as the magic and the string go): we can draw shaped,
  right-to-left Arabic ourselves into the same format, with no in-game font or shaping limits.
- RMD decode so far (`dev/psnova/rmd/RMD-FORMAT.md`, `rmd.py info|atlas`; 13 Japanese/English pairs):
  header confirmed (message id at 0x90 = the file name's number; atlas size at 0x70/0x74, seen 128x32 to 256x128;
  data block = 0x1E0 bytes of tri-Ace chunks ` FIA`, ` FRa`, `ATIV` + width x height bytes). **Not decoded:** the atlas
  pixel layout (8-bit linear, Morton, tiles and 16-bit readings all unreadable: at 1 byte a pixel it may be DXT5/BC3 or
  the Vita's swizzle) and the glyph table. Next: read the texture format the renderer logs when the game draws a message,
  rather than guessing offline.
- Other formats: CRI ADX2 sound (`.acb` @UTF, `.awb` AFS2), Lua 5.1 bytecode scripts (`.lua`), CSV tables, tri-Ace
  formats with reversed four-letter tags (` FIA` .aif, ` FAA` .aai, ` FSA` .axs). The rePatch movie archive changes 9 of
  21 movies (MP00/MP06/MP09 and `Attention.mp4`).

## Status

| Area | State | Strength |
|---|---|---|
| Decrypt, import, analyze, recompile | done | single run |
| Build | `game_host.exe` 164 MB, 0 missing labels | proven (several builds) |
| Imports | 649: 245 runtime, 331 Sony's recompiled libraries, 73 stubs (below) | single run |
| First boot (headless, GPU) | 4 modules start, the game runs 30,821 system calls on 30 threads, then calls a missed ARM function (fixed, see above) | single run |
| Boot to title | **reached**: the title screen renders correctly (`docs/psnova/title-2026-11-18.png`), ~28 fps headless on the GPU | proven (many runs) |
| English via the fan rePatch (history) | worked (`vitarecomp repatch`: "English patch [DEBUG BUILD]" on the title), then **retired** 2026-11-18 evening for our own overlay (`REPATCH = "off"`; see "English text" below) | proven (screenshots), no longer used |
| Movies (the firmware's AvPlayer + host H.264) | the three start-up movies decode and show (after the block alignment and decoder-size fixes); the opening movie's "garbled" lines are SEGA's own in-universe script (checked against Chrome's decode of the same file) | proven (screenshots) |
| Buttons | **work** after the SceCtrlData fix: Start skips the movie and opens the menu, Cross closes dialogs, Circle confirms (Japanese layout) | proven (scripted runs, screenshots) |
| Main menu, NEW GAME, story intro | reached: NEW GAME / CONTINUE / OPTION, the PSO2 bonus dialog, then the intro movie (with burned-in English subtitles since the movie work below) | proven (screenshots) |
| Hand play by me (windowed) | **yes**: 2026-11-19 (into the Filldia cutscene; a crash and a freeze, both since fixed), 2026-11-20 (F12 captures), 2026-11-21 (bridge and captain-death scenes confirmed correct), 2026-11-22 (a 2 h 25 min session: the slowdown below) | proven (me) |
| Saves of other titles | "not found" (PSO2 bonus and demo import no longer offered: neither save exists here); this game's own slots listed by the slot search. `sceAppUtilSaveDataMount` itself unchanged (next steps) | single run |
| Character creation | all steps, skinned characters on the GPU (shader loops) | proven (screenshots) |
| Name entry | the PC name editor in the window (controller grid, or a keyboard/mouse text field, a limit of 10 UTF-16 code units): typed and cancelled, and a controller-grid name reached "Start the Game". Not tried: a physical gamepad, saving and reloading a newly named character. Headless runs keep the fixed answer ("Nova", `RECOMP_IME_TEXT`) ([save-and-name-dialogs-2026-11-21.md](save-and-name-dialogs-2026-11-21.md)) | single run (synthetic input) |
| Sound (NGS, ATRAC9) | **starts** since the NGS memory-size fix (11 NGS systems, title music; journal, sound section). **Chopping fixed** 2026-11-19: the A/V delay's silence top-up made 12-27 clicks a second; after the fix 0 top-ups, real-time rate. Checked on the title music only; gameplay and movie sound not rechecked, and I have not confirmed by ear ([audio.md](audio.md)) | single run (title, windowed) |
| After "Start the Game" | **fixed** (2026-11-18 afternoon): the abort was a recompiler bug -- tail calls set lr (journal, abort section; recomp.py `tail()`). Now: the save, the warp cutscene, the ship corridor and Rietheia's dialogue | single run (screenshots) |
| Training arena (tutorial) | **all quests cleared by the scripted play** -- move to the arrows, attack, avoid/block, annihilate -- and on to the next story scene (Lutina) by frame ~27,600 (take 7; `dev/psnova/make_arena_inputs.py`) | recording run (take 7) |
| Saves: writing | the character-creation save writes (569,108 bytes through the save dialog, slot 0); a copy in `dump/saves/after-creation-2026-11-18/` | single run |
| Saves: the PC save picker and loading | the recomp's own picker (original slot ids and callbacks; class and chapter in English). On an isolated copy, the Force Lv6 slot loaded (`savedata1.bin` opened, the character in gameplay, all slot files byte-identical afterwards); slot 2 resumed at the base. My own loads appear in the 2026-11-22 log. A freeze at the load list was the launcher cutting UTF-8 characters, fixed 2026-11-20 ([save-and-name-dialogs-2026-11-21.md](save-and-name-dialogs-2026-11-21.md), [picture-faults.md](picture-faults.md)) | single run (isolated copies) + my runs |
| Save backups (F10 > Saves) | back up, restore (asks first, keeps a "before restore" copy), delete; copies of the save folder, not save states; 17/17 unit checks, windowed check clean ([save-backups.md](save-backups.md)) | single run |
| Vita firmware dialogs (native save picker, IME) | **paused** at the player's request; normal play uses the PC dialogs. Picker: three rows draw with icons but no text (PAF's layout loops on `scePvfGetCharInfo`, 28,898 calls, never asks for a glyph), and a chosen slot did not open its file. IME: `sceImeOpen` fails (0x80100705; no shell IPC server or IME plug-in) ([vita-firmware-dialogs-2026-11-22.md](vita-firmware-dialogs-2026-11-22.md)) | open (paused) |
| Dialogue box, HUD, Filldia, Nova's armour | **fixed** (2026-11-18 evening): the renderer downloaded character creation's stale RGBA targets over textures the game later copied into the same memory; downloads now keep the pages the game rewrote (gfx_gpu.c `kept_pages_find`, journal "Noisy textures") | two runs (screenshots), reviewed by two agents |
| NOW LOADING screen | **fixed** while the rePatch was in use (`REPATCH_KEEP` merges back `tex_nova_ui_common.aif`, which the rePatch dropped). Moot now that `REPATCH = "off"`; the screen is redrawn by our own UI textures | three runs (then) |
| Frame rate | **30 fps steady, 60 fps mode** (2026-11-19): GPU views for ARGB targets (copy-back gone), 1-edge flips, precise DelayThreadCB sleeps, the game's own target set by the `psn_frame_rate` hook; select 60 with the `frame_rate` setting or F10 ([frame-rate.md](frame-rate.md)). Arena 56-60 fps at 60 headless; windowed 2x and 4x base routes 59.99-60.02 (2026-11-22). Fixed-step effects and cutscene timing at 60 not checked broadly | proven (several runs) |
| Long-session slowdown | **open, cause unknown** (2026-11-22): in the user's 2 h 25 min session at 60 fps, after loading the Force Lv6 slot, the frame rate fell to 15.9 then 8.5 fps, with 1,243 hitches of 100 ms or more. Two fresh base tests did not reproduce it; GPU-fence and wait data were not recorded for that interval and the route was not recorded. The launcher now writes those measurements to `session.log` on every Nova run ([fps-investigation-2026-11-22.md](fps-investigation-2026-11-22.md)) | open |
| Line primitives | **drawn** (2026-11-20): 2D lines as GPU quads (`lines_as_quads`), 3D lines as a LINELIST pipeline; fixed the shadow edges in replay. `RECOMP_NO_LINES=1` / `RECOMP_GPU_SOFT_LINES=1` to compare ([picture-faults.md](picture-faults.md)) | single run (replays) |
| Depth clip | **on** (`RECOMP_GPU_DEPTH_CLIP=1` in RUN_ENV, 2026-11-20): restores Kisara's console and Fildia on the bridge, against Vita reference frames; supersedes the earlier "needs a game camera change" and "changed nothing" notes ([render-investigation-2026-11-20.md](render-investigation-2026-11-20.md)) | proven (replays + scenes I confirmed 2026-11-21) |
| Colours (sRGB) | **on** (`RECOMP_SRGB=1` in RUN_ENV and TEST_ENV, 2026-11-19): the Lutina cutscene matches the Vita; the after-landing magenta sky not yet seen with it on ([cutscene-colours.md](cutscene-colours.md)) | proven for the cutscene |
| Instanced draws, deferred draws | one draw per instance (stripes and beams fixed); the instance-index source honoured on every draw (the coloured wedges; shown in 4 replays, not rerun live in the desert); draws held to the end of the scene (`RECOMP_DEFER_DRAWS=1`; one unexplained 82 s freeze in test111) ([picture-faults.md](picture-faults.md), [render-investigation-2026-11-21.md](render-investigation-2026-11-21.md)) | single run (replays) |
| Missing party in the ruins | **open**: the player confirmed the missing figures are the party; Lutina's origin sits ~35 units behind the eye in that capture. No camera or placement change made; no route to the ruins found ([render-investigation-2026-11-21.md](render-investigation-2026-11-21.md)) | open |
| English text | **our own overlay on the Japanese game** (`REPATCH = "off"`, my decision 2026-11-18 evening; the earlier rePatch row is history). Built from text sheet v7 (installed 2026-11-20) in the supplied English font, layered from `lang/en`; English is the default language (`lang/default.txt`). Dialogue reflowed and speaker names centred 2026-11-21; the layout check passes for 9,577 messages. Some cells still hold Japanese or placeholders ([localization-notes.md](localization-notes.md), [english-layout-2026-11-21.md](english-layout-2026-11-21.md)) | proven (in-game tests 3-12, my play) |
| HD (2x) English text | a pilot builder option (`--english-atlas-scale 2`); six selected messages passed archive/layout checks. The corrected name-entry label was verified live and Kisara's text in matched GPU replay; the selected caption and Advanced Personnel scene still need their live routes. Not installed, the default stays 1x ([hd-english-text-2026-11-22.md](hd-english-text-2026-11-22.md)) | single run (pilot) |
| HUD sharpness | replay prototypes only (re-drawn text sharpens; upscaled HUD art still soft); nothing installed ([hud-sharpness-2026-11-22.md](hud-sharpness-2026-11-22.md)) | untested live |
| Arabic text (every-project standard) | **partial**: menus, labels, descriptions, objectives, tutorials, quest banners and name plates (Arabic in about 15,580 of 25,484 messages), shaped, right-to-left, right-aligned by the `psn_rtl_*` hooks ([arabic-style.md](arabic-style.md)). About 9,900 messages, most of the dialogue and cutscene subtitles, still show English in Arabic mode. Last in-game test: Test 12 (2026-11-20) | single run per test |
| UI textures (Japanese inside pictures) | 88 redrawn for English and Arabic (title, banners, button guide, chapter cards, 83 tutorial pictures), installed 2026-11-19; banner and button guide seen in game, chapter cards and tutorial pictures only in previews ([ui-textures-research.md](ui-textures-research.md)) | single run |
| Movies | Japanese subtitles removed from the 8 story movies (v3 per-line masks: leftover subtitle frames 2+0+19, smears remain under the new subtitle strip); English subtitles burned in (138 cues, 28 px); the boot warning redrawn; the opening announcement subtitled with my wording (2026-11-21) ([movie-cleaning-v3.md](movie-cleaning-v3.md), [opening-announcement-2026-11-21.md](opening-announcement-2026-11-21.md)) | single run |
| Fonts | English K2D Medium 18 px (subtitles 28 px), shipped under the SIL Open Font License; Arabic Segoe UI Bold from `tools/fonts` (this machine's copies). Files and sizes in `dev/psnova/fonts.json`; a font dropped into `packs/PCSG00351/english/fonts/` is used in the default's place ([fonts.md](fonts.md)) | proven in game |
| Keyboard keys in button prompts (every-project standard) | not started (the button guide texture is redrawn with English/Arabic labels, still pad buttons) | n/a |
| Real-game reference pictures | **available**: my two walkthroughs of the real Vita game (section below); used for the colour and bridge comparisons | proven (used) |

## Real-game reference (from me, 2026-11-18)

`C:\New PATH\screenshots`: two YouTube walkthroughs of the real Vita game, one frame a second at 1920x1080 --
part 1 "Character Creator + intro" (1,419 frames, 0:05-23:43), part 2 "mission 1" (1,117 frames, 0:05-18:41).
Contact sheets (16 s each, timestamped) in `dump/reference/part1|part2/` (git-ignored: someone else's video), made by
`dev/psnova/make_ref_sheets.py`; the index (spot-checked) in [reference-index.md](reference-index.md).
Use it before any visual change and to script runs past character creation.

## Stubbed imports that matter (return 0 today)

From `RECOMP_IMPORTS=1` (dev/psn-logs/imports-run.log). Network, ad hoc, NP, trophies and screenshots are expected
stubs (offline play; the runtime returns "not initialised" for the network families).

| Import | Why it matters |
|---|---|
| `sceNgsVoiceDefGetAtrac9Voice`, `...MixerBuss`, `...Template1`, `...EqBuss`, `...DelayBuss`, `...DistortionBuss`, `...PitchShiftBuss` | NGS voice definitions: with a null definition the game's sound racks can't be made (Uncharted and Killzone only used the master/reverb/compressor ones) |
| `sceAppUtilSaveDataSlotSearch`, `sceAppUtilSaveDataMount`, `...Umount` | loading saves |
| `sceImeDialogInit/GetStatus/GetResult/Term`, `sceImeOpen/Update/Close` | text entry (likely naming the character) |
| `sceKernelCancelEventFlag`, `sceAudioOutReleasePort` | small kernel/audio calls |
| `sceJpegCsc`, `sceJpegMJpegCsc`, `sceJpegGetOutputInfo` | JPEG decoding (use not known yet) |
| `sceKernelLoadStartModule`, `sceSysmoduleLoadModule` | answered 0 (success); the modules it loads (libsmart, libface...) are not imported by the main program |

## Controls (Project Nativ's defaults)

D-pad: arrow keys · Cross/Circle/Square/Triangle: Space/C/F/E · Start/Select: Enter/Tab · L/R: right/left mouse
button (or Q and R) · sticks: WASD and mouse · front touch: Alt+click · F10 menu, F1 frame rate, F5 bug mark.
A Japanese release usually confirms with **Circle (C)** and cancels with **Cross (Space)**: to be checked in the game.

## The button problem (investigation, 2026-11-18)

- Two controller reads exist in the whole program (generated C, call sites of the import stubs):
  `fn_815920de` (sceCtrlReadBufferPositive2 port 0, every frame, main game loop) keeps only L, R, L3, R3 (the PS TV
  extra buttons games use in place of touch); `fn_81b1c958` (sceCtrlPeekBufferPositive) is the real pad device's read.
- The real read's chain (RECOMP_CTRL_BACKTRACE): Aska worker `fn_81a23802` -> job `fn_81a1f276` -> `fn_81b1cd18` ->
  `fn_81b1c958`. The job loops "while not quit: update the 3 device slots (+0x18, vtable +0x24); sleep 8 ms"; the pad
  update locks (spin, then 1 ms sleeps), peeks, and processes buttons only when the sample's timestamp changed.
- It peeked once (frame 0) and never again, while the loop kept spinning. The trace hooks showed why: from the second
  pass the loop's object pointer (r5, callee-saved) was 0, so it read empty slots at 0/4/8 forever. **Cause:** the
  runtime wrote each `SceCtrlData` as 64 bytes; it is 0x20. The pad update keeps its sample at `sp+0` under its canary
  at `sp+0x24` and the saved r4-r8 from `sp+0x2c`: the extra 32 bytes zeroed them, and the canary check passed because
  `__stack_chk_guard` is left 0. **Fixed** (display.c): the pad update ran 218,000 times in the next run and the
  buttons work.
- Not the cause (checked): the save-slot stubs (that call only counts saves, and 0 is right for a fresh test),
  sound (not started before the title), the app state (all zeros: nothing overlaid), skipped movies.

## Open questions and next steps

Reconciled 2026-11-22. In order of priority:

1. **Repeatable save-based routes** for regression checks: scripted inputs from a fixed save (a copy kept in
   `dump/saves/`) through the base, a mission and a cutscene, so fixes and slowdowns can be compared run to run.
2. **The long-session slowdown**: reproduce it on such a route (load the Force Lv6 slot after a long session, or a
   long scripted run), then read `session.log`'s GPU-fence, wait and metrics lines for the slow interval before
   changing anything.
   Measured from a live session, 2026-11-27 (single run; a 45-minute play at render scale 6x, 2584 metrics samples,
   580 hitches of 100 ms or more, the worst 42.4 s at frame 59047). Its symptoms are not confined to the frame rate:
   **audio drops out and audio-timed cutscenes pause**, because the runtime paces the guest's audio handovers by the
   device queue (`runtime/ui/window.c` `audio_output`: "a game times its cutscenes by the buffers it has handed over")
   and that wait has no timeout.
   The slowdown itself has a shape: one guest thread's CPU share climbs steadily and saturates. `CRI Server Manager`
   takes 0.3% of a core at the start of the session and 93.5% (peak 96.0%) by the end, and its per-frame sleeps collapse
   from 41.6 ms to about 1 ms, so it stops idling and spins (measured across 629 waits blocks). `CRI FS File Access` is
   blocked 30-89 ms/frame throughout, the Aska render workers block ~92 ms/frame, and at the worst stall the GPU was
   **0% busy across 42.36 s** while the game's own `speed` read `0.00x`. `CRI Atom AudioOut` is never blocked, so the
   audio path is a victim and not the cause. This points at the game's CRI streaming layer, most likely at something the
   server manager polls that never becomes ready. Not established: what it is polling, and whether it or the runtime's
   file IO is at fault.
3. 60 fps correctness: fixed-step effects and cutscene timing on longer routes (the arena and base routes only so far).
4. The missing party in the ruins: needs a route or a save just before it.
5. Arabic: write the ~9,900 remaining messages (most dialogue and the cutscene subtitles); the squeezed enemy name by
   the TARGET marker; the Japanese names in the mission-prep team panel; speaker-name boxes not yet seen in game.
   Keyboard-key prompts (button guide texture and pre-rendered messages) not started.
6. Visual review of what was only previewed: chapter cards, tutorial pictures, the magenta sky with sRGB on, the
   desert wedges with the instance fix; the dark bands on the ground (may be the game's own shadow).
7. Make `sceAppUtilSaveDataMount` answer "not found" for another title's save (no free PSO2 bonus) unless I
   want the bonus.
8. The two shaders the translator refused: find which draws use them (one untranslated program, 0x110ff3c0, was
   found in none of the bad captures: render-notes-2026-11-20.md).
9. Font licences: whatever font a build was drawn with, before it is shared.
10. Bring the SceCtrlData fix to the Uncharted copies (their stacks may be quietly damaged the same way); I decide.
11. Paused at my request: the Vita firmware save picker and IME. HD English text and HUD sharpness remain
    optional pilots, with incomplete live coverage; neither is installed.

Done since 2026-11-19: hand play by me; line primitives drawn; save loading; PC name entry; the arena route
(`dev/psnova/make_arena_inputs.py`, take 7); the RMD decode and Arabic/English overlays; the branch committed
(2026-11-22, source and tools committed after 3e5328a; `AGENTS.md` and the local font folder left uncommitted on purpose).

Leads from the Uncharted session's comparison with the Luufen Nativ fork (read-only clone at `recent recomps\Nativ
   Luufen fork`; `Uncharted Golden Abyss Recomp RT\docs\fork-benefit-check.md`, Nova section): taken -- dfc075d (NEON
   post-increment). Not yet, test one at a time: 1deb30f GPU views for any U8U8U8U8 order (~5 target downloads a frame,
   ~12 ms of 51 ms; confirm with `RECOMP_GPU_TRACE_SYNC=1`), 340a30f/ad8dd3d IME text card, SOP2 blend ops on the GPU,
   74e8f78/33c4b5b/3854bf2 NGS (start buffer at +81), 756959a hooks-scan (60 fps / widescreen sites), 9d2bdb6 gap
   report. Do NOT take 47e54dc (L1/R1 bits) without tracing Nova's bit tests first.

# Phantasy Star Nova Recomp feature inventory

Reviewed November 23, 2026.

The inventory covers the Windows Nova pack for `PCSG00351`, targeting Sega's Japanese 1.05 update. I checked the pack defaults and matched the active executable, English text archive and English movie archive to the hashes recorded in the implementation notes.

## Windows play and input

- Windows launcher builds and runs Nova through Project Nativ from your imported game data. The Nova checkout has its own local Python and toolchain, separate from Uncharted. The launcher checks the project virtual environment and falls back to the bundled Python.
- The recompiled Windows game boots through the warning, logos and title. New Game, Continue, character creation, save writes and loads, the introductory story, tutorial arena and later base/field play have documented runs. The training quests were cleared with scripted input. Theater Scope is the game's own event replay menu.
- Keyboard and mouse and gamepad input are supported by the host. The default keyboard mapping uses Enter for Start, C for the game's Circle confirm, Space for Cross cancel, arrow keys for the D-pad, and WASD and mouse for stick input. Shared controls expose key rebinding, mouse sensitivity and gamepad touch-cursor emulation.
- F10 opens the pausing PC overlay with game, display, performance, audio, controls and save settings. The language selector exposes installed language overlays. On-screen menu access also works through the runtime's menu bar and gamepad shortcuts.
- Character creation has the PC name editor. Mouse and keyboard use a text field. Controller mode has an on-screen grid with case, numbers, symbols, space, erase and Done. Automatic mode follows the active input device at open. It honors the game's ten UTF-16-unit limit and hands the entered name to the game's confirmation screen. The grid and cancellation were tested with synthetic and pointer input. Physical controller entry and a save/reload of a freshly named character still need a combined test.

[Launcher](../../Play%20Phantasy%20Star%20Nova.bat) · [Nova status](README.md) · [PC dialog checks](save-and-name-dialogs-2026-11-21.md) · [Overlay code](../../runtime/ui/overlay.cpp)

## Saves

- The PC save/load picker preserves Nova's slot IDs and callbacks. It shows the game icon, slot metadata, dates, playtime, confirmation and progress, with English class and chapter names in English mode.
- F10 save backups copy the game's save folder. The menu lists, creates, restores and deletes backups, and makes a recovery copy of the current saves before a restore. These snapshots cover saved game progress.
- Verified paths include creation saving and loading copied existing slots into gameplay. Headless routes can set an isolated save row and provide a scripted name.

[Save picker and name input](save-and-name-dialogs-2026-11-21.md) · [Save backups](save-backups.md)

## Graphics and performance

- GPU rendering with Vulkan on the tested Windows machine, adjustable internal resolution and F2 cycling. A 4× frame is 3840 × 2176 from the 960 × 544 Vita canvas. The display menu provides fullscreen, Fit/Stretch/Fill, FXAA, sharpening and anisotropic filtering. These are shared player controls.
- Nova offers 30 and 60 FPS modes. The game-rate hook, frame delivery changes and more precise wait handling support the 60 FPS target. Fresh base routes reached approximately 60 FPS at 2× and 4×. Scripted arena testing reported about 56–60 FPS. Long sessions vary, and fixed-step effects and cutscene timing at 60 FPS still need broader checks.
- The Nova pack enables sRGB texture and surface handling, deferred GPU draws and depth clipping. sRGB restores color and contrast in compared scenes and retains the original bloom. Depth clipping restores the bridge view that had been covered by near geometry. I confirmed the bridge and captain-death scenes in live play.
- GPU shader loop support lets skinned characters render on the GPU. Line primitives and instanced particle drawing were corrected. Instancing fixes address connected particle strips and incorrect per-instance vertex fetches. The latter was verified in replay.
- Render-target synchronization fixes preserve guest-written texture pages after GPU downloads. This corrected corruption affecting parts of character creation, the HUD, dialogue and armor. GPU target views reduce costly copy-backs where supported.
- A presentation fix keeps the scaled GPU image available across readbacks when the guest image matches it. The tested F12 path previously showed four native-resolution frames after a readback. The corrected test used the GPU image throughout.
- Startup shader scanning bounds and a private NVIDIA shader cache improve startup and avoid different recomp titles competing for the same cache. The runtime includes shader and pipeline warm-up tools.
- Shared optional render paths for expanded widescreen, per-game HUD rearrangement, FSR 3.1, ambient occlusion and full-resolution-world overrides exist in the runtime. The Nova pack does not declare those title-specific features supported. Nova's shadow samplers also differ from the shared soft-shadow filter's documented match.

[Pack defaults](../../packs/PCSG00351/pack.toml) · [Frame rate](frame-rate.md) · [Rendering fixes](picture-faults.md) · [Bridge and particles](render-investigation-2026-11-20.md) · [Presentation](render-investigation-2026-11-21.md)

## Audio and movies

- The Vita movie path uses recompiled playback modules and host H.264 decoding. Corrected memory alignment and decoder allocation restored video in startup movies that previously played audio over black. Story movies, the warning and the opening preview have recorded playback.
- NGS and ATRAC9 work brought up title audio. The Windows title audio check found that preventing silence top-ups removed the measured clicks. Wider in-game audio quality still has limited verification. The shared PC menu provides volume control and audio/video sync settings exist in the runtime.

[Audio](audio.md) · [Nova implementation and playback](README.md)

## Localization

- English is the default in the current install. The project uses its own English overlay with the supplied font's lettering, localized menu and dialogue text, and translated metadata in save views. Original Japanese is available through the language selector. The pack disables the fan rePatch. Some English rows still contain Japanese or placeholders.
- The English dialogue builder wraps to fit the box, preserves word order and control codes, and uses descending line lengths on multiline dialogue. Speaker names are centered in their nameplates. In-engine cinematic captions use at most two lines and preserve character proportions. The layout verifier covered 9,577 classified messages.
- The centered three-line boot warning, subtitle translations on eight story movies, and the English opening preview announcement about Planet Wakua are installed. The movie build retains the original audio and supports up to two lines without distorting letters. The English backing in **The Enigmatic Girl I** was centered via the November 23 single-movie update.
- The Arabic overlay provides right-to-left shaping and right alignment for translated menus, labels, tutorials, quests and other covered messages. The documented coverage is about 15,580 of 25,484 messages. Arabic mode still uses English for much of the remaining dialogue and captions.
- An English/Arabic art pass redrew 88 UI images, including banners, button guides and tutorial pictures. The button guide still displays controller glyphs. Per-language font and layout settings live in the build tooling.
- **2× English text pilot.** The optional builder doubles physical glyph atlas resolution while retaining original logical dimensions and layout. The corrected name label was verified live, and Kisara's message was verified in a matched GPU replay. The pilot remains staged and the normal English text archive uses 1× glyphs. Enlarging the HUD artwork alone produced little improvement in the replay.

[Localization status](README.md) · [English layout](english-layout-2026-11-21.md) · [Arabic overlay](arabic-style.md) · [Opening preview](opening-announcement-2026-11-21.md) · [Subtitle backing](subtitle-backing-2026-11-23.md) · [HD pilot](hd-english-text-2026-11-22.md)

## Diagnostics and project tooling

- F1 cycles on-screen performance stats. F5 marks the log and saves recent-present history in the GPU path. F12 captures guest graphics commands and memory to VFC for replay and can briefly stall play. The gameplay recorder captures picture and sound for H.264/AAC export.
- Nova's standard launcher writes frame metrics, GPU estimated busy time, completion latency and queue depth, plus thread wait and game-clock diagnostics to `session.log`. More detailed traces and a bounded Windows CPU sampler are available for investigation.
- Scripted runs support isolated saves and settings, recorded inputs, reference screenshots, frame-rate thresholds and route comparisons. The local route tool includes a base walk and camera route. The pack's reference test defaults to software rendering and a fixed clock. Normal play uses the GPU and real clock.
- Build tooling checks generated labels and handles ARM/Thumb pointer targets, shared tails, function entry decoding and tail-call cases found while getting Nova to boot and start gameplay. The runtime also implements or corrects controller data, event cancellation, memory alignment and save service behavior used by the title.
- Asset tooling reads CRI CPK archives and builds text and movie overlays. Scripts regenerate RMD glyph atlases and dialogue layout, replace UI textures, remove legacy subtitles, burn translated captions and verify archive entries and audio payloads.
- F12 GPU/CPU replays and Vita-reference comparisons are used for color, depth, particles, camera and presentation regressions. This tooling is for diagnosis and repeatable testing.

[Performance instrumentation](fps-investigation-2026-11-22.md) · [Local route tool](../../dev/psnova/route.py) · [Capture code](../../runtime/debug/gfx_capture.c) · [Build notes](README.md)

## Known gaps and paused work

- The intermittent single-digit FPS drops in planet fields remain open. Captured slow windows showed roughly 5–7 ms of GPU work with an empty measured present queue. The specific CPU-side cause remains unresolved. A later isolated field run did not reproduce the drop.
- The missing party in the ruins remains open. A captured actor sat behind the camera and other expected player draws were absent from that pass. There is no verified camera or placement fix.
- Original Vita OS save and IME dialogs are paused. Normal play uses the PC picker and editor. A full campaign regression pass, remaining subtitle/cutscene checks and broader hardware checks are still pending.
- The reviewed build evidence does not establish DLC support. Localization gaps and the optional HD text work are tracked above.

[Field slowdown](fps-investigation-2026-11-22.md) · [Missing party](render-investigation-2026-11-21.md) · [Paused Vita dialogs](vita-firmware-dialogs-2026-11-22.md)

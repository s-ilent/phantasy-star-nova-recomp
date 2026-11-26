# Phantasy Star Nova Recomp

**A fork of [Project Nativ](https://github.com/TheLostPantheon/nativ), focused on *Phantasy Star Nova*.**

Phantasy Star Nova Recomp turns the Japanese PS Vita release of *Phantasy Star Nova* (tri-Ace / SEGA, 2014) into a
native Windows program. It is not an emulator. The game's ARM code is translated to C once, ahead of time, and compiled
into a normal Windows executable. A runtime stands in for the Vita's system software and hardware: it runs the game's
threads, draws its graphics on your GPU through Vulkan, plays its sound and movies, and reads your keyboard, mouse or
controller.

You bring your own copy of the game. Nothing of the game ships in this repository.

## What you get

- **The full game running natively**, from the title screen through gameplay, movies and saves.
- **Higher resolution and frame rate:** up to 6× the Vita's 960 × 544 internal resolution, and an optional 60 FPS
  mode where the Vita ran at 30.
- **PC controls:** keyboard and mouse, or an Xbox-style controller you can plug in at any time. The game follows
  whichever device you used last.
- **Saves you can manage:** a PC save picker, and save backups from the in-game menu.
- **An in-game menu (F10)** for resolution, frame rate, controls, language and saves.
- **Graphics fixes** for depth, deferred draws and lines that the Vita's GPU handled differently.

## Status

**Beta.** In testing on Windows 11, the game runs through character creation, gameplay, movies, saving and loading.
Setup builds an **English localization** from your copy: menus, dialogue, UI art and movie subtitles, with the
Japanese subtitles burned into the movies removed (see [English](#english)). Known issues are tracked in
[docs/psnova/README.md](docs/psnova/README.md).

## Setup

You set up once, in six steps. It takes 40 minutes to an hour, most of it waiting while your PC builds the game. After
that you start the game with a double-click.

| Step | What it does | Time |
| --- | --- | --- |
| [1. Download the project](#1-download-the-project) | Gets the code and its Python packages | 2 min |
| [2. Install the build tools](#2-install-the-build-tools) | Downloads the compiler and libraries | 5–30 min |
| [3. Add the Vita system software](#3-add-the-vita-system-software) | Takes the modules the game needs from Sony's firmware file | 1 min |
| [4. The English font](#4-the-english-font) | A font ships with the project; use your own if you like | 1 min |
| [5. Add your game](#5-add-your-game) | Builds the Windows game and its English | 30 min |
| [6. Play](#6-play) | | |

### Before you start

Get these ready. Everything else is downloaded for you.

- [ ] **A Windows PC:** Windows 10 or 11 (64-bit), a graphics card with an up-to-date driver, and about 12 GB of free
  disk space.
- [ ] **[Git for Windows](https://git-scm.com/download/win)** and **[Python](https://www.python.org/downloads/)**
  3.12 or newer, installed with their default options. For Python, choose the **Windows installer (64-bit)**: the
  32-bit and ARM64 versions can't install what setup needs.
- [ ] **Your copy of the game:** *Phantasy Star Nova* for the Japanese PS Vita (`PCSG00351`), both the **1.00** game
  and the official **1.05** update. PKG files work, and so do the `app` and `patch` folders copied from a Vita.
- [ ] **Your game's licence file:** `work.bin` or a `.rif` file. In a game folder copied from a Vita it is in
  `sce_sys\package\`.
- [ ] **The Vita system software:** `PSVUPDAT.PUP` version 3.74, from
  [PlayStation's download page](https://www.playstation.com/en-us/support/hardware/psvita/system-software/).
- [ ] **For English:** nothing extra. A font, **K2D Medium** under the SIL Open Font License, ships with the project
  and draws the English. To use your own instead, drop a `.ttf` or `.otf` into `packs\PCSG00351\english\fonts\`.

Other regions and versions don't work. A copy that already has a fan translation works: setup removes the fan
translation and puts this English in its place, with a few limits (see [English](#english)).

> [!TIP]
> **Running the commands.** To open PowerShell in a folder, open the folder in File Explorer, click the address bar,
> type `powershell` and press Enter. Copy a whole code block, paste it into the window with Ctrl+V, and wait
> until the prompt comes back before the next one. Where a command says `C:\path\to\…`, put the path of your own file
> between the quotes. Dragging the file onto the PowerShell window types its path for you.

### 1. Download the project

Open PowerShell in the folder where you want the project, for example your Documents folder, and run:

```powershell
git clone https://github.com/aggc01/phantasy-star-nova-recomp.git
cd phantasy-star-nova-recomp
py -3 -m venv .venv
.\.venv\Scripts\python.exe pipeline\check_python.py
```

**It worked if** the last line says `64-bit: ready`. If it says this Python can't be used, follow its
instructions before going on.

Then install the Python packages setup uses and make a `dump` folder:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
New-Item -ItemType Directory dump
```

**It worked if** the last line shows a new folder named `dump`. That folder holds your game library, the build and
your saves. Keep this PowerShell window open for steps 3 to 5.

### 2. Install the build tools

This step uses **Git Bash**, which came with Git. In File Explorer, open the new `phantasy-star-nova-recomp` folder,
right-click an empty spot and choose **Open Git Bash here** (on Windows 11 it is under **Show more options**). Run:

```bash
ATIV_WIN_TOOLCHAIN="$PWD/toolchain" bash runtime/platform/win/setup-toolchain.sh
```

It downloads about 280 MB into a `toolchain` folder inside the project, then unpacks the compiler and builds part of
FFmpeg. **That part shows nothing on screen for 5 to 30 minutes, depending on your PC.** It hasn't stopped: leave the
window open and let it finish. Each stage prints a line starting `==` when it begins.

**It worked if** the last line starts with `toolchain:` and doesn't say `MISSING`. You can close Git Bash now. If you
closed it early, run the same command again: it skips what's already downloaded.

### 3. Add the Vita system software

Back in PowerShell, with the path of your `PSVUPDAT.PUP`:

```powershell
.\.venv\Scripts\python.exe pipeline\vitarecomp.py firmware "C:\path\to\PSVUPDAT.PUP"
```

**It worked if** the last line starts with `firmware 3.74`.

### 4. The English font

**You can skip this step.** K2D Medium, under the SIL Open Font License, ships in
`packs\PCSG00351\english\fonts\` and draws the English.

To draw it with a font of your own, copy any `.ttf` or `.otf` into that folder: a font you put there is used in the
default's place. It stays on your PC — git never uploads fonts from there, and the project's default is the only font
it commits. The font's own spacing decides the layout, so a wider one may crowd a box.

Skip this step if you want the game in Japanese.

### 5. Add your game

Run the first command with your base game and its licence file, then the second with the 1.05 update:

```powershell
.\.venv\Scripts\python.exe pipeline\vitarecomp.py add "C:\path\to\base-game.pkg" --license "C:\path\to\work.bin" --no-build
```

```powershell
.\.venv\Scripts\python.exe pipeline\vitarecomp.py add "C:\path\to\update-1.05.pkg"
```

The first takes a minute. The second builds the game (about 15 minutes), then the English (about 15 minutes), and
prints a lot as it goes. **It worked if** it ends with a line starting `English localization ready`. If the English
could not be built, it says why instead, and the game is built in Japanese.

Your game files are only read, never changed.

<details>
<summary>Your game is in folders or a ZIP, not PKG files</summary>

Unpack a ZIP first. Then give the folders instead of the PKG files: the folder ending `app\PCSG00351` for the base
game, and the one ending `patch\PCSG00351` for the update.

</details>

<details>
<summary>Red text appears while it runs</summary>

PowerShell shows some of the tools' notes in red, for example one saying `sce_sys\about\right.suprx` is skipped. That
is expected. A step has worked if it ends without an error message.

</details>

<details>
<summary>You changed the font later, or the English stopped</summary>

Build only the English (about 15 minutes):

```powershell
.\.venv\Scripts\python.exe pipeline\vitarecomp.py localize PCSG00351
```

</details>

### 6. Play

Double-click **`Play Phantasy Star Nova.bat`** in the project folder. See [Playing](#playing) for the controls and
the in-game menu.

If something went wrong, see [Troubleshooting](#troubleshooting).

<details>
<summary>Rebuilding after you change the code</summary>

Run `bash dev/psn_build_all.sh` from Git Bash. It runs the import, analyze, recompile and build stages again and
writes a log for each to `dev/psn-logs/`.

</details>

## Playing

The game opens in a 960 × 544 window, the Vita's own resolution, with the frame rate shown in the top-left corner
(**F1** cycles or hides it). Press **F10** at any time for the in-game menu, where you can raise the resolution (up to
6×) and turn on 60 FPS. Both are saved for next time. 4× and above need a strong GPU.

| Action | Keyboard and mouse | Controller |
| --- | --- | --- |
| Move | W A S D | Left stick |
| Camera | Mouse | Right stick |
| Confirm (Circle) / Cancel (Cross) | C / Space | B / A |
| Square / Triangle | F / E | X / Y |
| L / R | Q / R, or the mouse buttons | LB / RB |
| D-pad | Arrow keys | D-pad |
| Start / Select | Enter / Tab | Menu / View |
| In-game menu | F10 | |
| Quit | Alt+F4 | |

Controls can be changed in **F10 → Controls**.

| What | Where |
| --- | --- |
| Saves | `dump\decrypted\PCSG00351\recomp\fs\savedata0` |
| Settings | `dump\decrypted\PCSG00351\recomp\settings.ini` |
| Log | `dump\decrypted\PCSG00351\recomp\session.log` |

Back up your saves from **F10 → Saves** before trying anything risky.

## English

The English localization covers menus, dialogue, names, UI art and movie subtitles, with some lines still in
Japanese. It lives in [`packs/PCSG00351/english/`](packs/PCSG00351/english/localize.py) as recipes: the English text,
instructions for redrawing each UI image, and subtitle timings, each tied to the SHA-256 of the original file it
applies to. No game file is in the repository. On your PC, step 5 (or `vitarecomp localize PCSG00351`):

1. checks that your game and update archives are the unmodified Japanese originals;
2. writes the English messages and redrawn UI images into a copy of the update's archive;
3. removes the Japanese subtitles burned into the story movies, frame by frame, and draws English subtitles in their
   place;
4. puts both archives in `dump\decrypted\PCSG00351\lang\en` and makes English the starting language.

Your original archives stay untouched. **F10 → Game → Language** switches between English and the original Japanese
at any time. A later run only rebuilds what changed.

If your copy already carries a fan translation (such as Arks-Layer's English patch, often found merged into a
"v1.05 English" copy), step 5 removes it and builds this English in its place:

- the update's archive is rebuilt from the untouched base game, so none of the fan's text is left;
- the story movies, which the fan translation re-encoded with its English under the Japanese line, have both lines
  erased before the English subtitles are drawn;
- the opening warning screen, which the fan translation turns into its credits, is drawn again in English.

A fan copy no longer holds everything the original had. One UI texture is gone, so some screens can show noise.
Eight lines that this English leaves untranslated show the base game's older Japanese wording. The story movies
start from the fan's lower-quality re-encode. Step 5 says so when it runs. For the full result, use an unmodified
Japanese copy.

## Troubleshooting

| Problem | What to do |
| --- | --- |
| `no Windows toolchain at …` | Run step 2 again, and check that `toolchain\llvm-mingw` exists. |
| The firmware or the game went to `%LOCALAPPDATA%\ProjectNativ` | The `dump` folder was missing. Create it (step 1) and run steps 3 and 5 again. |
| `Building wheel for capstone … did not run successfully` or `'cmake' is not recognized` in step 1 | Your Python is 32-bit or ARM64. Install Python with the **Windows installer (64-bit)**, delete the `.venv` folder and run step 1 again. `py -0p` lists the Pythons you have: a 32-bit one shows `-32`. |
| `Python not found` when starting the game | Create `.venv` as in step 1. |
| The update is refused or asks for a licence | Add the base game first (step 5), with its `work.bin` or `.rif`. |
| `English localization: The English text needs a font` | Restore `K2D-Medium.ttf` in `packs\PCSG00351\english\fonts\`, or put another font there (step 4), then run `vitarecomp localize PCSG00351`. |
| `English localization: this copy carries a fan translation` | Expected with a fan-translated copy: the fan translation is removed and this English applied, with the limits the message lists. For the full result, add an unmodified copy (step 5). |
| `… is not the original Japanese base game archive` | The base game itself is modified. Add an unmodified copy (step 5). |
| The game is in Japanese after setup | Check the end of step 5's output for a line starting `English localization`, which says what stopped it. |
| A stage fails during the build | Read its log in `dev/psn-logs/`, or the command's output. Most failures name the file or setting at fault. |
| Black screen or crash at start | Update your GPU driver. Check `session.log` for the last lines before the problem. |

## How it works

1. **Import:** the game's executable and Sony's system modules are decrypted from your files and checked against the
   versions this project supports.
2. **Analyze:** every function in the game's 28 MB executable is found, about 40,000 in all.
3. **Recompile:** each function's ARM instructions are translated to C. The output is about 1 GB of C in 100 files.
4. **Build:** Clang compiles that C together with the runtime into one Windows program.
5. **Run:** the runtime provides what the game expects from a Vita: memory, threads, files, the GPU, sound, input and
   the system dialogs for saves and names.

Game-specific fixes, such as the 60 FPS frame pacing and the input hooks, live in
[`packs/PCSG00351/`](packs/PCSG00351/pack.toml). Project Nativ's [architecture guide](docs/architecture.md) explains the
recompiler and runtime in depth.

## Repository layout

| Path | What's in it |
| --- | --- |
| `packs/PCSG00351/` | The game pack: supported versions, code hooks, function seeds and shader recipes |
| `packs/PCSG00351/english/` | The English localization: text, UI and subtitle recipes, and the scripts that build them |
| `recompiler/` | The static recompiler (ARM to C) |
| `runtime/` | What the recompiled game runs on: kernel and libraries, graphics, audio, input, UI |
| `pipeline/` | `vitarecomp.py`, the driver for every stage |
| `decrypt/` | Decryption of firmware and game packages |
| `dev/psnova/` | Nova tools: localization builders, archive tools, subtitles, checks |
| `dev/psnova/release/` | The standalone Windows release: setup program, launchers and guides |
| `docs/psnova/` | Nova documentation: current state, investigations and design notes |

## Relationship to Project Nativ

The recompiler, runtime, pipeline and decryption come from Project Nativ
([TheLostPantheon/nativ](https://github.com/TheLostPantheon/nativ)). This fork changes them where *Phantasy Star Nova*
needs it, and adds the game pack, the localization tools and the Windows release. Nativ's other game packs (Killzone:
Mercenary, Unit 13, Shovel Knight) are still in `packs/` but are not maintained or tested here.

## Licence

Free software under the GNU General Public License, version 2 or (at your option) any later version, like Project
Nativ: see [LICENSE](LICENSE). Third-party code keeps its own licence, listed in [THIRD_PARTY.md](THIRD_PARTY.md).

This repository contains no Sony or game code. The game is recompiled on your machine from your own copy and never
leaves it.

## Credits

Built on [Project Nativ](https://github.com/TheLostPantheon/nativ). To support Nativ itself, see its
[Ko-fi](https://ko-fi.com/kingtorro).

The English text started from Arks-Layer's fan translation of *Phantasy Star Nova* and was revised and extended for
this project. The English lettering is drawn with K2D Medium (SIL Open Font License), which the project ships, or with
a font the player supplies in its place. The movie subtitles are encoded with
[FFmpeg](https://ffmpeg.org/), using Gyan Doshi's Windows build.

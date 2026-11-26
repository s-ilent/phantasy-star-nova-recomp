# Phantasy Star Nova Recomp for Windows

**0.1.0 Beta 1**

Play the Japanese PS Vita release of *Phantasy Star Nova* on a Windows PC from your own game files. You extract this release, run one setup program, and point it at your copy of the game. Setup builds the game on your PC, applies the English localization and the graphics and performance enhancements, and creates **Phantasy Star Nova.exe**.

English is on by default and covers the menus, dialogue, UI art and movie subtitles that are implemented so far. Some lines and screens are still Japanese. To go back to the original Japanese game, open **F10 → Game → Language**, choose **Original**, and restart the game.

## Supported game versions

| What | Supported version |
| --- | --- |
| Game | *Phantasy Star Nova*, Japan, PS Vita. Title ID `PCSG00351`, content ID `JP0177-PCSG00351_00-NOVAAPPLICATION0` |
| Base game | version **1.00** |
| Update | version **1.05**, the official update for `PCSG00351` |
| Sony system software | PS Vita **3.74**, the file `PSVUPDAT.PUP` |
| Font | any font file you supply, `.ttf` or `.otf` (see step 1) |

Other versions, other title IDs, and games that already carry a fan translation are not supported. Setup checks the original game archives, and it tells you if one has been changed. Use the unmodified base game and update.

## What you need

- 64-bit Windows 10 or 11 and a graphics driver with Vulkan support.
- **About 14 GB of free space** on the drive where you extract the release. Setup compiles the game on your PC, so it takes a while, and the first run is the longest.
- Your game, in **one of these two layouts** (not a `.vpk`):
  - **Two PKG files**: the base-game package (version 1.00) and the official update package (version 1.05).
  - **One ZIP file** that holds both PKG files. Make it with Windows ("Send to > Compressed (zipped) folder"), 7-Zip or similar, with the default Store or Deflate compression and **no password**. Other files in the ZIP, and add-on (DLC) packages, are ignored.
- Your game's **license**: the `work.bin` (or a `.rif`) for *Phantasy Star Nova*. Most PKG files do not carry one. If the base-game PKG already has a license inside it, setup uses that and you can leave the field empty.
- **Vita system software 3.74** as `PSVUPDAT.PUP`. Setup uses it to prepare five system modules the game needs. [PlayStation's download page](https://www.playstation.com/en-us/support/hardware/psvita/system-software/)
- A **font file** (`.ttf` or `.otf`) to draw the English with. See step 1.

## Setup

1. **Add a font.** This release includes no font and names none: the English text, UI art and movie subtitles are drawn with a font you supply. Copy any `.ttf` or `.otf` into the `localization\fonts` folder of this release, or choose one in the setup window. Its own metrics decide the spacing, so a wider or taller font may crowd a box.
2. **Extract** the whole release to a folder you can write to, such as `C:\Games\Phantasy Star Nova`. Do not run setup from inside the zip.
3. Open **Setup Phantasy Star Nova.exe**.
4. Choose your game files (see the table below), your **Game license**, and `PSVUPDAT.PUP`. If you did not copy the font in step 1, choose it too.
5. Click **Build and install** and leave the window open. Setup reads the package headers first, before it builds anything. If a package is the wrong game or version, damaged, or missing, or if the license does not match, it stops and names the file. Each stage is listed as it runs.
6. When setup says it is complete, click **Play**, or open **Phantasy Star Nova.exe** from the release folder. Use that file from now on.

### Choosing your game files

| You have | **Game PKG or ZIP** | **Update PKG (optional)** | **Game license (if required)** |
| --- | --- | --- | --- |
| A base-game PKG and an update PKG | the base-game PKG | the update PKG | your `work.bin` or `.rif`, unless the base PKG has one inside |
| One ZIP with both PKGs | the ZIP | leave empty | the same |

Setup tells the packages apart by reading their headers, not their names, so a PKG chosen in the wrong field is still found. It needs exactly one *Phantasy Star Nova* base game 1.00 and one update 1.05: a second matching package, a different game, or a different version is reported by file name. Your files are only read. A PKG inside a ZIP is unpacked to `NovaData\scratch` while it is imported and deleted right after, so the drive needs room for that (the 14 GB above covers it). Whatever you select is remembered in `NovaData\setup-inputs.json`, so after a stop the window opens with the same files chosen.

**Command line.** Setup also runs from a command prompt, which shows the same messages:

```
"Setup Phantasy Star Nova.exe" --game "D:\Nova\Phantasy Star Nova (Japan).pkg" --update "D:\Nova\Nova update 1.05.pkg" --license "D:\Nova\work.bin" --firmware "D:\Nova\PSVUPDAT.PUP"
"Setup Phantasy Star Nova.exe" --game "D:\Nova\Nova both packages.zip" --license "D:\Nova\work.bin" --firmware "D:\Nova\PSVUPDAT.PUP"
```

Add `--font` if the font is not in `localization\fonts`. Extracted game folders (`--game` with `app\PCSG00351` and `patch\PCSG00351` inside, or a `--game` folder and an `--update` folder) still work from the command line, and a PKG can be mixed with a folder.

Windows or your antivirus may ask about the program you just built, because it was made on your PC and is not signed. Allow it. If the game does not start because a file went missing or was quarantined, restore or allow the file and run setup again. Setup rebuilds anything that is gone.

## Playing

The first launch uses English at 4× internal resolution and a 60 FPS target. It starts with a card that explains how touch input works on a PC. Press **Esc** to skip it. Press **F10** at any time to open the overlay, where you can change the controls, resolution, frame rate and language.

**Keyboard and mouse** (change them in F10 → Controls)

| Action | Key |
| --- | --- |
| Start / Select | Enter / Tab |
| Confirm (Circle) / Cancel (Cross) | C / Space |
| Square / Triangle | F / E |
| L / R | Q / R (or the right / left mouse button) |
| Move | W A S D |
| D-pad | Arrow keys |
| Camera | Mouse |
| Overlay | F10 |

**Controller**: plug in an Xbox-style pad at any time. The default **Auto** input mode follows the device you used last, so you can swap between controller and keyboard and mouse without changing a setting. In the game, **B / Circle** confirms and **A / Cross** cancels, as in the original Japanese game. The PC save and load picker is the opposite: **A / Cross** selects and **B / Circle** goes back. The left and right triggers act as L and R. The left stick moves and the right stick looks.

**Character names** can be typed on the keyboard, or entered with the controller on the on-screen grid.

## Saves, settings and logs

Everything that is yours lives in **`NovaData\Player`** inside the release folder:

| What | Where |
| --- | --- |
| Saves | `NovaData\Player\savedata0` |
| Save backups and deleted saves | `NovaData\Player\save_backups`, `NovaData\Player\deleted_saves` |
| Settings | `NovaData\Player\settings.ini` |
| Graphics debug captures (F12) | `NovaData\Player\captures` |
| Last two game logs | `NovaData\Player\session.log`, `NovaData\Player\session.prev.log` |
| What happened at each game start and exit | `NovaData\Player\launch.json`, `launch.prev.json` (no file paths in them) |
| Setup logs | `NovaData\installs\<build-id>\logs` (the **Open setup logs** button opens them) |
| The latest setup attempt | `NovaData\setup-attempt.json` |
| Support reports you exported | `NovaData\Reports` |
| Downloaded updates (checked, then unpacked) | `NovaData\Updates` |

Your game files are only read, never changed. The saves use the game's own save format. To move to another PC, copy the `NovaData\Player` folder.

## Resuming, updating and rolling back

Run **Setup Phantasy Star Nova.exe** again to resume an interrupted setup. Finished stages are skipped. Your saves and settings in `NovaData\Player` are kept, and your game files stay where you chose them.

**Updates inside the game folder.** When update checks are on in your release, Setup asks the update feed when it opens, and the game's launcher asks after you quit normally, **at most once a day** between them. The **Updates** panel in Setup shows what a newer release changes before anything is downloaded: the version, the notes, the download size and how much has to be rebuilt:

| The update changes | Setup rebuilds | About |
| --- | --- | --- |
| English menus and dialogue | only the English text archive | a few minutes |
| English movie subtitles | only the English movie archive | about ten minutes |
| The game's engine | the game itself, from the game data already on your PC | about half an hour |

Nothing is installed until you click **Install update**, and the game has to be closed. The new build is made next to your working one and only switched on when it is complete and checked, so a stopped or failed update leaves the build you were playing untouched. **Check for updates** asks the feed again right away. With no connection the check fails quietly and the game starts as usual. Updates are signed: Setup checks the signature and every download's SHA-256 before it unpacks or runs anything, and ignores an older release than one it already took. Changes to Setup's own programs, the bundled Python or the build tools come only with a new release download: extract it over the old folder and run setup as before.

Setup keeps your **previous build** as well as the current one. If a new build misbehaves, close the game and click **Roll back** to go back to the earlier one (click it again to return). Your saves and settings are never touched. An update needs room for a second build on the release drive: Setup works out the figure (about 8 GB) and checks it before it downloads anything.

If update checks are off ("Update checks are off in this release"), the release you have does not point at a feed yet. Everything else works the same.

An update that only changes English text or movies needs your **font** again to rebuild it. If Setup cannot find it, it says so and leaves the installed game alone: choose your font file in the Font field and click **Install update** again. If your installed build was made by an earlier version of Setup, run **Build and install** once with your game files first; after that, updates reuse your build.

## If the game or setup has a problem: support reports

Click **Export support report** in Setup, at any time, even before the first successful install. The window also offers it when setup fails, and the game's launcher offers it when the game fails to start, crashes or closes abnormally (a normal quit stays quiet). Setup writes a ZIP to `NovaData\Reports` and shows where it is. **Nothing is sent anywhere**: you decide whether to share the file.

The report holds a readable summary (release and build numbers, Windows and graphics card, your graphics and input settings), what the latest setup attempt did and where it stopped, whether the game last ended normally, crashed or was interrupted, and short excerpts of the setup and game logs. It also says which build you can still play when an update failed. Your user name, folder paths, the names of the files you chose and any license values are replaced with markers such as `<path>`, and setup refuses to write a report that still contains them. It never holds saves, game files, packages, licenses, fonts, screenshots or memory dumps.

From a command prompt: `"Setup Phantasy Star Nova.exe" --export-report`.

## If setup stops

| Setup says | What to do |
| --- | --- |
| Only the base game was found | Choose the update PKG in **Update PKG**, or choose a ZIP that holds both packages. |
| The base game was not found | Choose the base-game PKG (version 1.00) in **Game PKG or ZIP**, or a ZIP that holds it. |
| A package is another game, an add-on, or reports another version | Use the Japanese base game 1.00 and update 1.05 for `PCSG00351`. The message names the file. |
| More than one package matches | Keep one base and one update. The message lists the files, including the names of the PKGs inside a ZIP. |
| A package is damaged or incomplete | Copy or download that file again. If it is inside a ZIP, make the ZIP again. |
| The ZIP is password protected, or uses a compression method setup cannot read | Make the ZIP again with Store or Deflate and no password. |
| The base package does not contain a game license | Choose your game's `work.bin` or `.rif` in **Game license**. |
| The license is for another game, or the wrong size | Choose the `work.bin` or `.rif` of *Phantasy Star Nova* (`PCSG00351`). |
| Importing a package failed | The package may be damaged, or the license may not belong to it. The message names the log. |
| A file differs from the supported game | Use the original, unmodified packages from your base game and update. |
| It cannot find the base game or the update in a folder (command line) | Choose the folder that contains `app\PCSG00351` and `patch\PCSG00351`, or choose the two folders separately. |
| Required files are missing or empty (folders) | Copy the listed files from your dump into the matching folder, then run setup again. |
| The firmware is not the supported file | Download `PSVUPDAT.PUP` for system software 3.74 from the PlayStation page above. |
| It needs a font | See step 1. |
| Not enough free space | Free up space on the release drive and run setup again. |
| The update needs more free space | An update makes a second build before it switches. Free up the space it names. Nothing was downloaded and your build is untouched. |
| Close Phantasy Star Nova, then try again | An update or roll back only runs while the game is closed. |
| The update does not match the signed manifest, or its signature does not match | The download was damaged or changed. It was deleted and nothing was installed. Try again later; if it keeps happening, do not install it and send a support report. |
| The installed build was made before build records were kept | Run **Build and install** once with your game files. After that, updates reuse your build. |
| The English text font was not found | Choose your font file in the Font field (or copy one to `localization\fonts`), then click **Install update** again. |
| The new build is ready, but the game is running | Close the game and run setup again to switch to it. |
| A stage failed | The message names the log. **Open setup logs** shows the folder. |

## Credits and licenses

The project license is in `engine\LICENSE`. Third-party software is listed in `engine\THIRD_PARTY.md`, and the toolchain and FFmpeg notices are in `engine\release\TOOLCHAIN.md`. The font's attribution is in `localization\fonts\ATTRIBUTION.md`. *Phantasy Star Nova* is the property of its owners. This project does not include any game files.

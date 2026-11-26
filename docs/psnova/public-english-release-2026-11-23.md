# English localization for a bring-your-own-copy release

Audited November 23, 2026.

## Current player experience

A fresh distribution with an imported Japanese PCSG00351 1.05 copy plays the Japanese game. `vitarecomp dist` ships the tracked pack and runtime. The Nova localization builder under `dev/psnova` and the working data under `dump/psnova-l10n` are developer inputs. The localized CPK files on this machine are in the local game library. Together they occupy about 1.24 GB and include original game entries.

Import already links installed language folders into `recomp/fs/lang`. The runtime uses the chosen language's matching files and falls back to the original archive for files without overrides. This hook is the integration point for a player-facing English install.

## Proposed player workflow

1. Import the supported Japanese game and 1.05 update using the normal launcher workflow.
2. Select **Install English**. The launcher validates the region, update, and source archives, then builds the localized text/UI and movie overlays from the imported copy with the bundled language pack.
3. After validation, install both outputs under the local title's `lang/en` and register English in the language selector. The next launch uses English. Keep the English pack version with the generated outputs so repeat launches can reuse them.

The release payload should contain distributable English text, UI transformation instructions, subtitle cue text and timing, font assets cleared for distribution or an approved substitute, and the build code and its dependencies. Generate both CPK archives using the player's assets. The movie build uses the player's original movies, applies the existing subtitle cleaning and rendering recipes, and retains their audio. Stage and validate the generated files before switching the runtime to them. The installed game and saved progress sit outside the generated language directory.

## Release work

- Promote the English source data out of the local research tree. The current builders consume extracted RMDs and lookup data, event and caption tables, tutorial/UI recipes, cleaned movies and cue tables. Reconstruct the game-derived inputs locally and ship the release-ready English instructions and data. The current TSV began with fan rePatch wording and was revised over time. Review the source and redistribution status of the retained text and the font, or replace those inputs with distributable alternatives.
- Package the builder and pinned dependencies. The current movie scripts assume this machine's Windows FFmpeg path and developer Python environment. Exercise the shipped player environment using a fresh workspace with only the supported game inputs.
- Set a coverage gate for player-facing content. Applying the builder's language-selection logic to sheet v7 gives 24,427 accepted rows out of 25,484. There are 938 blank English cells and 119 English cells equivalent to their Japanese source. These are sheet counts. They include placeholders and do not establish campaign coverage. Review remaining reachable menus, dialogue, radio lines, tutorials, credits and movies before calling the locale complete. Track DLC separately.
- Run a clean-install test through the normal launcher. Verify both archives, check subtitle timing and text layout, launch in English, and confirm Japanese remains available. Include a campaign playthrough and representative replay tests for the movie and in-engine caption paths.

[Distribution code](../../pipeline/vitarecomp.py) · [Text builder](../../dev/psnova/rmdtext/build_l10n.py) · [Movie builder](../../dev/psnova/run_burn_subs.sh) · [Localization history](localization-notes.md)

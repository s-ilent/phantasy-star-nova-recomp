# Opening preview subtitles

English wording by me, including "Planet Wakua."

`OpeningDemo.mp4` plays after the warning and logos, before the title screen. The earlier music-only assessment in `text-render-faults.md` missed the Japanese radio announcement. Local transcription located the opening call at about 12.75 seconds and the end of the descent order at about 24.08 seconds.

| Movie time | English cue | Game capture |
|---|---|---|
| 12.75–19.90 s | Attention, Delta and all units.<br>Our ship will soon arrive at Planet Wakua. | `arrival.png` |
| 19.90–22.00 s | Begin deployment of the first exploration team. | `deployment.png` |
| 22.00–24.50 s | Initiate the descent sequence. | `descent.png` |

The English movie build takes its cue text and times from `dev/psnova/subs/OpeningDemo.json`. The renderer uses the existing proportional font at 28 px and centers the cues at y=496 on the 960 × 544 frames. The first cue spans two lines below the game's cyan lettering. The story-movie workflow still uses the frame and mask tables from subtitle detection.

## Installation and verification

The installed archive is `dump/decrypted/PCSG00351/lang/en/NOVA_FileList_Vita_movie.cpk`. The game resolves it through `recomp/fs/lang/en`. The replacer verified all 21 entries against their expected sources. It replaced only `OpeningDemo.mp4`. The MP4 contains all 4,196 frames at the source resolution. The source and encoded AAC packet payloads have the same SHA-256, `6e3ce2695f83c770294e54a5ffd14f8c5fe9da99c55139d68685f4bd3375171f`. The installed archive's SHA-256 is `7d2e72bcb9af3bcb64372407fbb5276913ef83b41d1715443afc889694ffc84b`.

The standard launcher route, `pipeline/vitarecomp.py run PCSG00351`, used English with no skip input. Game frames 1980, 2250 and 2400 show the cues in order. Game frame 2520 shows the scene after the cues clear. The PNGs and session log are under `dump/psnova-l10n/opening_codex_20261121/ingame`.

The original English archive is preserved under `dump/psnova-l10n/opening_codex_20261121/NOVA_FileList_Vita_movie.before-codex-opening.cpk`. To roll back, close the game and copy that backup over the installed English archive. To reproduce the encode, use the opening step in `dev/psnova/run_burn_subs.sh`. For a one-entry update, use `dev/psnova/cpk_replace.py` with the current English archive as its base.

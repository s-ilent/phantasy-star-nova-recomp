# Nova HUD sharpness, 2026-11-22


## What the capture shows

Replayed `frame_117190.vfc` through Windows `build/gfxreplay.exe` with `RECOMP_GFX=gpu`, `RECOMP_RENDER_SCALE=4`, `RECOMP_REPLAY_KEEP_TARGETS=1`, `RECOMP_SRGB=1` and `RECOMP_GPU_DEPTH_CLIP=1`. `RECOMP_GPU_DUMP_PRESENT` produced three 3840 × 2176 images. The last image shows the original Kisara notice, party bars, and minimap. The blur is already visible in the GPU present surface before the window's final scaling and post-processing. The ordinary replay PPM is the 960 × 544 guest readback.

The capture's HUD draw binds `UI_Field.aif` from the update at `0x1fc40040`. The captured BC2 bytes match the decoded asset's source file exactly. Its 1024 × 512 atlas contains many icons about 16–20 pixels wide. The English message `msg_261211.rmd` from the active language archive has a separate 256 × 128 BC2 atlas at `0x1fc35fe0`. Its bytes also match exactly. The localized message uses the supplied font drawn at 18 px into 21 px-tall strips.

## Matched-frame tests

The tests redirected the matching texture descriptors in an isolated copy of the capture. Both retained the original game draw, normalized UVs, placement, and 4× frame render scale. The comparison PNGs show 1920 × 1088-equivalent crops made by halving the GPU present image with a box filter.

- **HUD art.** Resampled `UI_Field.aif` to 2048 × 1024 with Lanczos and re-encoded BC2. The test changed 69 bindings across three frames. The bars and number edges changed slightly. The source icons still looked soft.
- **Text.** Re-rasterized both lines of the Kisara message directly from the configured font file at 36 and 72 px. Reused the glyph rectangles and original line advances to preserve the on-screen layout. The test changed three bindings across three frames. The candidate RMDs reparse with the same tokens and glyph records. Both variants sharpened the lettering visibly. In both cases all changed pixels landed in the text region `(1236, 206, 2187, 432)` of the 3840 × 2176 output (exclusive end coordinates). The original BC2 payload is 32 KiB, the 2× test is 128 KiB, and the 4× test is 512 KiB.

The [HUD comparison](<C:/Users/<user>/.codex/visualizations/2026/11/18/01a1ef68-356c-71b2-8aaf-9ee9791a4f22/nova-hud-atlas-comparison.png>) and [text comparison](<C:/Users/<user>/.codex/visualizations/2026/11/18/01a1ef68-356c-71b2-8aaf-9ee9791a4f22/nova-hud-text-comparison.png>) document the visual results. The local scripts are [the atlas replay test](<C:/Users/<user>/.codex/visualizations/2026/11/18/01a1ef68-356c-71b2-8aaf-9ee9791a4f22/nova-hud-atlas-test.py>) and [the text replay test](<C:/Users/<user>/.codex/visualizations/2026/11/18/01a1ef68-356c-71b2-8aaf-9ee9791a4f22/nova-hud-text-test.py>). Run either with the project virtual environment from the repository root. The text test accepts `2` or `4` and uses the matching message extracted from the active archive in that work folder.

## Integration status

These are replay prototypes. The installed game, active language archive, settings, and saves received no changes. A live test still needs to check the guest RMD loader's acceptance of the larger dimensions, message memory use, and frame-time cost. A 2× atlas is a reasonable first live candidate for English text. Redrawing selected artwork at higher resolution is a separate job. Movie subtitles are outside this test.

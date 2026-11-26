# Redrawing Japanese inside UI textures (2026-11-19)

Japanese drawn as pictures in the game's UI textures (`.aif`) is replaced per language by redrawing labels from a
**spec** (one JSON per texture) with `dev/psnova/uitex/apply_spec.py`. Research: `docs/psnova/ui-textures-research.md`.

## Inputs

- Original textures: `dump/psnova-l10n/scratch/research/patch/<name>.aif` (Sega's 1.05 update copy: the one the game
  uses when it exists) else `dump/psnova-l10n/scratch/research/base/<name>.aif`. Rendered PNGs of every texture:
  `dump/psnova-l10n/scratch/research/uitex/png/{patch,base}/<name>.png` (pixel coordinates = texture coordinates).
- Fonts (`dev/psnova/fonts.json`): `ui_english` (the supplied font, my choice) for English, `ui_arabic` (Segoe UI Bold)
  for Arabic; Arabic is shaped and ordered with `dev/psnova/rmdtext/arabic.py` `to_display()` and drawn with Pillow's
  BASIC layout engine (as the encoder does).
- Format: same 0x1e0-byte header as the message atlases; format byte at 0xa0 (0x12 = DXT3 for all UI textures),
  W/H at 0xa8/0xaa, blocks in Vita Morton order (`dev/psnova/rmdtext/rmdlib._perm`), texture ID 0x91-0x93 (keep it).
  Decoder/encoder starting points: `dev/psnova/uitex/aiftex.py`, `aif_encode_test.py`, `poc_redraw_guide.py`.

## Spec file: `dump/psnova-l10n/uitex/specs/<texture name without .aif>.json`

```json
{
  "texture": "tex_nova_ui_common.aif",
  "archive": "patch",
  "note": "free text",
  "labels": [
    {
      "box": [925, 636, 1024, 657],
      "jp": "カメラ初期化",
      "en": "Reset Camera",
      "ar": "إعادة ضبط الكاميرا",
      "clear": "transparent",
      "align": "right",
      "color": [255, 255, 255],
      "outline": [0, 0, 0],
      "outline_px": 1,
      "size": null,
      "valign": "center"
    }
  ]
}
```

- `box`: [x0, y0, x1, y1) in texture pixels: the whole area the Japanese occupied (the replacement must stay inside it:
  the game's layout cells crop to it).
- `en` / `ar`: the replacement text ("" = only erase the Japanese, draw nothing). Use "\n" for two lines if needed.
- `clear`: how the Japanese is removed before drawing:
  - `transparent`: alpha 0 in the box (sprite sheets: banners, labels, button guide, chapter word pieces);
  - `inpaint`: the text pixels (bright/saturated strokes differing from the local background) are removed by
    inpainting from the surroundings (screenshots: callout labels, Japanese menu rows inside tutorial pictures);
  - `fill`: fill the box with `fill_color` [r,g,b,a] (flat panels);
  - `keep`: nothing removed (draw over).
- `color`, `outline`, `outline_px`: text colour and an optional outline (sample them from the Japanese text: white, the
  cyan of the banners, red callouts with white outline...). `glow`: optional [r,g,b] soft glow like the banners.
- `size`: font size in px, or null = the largest that fits the box (width and height); `align`: left/center/right;
  `valign`: top/center/bottom. Arabic labels: align right when the Japanese was left-aligned, unless the box is centred.
- A label whose Japanese should simply disappear in a language: set that language's text to "".

## Output

`apply_spec.py <spec.json> <lang en|ar> <out dir>` -> `<out dir>/<texture>.aif` (same header, same size, same texture
ID, DXT3 with colour) and `<out dir>/preview/<texture>.png` + a before/after strip. `apply_all.sh` runs every spec for
both languages into `dump/psnova-l10n/uitex/out/{en,ar}/`; `build_l10n.py --extra-dir dump/psnova-l10n/uitex/out/<lang>`
puts them into that language's archive.

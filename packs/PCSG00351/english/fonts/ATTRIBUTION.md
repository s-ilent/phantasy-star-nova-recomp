# The English font

The project ships one font as its default: **K2D Medium** (`K2D-Medium.ttf`), from
[the K2D Project Authors](https://github.com/cadsondemak/K2D), under the **SIL Open Font License 1.1**. The licence
text is beside it in `OFL-K2D.txt`; the font may be used, changed and redistributed under that licence. The English
text, UI lettering and movie subtitles are drawn with it, so a build needs no font of your own.

Any other font works too, and is used in its place:

1. Copy a `.ttf` or `.otf` into this folder (`packs/PCSG00351/english/fonts/`), or keep it anywhere and name it with
   `--font` or `RECOMP_ENGLISH_FONT`.
2. Run `vitarecomp localize PCSG00351`, or add the game as the README describes: the English is then built on its own.

Git ignores every font here except the shipped default, so your own is never committed and never leaves your PC. The
font's own metrics decide the spacing, so a wider or taller font may crowd a box; `text/english_layout.py`, the layout
check the builders run, reports what the result actually did. What the font draws stays in your `dump` folder.

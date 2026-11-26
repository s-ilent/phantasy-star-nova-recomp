"""English release adapter for the project RMD encoder."""
import hashlib, re, struct
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from rmdlib import Rmd, LOCAL_BASE
import rmdwrite
from english_layout import CAPTION_CELL, WIDTH_PX, reflow
from glyph_slicing import letter_slice_spans

BASE_LATIN = 18        # the game's Latin glyphs stand on row ~18
PARAM_LEN = {0x8081: 1, 0x8099: 1, 0x8094: 2}
TAG = re.compile(r'\{ruby:([^}]*)\}|\{/ruby\}|\{end\}|\{/color\}|\{([0-9a-f]{4})(?::([0-9a-f]*))?\}|\n|.', re.S)
class Encoder:
    """Encode translated text as game-compatible message glyph atlases."""

    def __init__(self, font_path, fallback_font_path, settings, code_of, pic_of, charset):
        self.font_path = font_path
        self.fallback = set(settings['fallback'])
        self.size = settings['size']
        self.english_atlas_scale = 1
        self.code_of = code_of
        self.pic_of = pic_of
        self.font = ImageFont.truetype(fallback_font_path, 16, layout_engine=ImageFont.Layout.BASIC)
        self.basic = [record[0] for record in Rmd(charset).recs]
        self.latin = ImageFont.truetype(font_path, self.size, layout_engine=ImageFont.Layout.BASIC)
        self.latin_base = settings['baseline']

    # Use the same runs for width measurement and rendering.
    def _latin_runs(self, items):
        run = []
        for item in items:
            if (self.latin is not None and item[0] == 'ch' and ord(item[1]) < 0x250
                    and item[1] not in self.fallback and self._latin_available(item[1])):
                run.append(item[1])
                continue
            if run:
                yield ('latin', ''.join(run))
                run.clear()
            yield item
        if run:
            yield ('latin', ''.join(run))

    def _latin_words(self, items):
        """English runs -> one glyph picture per word with the spaces after it (the game draws at most 128 glyphs per
        message: one picture per letter cut long pages off after 128 characters, seen in the game 2026-11-19).
        Characters the font lacks or fonts.json's game_english "fallback" lists keep the game's own letter."""
        return [('pic', 'R:' + x[1], self.latin_run(x[1])) if x[0] == 'latin' else x
                for x in self._latin_runs(items)]

    # Cache font work during line planning.
    @lru_cache(maxsize=1024)
    def _latin_available(self, ch):
        return ch == ' ' or bool(self.latin.getmask(ch).getbbox())

    @lru_cache(maxsize=32768)
    def _latin_geometry(self, s):
        advance = self.latin.getlength(s)
        left, _, right, _ = self.latin.getbbox(s, anchor='ls') if s.strip() else (0, 0, 0, 0)
        origin = max(0, -int(np.floor(left)))
        return origin, max(1, int(np.ceil(max(advance, right))) + origin)

    def latin_run(self, s):
        """a run of English (any width) drawn with the game_english font: (alpha 21 x W, advance, class 10); cut into
        glyph-sized slices by _slices()"""
        f = self.latin
        x0, W = self._latin_geometry(s)
        im = Image.new('L', (W + 2, 21), 0)
        if s.strip():
            ImageDraw.Draw(im).text((x0, self.latin_base), s, fill=255, font=f, anchor='ls')
        glyph = (np.array(im)[:, :W], W, 10)
        if self.english_atlas_scale == 1:
            return glyph
        return (*glyph, self._scaled_latin_run(s, W))

    # Draw the full run before slicing to preserve kerning
    # and keep letter fragments aligned across cell boundaries.
    @lru_cache(maxsize=32)
    def _scaled_latin_font(self, size):
        return self.latin.font_variant(size=size * self.english_atlas_scale)

    def _scaled_latin_run(self, text, logical_width):
        scale = self.english_atlas_scale
        if not text.strip():
            return np.zeros((21 * scale, logical_width * scale), dtype=np.uint8)
        font = self._scaled_latin_font(self.latin.size)
        left, _, right, _ = font.getbbox(text, anchor='ls')
        origin = max(0, -left)
        width = max(1, int(np.ceil(max(font.getlength(text), right))) + origin)
        image = Image.new('L', (width, 21 * scale))
        ImageDraw.Draw(image).text((origin, self.latin_base * scale), text, fill=255, font=font, anchor='ls')
        return np.asarray(image.resize((logical_width * scale, 21 * scale), Image.Resampling.LANCZOS))

    def english_width(self, items, caption=False):
        """Measure original glyph advances and custom runs in game pixels."""
        total = 0
        for item in self._latin_runs(items):
            kind = item[0]
            if kind == 'latin':
                width = self._latin_geometry(item[1])[1]
                total += rmdwrite.roundup(width, CAPTION_CELL) if caption else width
            elif kind == 'ch':
                total += CAPTION_CELL if caption else self._character_width(item[1])
            elif kind == 'ctl':
                # Inline button icons and value substitutions occupy visible space.
                total += {0x8099: 24, 0x8094: 48}.get(item[1], 0)
        return total

    def _character_width(self, char):
        code = self.code_of.get(char)
        if code is None:
            return self.picture(char)[1]
        index = ((code & 0x7f) | ((code >> 8) << 7)) - 1
        return self.basic[index]

    def _caption_cells(self, items):
        # Keep the run intact across words. Only the last cell of the run
        # receives transparent padding, so there is no extra interword space.
        for item in self._latin_runs(items):
            if item[0] == 'latin':
                glyph = self.latin_run(item[1])
            elif item[0] == 'ch' and item[1] not in self.code_of:
                glyph = self.picture(item[1])
            else:
                yield item
                continue
            image = glyph[0]
            scale = self.english_atlas_scale
            for start in range(0, image.shape[1], CAPTION_CELL):
                piece = image[:, start:start + CAPTION_CELL]
                cell = np.zeros((21, CAPTION_CELL), dtype=np.uint8)
                cell[:piece.shape[0], :piece.shape[1]] = piece
                key = 'caption:' + hashlib.sha1(cell.tobytes()).hexdigest()
                cell_glyph = (cell, CAPTION_CELL, 10)
                if len(glyph) == 4:
                    high_piece = glyph[3][:, start * scale:(start + CAPTION_CELL) * scale]
                    high_cell = np.zeros((21 * scale, CAPTION_CELL * scale), dtype=np.uint8)
                    high_cell[:, :high_piece.shape[1]] = high_piece
                    cell_glyph = (*cell_glyph, high_cell)
                yield ('pic', key, cell_glyph)

    def _slices(self, items: list[tuple], maxw: int) -> list[tuple]:
        """Split pictures into bounded glyphs, keeping Latin edges between letters.

        Render the run whole to preserve kerning, then choose character boundaries:
        independently filtered quads and their outlines expose cuts inside letters.
        Other pictures retain uniform slicing; fixed caption cells use their own path.
        """
        out = []
        for x in items:
            if x[0] != 'pic' or x[2][0].shape[1] <= maxw:
                out.append(x); continue
            glyph = x[2]
            a = glyph[0]; W = a.shape[1]
            if isinstance(x[1], str) and x[1].startswith('R:'):
                text = x[1][2:]
                origin, _ = self._latin_geometry(text)
                spans = letter_slice_spans(self.latin, text, origin, W, maxw)
            else:
                n = -(-W // maxw)
                sw = -(-W // n)
                spans = [(k, min(k + sw, W)) for k in range(0, W, sw)]
            for k, end in spans:
                piece = a[:, k:end]
                key = 's:' + hashlib.sha1(bytes(piece.shape) + piece.tobytes()).hexdigest()[:16]
                sliced = (piece.copy(), piece.shape[1], 10)
                if len(glyph) == 4:
                    scale = self.english_atlas_scale
                    sliced = (*sliced, glyph[3][:, k * scale:end * scale].copy())
                out.append(('pic', key, sliced))
        return out

    def draw(self, s, baseline):
        """draw a string (already in display order) -> (alpha 21xW, cut positions per character). The picture covers the
        whole ink (nothing clipped at either end); cuts follow the font's advances."""
        f = self.font
        adv = [f.getlength(s[:i]) for i in range(len(s) + 1)]
        l, t, r, b = f.getbbox(s, anchor='ls')
        x0 = max(0, -int(np.floor(l)))                         # ink left of the pen start
        W = max(1, int(np.ceil(max(adv[-1], r))) + x0)
        im = Image.new('L', (W + 2, 21), 0)
        ImageDraw.Draw(im).text((x0, baseline), s, fill=255, font=f, anchor='ls')
        a = np.array(im)[:, :W]
        cuts = [int(round(x)) + x0 for x in adv]
        cuts[0] = 0; cuts[-1] = W
        return a, cuts

    def picture(self, ch):
        if ch in self.pic_of:
            return self.pic_of[ch]
        a, _ = self.draw(ch, BASE_LATIN)
        return (a, min(255, a.shape[1]), 10)

    # ---------- text ----------
    def parse(self, text):
        """sheet cell -> items: ('ch', c) / ('nl',) / ('ruby', reading) / ('rend',) / ('ctl', code, hexparam) / ('end',)"""
        out = []
        for m in TAG.finditer(text):
            t = m.group(0)
            if m.group(1) is not None:
                out.append(('ruby', m.group(1)))
            elif t == '{/ruby}':
                out.append(('rend',))
            elif t in ('{end}', '{/color}'):   # 0x8082: colour back to white (not an end; {end} is the old name)
                out.append(('end',))
            elif m.group(2):
                code, prm = int(m.group(2), 16), m.group(3) or ''
                if code < 0x8000 or code in (0x8080, 0x8082, 0x8090, 0x8091):
                    raise ValueError('tag {%s} is not a control code to write this way' % m.group(2))
                if len(prm) != 2 * PARAM_LEN.get(code, 0) or (prm and not re.fullmatch('[0-9a-f]+', prm)):
                    raise ValueError('tag {%s:%s}: %d parameter bytes expected' % (m.group(2), prm, PARAM_LEN.get(code, 0)))
                out.append(('ctl', code, prm))
            elif t == '\n':
                out.append(('nl',))
            elif t == '{':
                raise ValueError('a "{" that is not a known tag near: %r' % text[max(0, m.start() - 10):m.start() + 20])
            else:
                out.append(('ch', t))
        return [x for x in out if x[0] not in ('ruby', 'rend')]

    # Uniformly reduce the font only when a message cannot
    # fit at the configured size, then restore it for the next message.
    def encode(self, msg_id, text, template=None, context=None):
        # Measure, reflow and rasterize with the same font instance.
        items = self.parse(text)
        original = self.latin
        try:
            if context in WIDTH_PX:
                caption = context == 'caption'
                limit = WIDTH_PX[context]
                size = self.size
                while True:
                    wrapped = reflow(items, lambda line: self.english_width(line, caption), context)
                    lines = [[]]
                    for item in wrapped:
                        if item[0] == 'nl':
                            lines.append([])
                        else:
                            lines[-1].append(item)
                    if all(self.english_width(line, caption) <= limit for line in lines):
                        items = wrapped
                        break
                    size -= 1
                    if size < 8:
                        raise ValueError('English message cannot fit without dropping text')
                    self.latin = ImageFont.truetype(self.font_path, size,
                                                    layout_engine=ImageFont.Layout.BASIC)
                    self._latin_geometry.cache_clear()
                    self._latin_available.cache_clear()
                if caption:
                    data = self._build(msg_id, self._caption_cells(items), template,
                                       atlas_scale=self.english_atlas_scale)
                    if self.last_drawn > 128:
                        raise ValueError('caption exceeds the 128-glyph limit')
                    return data
            return self._encode_items(msg_id, items, template)
        finally:
            if self.latin is not original:
                self.latin = original
                self._latin_geometry.cache_clear()
                self._latin_available.cache_clear()

    def _encode_items(self, msg_id, items, template):
        drawn = self._latin_words(items)
        # glyph-sized slices (21 px, the game's own glyph width); wider slices only when a message would pass the game's
        # 128 glyphs per message or not fit the largest atlas
        last = None
        for maxw in (21, 32, 48, 96, 255):
            try:
                data = self._build(msg_id, self._slices(drawn, maxw), template,
                                   atlas_scale=self.english_atlas_scale)
            except ValueError as e:
                if 'atlas' not in str(e):
                    raise
                last = e
                continue
            if self.last_drawn <= 128 or maxw == 255:
                return data
        raise last if last else ValueError('message does not fit')

    def _build(self, msg_id, items, template, atlas_scale=1):
        glyphs, gindex = [], {}
        tb = bytearray()
        lines = 1

        def own(key, pic):
            if key not in gindex:
                gindex[key] = len(glyphs); glyphs.append(pic)
            return LOCAL_BASE + gindex[key]

        def code_bytes(code):
            # own glyph i is game code 401 + i, written (0x80 | low 7 bits, rest); equals the u16 0x391 + i only below 111
            if code >= LOCAL_BASE:
                g = 401 + code - LOCAL_BASE
                return bytes((0x80 | (g & 0x7f), g >> 7))
            return struct.pack('<H', code)
        drawn = 0
        for it in items:
            k = it[0]
            if k == 'ch':
                c = it[1]
                code = self.code_of.get(c)
                if code is None:
                    code = own(('ch', c), self.picture(c))
                tb += code_bytes(code); drawn += 1
            elif k == 'pic':
                tb += code_bytes(own(('pic', it[1]), it[2])); drawn += 1
            elif k == 'nl':
                tb += b'\x80\x80'; lines += 1
            elif k == 'ctl':
                tb += struct.pack('<H', it[1]) + bytes.fromhex(it[2])
            elif k == 'end':
                tb += b'\x82\x80'
        self.last_drawn = drawn              # the game lays out and draws at most 128 glyphs per message (fn_817e8410)
        height = 21.0 + 20.0 * (lines - 1)
        box0 = 0.0
        src = None
        if template is not None:
            t = Rmd(template)
            box0 = t.box[0]
            tl = 1 + sum(1 for x in t.tokens() if x[0] == 'nl')
            height = t.box[1] + 20.0 * (lines - tl)                     # keep the original's value, adjusted by the line change
            src = template[t.hs:t.hs + 0x1e0]                           # its texture ID and per-file IDs (see rmdwrite.gxm_for)
        return rmdwrite.build_rmd(msg_id, bytes(tb), glyphs, box=(box0, height), gxm_src=src,
                                  atlas_scale=atlas_scale)

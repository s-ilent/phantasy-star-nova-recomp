"""Plan Latin bitmap slices at character boundaries without losing source pixels."""

from bisect import bisect_right
from functools import lru_cache

from PIL import ImageFont


@lru_cache(maxsize=1024)
def _advance(font: ImageFont.FreeTypeFont, character: str) -> float:
    """Return one BASIC-layout glyph advance, cached for repeated text."""
    return float(font.getlength(character))


@lru_cache(maxsize=8192)
def _kerning(font: ImageFont.FreeTypeFont, previous: str, character: str) -> float:
    """Return the BASIC-layout kerning adjustment between two glyphs."""
    return float(font.getlength(previous + character)) - _advance(font, previous) - _advance(
        font, character
    )


def letter_slice_spans(
    font: ImageFont.FreeTypeFont,
    text: str,
    origin: int,
    width: int,
    max_width: int,
) -> list[tuple[int, int]]:
    """Cover a rendered run with bounded slices, preferring character boundaries.

    Args:
        font: The same BASIC-layout font used to render the complete run.
        text: The rendered Latin text.
        origin: Horizontal padding for a negative left bearing.
        width: Complete bitmap width, including overhangs and trailing spaces.
        max_width: Maximum slice width in logical pixels.

    Returns:
        Contiguous half-open spans covering every source column exactly once.
        A glyph wider than max_width is split only when no boundary fits.

    Raises:
        ValueError: If width is negative or max_width is not positive.
    """
    if width < 0 or max_width <= 0:
        raise ValueError("width must be nonnegative and max_width must be positive")
    position = 0.0
    previous = ""
    cuts = set()
    # BASIC layout is glyph advances plus pair kerning. Reusing these measurements
    # avoids repeatedly shaping every prefix of long CFF-font messages.
    for character in text[:-1]:
        position += _advance(font, character)
        if previous:
            position += _kerning(font, previous, character)
        cut = round(position) + origin
        if 0 < cut < width:
            cuts.add(cut)
        previous = character
    boundaries = sorted(cuts | {width})
    spans = []
    start = 0
    while start < width:
        index = bisect_right(boundaries, start + max_width) - 1
        end = boundaries[index] if index >= 0 else start
        if end <= start:
            end = min(start + max_width, width)
        spans.append((start, end))
        start = end
    return spans

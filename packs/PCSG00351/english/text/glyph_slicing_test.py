"""Regression tests for Latin strip seams and unaffected bitmap paths."""

import unittest
from unittest.mock import MagicMock

import numpy as np

from encode_text import Encoder
from glyph_slicing import letter_slice_spans


def make_font(advance: int = 10, pairs: dict[str, float] | None = None) -> MagicMock:
    """Return a deterministic BASIC-layout font with optional pair kerning."""
    font = MagicMock()
    adjustments = pairs or {}

    def measure(text: str) -> float:
        """Measure glyph advances and adjacent-pair adjustments."""
        return len(text) * advance + sum(
            adjustments.get(text[i:i + 2], 0) for i in range(len(text) - 1)
        )

    font.getlength.side_effect = measure
    return font


class LetterSliceSpansTest(unittest.TestCase):
    """Check safe cuts, coverage, kerning, and oversize-glyph fallback."""

    def test_groups_whole_letters(self) -> None:
        """Choose measured letter ends rather than equal pixel strips."""
        self.assertEqual(
            letter_slice_spans(make_font(11), "ABC", 0, 33, 21),
            [(0, 11), (11, 22), (22, 33)],
        )

    def test_preserves_pair_kerning(self) -> None:
        """Use the same rounded prefix positions as BASIC font layout."""
        font = make_font(10, {"AV": -1, "VA": -1})
        self.assertEqual(letter_slice_spans(font, "AVA", 0, 28, 20), [(0, 19), (19, 28)])

    def test_includes_bearings_and_trailing_columns(self) -> None:
        """Keep all padding and overhang columns in the complete run."""
        self.assertEqual(
            letter_slice_spans(make_font(), "ABC", 2, 34, 21),
            [(0, 12), (12, 22), (22, 34)],
        )

    def test_splits_a_single_oversize_glyph(self) -> None:
        """Respect the size limit when no character boundary can fit."""
        self.assertEqual(
            letter_slice_spans(make_font(30), "W", 0, 30, 21), [(0, 21), (21, 30)]
        )

    def test_empty_bitmap_has_no_spans(self) -> None:
        """Handle an empty run without emitting zero-width glyphs."""
        self.assertEqual(letter_slice_spans(make_font(), "", 0, 0, 21), [])

    def test_rejects_invalid_dimensions(self) -> None:
        """Reject bounds that could otherwise cause a nonterminating loop."""
        for width, maximum in [(-1, 21), (10, 0), (10, -1)]:
            with self.subTest(width=width, maximum=maximum), self.assertRaises(ValueError):
                letter_slice_spans(make_font(), "A", 0, width, maximum)

    def test_reuses_font_measurements_for_long_runs(self) -> None:
        """Avoid measuring every growing prefix in long CFF-font messages."""
        font = make_font(10, {"AV": -1, "VA": -1})
        spans = letter_slice_spans(font, "AV" * 100, 0, 1801, 21)
        self.assertEqual(spans[-1][1], 1801)
        self.assertLessEqual(font.getlength.call_count, 4)


class EncoderSlicingTest(unittest.TestCase):
    """Check source-pixel preservation and non-target slicing paths."""

    def setUp(self) -> None:
        """Create only the encoder state needed by the strip operations."""
        self.encoder = Encoder.__new__(Encoder)
        self.encoder.latin = make_font(11)
        self.encoder._latin_geometry = MagicMock(return_value=(0, 33))
        self.encoder.english_atlas_scale = 1
        self.alpha = np.arange(21 * 33, dtype=np.uint16).reshape(21, 33).astype(np.uint8)

    def test_keeps_latin_letters_intact_without_losing_pixels(self) -> None:
        """Regress a 33-pixel run whose old 17-pixel strips cut its middle letter."""
        parts = self.encoder._slices([("pic", "R:ABC", (self.alpha, 33, 10))], 21)
        self.assertEqual([p[2][1] for p in parts], [11, 11, 11])
        np.testing.assert_array_equal(np.concatenate([p[2][0] for p in parts], axis=1), self.alpha)

    def test_preserves_non_latin_picture_slicing(self) -> None:
        """Retain the existing uniform widths for unrelated bitmap pictures."""
        parts = self.encoder._slices([("pic", "icon", (self.alpha, 33, 10))], 21)
        self.assertEqual([p[2][1] for p in parts], [17, 16])
        np.testing.assert_array_equal(np.concatenate([p[2][0] for p in parts], axis=1), self.alpha)

    def test_keeps_high_resolution_slices_aligned(self) -> None:
        """Apply identical logical boundaries to a doubled texture payload."""
        self.encoder.english_atlas_scale = 2
        high = self.alpha.repeat(2, axis=0).repeat(2, axis=1)
        parts = self.encoder._slices([("pic", "R:ABC", (self.alpha, 33, 10, high))], 21)
        np.testing.assert_array_equal(np.concatenate([p[2][3] for p in parts], axis=1), high)

    def test_caption_cells_remain_fixed_width(self) -> None:
        """Keep cinematic cell widths and their final transparent padding unchanged."""
        self.encoder._latin_runs = MagicMock(return_value=[("latin", "ABC")])
        self.encoder.latin_run = MagicMock(return_value=(self.alpha, 33, 10))
        parts = list(self.encoder._caption_cells([]))
        self.assertEqual([p[2][1] for p in parts], [21, 21])
        restored = np.concatenate([p[2][0] for p in parts], axis=1)
        np.testing.assert_array_equal(restored[:, :33], self.alpha)
        self.assertFalse(restored[:, 33:].any())


if __name__ == "__main__":
    unittest.main()

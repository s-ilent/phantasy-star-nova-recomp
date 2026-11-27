"""Native tests for the menu-only frame-count correction."""

import ctypes
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class MenuRepeatTest(unittest.TestCase):
    """Exercise the production C hook without game files or a GPU."""

    @classmethod
    def setUpClass(cls) -> None:
        """Compile the hook with stubs for the two display settings it reads."""
        compiler = (ROOT / "toolchain/llvm-mingw/bin/x86_64-w64-mingw32-clang.exe"
                    if os.name == "nt" else shutil.which("cc"))
        if not compiler or not Path(compiler).is_file():
            raise unittest.SkipTest("C compiler unavailable")
        cls.library = None
        cls.temporary = tempfile.TemporaryDirectory(prefix="psnova-menu-repeat-")
        cls.addClassCleanup(cls.cleanup)
        folder = Path(cls.temporary.name)
        (folder / "hooks.h").write_text(
            "#include <stdint.h>\ntypedef struct { uint32_t r[16]; } Cpu;\n"
            "int display_vblank_hz(void);\nint display_frame_rate_60(void);\n")
        bridge = folder / "bridge.c"
        bridge.write_text('''#include "hooks.h"
#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif
void recomp_ihook_psn_menu_repeat_frames(Cpu *, int);
void recomp_ihook_psn_menu_repeat_interval(Cpu *, int);
static int hz, unlocked;
int display_vblank_hz(void) { return hz; }
int display_frame_rate_60(void) { return unlocked; }
EXPORT uint32_t repeat_value(uint32_t frames, int rate, int unlock, int reg, int interval) {
    Cpu c = {{0}}; c.r[0] = frames; hz = rate; unlocked = unlock;
    if (interval) recomp_ihook_psn_menu_repeat_interval(&c, reg);
    else recomp_ihook_psn_menu_repeat_frames(&c, reg);
    return c.r[0];
}
EXPORT int registers_unchanged(void) {
    Cpu c; for (unsigned i = 0; i < 16; ++i) c.r[i] = 100 + i;
    hz = 120; unlocked = 1; recomp_ihook_psn_menu_repeat_frames(&c, 0);
    for (unsigned i = 1; i < 16; ++i) if (c.r[i] != 100 + i) return 0;
    return 1;
}
''')
        output = folder / ("repeat.dll" if os.name == "nt" else "repeat.so")
        subprocess.run([str(compiler), "-shared", "-O2", "-I", str(folder),
                        str(ROOT / "packs/PCSG00351/input_repeat.c"), str(bridge),
                        "-o", str(output)], check=True, capture_output=True)
        cls.library = ctypes.CDLL(str(output))
        cls.library.repeat_value.argtypes = [ctypes.c_uint32] + [ctypes.c_int] * 4
        cls.library.repeat_value.restype = ctypes.c_uint32
        cls.library.registers_unchanged.restype = ctypes.c_int

    @classmethod
    def cleanup(cls) -> None:
        """Unload the test DLL before removing the bounded temporary directory."""
        if cls.library is not None and os.name == "nt":
            import _ctypes
            _ctypes.FreeLibrary(cls.library._handle)
            cls.library = None
        assert Path(cls.temporary.name).resolve().is_relative_to(
            Path(tempfile.gettempdir()).resolve())
        cls.temporary.cleanup()

    def value(self, frames: int, hz: int, unlocked: int = 1, reg: int = 0, interval: int = 0) -> int:
        """Read a menu threshold after the production instruction hook."""
        return self.library.repeat_value(frames, hz, unlocked, reg, interval)

    def test_original_30_fps_is_unchanged(self) -> None:
        """Preserve every byte-valued threshold at the original frame rate."""
        for count in range(256):
            self.assertEqual(self.value(count, 60, 0), count)

    def test_120_fps_repeat_delay_and_interval(self) -> None:
        """Regress four-times-faster menu navigation with the 120 Hz unlock."""
        self.assertEqual(self.value(8, 120), 32)
        self.assertEqual(self.value(3, 120, interval=1), 15)

    def test_60_fps_is_normalized_too(self) -> None:
        """Preserve console menu timing at the usual 60 fps unlock."""
        self.assertEqual(self.value(8, 60), 16)

    def test_forced_grid_with_original_limiter(self) -> None:
        """Account for the two-edge limiter when the unlock is disabled."""
        self.assertEqual(self.value(8, 120, 0), 16)

    def test_threshold_wall_times_match(self) -> None:
        """Delay and repeat intervals remain equal across supported fast grids."""
        for hz in [60, 90, 120, 240, 480]:
            for count in [3, 8, 255]:
                self.assertAlmostEqual(self.value(count, hz) / hz, count / 30)

    def test_interval_accounts_for_the_repeat_callback(self) -> None:
        """The guest subtracts its interval instead of incrementing on a repeat."""
        for hz in [60, 90, 120, 240, 480]:
            for count in [0, 2, 3, 255]:
                self.assertAlmostEqual((self.value(count, hz, interval=1) + 1) / hz,
                                       (count + 1) / 30)
        for count in range(256):
            self.assertEqual(self.value(count, 60, 0, interval=1), count)

    def test_fractional_frames_round_up(self) -> None:
        """Avoid an early repeat when the grid ratio is not an integer."""
        self.assertEqual(self.value(3, 75), 8)

    def test_zero_and_lower_grids(self) -> None:
        """Leave zero thresholds and non-target low/invalid grid rates alone."""
        self.assertEqual(self.value(0, 120), 0)
        for hz in [-1, 0, 30]:
            self.assertEqual(self.value(8, hz), 8)

    def test_non_target_registers(self) -> None:
        """Change only r0 at the two declared instruction sites."""
        for reg in [-1, 1, 14, 15]:
            self.assertEqual(self.value(8, 120, reg=reg), 8)
        self.assertEqual(self.library.registers_unchanged(), 1)


if __name__ == "__main__":
    unittest.main()

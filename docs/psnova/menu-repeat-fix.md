# Menu navigation repeat at higher frame rates

The in-game navigation handler `fn_8190b9ee` uses a separate repeat counter from
`fn_81b19e9a` (the physical pad polling layer). Normalizing the physical pad clock
alone did not change the Settings menu's scrolling in a native GPU replay.

The menu handler receives press/held/release action callbacks and increments a
signed 16-bit counter for its six repeatable navigation actions. Its original
thresholds assume 30 presented frames per second. At 120 fps the delay and repeat
period therefore take one quarter of the original time.

`input_repeat.c` hooks only the two byte loads into r0:

- `0x8190bb4a`: initial delay, loaded from object +0x48.
- `0x8190bb56`: repeat interval, loaded from object +0x49.

The frame limiter waits two grid edges without the unlock and one with it, so the
scale is grid Hz /60 or grid Hz /30 respectively, bounded below by one. A repeat
subtracts the interval instead of incrementing the counter. Its actual period is
interval +1, so the scaled interval is ceil((interval +1) * scale) -1.

The hooks change the loaded registers, preserving byte configuration and all
press/release handling. Raw pad state, gameplay input, display timing and F10's
ImGui input path are unchanged. Both supported 1.05 pack variants declare the
hooks; the relinked variant is address-checked but has not been played with this fix.

Validation on 2026-11-26:

- Nine Python unittest cases compile and call the production C hooks through a
  small display/CPU stub. Original 30 fps, faster grids, rounding, interval +1,
  zero thresholds and non-target registers are covered.
- A local native harness executes the actual recompiled navigation function,
  including its original jump tables, with and without the hooks. Up and Down
  at 60/120/240 fps match original 30 fps counts, for 175 ms taps and one-second
  holds. With an 8/3 delay/interval fixture, a 175 ms tap at 120 fps changes from
  five selections to one; a one-second hold changes from 29 to seven. Releases
  reset the counter and the original byte configuration stays intact.
- A 2,500-frame native GPU Settings replay at 120 Hz shows a 32-frame initial
  delay followed by one repeat every 12 frames. A one-second Down hold makes
  nine selections; subsequent 175 ms Up and Down taps each move exactly one row.
  Local screenshots, measurements and installation hashes are under
  `dump/input-repeat-fix`; the pre-install executable and save/settings backup
  are in its `before-install` directory.

The generated handler was regenerated from the analyzed input and compared
byte-for-byte before adding hooks. Its only differences are the two emitted hook
calls. Temporary diagnostics and the unused pad-clock experiment were removed.

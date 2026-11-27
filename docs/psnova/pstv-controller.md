# Phantasy Star Nova: PS TV controller evidence and runtime support

## Guest input atlas

Audited installed variant: **1.05-maidump**, ELF SHA-256 `74e66d0bafc561f4ba4a763d9539e49833fe5b683c50e60af55745c7a5316f1c`. The image base is `0x82700000`, a `+0x01700000` relocation of the reference addresses. `pack.toml` records the same hash and relocation. The patch-layer wrapper `dump/decrypted/PCSG00351/patch0/eboot.bin` and `recomp/fs/app0/eboot.bin` have SHA-256 `C2E45100F1E5AD4566D74EE10606D7783B07664C2D39D654884ED07751A610F7`; the base app0 wrapper is a different executable.

| Guest site | Evidence | Input / action | Confidence |
|---|---|---|---|
| `fn_82c920de` (`fn_815920de` + `0x01700000`) at `0x82c920de` | Generated code calls `sceCtrlReadBufferPositive2` at `0x82c92100` with `r0=0`, `r1=sp+0x18`, `r2=1`. Its only direct caller found is `0x82c94680`. | Reads one 32-byte `SceCtrlData` record on port 0. It tests `buttons & 0x100`, `0x200`, `0x2`, `0x4`, then maps those four states to internal action bits `0x1`, `0x2`, `0x4`, `0x8` (pressed/released state is updated in four object halfwords). | **A** for call, masks, and internal bits. **A** for button-to-action names from the original manual below. |
| `fn_8321ca18` | Generated caller sets port `0`, output `sp`, count `1`, then calls `sceCtrlPeekBufferPositive`. It is the only direct caller of this import found in generated game C. | Ordinary Aska engine controller input. | **A** for import, arguments and caller. Exact semantic consumers need a separate input-trace audit. |
| `sceTouchPeek`, `sceTouchGetPanelInfo`, `sceTouchSetSamplingState` | Present in the ELF import inventory. | Touch APIs remain part of the guest surface. Their presence is not a reason to remove touch emulation in other games. | **A** for imports; per-call Nova state not measured here. |

### Original PS TV controls

Local asset `dump/decrypted/PCSG00351/app0/sce_sys/manual/009.png` is the manual's printed page 10. Its PS Vita TV section states that the game can be played without the touch pointer, and that in-game touch actions are done with buttons. The table says:

- **L3:** toggle the radar-map display. Press duration selects the two-stage map display.
- **R3:** switch viewpoint mode between normal and over-the-shoulder.
- **L2:** select a sub-palette entry.
- **R2:** confirm the selected sub-palette entry.
- Before play, disable the PS Vita TV system's touch-pointer feature.

This is direct title documentation, not inferred from an emulator's behavior. SEGA's [FAQ](https://faq.sega.jp/hc/ja/articles/360018923713) independently confirms PS Vita TV support and button substitution for touch operations.

## What the audit does not establish

- No `sceKernelGetModel`, `sceKernelIsPSVitaTV`, controller-enumeration, or multi-controller capability imports were found in the ELF's NID import table. The identified PS TV action poller does not query these APIs; it consumes the extended button masks on port 0.
- No distinct in-game PS TV tutorial text or glyph set has been confirmed beyond the manual page.
- The owner reports that the manual PS TV gameplay test works perfectly. No step-by-step test log or physical controller model was recorded in this repository.
- The headless save-based route attempt timed out before a slot was selected and before its scripted input window. Its report confirms the live save was unchanged. It is not a successful route test.
- `RECOMP_INPUT` is injected after API conversion and does not, by itself, prove physical host input mapping. `RECOMP_CTRL_PHYSICAL` is a separate physical-control test seam before format conversion.
- A generic host gamepad reported as DS3 in the 16-byte controller-port-info structure is a compatibility classification, not proof that the host device is physically a DS3. SDL identifies PS4/PS5 devices as DS4; other external gamepads currently use the DS3 class because the Vita ABI exposes no generic class in the target contract.
- Nativ and Vita3K disagree on some unsupported/disconnected port details. This patch keeps the existing title-compatible port-1 polling behavior and limits port-info claims to the primary virtual controller and one actually connected host pad. It does not fabricate extra players.

## Runtime mapping contract

For PS TV input, conventional bumper/trigger mapping is fixed regardless of the handheld `shoulder_buttons` preference:

| Physical input | Legacy format | Extended format |
|---|---:|---:|
| L1 / LB | `0x100` | `0x400` |
| R1 / RB | `0x200` | `0x800` |
| L2 / LT | — | `0x100` |
| R2 / RT | — | `0x200` |
| L3 | — | `0x2` |
| R3 | — | `0x4` |

The existing shoulder preference continues to affect the handheld layout only. Ordinary buttons and sticks retain their existing encoding. Extended format selection is independent of port: Nova's port-0 `Positive2` read receives the PS TV mapping when the selected profile is PS TV, while Standard mode retains the handheld mapping. The 32-byte `SceCtrlData` stride is asserted by the host-side mapping test.

The F10 Controller layout selector is exposed for Nova through the existing `controller_layout` game setting. Explicit Standard and PS TV modes resolve before guest startup. `Ask` in headless mode deterministically selects Standard; in windowed mode the existing choice card remains available. Runtime read handlers do not intercept or disable SceTouch globally. PS TV keyboard defaults add independently rebindable `1=L2`, `2=R2`, `3=L3`, and `4=R3`, preserving prior bindings.

## Verification status

The Windows runtime build passed and the pure mapping/ABI test passed **33 checks, 0 failures** on 2026-11-27. The owner reports that manual PS TV gameplay works perfectly. The isolated route did not complete, and production SDL virtual-controller and handheld-regression tests remain unverified. See `runtime/tests/README.md` for the host-side mapping test.
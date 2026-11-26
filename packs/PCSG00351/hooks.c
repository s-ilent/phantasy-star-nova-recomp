/*
 * Phantasy Star Nova (PCSG00351): its hooks, built into this game alone (runtime/build.py RECOMP_PACK_SOURCES);
 * packs/PCSG00351/pack.toml's HOOKS= / IHOOKS= place them (1.05 addresses). What every game's hooks share is
 * runtime/core/hooks.h.
 */
#include "hooks.h"

/*
 * Diagnostics for the input thread (RECOMP_PSN_INPUT_TRACE=1), 2026-11-18. The game's controller is read by an Aska
 * worker whose job, fn_81a1f276, loops "while not quit: for each of 3 device slots (+0x18): slot->update() (vtable
 * +0x24); sleep 8 ms". The pad device's update (fn_81b1cd18 -> fn_81b1c958) reads sceCtrlPeekBufferPositive -- yet in
 * play that read happened once, at frame 0, and buttons never reached the game. psn_input_slot (after the slot load at
 * 0x81a1f284): which device each slot holds, as the loop sees it; psn_pad_update (fn_81b1c958's entry): how often the
 * pad's update runs and with what lock state.
 */
static int psn_trace(void) { static int v = -1; if (v < 0) v = getenv("RECOMP_PSN_INPUT_TRACE") != 0; return v; }
void recomp_ihook_psn_input_slot(Cpu *c, int reg) {
	if (!psn_trace()) return;
	static unsigned n;
	if (n++ < 24 || n % 2000 == 0) {
		uint32_t dev = c->r[0], vt = dev ? RD32(dev) : 0, upd = vt ? RD32(vt + 0x24) : 0;
		fprintf(stderr, "    psn input: pass %u slot %#x -> device %#x vtable %#x update %#x quit %u (frame %llu)\n",
		        n, c->r[4], dev, vt, upd, RD8(c->r[5] + 0x24), (unsigned long long)display_frames());
	}
}
void recomp_hook_psn_pad_update(Cpu *c) {
	if (!psn_trace()) return;
	static unsigned n;
	uint32_t o = c->r[0];
	if (n++ < 12 || n % 500 == 0)
		fprintf(stderr, "    psn pad update #%u: device %#x lock %#x waiters %#x (frame %llu)\n", n, o, o ? RD32(o + 4) : 0, o ? RD32(o + 8) : 0,
		        (unsigned long long)display_frames());
}

/*
 * 60 fps (2026-11-19; docs/psnova/60fps-sites.md, docs/psnova/frame-rate.md). The engine is built for 60: its vsync
 * object T = *0x82474314 is constructed with T+0xcc = 60 (fn_81a242bc), and the frame limiter fn_81a24692 waits
 * uidiv(60, T+0xcc) vblanks. One boot-time function, fn_8178c3e4, sets this game to 30 (`movs r1,#0x1e; str.w r1,
 * [r0,#0xcc]` at 0x8178c5f2) and its cloth/physics step 0x82474334 to 1/31 (0x3d042108; the data default is 0.016,
 * 0x3c83126f). Game time comes from measured vblanks (T+0x8c, 1/count, seconds), so nothing runs double speed.
 * psn_frame_rate, at the entry of the per-frame task fn_81a7756c (the limiter's only caller, at 0x81a775b6): with the
 * frame_rate setting at 60 it writes 60 and 0.016; switched back to 30, it restores the game's own 30 and 1/31. It reads
 * the setting every frame, so the F10 menu (or RECOMP_FRAME_RATE / RECOMP_FRAME_RATE_FROM) applies at once. At 30, until
 * a switch, it writes nothing: the game's own code runs untouched.
 */
static void psn_settings_trace(void);   /* below: the option record, under RECOMP_PSN_SETTINGS_TRACE */
void recomp_hook_psn_frame_rate(Cpu *c) {
	(void)c;
	static int last = 30;
	const int want = display_frame_rate_60() ? 60 : 30;
	/* The vsync object pointer and the cloth/physics step are the game's own data, so their addresses come from this
	 * build's GAME_ADDRS (hooks.h's game_addr) rather than from 1.05's numbers written here: a build that was re-linked
	 * moves code and data by different amounts, and as literals these addressed another build's image, which left 60 fps
	 * doing nothing (2026-11-27, pack.toml's ADDR_DATA_DELTA). */
	const uint32_t obj = game_addr("psn_vsync_object"), step = game_addr("psn_frame_step");
	if (!obj || !step) return;   /* not an address this build has: game_addr has said so once */
	{	/* RECOMP_PSN_FPS_TRACE=1: every 300th frame, what the game's clock measured for the frame before (T+0x8c vblanks, T+0xb0 seconds) */
		static int tr = -1; if (tr < 0) tr = getenv("RECOMP_PSN_FPS_TRACE") != 0;
		static unsigned n; const uint32_t t0 = RD32(obj);
		if (tr && t0 && n++ % 300 == 0) { uint32_t s = RD32(t0 + 0xb0); float f; memcpy(&f, &s, 4);
			fprintf(stderr, "    psn clock: frame %llu target %u fps, last frame %u vblanks = %.4f s\n", (unsigned long long)display_frames(), RD32(t0 + 0xcc), RD16(t0 + 0x8c), f); }
	}
	psn_settings_trace();
	if (want == 30 && last == 30) return;
	const uint32_t t = RD32(obj);
	if (!t) return;
	WR32(t + 0xcc, (uint32_t)want);
	static uint32_t step60 = 0;   /* RECOMP_PSN_60_STEP=<hex float bits>: the step written at 60 instead of 0.016 (a test switch: 0x3d042108 keeps the game's 1/31) */
	if (!step60) { const char *e = getenv("RECOMP_PSN_60_STEP"); step60 = e && *e ? (uint32_t)strtoul(e, 0, 16) : 0x3c83126fu; if (!step60) step60 = 0x3c83126fu; }
	/* The step is the seconds ONE VBLANK of this build's grid is worth, so the clock the game keeps from measured
	 * vblanks (the count at T+0x8c, the seconds at T+0xb0) stays real time at any grid rate: display_vblank_hz is 60
	 * unless the frame-rate setting asks for more, when the grid follows the panel and the game runs at its rate
	 * (its limiter waits uidiv(60, T+0xcc) vblanks: one a frame at 60 leaves 120 a second on a 120 Hz grid). */
	{
		const int hz = display_vblank_hz();
		if (want == 30) WR32(step, 0x3d042108u);   /* 1/31: the game's own 30 fps value, unchanged */
		else if (hz != 60) { union { float f; uint32_t u; } v; v.f = 1.0f / (float)hz; WR32(step, v.u); }
		else WR32(step, step60);
	}
	if (want != last) fprintf(stderr, "    psn frame rate: %d fps (frame %llu)\n", want, (unsigned long long)display_frames());
	last = want;
}

/*
 * The game's option record (2026-11-27). The save log names it: "save system.bin: 384 bytes at 0 from %#x" is the guest
 * address SceAppUtilSaveDataDataSave hands the runtime, and the record is written verbatim, so the file's offsets are
 * its offsets. The live run of values is at +0x15c, six 32-bit fields in the order the option screens list them:
 * camera (left/right) speed, camera (up/down) speed, BGM volume, SE volume, Voice volume, Movie volume (all 0..100).
 * A stale run sits at +0xa0 and does not follow a change. The camera wants its speed scaled by 30/fps, and the record
 * is the wrong place for that: the save writes it back to disk, so a runtime write would be saved, and the next start
 * would divide it again.
 *
 * RECOMP_PSN_SETTINGS_TRACE=1 reads the record once a second and, once, scans the game's heap for another word holding
 * the camera up/down speed. A copy the save never writes would be the safe place to scale; if there is none, the
 * camera's own read is, and that is what to look for next. RECOMP_PSN_SETTINGS=<hex> overrides the address.
 */
#define PSN_HEAP_LO 0x1031d000u   /* ASKA_HEAP, where the record and the game's objects live */
#define PSN_HEAP_HI 0x1c31d000u
static void psn_settings_trace(void) {
	static int on = -1; if (on < 0) on = getenv("RECOMP_PSN_SETTINGS_TRACE") != 0;
	if (!on) return;
	static uint32_t rec; static unsigned n;
	if (!rec) { const char *e = getenv("RECOMP_PSN_SETTINGS"); rec = e && *e ? (uint32_t)strtoul(e, 0, 0) : 0x14bc7f94u; }
	if (!rec) return;
	uint32_t camLR = RD32(rec + 0x15c), camUD = RD32(rec + 0x160), stale = RD32(rec + 0xa0);
	if (n++ % 60 == 0)
		fprintf(stderr, "    psn settings: rec %#x frame %llu: camLR %u camUD %u bgm %u se %u voice %u movie %u (stale run camLR %u)\n",
		        rec, (unsigned long long)display_frames(), camLR, camUD, RD32(rec + 0x164), RD32(rec + 0x168),
		        RD32(rec + 0x16c), RD32(rec + 0x170), stale);
	if (n != 1261 && n != 6001) return;
	{	/* Three fingerprints in one pass, because nothing holds the record's own address (that scan found no copy of it
		 * anywhere in the data segment or the low heap). (a) A float holding the camera up/down speed: if the game turns
		 * the option into a float for the camera, that copy is a unique word and the place to scale. (b) A word pointing
		 * a little below the record, the base of the object whose field the record is, which is what the game would hold
		 * instead. (c) The arena base the game was handed. Any of them in the data segment is a compile-time constant
		 * whose movw/movt halves name every user of the settings.
		 * The record itself cannot be scaled: its fields are integers 0..100 (1 and 99 read back as those integers, not as
		 * floats), so a 30/fps factor quantises, and at 120 Hz the factor 0.25 would round the operator's own 1 to 0. */
		static const struct { uint32_t lo, hi; const char *what; } where[] = {
			{ 0x83b80000u, 0x83c3c3a0u, "data" },
			{ 0x10000000u, 0x28000000u, "heap" },
		};
		uint32_t f99 = 0, near = 0, arena = 0, printed = 0;
		for (unsigned w = 0; w < sizeof where / sizeof where[0]; w++)
			for (uint32_t a = where[w].lo; a + 4 <= where[w].hi; a += 4) {
				uint32_t v = RD32(a);
				if (v == 0x42c60000u) {   /* 99.0f */
					f99++;
					if (printed++ < 30) fprintf(stderr, "    psn settings: a float %u.0 for the camera up/down speed at %#x (%s) frame %llu\n",
					                             camUD, a, where[w].what, (unsigned long long)display_frames());
				}
				if (v && v <= rec && rec - v < 0x40000u) {
					near++;
					if (printed++ < 30) fprintf(stderr, "    psn settings: %#x (%s) points %#x, %#x below the record (frame %llu)\n",
					                             a, where[w].what, v, rec - v, (unsigned long long)display_frames());
				}
				if (v == 0x1031d000u) {
					arena++;
					if (printed++ < 30) fprintf(stderr, "    psn settings: ASKA_HEAP's base named at %#x (%s) (frame %llu)\n",
					                             a, where[w].what, (unsigned long long)display_frames());
				}
			}
		fprintf(stderr, "    psn settings: %u floats for camUD, %u words point below the record, %u name ASKA_HEAP (frame %llu)\n",
		        f99, near, arena, (unsigned long long)display_frames());
	}
}

/*
 * The abort after "Start the Game" (2026-11-18): an Aska worker calls fn_81b2a8bc, a std::map/set insert (MS STL:
 * "if (size >= max_size) _Xlength_error"; max_size 0x071c71c6 = 36-byte nodes), on a tree whose size field (+8) reads
 * >= 0x071c71c6, so the game aborts. psn_tree_insert (its entry) prints the tree and its caller when the size is that
 * large -- which call site (lr), the caller's callee-saved registers (the object the tree belongs to) and the memory
 * around the tree -- then the native chain. Costs one guest read per insert; prints only on the bad one.
 */
void recomp_hook_psn_tree_insert(Cpu *c) {
	uint32_t t = c->r[0];
	if (!t || RD32(t + 8) < 0x071c71c6u) return;
	static int shown;
	if (shown++ >= 2) return;
	fprintf(stderr, "    psn tree insert: tree %#x head %#x size %#x  r1 %#x r2 %#x [sp+0]=%#x lr %#x (frame %llu)\n", t, RD32(t + 4),
	        RD32(t + 8), c->r[1], c->r[2], RD32(c->r[13]), c->r[14], (unsigned long long)display_frames());
	fprintf(stderr, "    psn tree insert: r4 %#x r5 %#x r6 %#x r7 %#x r8 %#x r9 %#x r10 %#x r11 %#x sp %#x\n", c->r[4], c->r[5], c->r[6],
	        c->r[7], c->r[8], c->r[9], c->r[10], c->r[11], c->r[13]);
	for (int k = -0x40; k < 0x40; k += 16)
		fprintf(stderr, "    psn tree insert: %08x: %08x %08x %08x %08x\n", t + k, RD32(t + k), RD32(t + k + 4), RD32(t + k + 8), RD32(t + k + 12));
	plat_backtrace(stderr);
}


/*
 * Arabic right alignment (localization session, 2026-11-19; docs/psnova/right-alignment-research.md). Every UI text box
 * has an alignment at box+0x94 (0 left, 1 centre, 2 right) that the line-placement routine fn_81905ae0 reads at
 * 0x81905b10 (x = 0 / (box - line) / 2 / box - line); most boxes have no Align in their .crbpj and stay left. Our encoder
 * starts every Arabic message with the control code 0x8095 (bytes 95 80), a no-op in all five text decoders.
 * psn_rtl_mark (entry of the message layouts fn_817e850e / fn_817e882e): remember, per text-output block (RD32(sp) =
 * box+0xa4), whether the message laid out there starts with 95 80 -- every layout rewrites it, so a box that later shows a
 * non-Arabic message is cleared. psn_rtl_align (after 0x81905b10 ldr r2,[r5,#0x94], r5 = the box): a marked box's
 * "left" becomes "right"; centred and right-aligned boxes are left alone; guest memory is never written.
 * Without the mark (Japanese / English text) nothing changes.
 */
#define PSN_RTL_N 2048
static uint32_t psn_rtl_key[PSN_RTL_N]; static volatile uint8_t psn_rtl_val[PSN_RTL_N];
static int psn_rtl_slot(uint32_t k, int add) {   /* open addressing; keys are box addresses (never 0) */
	unsigned h = (k >> 2) * 2654435761u % PSN_RTL_N;
	for (int i = 0; i < PSN_RTL_N; i++, h = (h + 1) % PSN_RTL_N) {
		uint32_t cur = __atomic_load_n(&psn_rtl_key[h], __ATOMIC_ACQUIRE);
		if (cur == k) return (int)h;
		if (!cur) {
			if (!add) return -1;
			uint32_t z = 0;
			if (__atomic_compare_exchange_n(&psn_rtl_key[h], &z, k, 0, __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE) || z == k) return (int)h;
		}
	}
	return -1;
}
void recomp_hook_psn_rtl_mark(Cpu *c) {
	uint32_t out = RD32(c->r[13]), obj = c->r[1];
	if (!out) return;
	uint32_t hdr = obj ? RD32(obj) : 0, base = obj ? RD32(obj + 8) : 0;
	uint32_t p = (hdr && base) ? base + RD32(hdr + 8) : 0;
	int rtl = p && RD8(p) == 0x95 && RD8(p + 1) == 0x80;
	int s = psn_rtl_slot(out, rtl);
	if (s >= 0) psn_rtl_val[s] = (uint8_t)rtl;
	if (rtl && getenv("RECOMP_PSN_RTL_TRACE")) {
		static unsigned n; if (n++ < 40) fprintf(stderr, "    psn rtl: Arabic message at %#x laid out in box block %#x (frame %llu)\n", p, out, (unsigned long long)display_frames());
	}
}
void recomp_ihook_psn_rtl_align(Cpu *c, int reg) {
	if (reg != 2 || c->r[2] != 0) return;
	int s = psn_rtl_slot(c->r[5] + 0xa4, 0);
	if (s >= 0 && psn_rtl_val[s]) c->r[2] = 2;
}

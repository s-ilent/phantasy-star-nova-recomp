#ifndef RECOMP_CONTROLLER_MAP_H
#define RECOMP_CONTROLLER_MAP_H

#include <stddef.h>
#include <stdint.h>

/* The window input state uses Vita L/R for the physical bumpers in PS TV mode.
 * Triggers and stick clicks occupy private host-state bits until API encoding. */
enum {
	RECOMP_PHYS_L1 = 0x01u,
	RECOMP_PHYS_R1 = 0x02u,
	RECOMP_PHYS_L2 = 0x04u,
	RECOMP_PHYS_R2 = 0x08u,
	RECOMP_PHYS_L3 = 0x10u,
	RECOMP_PHYS_R3 = 0x20u,
	RECOMP_CTRL_L3 = 0x00000002u,
	RECOMP_CTRL_R3 = 0x00000004u,
	RECOMP_CTRL_L = 0x00000100u,
	RECOMP_CTRL_R = 0x00000200u,
	RECOMP_CTRL_EXT_L1 = 0x00000400u,
	RECOMP_CTRL_EXT_R1 = 0x00000800u,
	RECOMP_CTRL_HOST_L2 = 0x00010000u,
	RECOMP_CTRL_HOST_R2 = 0x00020000u,
};

static inline uint32_t recomp_ctrl_physical_state(uint32_t physical) {
	return ((physical & RECOMP_PHYS_L1) ? RECOMP_CTRL_L : 0)
		| ((physical & RECOMP_PHYS_R1) ? RECOMP_CTRL_R : 0)
		| ((physical & RECOMP_PHYS_L2) ? RECOMP_CTRL_HOST_L2 : 0)
		| ((physical & RECOMP_PHYS_R2) ? RECOMP_CTRL_HOST_R2 : 0)
		| ((physical & RECOMP_PHYS_L3) ? RECOMP_CTRL_L3 : 0)
		| ((physical & RECOMP_PHYS_R3) ? RECOMP_CTRL_R3 : 0);
}

static inline uint32_t recomp_ctrl_encode_legacy(uint32_t state) {
	return state & ~(RECOMP_CTRL_L3 | RECOMP_CTRL_R3 | RECOMP_CTRL_HOST_L2 | RECOMP_CTRL_HOST_R2);
}

static inline uint32_t recomp_ctrl_encode_extended(uint32_t state) {
	return (state & ~(RECOMP_CTRL_L | RECOMP_CTRL_R | RECOMP_CTRL_HOST_L2 | RECOMP_CTRL_HOST_R2))
		| ((state & RECOMP_CTRL_L) ? RECOMP_CTRL_EXT_L1 : 0)
		| ((state & RECOMP_CTRL_R) ? RECOMP_CTRL_EXT_R1 : 0)
		| ((state & RECOMP_CTRL_HOST_L2) ? RECOMP_CTRL_L : 0)
		| ((state & RECOMP_CTRL_HOST_R2) ? RECOMP_CTRL_R : 0);
}

typedef struct {
	uint64_t timestamp;
	uint32_t buttons;
	uint8_t sticks[4];
	uint8_t pressure[12];
	uint8_t reserved[4];
} RecompCtrlData;

_Static_assert(sizeof(RecompCtrlData) == 0x20, "SceCtrlData must remain 32 bytes");
_Static_assert(offsetof(RecompCtrlData, buttons) == 0x08, "SceCtrlData buttons offset");
_Static_assert(offsetof(RecompCtrlData, sticks) == 0x0c, "SceCtrlData sticks offset");
_Static_assert(offsetof(RecompCtrlData, pressure) == 0x10, "SceCtrlData pressure offset");
_Static_assert(offsetof(RecompCtrlData, reserved) == 0x1c, "SceCtrlData reserved offset");

#endif

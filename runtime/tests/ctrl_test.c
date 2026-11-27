#include <stdio.h>
#include <string.h>
#include "controller_map.h"

static int checks, failed;
static void eq(const char *name, uint32_t got, uint32_t want) {
	checks++;
	if (got != want) { fprintf(stderr, "%s: got %#x, wanted %#x\n", name, got, want); failed++; }
}

int main(void) {
	const uint32_t cross = 0x4000u, circle = 0x2000u, dpad_right = 0x20u;
	eq("neutral legacy", recomp_ctrl_encode_legacy(0), 0);
	eq("physical L1 legacy", recomp_ctrl_encode_legacy(recomp_ctrl_physical_state(RECOMP_PHYS_L1)), 0x100u);
	eq("physical R1 legacy", recomp_ctrl_encode_legacy(recomp_ctrl_physical_state(RECOMP_PHYS_R1)), 0x200u);
	eq("physical L1 extended", recomp_ctrl_encode_extended(recomp_ctrl_physical_state(RECOMP_PHYS_L1)), 0x400u);
	eq("physical R1 extended", recomp_ctrl_encode_extended(recomp_ctrl_physical_state(RECOMP_PHYS_R1)), 0x800u);
	eq("physical L2 extended", recomp_ctrl_encode_extended(recomp_ctrl_physical_state(RECOMP_PHYS_L2)), 0x100u);
	eq("physical R2 extended", recomp_ctrl_encode_extended(recomp_ctrl_physical_state(RECOMP_PHYS_R2)), 0x200u);
	eq("physical stick clicks extended", recomp_ctrl_encode_extended(recomp_ctrl_physical_state(RECOMP_PHYS_L3 | RECOMP_PHYS_R3)), 0x6u);
	eq("physical all six extras", recomp_ctrl_encode_extended(recomp_ctrl_physical_state(0x3fu)), 0xf06u);
	eq("physical triggers absent in legacy", recomp_ctrl_encode_legacy(recomp_ctrl_physical_state(RECOMP_PHYS_L2 | RECOMP_PHYS_R2 | RECOMP_PHYS_L3 | RECOMP_PHYS_R3)), 0);
	eq("neutral extended", recomp_ctrl_encode_extended(0), 0);
	eq("left bumper legacy L1", recomp_ctrl_encode_legacy(RECOMP_CTRL_L), 0x100u);
	eq("left bumper extended L1", recomp_ctrl_encode_extended(RECOMP_CTRL_L), 0x400u);
	eq("right bumper legacy R1", recomp_ctrl_encode_legacy(RECOMP_CTRL_R), 0x200u);
	eq("right bumper extended R1", recomp_ctrl_encode_extended(RECOMP_CTRL_R), 0x800u);
	eq("left trigger legacy isolated", recomp_ctrl_encode_legacy(RECOMP_CTRL_HOST_L2), 0);
	eq("left trigger extended L2", recomp_ctrl_encode_extended(RECOMP_CTRL_HOST_L2), 0x100u);
	eq("right trigger legacy isolated", recomp_ctrl_encode_legacy(RECOMP_CTRL_HOST_R2), 0);
	eq("right trigger extended R2", recomp_ctrl_encode_extended(RECOMP_CTRL_HOST_R2), 0x200u);
	eq("L3 absent from legacy", recomp_ctrl_encode_legacy(RECOMP_CTRL_L3), 0);
	eq("L3 in extended", recomp_ctrl_encode_extended(RECOMP_CTRL_L3), 0x2u);
	eq("R3 absent from legacy", recomp_ctrl_encode_legacy(RECOMP_CTRL_R3), 0);
	eq("R3 in extended", recomp_ctrl_encode_extended(RECOMP_CTRL_R3), 0x4u);
	eq("left bumper + trigger legacy", recomp_ctrl_encode_legacy(RECOMP_CTRL_L | RECOMP_CTRL_HOST_L2), 0x100u);
	eq("left bumper + trigger extended", recomp_ctrl_encode_extended(RECOMP_CTRL_L | RECOMP_CTRL_HOST_L2), 0x500u);
	eq("right bumper + trigger extended", recomp_ctrl_encode_extended(RECOMP_CTRL_R | RECOMP_CTRL_HOST_R2), 0xa00u);
	eq("all extra buttons extended", recomp_ctrl_encode_extended(RECOMP_CTRL_L | RECOMP_CTRL_R | RECOMP_CTRL_L3 | RECOMP_CTRL_R3 | RECOMP_CTRL_HOST_L2 | RECOMP_CTRL_HOST_R2), 0xf06u);
	eq("ordinary inputs preserved", recomp_ctrl_encode_extended(cross | circle | dpad_right), cross | circle | dpad_right);
	eq("simultaneous mixed inputs", recomp_ctrl_encode_extended(cross | RECOMP_CTRL_L | RECOMP_CTRL_HOST_R2 | RECOMP_CTRL_R3), cross | 0x400u | 0x200u | 0x4u);
	RecompCtrlData data; memset(&data, 0, sizeof data); for (int i = 0; i < 4; i++) data.sticks[i] = 128;
	eq("neutral left stick x", data.sticks[0], 128); eq("neutral left stick y", data.sticks[1], 128);
	eq("neutral right stick x", data.sticks[2], 128); eq("neutral right stick y", data.sticks[3], 128);
	printf("controller mapping and ABI: %d checks, %d failed\n", checks, failed);
	return failed ? 1 : 0;
}

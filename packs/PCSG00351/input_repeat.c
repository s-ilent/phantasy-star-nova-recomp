/* Keep Nova's menu navigation repeat at console speed when frames run faster. */
#include "hooks.h"
#include "input_repeat.h"

/* fn_8190b9ee loads the menu's delay and interval into r0 at these two sites.
 * Scale the loaded values only: press/release events and held gameplay input keep
 * their original path, and the guest's byte-sized configuration stays unchanged. */
void recomp_ihook_psn_menu_repeat_frames(Cpu *c, int reg) {
    if (reg != 0) return;
    c->r[0] = psn_menu_repeat_frames(c->r[0], display_vblank_hz(), display_frame_rate_60());
}

/* A repeat consumes its own callback: the period is interval + 1 callbacks. */
void recomp_ihook_psn_menu_repeat_interval(Cpu *c, int reg) {
    if (reg != 0) return;
    c->r[0] = psn_menu_repeat_frames(c->r[0] + 1u, display_vblank_hz(),
                                    display_frame_rate_60()) - 1u;
}

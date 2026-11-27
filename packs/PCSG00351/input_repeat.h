/* Nova's menu repeat thresholds are counts written for 30 frames per second. */
#ifndef PSN_INPUT_REPEAT_H
#define PSN_INPUT_REPEAT_H
#include <stdint.h>

/* The limiter waits two grid edges at 30 fps, one with the 60 fps unlock. */
static inline uint32_t psn_menu_repeat_frames(uint32_t frames, int grid_hz, int unlocked) {
    uint32_t denominator = unlocked ? 30u : 60u;
    if (grid_hz <= (int)denominator) return frames;
    return (uint32_t)(((uint64_t)frames * (uint32_t)grid_hz + denominator - 1u)
                      / denominator);
}
#endif

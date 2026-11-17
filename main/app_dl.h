#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Create the detector, allocate the input buffer and start the inference task (core 1). */
esp_err_t app_dl_init(size_t buf_size, size_t align);

/* Input buffer to fill with an RGB565 frame, or NULL while an inference is running. */
uint8_t *app_dl_get_input_buffer(size_t *size);

/* Start inference on the filled buffer. Boxes are multiplied by scale to map them
 * back to display coordinates. */
void app_dl_submit(uint32_t width, uint32_t height, uint32_t scale);

/* Draw the latest detected boxes on a display frame. Call once per frame.
 * Returns true if anything was drawn (the CPU cache then holds dirty pixels). */
bool app_dl_draw(uint8_t *rgb565, uint32_t width, uint32_t height);

#ifdef __cplusplus
}
#endif

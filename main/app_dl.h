#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

esp_err_t app_dl_init(void);
void app_dl_detect_and_draw(uint8_t *rgb565, uint32_t width, uint32_t height,
                            bool run_inference);

#ifdef __cplusplus
}
#endif

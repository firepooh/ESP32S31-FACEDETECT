#include "app_dl.h"
#include <algorithm>
#include <list>
#include <new>
#include <vector>
#include "esp_log.h"
#include "human_face_detect.hpp"
#include "dl_image_draw.hpp"

static const char *TAG = "face_detect";
static HumanFaceDetect *s_detector;
static std::list<dl::detect::result_t> s_faces;

extern "C" esp_err_t app_dl_init(void)
{
    s_detector = new (std::nothrow) HumanFaceDetect();
    if (!s_detector) {
        return ESP_ERR_NO_MEM;
    }
    ESP_LOGI(TAG, "Face detector ready; model loads on first inference");
    return ESP_OK;
}

extern "C" void app_dl_detect_and_draw(uint8_t *rgb565, uint32_t width, uint32_t height,
                                       bool run_inference)
{
    if (!s_detector) {
        return;
    }

    dl::image::img_t image = {
        .data = rgb565,
        .width = static_cast<uint16_t>(width),
        .height = static_cast<uint16_t>(height),
        .pix_type = dl::image::DL_IMAGE_PIX_TYPE_RGB565LE,
    };

    if (run_inference) {
        s_faces = s_detector->run(image);
    }

    const std::vector<uint8_t> green = {0xE0, 0x07};
    for (const auto &face : s_faces) {
        // draw_hollow_rectangle() asserts that the box lies inside the image.
        int x1 = std::max(0, face.box[0]);
        int y1 = std::max(0, face.box[1]);
        int x2 = std::min(static_cast<int>(width) - 1, face.box[2]);
        int y2 = std::min(static_cast<int>(height) - 1, face.box[3]);
        if (x2 <= x1 || y2 <= y1) {
            continue;
        }
        dl::image::draw_hollow_rectangle(image, x1, y1, x2, y2, green, 3);
        if (run_inference) {
            ESP_LOGI(TAG, "face score=%.2f box=[%d,%d,%d,%d]", face.score, x1, y1, x2, y2);
        }
    }
}

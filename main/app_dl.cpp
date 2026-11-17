#include "app_dl.h"
#include <algorithm>
#include <atomic>
#include <cinttypes>
#include <list>
#include <new>
#include <vector>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "human_face_detect.hpp"
#include "dl_image_draw.hpp"

/*
 * Inference runs in its own task on core 1, so the camera callback (core 0)
 * never waits for the model. When the task is idle, the callback fills the
 * input buffer (PPA downscale, or memcpy as fallback) and submits it. Every
 * frame draws the latest known boxes. While the task is busy, frames are not
 * submitted.
 */

#define DL_TASK_CORE        1
#define DL_TASK_PRIORITY    3   /* below LVGL (4) and video stream (6) */
#define DL_TASK_STACK_SIZE  (16 * 1024)
#define DL_STATS_PERIOD_US  (5 * 1000 * 1000)

static const char *TAG = "face_detect";
static HumanFaceDetect *s_detector;

static uint8_t *s_inf_buf;
static size_t s_inf_buf_size;
static uint32_t s_inf_w, s_inf_h, s_inf_scale = 1;
static SemaphoreHandle_t s_frame_ready;     /* submit -> task: s_inf_buf holds a frame */
static std::atomic<bool> s_busy{false};     /* task owns s_inf_buf */

static SemaphoreHandle_t s_result_lock;
static std::vector<dl::detect::result_t> s_faces;   /* boxes in display coordinates */

/* Stats, reported every DL_STATS_PERIOD_US */
static std::atomic<uint32_t> s_stat_frames{0};
static uint32_t s_stat_runs;
static int64_t s_stat_run_us;

static void dl_task(void *arg)
{
    int64_t stat_start = esp_timer_get_time();
    while (true) {
        xSemaphoreTake(s_frame_ready, portMAX_DELAY);

        dl::image::img_t image = {
            .data = s_inf_buf,
            .width = static_cast<uint16_t>(s_inf_w),
            .height = static_cast<uint16_t>(s_inf_h),
            .pix_type = dl::image::DL_IMAGE_PIX_TYPE_RGB565LE,
        };
        const int scale = static_cast<int>(s_inf_scale);
        int64_t t0 = esp_timer_get_time();
        std::list<dl::detect::result_t> &faces = s_detector->run(image);
        int64_t t1 = esp_timer_get_time();

        std::vector<dl::detect::result_t> scaled(faces.begin(), faces.end());
        for (auto &face : scaled) {
            for (auto &v : face.box) {
                v *= scale;
            }
        }
        xSemaphoreTake(s_result_lock, portMAX_DELAY);
        s_faces.swap(scaled);
        xSemaphoreGive(s_result_lock);
        s_busy = false;

        s_stat_runs++;
        s_stat_run_us += t1 - t0;
        if (t1 - stat_start >= DL_STATS_PERIOD_US) {
            float secs = (t1 - stat_start) / 1e6f;
            ESP_LOGI(TAG, "camera %.1f fps, inference %.1f /s (avg %lld ms, input %" PRIu32 "x%" PRIu32 "), faces=%u",
                     s_stat_frames.load() / secs, s_stat_runs / secs, s_stat_run_us / s_stat_runs / 1000,
                     s_inf_w, s_inf_h, (unsigned)faces.size());
            xSemaphoreTake(s_result_lock, portMAX_DELAY);
            for (const auto &face : s_faces) {
                ESP_LOGI(TAG, "face score=%.2f box=[%d,%d,%d,%d]", face.score,
                         face.box[0], face.box[1], face.box[2], face.box[3]);
            }
            xSemaphoreGive(s_result_lock);
            stat_start = t1;
            s_stat_frames = 0;
            s_stat_runs = 0;
            s_stat_run_us = 0;
        }
    }
}

extern "C" esp_err_t app_dl_init(size_t buf_size, size_t align)
{
    s_detector = new (std::nothrow) HumanFaceDetect();
    s_inf_buf_size = (buf_size + align - 1) / align * align;
    s_inf_buf = static_cast<uint8_t *>(heap_caps_aligned_calloc(align, 1, s_inf_buf_size, MALLOC_CAP_SPIRAM));
    s_frame_ready = xSemaphoreCreateBinary();
    s_result_lock = xSemaphoreCreateMutex();
    if (!s_detector || !s_inf_buf || !s_frame_ready || !s_result_lock) {
        return ESP_ERR_NO_MEM;
    }
    if (xTaskCreatePinnedToCore(dl_task, "face_detect", DL_TASK_STACK_SIZE, nullptr,
                                DL_TASK_PRIORITY, nullptr, DL_TASK_CORE) != pdPASS) {
        return ESP_ERR_NO_MEM;
    }
    ESP_LOGI(TAG, "Face detector ready on core %d; model loads on first inference", DL_TASK_CORE);
    return ESP_OK;
}

extern "C" uint8_t *app_dl_get_input_buffer(size_t *size)
{
    if (!s_inf_buf || s_busy) {
        return nullptr;
    }
    *size = s_inf_buf_size;
    return s_inf_buf;
}

extern "C" void app_dl_submit(uint32_t width, uint32_t height, uint32_t scale)
{
    if (s_busy || width * height * 2 > s_inf_buf_size) {
        return;
    }
    s_inf_w = width;
    s_inf_h = height;
    s_inf_scale = scale ? scale : 1;
    s_busy = true;
    xSemaphoreGive(s_frame_ready);
}

extern "C" bool app_dl_draw(uint8_t *rgb565, uint32_t width, uint32_t height)
{
    s_stat_frames++;
    if (!s_result_lock) {
        return false;
    }

    std::vector<dl::detect::result_t> faces;
    xSemaphoreTake(s_result_lock, portMAX_DELAY);
    faces = s_faces;
    xSemaphoreGive(s_result_lock);

    dl::image::img_t image = {
        .data = rgb565,
        .width = static_cast<uint16_t>(width),
        .height = static_cast<uint16_t>(height),
        .pix_type = dl::image::DL_IMAGE_PIX_TYPE_RGB565LE,
    };
    const std::vector<uint8_t> green = {0xE0, 0x07};
    bool drawn = false;
    for (const auto &face : faces) {
        // draw_hollow_rectangle() asserts that the box lies inside the image.
        int x1 = std::max(0, face.box[0]);
        int y1 = std::max(0, face.box[1]);
        int x2 = std::min(static_cast<int>(width) - 1, face.box[2]);
        int y2 = std::min(static_cast<int>(height) - 1, face.box[3]);
        if (x2 <= x1 || y2 <= y1) {
            continue;
        }
        dl::image::draw_hollow_rectangle(image, x1, y1, x2, y2, green, 3);
        drawn = true;
    }
    return drawn;
}

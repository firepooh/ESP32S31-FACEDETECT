# For more information about build system see
# https://docs.espressif.com/projects/esp-idf/en/latest/api-guides/build-system.html
# The following five lines of boilerplate have to be in your project's
# CMakeLists in this exact order for cmake to work correctly
cmake_minimum_required(VERSION 3.16)

set(COMPONENTS main) # "Trim" the build. Include the minimal set of components; main and anything it depends on.
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(display_camera_new)

# LVGL's PPA draw unit is written for ESP32-P4 only:
# - LVGL adds the esp_driver_ppa / esp_mm dependencies only when the target is esp32p4.
# - It checks buffer alignment against CONFIG_CACHE_L2_CACHE_LINE_SIZE, which only exists
#   on ESP32-P4. ESP32-S31 has no L2 cache, so map it to the L1 D-cache line size.
if(CONFIG_LV_USE_PPA)
    idf_component_get_property(lvgl_lib lvgl__lvgl COMPONENT_LIB)
    target_link_libraries(${lvgl_lib} PRIVATE idf::esp_driver_ppa idf::esp_mm)
    target_compile_definitions(${lvgl_lib} PRIVATE
        CONFIG_CACHE_L2_CACHE_LINE_SIZE=${CONFIG_CACHE_L1_DCACHE_LINE_SIZE}
        CONFIG_CACHE_L1_CACHE_LINE_SIZE=${CONFIG_CACHE_L1_DCACHE_LINE_SIZE})
endif()

# ESP32-S31-Korvo-1 얼굴 검출 데모 (Assignment 7)

Espressif 워크숍 [Assignment 7](https://developer.espressif.com/workshops/introduction-to-esp32-s31-with-vision/assignment-7/)을 그대로 적용한 프로젝트다.
BSP 카메라 예제(`display_camera_video`, BSP 1.1.0)에 ESP-DL 얼굴 검출을 붙였다.
카메라 영상은 LCD에 표시되고, 검출된 얼굴에는 초록색 상자가 그려진다.

## 원본 예제에서 바꾼 부분

| 파일 | 내용 |
|---|---|
| `main/idf_component.yml` | `espressif/esp32_s31_korvo_1` 1.1.0, `espressif/human_face_detect` 0.5.0 추가. LVGL 9.5.x 고정 (아래 참고) |
| `main/app_dl.h`, `main/app_dl.cpp` | 새 파일. 코어 1에서 도는 추론 태스크와 상자 그리기 |
| `main/CMakeLists.txt` | `app_dl.cpp` 소스 추가 |
| `main/main.c` | 추론 태스크가 쉬고 있으면 PPA로 320x240 축소본을 만들어 넘기고, 매 프레임 최근 상자를 그린다. 캔버스를 LVGL PPA로 그리도록 설정 |
| `CMakeLists.txt` | LVGL PPA 그리기를 ESP32-S31에서 빌드하기 위한 설정 (아래 참고) |
| `partitions.csv` | 새 파일. factory 앱 파티션 6 MB |
| `sdkconfig.defaults` | 16 MB 플래시, 사용자 파티션 테이블 설정 추가. CPU 클럭을 240 MHz에서 320 MHz로 올림. LVGL PPA 그리기 켬 |

모델은 MSRMNP S8 V1이다. 저장 위치는 FLASH RODATA로, 펌웨어 안에 함께 링크된다.
빌드한 앱 크기는 약 3.2 MB(0x338950)로, 6 MB 파티션의 54 %를 쓴다.

### 워크숍 문서와 다른 점: LVGL 버전 고정

워크숍 문서에는 없는 설정이다.
BSP가 쓰는 `esp_lvgl_port` 2.9.0은 `LV_COLOR_FORMAT_RGB565_SWAPPED`를 쓴다.
이 정의는 LVGL 9.3부터 들어 있다.
EIM으로 설치한 오프라인 컴포넌트 저장소(`C:\Espressif\tools\components`)에는 LVGL 9.2.x만 있다.
그래서 버전을 지정하지 않으면 9.2.2가 선택되고 빌드가 실패한다.
이를 막으려고 `main/idf_component.yml`에 LVGL 버전을 지정했다.
처음에는 `~9.4.0`으로 고정했고, LVGL PPA 그리기를 쓰려고 지금은 `~9.5.0`으로 올렸다.
자세한 내용은 [LVGL_VERSION_KO.md](LVGL_VERSION_KO.md)에 정리했다.

## 실행 방법 (PowerShell)

ESP-IDF v6.1 환경을 활성화한다.

```powershell
. C:\Espressif\tools\Microsoft.v6.1.PowerShell_profile.ps1
cd C:\work\ESP32\ESP32S31-FACEDETECT\display_camera_video
```

빌드는 이미 끝나 있다. 다시 빌드하려면 아래 명령을 쓴다.

```powershell
idf.py build
```

보드의 USB Type-C UART 포트를 PC에 연결한다.
장치 관리자에서 새로 생긴 COM 포트 번호를 확인한다.
그 번호로 플래시하고 모니터를 연다.

```powershell
idf.py -p COMxx flash monitor
```

모니터는 `Ctrl+]`로 빠져나온다.
UartTerminal로 같은 포트를 열어 두었다면 먼저 닫아야 플래시할 수 있다.

## 정상 동작 확인

- LCD에 카메라 실시간 영상이 나온다.
- 얼굴을 비추면 초록색 상자가 그려진다.
- 시리얼 로그에 5초마다 아래와 비슷한 줄이 찍힌다. 얼굴이 있으면 그 시점의 상자 좌표도 함께 찍힌다.

```
I (17052) face_detect: camera 15.4 fps, inference 15.4 /s (avg 41 ms, input 320x240), faces=1
I (17052) face_detect: face score=0.98 box=[332,142,508,390]
```

## 성능 개선

처음 구성에서는 카메라 콜백 안에서 5프레임마다 추론을 직접 실행했다.
그래서 상자가 약 0.3초마다만 움직였다.
지금은 아래처럼 바꿨다.

1. 추론을 코어 1의 별도 태스크로 옮겼다. 우선순위는 3으로, LVGL(4)과 영상 스트림(6)보다 낮다.
   카메라 콜백은 추론을 기다리지 않는다.
2. 추론 태스크가 쉬고 있을 때만 새 프레임을 넘긴다. 바쁠 때 들어온 프레임은 넘기지 않고 최근 상자만 그린다.
3. 추론 입력은 PPA로 320x240 축소본을 만들어 넘긴다. 상자 좌표는 2배로 늘려 화면에 그린다.
   처음에는 640x480 프레임을 `memcpy`로 복사했다. 그런데 PSRAM끼리 614 KB를 복사하는 데 18 ms가 걸려 카메라가 12.5 fps로 떨어졌다.
4. CPU 클럭을 240 MHz에서 320 MHz로 올렸다. ESP-IDF v6.1에서 ESP32-S31의 기본값은 320 MHz다.
   `sdkconfig.defaults`가 ESP32-S3 예제 설정을 그대로 가져와 240 MHz로 낮춰 두고 있었다.
5. LVGL이 카메라 캔버스(640x480)를 PPA로 그리게 했다. 아래 "LVGL PPA 그리기" 절에 자세히 적었다.

보드에서 잰 결과는 다음과 같다. 카메라는 SC101IOT, 640x480 15 fps 설정이다.

| 구성 | 카메라 | 추론 횟수 | 추론 1회 |
|---|---|---|---|
| 처음 (콜백 안에서 5프레임마다, 240 MHz) | 15.5 fps | 초당 약 3회 | 약 40 ms |
| 별도 태스크 + `memcpy`, 240 MHz | 12.5 fps | 초당 약 10회 | 약 43 ms |
| 별도 태스크 + PPA 축소, 240 MHz | 14.0 fps | 초당 약 13회 | 약 46 ms |
| 별도 태스크 + PPA 축소, 320 MHz | 15.2 fps | 초당 약 15회 | 약 41 ms |
| 위 구성 + LVGL PPA 그리기 | 15.6 fps | 초당 약 15.6회 | 약 33 ms |

지금은 매 프레임 추론하며, 카메라 센서 설정(15 fps)이 상한이다.
더 빠르게 하려면 센서 해상도와 프레임 속도 설정을 바꿔야 한다.

### LVGL PPA 그리기

LVGL은 원래 카메라 캔버스를 CPU로 그렸다. 화면을 한 번 그리는 데 약 49 ms가 걸려 코어 하나를 거의 다 썼다.
LVGL 9.5의 PPA 그리기 유닛을 켜서 캔버스 복사를 PPA에 맡겼다.

| 항목 | CPU 그리기 | PPA 그리기 |
|---|---|---|
| 화면 1회 렌더링 | 약 49 ms | 약 28 ms |
| 화면 갱신 | 초당 약 19.6회 | 초당 약 26.5회 |
| 캔버스 그리기 (PPA) | - | 1회 약 8.8 ms |

LVGL의 PPA 코드는 ESP32-P4만 염두에 두고 작성돼 있어서, ESP32-S31에서 쓰려면 아래 네 가지가 필요했다.

1. **LVGL 9.5 이상.** 9.4의 PPA 코드는 그릴 위치를 무시하고 항상 레이어 왼쪽 위에 그린다.
2. **`esp_driver_ppa` 연결.** LVGL은 타깃이 `esp32p4`일 때만 이 의존성을 붙인다. 최상위 `CMakeLists.txt`에서 LVGL 컴포넌트에 직접 연결했다.
3. **캐시 라인 크기 정의.** LVGL은 P4 전용 설정인 `CONFIG_CACHE_L2_CACHE_LINE_SIZE`로 버퍼 정렬을 검사한다.
   S31에는 L2 캐시가 없으므로, 같은 `CMakeLists.txt`에서 이 값을 L1 D-cache 라인 크기(64)로 정의했다.
   `CONFIG_LV_DRAW_BUF_ALIGN`과 `CONFIG_LV_ATTRIBUTE_MEM_ALIGN_SIZE`도 64로 맞췄다.
4. **캔버스 불투명도를 253으로 설정.** LVGL 9.5는 `opa <= LV_OPA_MAX(253)`인 이미지만 PPA로 보낸다.
   완전히 불투명한(255) 캔버스는 CPU로 그려진다. PPA 블렌드 코드는 `opa`를 쓰지 않고 항상 불투명하게 복사하므로, 253으로 지정해도 화면은 똑같다.

PPA는 캔버스 버퍼를 DMA로 읽는다. 그래서 CPU로 상자를 그린 프레임은 `esp_cache_msync()`로 캐시 내용을 PSRAM에 먼저 내보낸다.

## 문제 해결

| 증상 | 확인할 내용 |
|---|---|
| `esp32s31` 타깃을 모른다는 오류 | v6.1 환경이 활성화됐는지 확인한다. 타깃 지정에는 `--preview`가 필요하다 |
| `app partition is too small` | `sdkconfig`를 지우고 `idf.py --preview set-target esp32s31`을 다시 실행한다 |
| `human_face_detect.hpp`를 찾지 못함 | `idf.py reconfigure`를 실행한다 |
| 카메라 장치를 열지 못함 | 카메라 모듈 장착 상태를 확인한다 |
| 화면이 검게 나옴 | LCD 보드 커넥터를 확인한다 |
| 프레임이 느림 | 부팅 로그의 `cpu freq`가 320000000인지 확인한다. 240 MHz이면 `sdkconfig`를 지우고 다시 빌드한다 |

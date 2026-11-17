# ESP32-S31-Korvo-1 얼굴 검출 데모 (Assignment 7)

Espressif 워크숍 [Assignment 7](https://developer.espressif.com/workshops/introduction-to-esp32-s31-with-vision/assignment-7/)을 그대로 적용한 프로젝트다.
BSP 카메라 예제(`display_camera_video`, BSP 1.1.0)에 ESP-DL 얼굴 검출을 붙였다.
카메라 영상은 LCD에 표시되고, 검출된 얼굴에는 초록색 상자가 그려진다.

## 원본 예제에서 바꾼 부분

| 파일 | 내용 |
|---|---|
| `main/idf_component.yml` | `espressif/esp32_s31_korvo_1` 1.1.0, `espressif/human_face_detect` 0.5.0 추가. LVGL 9.4.x 고정 (아래 참고) |
| `main/app_dl.h`, `main/app_dl.cpp` | 새 파일. 검출기 초기화와 검출·상자 그리기 |
| `main/CMakeLists.txt` | `app_dl.cpp` 소스 추가 |
| `main/main.c` | `app_dl.h` 포함, 5프레임마다 추론, `app_main()`에서 `app_dl_init()` 호출 |
| `partitions.csv` | 새 파일. factory 앱 파티션 6 MB |
| `sdkconfig.defaults` | 16 MB 플래시, 사용자 파티션 테이블 설정 추가 |

모델은 MSRMNP S8 V1이다. 저장 위치는 FLASH RODATA로, 펌웨어 안에 함께 링크된다.
빌드한 앱 크기는 약 3.2 MB(0x32c920)로, 6 MB 파티션의 53 %를 쓴다.

### 워크숍 문서와 다른 점: LVGL 버전 고정

워크숍 문서에는 없는 설정이다.
BSP가 쓰는 `esp_lvgl_port` 2.9.0은 `LV_COLOR_FORMAT_RGB565_SWAPPED`를 쓴다.
이 정의는 LVGL 9.3부터 들어 있다.
EIM으로 설치한 오프라인 컴포넌트 저장소(`C:\Espressif\tools\components`)에는 LVGL 9.2.x만 있다.
그래서 버전을 지정하지 않으면 9.2.2가 선택되고 빌드가 실패한다.
이를 막으려고 `main/idf_component.yml`에 `lvgl/lvgl: "~9.4.0"`을 추가했다.

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
- 시리얼 로그에 아래와 비슷한 줄이 찍힌다.

```
I (4231) face_detect: face score=0.91 box=[126,48,311,267]
```

추론은 5프레임에 한 번(10 FPS 기준 초당 약 2회) 실행한다.
그래서 얼굴이 빠르게 움직이면 상자가 조금 늦게 따라간다.
간격은 `main/main.c`의 `++frame_count % 5`에서 바꿀 수 있다.

## 문제 해결

| 증상 | 확인할 내용 |
|---|---|
| `esp32s31` 타깃을 모른다는 오류 | v6.1 환경이 활성화됐는지 확인한다. 타깃 지정에는 `--preview`가 필요하다 |
| `app partition is too small` | `sdkconfig`를 지우고 `idf.py --preview set-target esp32s31`을 다시 실행한다 |
| `human_face_detect.hpp`를 찾지 못함 | `idf.py reconfigure`를 실행한다 |
| 카메라 장치를 열지 못함 | 카메라 모듈 장착 상태를 확인한다 |
| 화면이 검게 나옴 | LCD 보드 커넥터를 확인한다 |
| 프레임이 느림 | 추론 간격을 늘린다 |

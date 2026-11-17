# LVGL 버전 충돌과 해결 방법

워크숍 Assignment 7 문서대로 빌드하면 LVGL 컴파일 단계에서 실패한다.
이 문서는 원인과 해결 방법, 확인 방법을 정리한다.

## 환경

| 항목 | 값 |
|---|---|
| ESP-IDF | v6.1 (EIM으로 설치) |
| 타깃 | esp32s31 (`--preview`) |
| BSP | `espressif/esp32_s31_korvo_1` 1.1.0 |
| esp_lvgl_port | 2.9.0 (BSP가 `^2`로 요구) |
| 문제가 된 LVGL | 9.2.2 |
| 해결 후 LVGL | 9.4.0 |

## 증상

`idf.py build`가 1520단계 중 1462단계 근처에서 멈춘다.
`esp_lvgl_port_disp.c`를 컴파일하다 아래 오류가 난다.

```
managed_components/espressif__esp_lvgl_port/src/lvgl9/esp_lvgl_port_disp.c:301:54:
error: 'LV_COLOR_FORMAT_RGB565_SWAPPED' undeclared (first use in this function);
did you mean 'LV_COLOR_FORMAT_RGB565A8'?
```

같은 파일의 312행, 319행도 같은 식별자를 쓴다.

## 원인

`esp_lvgl_port` 2.9.0은 `LV_COLOR_FORMAT_RGB565_SWAPPED`를 쓴다.
이 열거값은 LVGL 9.3.0부터 `src/misc/lv_color.h`에 들어 있다.
LVGL 9.2.x에는 없다.

그런데 `esp_lvgl_port`는 LVGL 버전을 `>=8,<10`으로만 제한한다.
따라서 9.2.2도 조건을 만족하고, 의존성 해석 단계에서는 오류가 나지 않는다.
오류는 컴파일 단계에 가서야 드러난다.

9.2.2가 선택된 이유는 EIM이 설치한 오프라인 컴포넌트 저장소 때문으로 보인다.
v6.1 활성화 스크립트는 아래 환경 변수를 설정한다.

```
IDF_COMPONENT_LOCAL_STORAGE_URL = file://C:\Espressif\tools
```

이 저장소(`C:\Espressif\tools\components\lvgl\lvgl`)에는 LVGL 9.2.0과 9.2.2만 있다.
반면 `esp_lvgl_port`는 이 저장소에 없어서 온라인 레지스트리의 최신판 2.9.0을 받는다.
결국 새 `esp_lvgl_port`와 옛 LVGL이 짝지어진다.

온라인 레지스트리에는 LVGL 9.3.0 이후 버전(9.4.0, 9.5.0, 9.6.0)이 올라와 있다.
오프라인 저장소가 없는 환경이라면 이 문제가 생기지 않을 수도 있다.

> 이후 LVGL PPA 그리기를 쓰려고 `~9.5.0`으로 올렸다. 9.5.0에서도 빌드와 동작을 확인했다.
> 자세한 내용은 [DEMO_KO.md](DEMO_KO.md)의 "LVGL PPA 그리기" 절에 있다.
> 아래 내용은 처음 9.4로 고정할 때의 기록이다.

## 해결 방법

`main/idf_component.yml`에 LVGL 버전을 직접 지정한다.

```yaml
dependencies:
  espressif/esp32_s31_korvo_1:
    version: "1.1.0"
  espressif/human_face_detect:
    version: "0.5.0"
  # esp_lvgl_port 2.9.0 needs LV_COLOR_FORMAT_RGB565_SWAPPED (LVGL >= 9.3).
  # The EIM offline mirror only has LVGL 9.2.x, so pin it explicitly.
  lvgl/lvgl:
    version: "~9.4.0"
```

`~9.4.0`은 9.4.x 안에서만 올라간다.
9.3.0 이상이면 되지만, 9.5 이후의 변경에 영향받지 않도록 9.4로 묶었다.

이미 9.2.2를 받아 둔 상태라면 잠금 파일과 받은 LVGL을 지운 뒤 다시 빌드한다.

```powershell
Remove-Item dependencies.lock
Remove-Item -Recurse managed_components\lvgl__lvgl
idf.py build
```

## 확인 방법

`dependencies.lock`에서 `lvgl/lvgl` 항목의 버전과 출처를 확인한다.

```yaml
  lvgl/lvgl:
    source:
      registry_url: https://components.espressif.com/
      type: service
    version: 9.4.0
```

이 설정으로 빌드가 끝까지 통과했다.
앱 크기는 0x32c920(약 3.2 MB)이다.
다만 보드에서 LCD 표시는 아직 확인하지 않았다.

## 다른 해결 방법

- 오프라인 저장소를 쓰지 않는다.
  `IDF_COMPONENT_LOCAL_STORAGE_URL` 환경 변수를 비운 셸에서 빌드한다.
  이 방법은 시험해 보지 않았다.
- EIM으로 오프라인 저장소를 갱신한다.
  새 저장소에 LVGL 9.3 이상이 들어 있는지는 확인하지 않았다.

프로젝트 안에서 버전을 고정하는 방법이 설치 환경과 무관하게 같은 결과를 낸다.
그래서 이 프로젝트는 버전 고정을 택했다.

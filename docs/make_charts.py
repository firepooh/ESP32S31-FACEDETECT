#!/usr/bin/env python3
"""Generate the README performance images (SVG, Korean and English).

All numbers are board measurements on ESP32-S31-Korvo-1 (SC101IOT, 640x480 15 fps).
Run from the repository root:  python docs/make_charts.py
"""

from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).parent / 'images'

# Measured per improvement stage (5-second averages from the serial log).
STAGES = {
    'ko': [
        ('원본', '콜백 안에서', '5프레임마다 추론'),
        ('추론 태스크 분리', '코어 1에서 추론,', 'memcpy 18 ms'),
        ('PPA 축소 입력', 'memcpy 대신', 'PPA로 320x240'),
        ('CPU 320 MHz', '240 MHz에서', '320 MHz로'),
        ('LVGL PPA 그리기', '캔버스를', 'PPA로 그림'),
    ],
    'en': [
        ('Original', 'inference in the', 'callback, every 5th'),
        ('Inference task', 'on core 1,', '18 ms memcpy'),
        ('PPA input', '320x240 scaled', 'by PPA'),
        ('CPU 320 MHz', 'raised from', '240 MHz'),
        ('LVGL PPA draw', 'canvas drawn', 'by PPA'),
    ],
}
INFERENCE_PER_S = [3.1, 10.4, 13.0, 15.2, 15.6]
CAMERA_FPS = [15.5, 12.5, 14.0, 15.2, 15.6]
INFERENCE_MS = [40, 43, 46, 41, 33]
LVGL = {'render_ms': (49, 28), 'refresh_per_s': (19.6, 26.5)}

TEXT = {
    'ko': {
        'title': '성능 개선 과정',
        'subtitle': 'ESP32-S31-Korvo-1 보드 실측 · 카메라 SC101IOT 640x480 15 fps',
        'rows': ['얼굴 추론', '카메라', '추론 1회'],
        'units': ['회/초', 'fps', 'ms'],
        'cap': '센서 상한',
        'arch_title': '처리 구조: 개선 전과 후',
        'before': '개선 전', 'after': '개선 후',
        'core0': '코어 0 · 카메라 콜백', 'core1': '코어 1 · 추론 태스크', 'lvgl': 'LVGL 태스크',
        'b_ppa': 'PPA: UYVY → RGB565 640x480', 'b_inf': '얼굴 추론 ~40 ms (5프레임마다, 콜백을 막음)',
        'b_draw': '상자 그리기', 'b_lvgl': '캔버스 CPU 그리기 ~49 ms',
        'a_ppa': 'PPA: 화면용 640x480', 'a_ppa2': 'PPA: 추론용 320x240 (쉴 때만)', 'a_draw': '최근 상자 그리기',
        'a_inf': '얼굴 추론 ~33 ms (매 프레임)', 'a_lvgl': '캔버스 PPA 그리기 ~9 ms',
        'idle': '(비어 있음)',
        'lvgl_title': 'LVGL 화면 렌더링 (⑤ 적용 전후)',
        'lvgl_rows': ['1회 렌더링', '화면 갱신'], 'lvgl_units': ['ms', '회/초'],
        'cpu': 'CPU 그리기', 'ppa': 'PPA 그리기',
    },
    'en': {
        'title': 'Performance improvements',
        'subtitle': 'Measured on ESP32-S31-Korvo-1 · SC101IOT camera 640x480 15 fps',
        'rows': ['Face inference', 'Camera', 'Per inference'],
        'units': ['per s', 'fps', 'ms'],
        'cap': 'sensor limit',
        'arch_title': 'Pipeline: before and after',
        'before': 'Before', 'after': 'After',
        'core0': 'Core 0 · camera callback', 'core1': 'Core 1 · inference task', 'lvgl': 'LVGL task',
        'b_ppa': 'PPA: UYVY → RGB565 640x480', 'b_inf': 'Face inference ~40 ms (every 5th, blocks callback)',
        'b_draw': 'Draw boxes', 'b_lvgl': 'Canvas drawn by CPU ~49 ms',
        'a_ppa': 'PPA: 640x480 for display', 'a_ppa2': 'PPA: 320x240 for model (when idle)', 'a_draw': 'Draw latest boxes',
        'a_inf': 'Face inference ~33 ms (every frame)', 'a_lvgl': 'Canvas drawn by PPA ~9 ms',
        'idle': '(idle)',
        'lvgl_title': 'LVGL render (before / after step ⑤)',
        'lvgl_rows': ['Render per frame', 'Screen refresh'], 'lvgl_units': ['ms', 'per s'],
        'cpu': 'CPU draw', 'ppa': 'PPA draw',
    },
}

FONT = "'Segoe UI', 'Malgun Gothic', 'Apple SD Gothic Neo', 'Noto Sans KR', system-ui, sans-serif"

# Reference palette (dataviz skill): series blue, neutral gray, accent orange.
STYLE = f"""
<style>
  .surface {{ fill: #fcfcfb; stroke: #e2e1dc; }}
  .t1 {{ fill: #0b0b0b; }}
  .t2 {{ fill: #52514e; }}
  .t3 {{ fill: #77756f; }}
  .grid {{ stroke: #e8e7e2; stroke-width: 1; }}
  .axis {{ stroke: #bdbbb3; stroke-width: 1; }}
  .s1 {{ fill: #2a78d6; }}
  .s1s {{ stroke: #2a78d6; }}
  .neutral {{ fill: #a8a69f; }}
  .accent {{ fill: #eb6834; }}
  .box {{ fill: #ffffff; stroke: #d8d6cf; }}
  .boxs1 {{ fill: #e9f1fb; stroke: #2a78d6; }}
  .boxacc {{ fill: #fdeee7; stroke: #eb6834; }}
  .cap {{ stroke: #77756f; stroke-dasharray: 5 4; stroke-width: 1.5; }}
  text {{ font-family: {FONT}; }}
  @media (prefers-color-scheme: dark) {{
    .surface {{ fill: #1a1a19; stroke: #33322f; }}
    .t1 {{ fill: #f0efec; }}
    .t2 {{ fill: #c3c2b7; }}
    .t3 {{ fill: #9b998f; }}
    .grid {{ stroke: #2c2b29; }}
    .axis {{ stroke: #4a4945; }}
    .s1 {{ fill: #3987e5; }}
    .s1s {{ stroke: #3987e5; }}
    .neutral {{ fill: #6e6c66; }}
    .accent {{ fill: #d95926; }}
    .box {{ fill: #222220; stroke: #3d3c38; }}
    .boxs1 {{ fill: #1b2a3d; stroke: #3987e5; }}
    .boxacc {{ fill: #3a2219; stroke: #d95926; }}
    .cap {{ stroke: #9b998f; }}
  }}
</style>
"""


def text(x, y, s, cls='t1', size=13, anchor='start', weight='normal'):
    return (f'<text x="{x}" y="{y}" class="{cls}" font-size="{size}" '
            f'text-anchor="{anchor}" font-weight="{weight}">{escape(str(s))}</text>')


def bar(x, y_base, w, h, cls):
    """Vertical bar with 4px rounded top, flat on the baseline."""
    r = min(4, h)
    return (f'<path class="{cls}" d="M{x},{y_base} V{y_base - h + r} Q{x},{y_base - h} {x + r},{y_base - h} '
            f'H{x + w - r} Q{x + w},{y_base - h} {x + w},{y_base - h + r} V{y_base} Z"/>')


def hbar(x, y, w, h, cls):
    """Horizontal bar with 4px rounded end, flat on the left baseline."""
    r = min(4, w)
    return (f'<path class="{cls}" d="M{x},{y} H{x + w - r} Q{x + w},{y} {x + w},{y + r} '
            f'V{y + h - r} Q{x + w},{y + h} {x + w - r},{y + h} H{x} Z"/>')


def svg(w, h, body, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-label="{escape(label)}">{STYLE}'
            f'<rect class="surface" x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="12"/>{body}</svg>\n')


def steps_chart(lang):
    t = TEXT[lang]
    W, H = 960, 600
    left, col_w = 190, 148
    bar_w = 52
    rows = [
        (INFERENCE_PER_S, 19, t['rows'][0], t['units'][0], '{:.1f}', None),
        (CAMERA_FPS, 19, t['rows'][1], t['units'][1], '{:.1f}', 15),
        (INFERENCE_MS, 58, t['rows'][2], t['units'][2], '{:.0f}', None),
    ]
    row_h, row_gap, top = 112, 34, 104
    out = [text(32, 44, t['title'], size=22, weight='600'), text(32, 70, t['subtitle'], 't2', 13)]

    for ri, (values, vmax, name, unit, fmt, cap) in enumerate(rows):
        y0 = top + ri * (row_h + row_gap)
        base = y0 + row_h
        out.append(text(32, y0 + row_h / 2 - 2, name, 't1', 15, weight='600'))
        out.append(text(32, y0 + row_h / 2 + 18, unit, 't3', 12))
        out.append(f'<line class="axis" x1="{left}" y1="{base}" x2="{left + col_w * 5}" y2="{base}"/>')
        if cap is not None:
            cy = base - cap / vmax * row_h
            out.append(f'<line class="cap" x1="{left}" y1="{cy:.1f}" x2="{left + col_w * 5}" y2="{cy:.1f}"/>')
            out.append(f'<line class="cap" x1="32" y1="{y0 + row_h / 2 + 34}" x2="56" y2="{y0 + row_h / 2 + 34}"/>')
            out.append(text(62, y0 + row_h / 2 + 38, t['cap'], 't3', 11))
        for i, v in enumerate(values):
            cx = left + col_w * i + col_w / 2
            h = v / vmax * row_h
            cls = 's1' if i == len(values) - 1 else 'neutral'
            out.append(bar(cx - bar_w / 2, base, bar_w, h, cls))
            out.append(text(cx, base - h - 8, fmt.format(v), 't1', 14, 'middle', '600'))

    label_y = top + 3 * row_h + 2 * row_gap + 30
    for i, (name, l1, l2) in enumerate(STAGES[lang]):
        cx = left + col_w * i + col_w / 2
        out.append(text(cx, label_y, f'{"①②③④⑤"[i]} {name}', 't1', 13, 'middle', '600'))
        out.append(text(cx, label_y + 20, l1, 't2', 12, 'middle'))
        out.append(text(cx, label_y + 37, l2, 't2', 12, 'middle'))
    return svg(W, H, ''.join(out), t['title'])


def lvgl_chart(lang):
    t = TEXT[lang]
    W, H = 960, 250
    left, bar_max, bh = 230, 560, 22
    out = [text(32, 44, t['lvgl_title'], size=18, weight='600')]
    # legend
    out.append(f'<rect class="neutral" x="{W - 300}" y="32" width="14" height="14" rx="3"/>')
    out.append(text(W - 280, 44, t['cpu'], 't2', 13))
    out.append(f'<rect class="s1" x="{W - 170}" y="32" width="14" height="14" rx="3"/>')
    out.append(text(W - 150, 44, t['ppa'], 't2', 13))
    metrics = [(LVGL['render_ms'], 50, t['lvgl_rows'][0], t['lvgl_units'][0], '{:.0f}'),
               (LVGL['refresh_per_s'], 30, t['lvgl_rows'][1], t['lvgl_units'][1], '{:.1f}')]
    for mi, ((before, after), vmax, name, unit, fmt) in enumerate(metrics):
        y = 80 + mi * 82
        out.append(text(32, y + 20, name, 't1', 14, weight='600'))
        out.append(text(32, y + 40, unit, 't3', 12))
        for k, (v, cls) in enumerate(((before, 'neutral'), (after, 's1'))):
            by = y + k * (bh + 6)
            w = v / vmax * bar_max
            out.append(hbar(left, by, w, bh, cls))
            out.append(text(left + w + 8, by + 16, fmt.format(v), 't1', 13, weight='600'))
        out.append(f'<line class="axis" x1="{left}" y1="{y - 4}" x2="{left}" y2="{y + 2 * bh + 10}"/>')
    return svg(W, H, ''.join(out), t['lvgl_title'])


def arch_chart(lang):
    t = TEXT[lang]
    W, H = 960, 470
    lane_x, lane_w = 230, 700
    out = [text(32, 44, t['arch_title'], size=20, weight='600')]

    def lane(y, title):
        out.append(text(32, y + 24, title, 't2', 13, weight='600'))

    def block(x, y, w, label, cls='box', h=36):
        out.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="6" stroke-width="1.5"/>')
        out.append(text(x + w / 2, y + h / 2 + 5, label, 't1', 12.5, 'middle'))

    def section(y, title, rows):
        out.append(text(32, y, title, 't1', 16, weight='700'))
        for i, (lane_title, blocks) in enumerate(rows):
            ly = y + 14 + i * 50
            lane(ly, lane_title)
            x = lane_x
            for w, label, cls in blocks:
                block(x, ly + 4, w, label, cls)
                x += w + 10
        return y + 14 + len(rows) * 50

    y = section(90, t['before'], [
        (t['core0'], [(210, t['b_ppa'], 'box'), (360, t['b_inf'], 'boxacc'), (110, t['b_draw'], 'box')]),
        (t['core1'], [(700, t['idle'], 'box')]),
        (t['lvgl'], [(300, t['b_lvgl'], 'boxacc')]),
    ])
    out.append(f'<line class="grid" x1="32" y1="{y + 8}" x2="{W - 32}" y2="{y + 8}"/>')
    section(y + 46, t['after'], [
        (t['core0'], [(210, t['a_ppa'], 'box'), (280, t['a_ppa2'], 'boxs1'), (190, t['a_draw'], 'box')]),
        (t['core1'], [(320, t['a_inf'], 'boxs1')]),
        (t['lvgl'], [(240, t['a_lvgl'], 'boxs1')]),
    ])
    return svg(W, H, ''.join(out), t['arch_title'])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for lang in ('ko', 'en'):
        (OUT / f'perf_steps_{lang}.svg').write_text(steps_chart(lang), encoding='utf-8')
        (OUT / f'perf_lvgl_{lang}.svg').write_text(lvgl_chart(lang), encoding='utf-8')
        (OUT / f'pipeline_{lang}.svg').write_text(arch_chart(lang), encoding='utf-8')
    for p in sorted(OUT.glob('*.svg')):
        print(p)


if __name__ == '__main__':
    main()

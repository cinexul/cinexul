#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
暗室渲染器 · cinexul/cinexul
============================
把 profile/live.json 里的数据冲洗成 assets/ 下的一组手写动画 SVG。

原理:GitHub README 的 HTML 会被 sanitizer 剥掉一切 <style>/<script>/style=,
但 <img> 引用的 SVG 在浏览器里是一份独立文档——它内部的 <style>、CSS 动画、
SMIL 动画、滤镜、渐变、蒙版全部生效(JS 与外链资源除外)。
于是整个"页面"被做成若干张 SVG 海报,README 只负责排版与链接。

零第三方依赖(仅标准库);同一份 live.json 渲染结果字节级可复现
(伪随机数用定长种子的 mulberry32,连噪点 PNG 都是自己编码的)。

设计令牌沿用「雨夜车窗」提案 + cinexul.com「信号与放学后」:
墨蓝夜色 / 路灯琥珀 / 尾灯红 / 雾蓝 / 磷光薄荷,等宽小字宽字距,衬线中文。
"""

from __future__ import annotations

import base64
import json
import math
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

# ───────────────────────── 设计令牌 ─────────────────────────

INK0, INK1, INK2 = "#04060b", "#071019", "#0c1622"
TEXT = "#e9eef4"
MUTED = "rgba(233,238,244,0.66)"
FAINT = "rgba(233,238,244,0.42)"
GHOST = "rgba(233,238,244,0.22)"
LINE = "rgba(233,238,244,0.13)"
LINE_SOFT = "rgba(233,238,244,0.08)"
LAMP, LAMP_HI = "#f2c069", "#f6d9a4"
TAIL = "#d24a41"
FOG = "#7fa3b2"
CREAM = "#e9e3d2"
PHOS = "#7ee8cf"          # CRT 磷光(薄荷偏青)
PHOS_DIM = "#4f9d8d"
MAGENTA = "#ff2e9b"       # 糖果品红,整页只许出现一粒
VIOLET = "#b48bff"

# 浅色主题(阅读模式纸面,用于跟随 GitHub 亮色主题的小件)
L_INK = "#2b2a25"
L_MUTED = "rgba(43,42,37,0.62)"
L_FAINT = "rgba(43,42,37,0.40)"
L_LINE = "rgba(43,42,37,0.16)"
L_ACCENT = "#c2613f"      # 陶土

MONO = "'JetBrains Mono','SFMono-Regular','Cascadia Code',Menlo,Consolas,'Liberation Mono',monospace"
SERIF = "'Noto Serif SC','Songti SC','STSong','SimSun','Yu Mincho','MS Mincho',serif"

EASE = "cubic-bezier(0.22,0.61,0.36,1)"

LANG_COLORS = {
    "Svelte": TAIL, "TypeScript": FOG, "Rust": LAMP, "JavaScript": CREAM,
    "CSS": VIOLET, "Python": PHOS_DIM, "HTML": "#e8b4a0", "Shell": "#8b90ad",
    "Go": "#69c7b8", "C": "#9aa7c7",
}
LANG_FALLBACK = [LAMP, FOG, TAIL, CREAM, VIOLET, PHOS_DIM]


# ───────────────────────── 基础设施 ─────────────────────────

class Mulberry32:
    """与提案 HTML 同款的确定性伪随机(种子相同则输出相同)。"""

    def __init__(self, seed: int):
        self.a = seed & 0xFFFFFFFF

    def __call__(self) -> float:
        self.a = (self.a + 0x6D2B79F5) & 0xFFFFFFFF
        t = self.a
        t = (t ^ (t >> 15)) * (t | 1) & 0xFFFFFFFF
        t = (t + ((t ^ (t >> 7)) * (t | 61) & 0xFFFFFFFF)) ^ t
        t &= 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296


def esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def fnum(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s if s else "0"


def noise_png(size: int = 160, seed: int = 20260707, tint=(202, 216, 229), max_alpha: int = 26) -> str:
    """手工编码一张雾蓝色调的胶片颗粒 RGBA PNG,返回 data URI。

    比在 SVG 里放一个实时 feTurbulence 便宜得多:噪点是静态贴图,
    动画只是整层做 steps() 平移抖动,浏览器只需重合成、不用重滤镜。
    """
    rng = Mulberry32(seed)
    raw = bytearray()
    r, g, b = tint
    for _ in range(size):
        raw.append(0)  # filter: None
        for _ in range(size):
            v = rng()
            a = int(v * v * max_alpha)
            raw += bytes((r, g, b, a))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))
    return "data:image/png;base64," + base64.b64encode(png).decode()


GRAIN_URI = noise_png()

REDUCED = ("@media (prefers-reduced-motion:reduce){*{animation:none !important}"
           ".rm-hide{display:none}}")


def svg_open(w: int, h: int, label: str, css: str, defs: str = "") -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'width="{w}" height="{h}" role="img" aria-label="{esc(label)}">\n'
            f"<style>{css}{REDUCED}</style>\n<defs>{defs}</defs>\n")


def grain_defs(pid: str = "grain") -> str:
    return (f'<pattern id="{pid}" width="160" height="160" patternUnits="userSpaceOnUse">'
            f'<image href="{GRAIN_URI}" width="160" height="160"/></pattern>')


def scan_defs(pid: str = "scan", alpha: float = 0.05) -> str:
    return (f'<pattern id="{pid}" width="2" height="4" patternUnits="userSpaceOnUse">'
            f'<rect width="2" height="1" fill="rgba(127,163,178,{alpha})"/></pattern>')


GRAIN_CSS = (".grain{animation:gj .55s steps(1,end) infinite}"
             "@keyframes gj{0%{transform:translate(0,0)}20%{transform:translate(-46px,33px)}"
             "40%{transform:translate(38px,-21px)}60%{transform:translate(-12px,-44px)}"
             "80%{transform:translate(26px,15px)}100%{transform:translate(0,0)}}")


def text_el(x, y, size, fill, content, *, ls=None, ff=MONO, anchor=None,
            weight=None, cls=None, opacity=None, extra="") -> str:
    a = [f'x="{fnum(x)}"', f'y="{fnum(y)}"', f'font-size="{fnum(size)}"',
         f'fill="{fill}"', f'font-family="{ff}"']
    if ls is not None:
        a.append(f'letter-spacing="{ls}"')
    if anchor:
        a.append(f'text-anchor="{anchor}"')
    if weight:
        a.append(f'font-weight="{weight}"')
    if cls:
        a.append(f'class="{cls}"')
    if opacity is not None:
        a.append(f'opacity="{opacity}"')
    if extra:
        a.append(extra)
    return f"<text {' '.join(a)}>{content}</text>"


def human_bytes(n: int) -> str:
    if n >= 1 << 20:
        return f"{n / (1 << 20):.1f} MB"
    if n >= 1 << 10:
        return f"{n / (1 << 10):.0f} KB"
    return f"{n} B"


def trunc(s: str, limit: int) -> str:
    """CJK 记 1、半角记 0.55 的近似宽度截断。"""
    w, out = 0.0, []
    for ch in s:
        w += 1 if ord(ch) > 0x2E80 else 0.55
        if w > limit:
            return "".join(out) + "…"
        out.append(ch)
    return s


# ═══════════════════════ 01 · 雨夜车窗 hero ═══════════════════════

def gen_hero(cfg: dict, live: dict) -> str:
    W, H = 1000, 460
    rng = Mulberry32(20260707)
    css = [GRAIN_CSS]
    body = []

    defs = [
        '<linearGradient id="bg" x1="0" y1="0" x2="0.22" y2="1">'
        f'<stop offset="0" stop-color="#0a1523"/><stop offset="0.44" stop-color="{INK1}"/>'
        f'<stop offset="1" stop-color="{INK0}"/></linearGradient>',
        '<radialGradient id="vig" cx="0.5" cy="0.46" r="0.72">'
        '<stop offset="0.55" stop-color="rgba(1,4,9,0)"/>'
        '<stop offset="1" stop-color="rgba(1,4,9,0.55)"/></radialGradient>',
        # 水珠是小透镜:芯比玻璃暗,边缘薄亮,底部映着街灯
        '<radialGradient id="dcore" cx="0.5" cy="0.42" r="0.62">'
        '<stop offset="0" stop-color="rgba(2,6,13,0.60)"/>'
        '<stop offset="0.55" stop-color="rgba(8,17,30,0.34)"/>'
        '<stop offset="0.85" stop-color="rgba(150,182,208,0.08)"/>'
        '<stop offset="1" stop-color="rgba(198,222,242,0.30)"/></radialGradient>',
        '<radialGradient id="dstreet" cx="0.5" cy="0.5" r="0.5">'
        f'<stop offset="0" stop-color="{LAMP}" stop-opacity="0.55"/>'
        f'<stop offset="0.6" stop-color="{LAMP}" stop-opacity="0.16"/>'
        f'<stop offset="1" stop-color="{LAMP}" stop-opacity="0"/></radialGradient>',
        '<linearGradient id="dwet" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="rgba(190,215,235,0)"/>'
        '<stop offset="1" stop-color="rgba(190,215,235,0.11)"/></linearGradient>',
        '<linearGradient id="ttrail" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="rgba(210,74,65,0)"/>'
        f'<stop offset="1" stop-color="rgba(210,74,65,0.55)"/></linearGradient>',
        grain_defs(), scan_defs(),
        '<filter id="b6" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="6"/></filter>',
        '<filter id="b14" x="-90%" y="-90%" width="280%" height="280%"><feGaussianBlur stdDeviation="14"/></filter>',
        '<filter id="tglow"><feDropShadow dx="0" dy="0" stdDeviation="7" flood-color="rgba(242,192,105,0.30)"/></filter>',
        f'<clipPath id="glass"><rect x="14" y="14" width="{W-28}" height="{H-28}" rx="8"/></clipPath>',
    ]

    # 底色 + 地平线光
    body.append(f'<rect width="{W}" height="{H}" fill="url(#bg)" rx="8"/>')
    body.append(f'<ellipse cx="500" cy="332" rx="430" ry="86" fill="{FOG}" opacity="0.05" filter="url(#b14)"/>')
    body.append(f'<ellipse cx="470" cy="338" rx="300" ry="38" fill="{LAMP}" opacity="0.055" filter="url(#b14)"/>')

    # 远处灯火(散景)
    css.append("@keyframes drift{50%{transform:translate(var(--dx),var(--dy))}}"
               "@keyframes flick{0%,100%{opacity:var(--o)}50%{opacity:calc(var(--o)*0.55)}}"
               ".bok{animation:drift var(--dd) ease-in-out infinite alternate,"
               "flick var(--fd) ease-in-out infinite}")
    palette = [LAMP] * 7 + [TAIL] * 2 + [FOG] * 2 + [CREAM] * 2
    for i, col in enumerate(palette):
        x = 60 + rng() * 880
        y = 300 + rng() * 46
        r = 4 + rng() * rng() * 15
        o = 0.10 + rng() * 0.22
        dx, dy = (rng() - 0.5) * 22, (rng() - 0.5) * 8
        dd, fd = 16 + rng() * 18, 5 + rng() * 6
        body.append(
            f'<circle class="bok" cx="{fnum(x)}" cy="{fnum(y)}" r="{fnum(r)}" fill="{col}" '
            f'filter="url(#b6)" style="--o:{fnum(o)};--dx:{fnum(dx)}px;--dy:{fnum(dy)}px;'
            f'--dd:{fnum(dd)}s;--fd:{fnum(fd)}s;opacity:{fnum(o)};'
            f'animation-delay:{fnum(-rng() * 20)}s,{fnum(-rng() * 6)}s"/>')
    # 一粒品红:整页唯一的糖果色(信号灯)
    body.append(f'<circle class="bok" cx="806" cy="309" r="2.6" fill="{MAGENTA}" filter="url(#b6)" '
                f'style="--o:0.5;--dx:6px;--dy:-3px;--dd:21s;--fd:3.8s;opacity:0.5"/>')

    # 水面/湿路反光条
    for _ in range(9):
        x = 80 + rng() * 840
        w = 1 + rng() * 2.2
        col = LAMP if rng() < 0.6 else (TAIL if rng() < 0.5 else FOG)
        body.append(f'<rect x="{fnum(x)}" y="340" width="{fnum(w)}" height="{fnum(60 + rng() * 55)}" '
                    f'fill="{col}" opacity="{fnum(0.03 + rng() * 0.05)}"/>')

    # 末班车尾灯:26 秒横穿一次
    css.append("@keyframes transit{0%{transform:translateX(-120px)}"
               "12%{transform:translateX(-120px)}88%{transform:translateX(1120px)}"
               "100%{transform:translateX(1120px)}}"
               ".transit{animation:transit 26s linear infinite}")
    body.append('<g class="transit" clip-path="url(#glass)"><g transform="translate(0,334)">'
                f'<rect x="-64" y="-1" width="62" height="2" fill="url(#ttrail)"/>'
                f'<circle r="3" fill="{TAIL}"/><circle r="7" fill="{TAIL}" opacity="0.4" filter="url(#b6)"/>'
                "</g></g>")

    # 雨(两层深度,整体 9° 斜落)
    css.append("@keyframes rfall{to{transform:translateY(640px)}}")
    rain = ['<g clip-path="url(#glass)"><g transform="rotate(9 500 230)">']
    for depth, (n, wd, lo, hi, dur) in enumerate(
            [(46, 1.0, 0.045, 0.085, 1.25), (24, 1.7, 0.10, 0.16, 0.72)]):
        for _ in range(n):
            x = -60 + rng() * 1120
            y0 = -640 + rng() * 640
            ln = (26 if depth == 0 else 42) + rng() * (24 if depth == 0 else 26)
            d = dur * (0.82 + rng() * 0.4)
            rain.append(
                f'<line x1="{fnum(x)}" y1="{fnum(y0)}" x2="{fnum(x)}" y2="{fnum(y0 + ln)}" '
                f'stroke="#cfe0ea" stroke-width="{wd}" opacity="{fnum(lo + rng() * (hi - lo))}" '
                f'style="animation:rfall {fnum(d)}s linear {fnum(-rng() * d)}s infinite"/>')
    rain.append("</g></g>")
    body.append("".join(rain))

    # ── 玻璃凝水珠 ──
    # 真实感的三个关键:① 水珠是透镜,芯比玻璃暗、边缘一圈薄亮;
    # ② 底部映着街灯的琥珀(越靠近下方的珠越亮);③ 滑落是蠕动式的
    # "黏住—挣脱—再黏住",走过的地方留一道湿痕和残珠。
    def blob(rr: float, seed_phase: float) -> tuple[str, str, list]:
        """不规则水珠轮廓(闭合平滑曲线)、底缘弧线,以及原始点集。"""
        pts = []
        n = 12
        w1, w2 = 0.05 + rng() * 0.05, 0.04 + rng() * 0.04
        p1, p2 = rng() * 6.28, rng() * 6.28
        for j in range(n):
            th = -math.pi / 2 + j / n * math.pi * 2
            rad = rr * (1 + w1 * math.sin(2 * th + p1) + w2 * math.sin(3 * th + p2))
            px = rad * math.cos(th) * 0.94
            py = rad * math.sin(th) * 1.16
            if math.sin(th) < 0:                       # 上半收窄,略呈垂滴形
                px *= 1 - 0.10 * (-math.sin(th))
            pts.append((px, py))
        mids = [((pts[j][0] + pts[(j + 1) % n][0]) / 2,
                 (pts[j][1] + pts[(j + 1) % n][1]) / 2) for j in range(n)]
        d = f"M{fnum(mids[-1][0])},{fnum(mids[-1][1])}"
        for j in range(n):
            d += f" Q{fnum(pts[j][0])},{fnum(pts[j][1])} {fnum(mids[j][0])},{fnum(mids[j][1])}"
        d += "Z"
        lower = [p for p in pts if p[1] > rr * 0.30]
        lower.sort(key=lambda p: math.atan2(p[1], p[0]))
        arc = f"M{fnum(lower[0][0])},{fnum(lower[0][1])}" + "".join(
            f" L{fnum(p[0])},{fnum(p[1])}" for p in lower[1:])
        return d, arc, pts

    css.append("@keyframes dfade{0%,3%{opacity:0}9%,80%{opacity:1}95%,100%{opacity:0}}")
    drops = ['<g clip-path="url(#glass)">']
    for i in range(11):
        x = 50 + rng() * 900
        y = 28 + rng() * 150
        s = 0.34 + rng() * 0.30          # 小珠:半径约 3.4~6.4px
        dur = 12 + rng() * 9
        # 写实轨迹(程序生成):黏住(久)→ 挣脱前微微下探 → 突然加速滑一段
        # → 再黏住;每次挣脱带横向游移,每滑一段失一点体积。
        # 关键帧内嵌 timing-function:挣脱段先加速后收,黏滞段几乎不动。
        kp = ["0%{transform:translate(0px,0px) scale(1)}"]
        p, ycur, xcur, sc = 0.0, 0.0, 0.0, 1.0
        while True:
            pause = 9 + rng() * 14
            if p + pause > 84 or ycur > 250:
                break
            p += pause
            kp.append(f"{fnum(p)}%{{transform:translate({fnum(xcur + (rng() - 0.5) * 0.9)}px,"
                      f"{fnum(ycur + 1.2 + rng() * 2.2)}px) scale({fnum(sc)});"
                      "animation-timing-function:cubic-bezier(0.6,0,0.8,0.35)}")
            p += 2.2 + rng() * 2.6
            ycur += 40 + rng() * 90
            xcur += (rng() - 0.5) * 6.0
            sc *= 0.93
            kp.append(f"{fnum(p)}%{{transform:translate({fnum(xcur)}px,{fnum(ycur)}px) "
                      f"scale({fnum(sc)});animation-timing-function:cubic-bezier(0.2,0.55,0.35,1)}}")
        kp.append(f"100%{{transform:translate({fnum(xcur + (rng() - 0.5) * 2)}px,"
                  f"{fnum(ycur + 46)}px) scale({fnum(sc * 0.95)})}}")
        css.append(f"@keyframes slip{i}{{{''.join(kp)}}}")
        d, arc, _ = blob(10, rng() * 6.28)
        defs.append(f'<clipPath id="dc{i}"><path d="{d}"/></clipPath>')
        street = 0.22 + 0.42 * (y / H)                 # 越低越接近街灯,映光越亮
        drops.append(
            f'<g style="animation:slip{i} {fnum(dur)}s {EASE} {fnum(-rng() * dur)}s infinite,'
            f'dfade {fnum(dur)}s linear {fnum(-rng() * dur)}s infinite" opacity="0">'
            f'<g transform="translate({fnum(x)},{fnum(y)}) scale({fnum(s)})">'
            # 湿痕与残珠(拖在上方,窄而淡)
            '<path d="M-0.8,-8 L-0.5,-24 Q0,-26 0.5,-24 L0.8,-8 Z" fill="url(#dwet)"/>'
            f'<circle cx="{fnum((rng() - 0.5) * 1.6)}" cy="-14" r="0.7" fill="rgba(190,215,235,0.10)"/>'
            f'<circle cx="{fnum((rng() - 0.5) * 2)}" cy="-20" r="0.55" fill="rgba(190,215,235,0.08)"/>'
            # 珠体:暗芯透镜 + 街灯月牙 + 底缘薄亮 + 高光
            f'<path d="{d}" fill="url(#dcore)" stroke="rgba(233,238,244,0.10)" stroke-width="0.6"/>'
            f'<ellipse cx="0" cy="6.4" rx="7.0" ry="4.6" fill="url(#dstreet)" '
            f'opacity="{fnum(street)}" clip-path="url(#dc{i})"/>'
            f'<path d="{arc}" fill="none" stroke="rgba(220,238,250,0.44)" stroke-width="1.1" '
            'stroke-linecap="round"/>'
            '<ellipse cx="-2.7" cy="-3.6" rx="2.0" ry="1.25" fill="rgba(255,255,255,0.62)" '
            'transform="rotate(-24 -2.7 -3.6)"/>'
            '<circle cx="-1.15" cy="-4.9" r="0.5" fill="rgba(255,255,255,0.72)"/>'
            "</g></g>")
    # 静止微水珠(玻璃上的凝露背景,含少量竖长珠与成簇)
    css.append("@keyframes shim{50%{opacity:0.16}}")
    for _ in range(36):
        cluster = rng() < 0.3
        bx, by = 20 + rng() * 960, 20 + rng() * 400
        for _ in range(3 if cluster else 1):
            x2, y2 = bx + (rng() - 0.5) * 26, by + (rng() - 0.5) * 20
            r = 0.6 + rng() * rng() * 2.1
            tall = rng() < 0.4
            extra = (f' style="animation:shim {fnum(4 + rng() * 5)}s ease-in-out '
                     f'{fnum(-rng() * 5)}s infinite"') if rng() < 0.35 else ""
            if tall:
                drops.append(f'<ellipse cx="{fnum(x2)}" cy="{fnum(y2)}" rx="{fnum(r * 0.72)}" '
                             f'ry="{fnum(r * 1.35)}" fill="#cfe0ea" opacity="0.115"{extra}/>')
            else:
                drops.append(f'<circle cx="{fnum(x2)}" cy="{fnum(y2)}" r="{fnum(r)}" '
                             f'fill="#cfe0ea" opacity="0.12"{extra}/>')
            if r > 1.7:
                drops.append(f'<circle cx="{fnum(x2 - r * 0.3)}" cy="{fnum(y2 - r * 0.4)}" r="0.4" '
                             'fill="rgba(255,255,255,0.30)"/>')
    drops.append("</g>")
    body.append("".join(drops))

    # ── 文字层 ──(全 CSS,不依赖 SMIL:逐字出现 + 光标 steps 跳步)
    name = cfg["login"]
    fs = 46
    adv = fs * 0.602 + fs * 0.26          # 等宽字宽 + letter-spacing
    x0, base = 78, 178
    n = len(name)
    step = 0.13
    css.append("@keyframes tchar{to{opacity:1}}"
               ".tchar{opacity:0;animation:tchar 0.01s steps(1,end) both}")
    chars = [text_el(x0 + i * adv, base, fs, CREAM, esc(ch), weight="500", cls="tchar",
                     extra=f'style="animation-delay:{fnum(0.6 + i * step)}s"')
             for i, ch in enumerate(name)]
    body.append(f'<g filter="url(#tglow)">{"".join(chars)}</g>')
    css.append("@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}"
               f"@keyframes cadv{{to{{transform:translateX({fnum(n * adv)}px)}}}}"
               ".cursor{animation:blink 1.12s steps(1,end) infinite,"
               f"cadv {fnum(n * step)}s steps({n},end) 0.6s forwards}}")
    body.append(f'<rect class="cursor" x="{fnum(x0 + 4)}" y="{base - fs + 8}" width="21" height="{fs - 4}" '
                f'fill="{LAMP}" opacity="0.85"/>')

    # 显影副标题(整行从虚焦里洗出来,CSS filter 动画)
    css.append("@keyframes dev{from{opacity:0;filter:blur(9px)}to{opacity:1;filter:blur(0px)}}"
               f".dev{{animation:dev 2s {EASE} 1s both}}")
    body.append('<g class="dev">'
                + text_el(x0 + 2, 226, 21, MUTED, esc(cfg["tagline_cjk"]), ls="0.14em", ff=SERIF)
                + "</g>")
    body.append(text_el(x0 + 3, 258, 9.5, FAINT,
                        esc(f"CRAFTSMAN BEFORE PROGRAMMER · THE KNIFE CHANGED, NOT THE HANDS · EST. {live['est_year']}"),
                        ls="0.3em"))

    # 角标与取景框
    body.append(f'<rect x="14" y="14" width="{W-28}" height="{H-28}" rx="8" fill="none" stroke="{LINE}"/>')
    tick = []
    for cx, cy, sx, sy in [(30, 30, 1, 1), (W - 30, 30, -1, 1), (30, H - 30, 1, -1), (W - 30, H - 30, -1, -1)]:
        tick.append(f'<path d="M{cx + 12 * sx} {cy}H{cx}V{cy + 12 * sy}" fill="none" '
                    f'stroke="{FAINT}" stroke-width="1.2"/>')
    body.append("".join(tick))
    body.append(text_el(W - 44, 40, 8.5, FAINT, esc(f"{live['develop_date'][:4]} · 雨夜 · 车窗"),
                        ls="0.3em", anchor="end"))

    # EXIF 与显影批号
    body.append(text_el(x0, H - 40, 10, FAINT,
                        esc("50mm · ƒ/1.4 · 1/30s · ISO 3200 · 手持 · 隔着车窗玻璃"), ls="0.12em"))
    css.append("@keyframes sig{50%{opacity:0.25}}.sig{animation:sig 2.2s ease-in-out infinite}")
    sig_text = f"SIG №{live['develop_no']:03d} · LAST DEVELOP {live['develop_ts']}"
    sig_w = len(sig_text) * 9.5 * (0.602 + 0.14)
    body.append(f'<circle class="sig" cx="{fnum(W - 44 - sig_w - 14)}" cy="{H - 44}" r="2.4" fill="{MAGENTA}"/>')
    body.append(text_el(W - 44, H - 40, 9.5, FAINT, esc(sig_text), ls="0.14em", anchor="end"))

    # 颗粒 / 扫描线 / 暗角
    body.append(f'<g clip-path="url(#glass)"><rect class="grain" x="-200" y="-200" '
                f'width="{W + 400}" height="{H + 400}" fill="url(#grain)" opacity="0.5"/></g>')
    body.append(f'<rect x="14" y="14" width="{W-28}" height="{H-28}" rx="8" fill="url(#scan)"/>')
    body.append(f'<rect width="{W}" height="{H}" rx="8" fill="url(#vig)"/>')

    return (svg_open(W, H, "cinexul — 暗室里还亮着一台机器(雨夜车窗动画头图)",
                     "".join(css), "".join(defs)) + "\n".join(body) + "\n</svg>\n")


# ═══════════════════════ 02 · 以光为弦(语言) ═══════════════════════

def gen_strings(live: dict) -> str:
    langs = live["languages"][:6]
    total = sum(x["bytes"] for x in langs) or 1
    n = len(langs)
    row, top, bottom = 47, 84, 42
    W, H = 1000, top + n * row + bottom
    x1, x2 = 168, 846
    cycle = max(n * 3.8, 12)

    css = [GRAIN_CSS,
           "@keyframes sweep{0%{stroke-dashoffset:764;opacity:0}"
           "0.7%{opacity:0.9}7.6%{stroke-dashoffset:-84;opacity:0.9}"
           "8.6%,100%{stroke-dashoffset:-84;opacity:0}}",
           "@keyframes gk{0%{opacity:0.3}1.2%{opacity:0.8}8.3%,100%{opacity:0.3}}"]
    defs = [grain_defs(), scan_defs("scan2", 0.035),
            '<filter id="sb3" x="-40%" y="-400%" width="180%" height="900%">'
            '<feGaussianBlur stdDeviation="2.6"/></filter>',
            '<radialGradient id="svig" cx="0.5" cy="0.5" r="0.75">'
            '<stop offset="0.6" stop-color="rgba(1,4,9,0)"/>'
            '<stop offset="1" stop-color="rgba(1,4,9,0.42)"/></radialGradient>']
    body = [f'<rect width="{W}" height="{H}" rx="8" fill="{INK1}"/>',
            f'<rect x="10" y="10" width="{W-20}" height="{H-20}" rx="6" fill="none" stroke="{LINE_SOFT}"/>']

    # 表头
    body.append(text_el(40, 46, 14.5, TEXT, "以光为弦", ls="0.3em", ff=SERIF))
    body.append(text_el(158, 46, 8.5, FAINT, "TOP LANGUAGES — EVERY LANGUAGE, A STRING OF LIGHT", ls="0.3em"))
    body.append(text_el(W - 40, 46, 8.5, FAINT, esc("每 6 小时自动重新调音 · RETUNED BY ACTIONS"),
                        ls="0.22em", anchor="end"))
    body.append(f'<line x1="40" y1="60" x2="{W-40}" y2="60" stroke="{LINE_SOFT}"/>')

    # 竖直刻度
    for gx in range(x1, x2 + 1, 68):
        body.append(f'<line x1="{gx}" y1="{top - 8}" x2="{gx}" y2="{H - bottom + 4}" '
                    f'stroke="rgba(233,238,244,0.045)"/>')

    for i, item in enumerate(langs):
        y = top + i * row + 22
        pct = item["bytes"] / total * 100
        col = LANG_COLORS.get(item["name"], LANG_FALLBACK[i % len(LANG_FALLBACK)])
        sw = 1.1 + (item["bytes"] / total) * 4.6
        gid = f"lg{i}"
        defs.append(
            f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{x1}" y1="0" x2="{x2}" y2="0">'
            f'<stop offset="0" stop-color="{col}" stop-opacity="0"/>'
            f'<stop offset="0.1" stop-color="{col}" stop-opacity="0.85"/>'
            f'<stop offset="0.5" stop-color="{LAMP_HI if col == LAMP else col}" stop-opacity="1"/>'
            f'<stop offset="0.9" stop-color="{col}" stop-opacity="0.85"/>'
            f'<stop offset="1" stop-color="{col}" stop-opacity="0"/></linearGradient>')

        straight = f"M{x1},{y} Q{(x1 + x2) // 2},{y} {x2},{y}"
        begin = fnum(i * 3.8)
        # 拨弦 = 一段亮光沿弦扫过(dasharray 位移)+ 弦身瞬间变粗再回弹,全 CSS
        css.append(
            f"@keyframes pk{i}{{0%{{stroke-width:{fnum(sw)}}}1%{{stroke-width:{fnum(sw * 2.1)}}}"
            f"4.2%{{stroke-width:{fnum(sw * 1.3)}}}8.3%,100%{{stroke-width:{fnum(sw)}}}}}")
        body.append(f'<path d="{straight}" stroke="url(#{gid})" stroke-width="{fnum(sw * 2.6)}" '
                    f'fill="none" stroke-linecap="round" opacity="0.3" filter="url(#sb3)" '
                    f'style="animation:gk {fnum(cycle)}s linear {begin}s infinite"/>')
        body.append(f'<path d="{straight}" stroke="url(#{gid})" stroke-width="{fnum(sw)}" '
                    f'fill="none" stroke-linecap="round" opacity="0.95" '
                    f'style="animation:pk{i} {fnum(cycle)}s {EASE} {begin}s infinite"/>')
        body.append(f'<path d="{straight}" pathLength="700" stroke="#fdfcf7" '
                    f'stroke-width="{fnum(max(sw * 1.15, 1.6))}" fill="none" stroke-linecap="round" '
                    f'stroke-dasharray="64 736" stroke-dashoffset="764" opacity="0" '
                    f'style="animation:sweep {fnum(cycle)}s linear {begin}s infinite"/>')

        body.append(text_el(x1 - 22, y + 4, 11.5, MUTED, esc(item["name"]), ls="0.14em", anchor="end"))
        body.append(text_el(x2 + 24, y + 4, 12.5, "rgba(233,238,244,0.85)", f"{pct:.1f}<tspan font-size=\"8\">%</tspan>",
                            ls="0.05em", extra='font-variant-numeric="tabular-nums"'))
        body.append(text_el(x2 + 24, y + 17, 7.5, FAINT, esc(human_bytes(item["bytes"])), ls="0.12em"))

    src = live.get("languages_source", "github api")
    body.append(text_el(40, H - 18, 8, FAINT,
                        esc(f"公开仓库字节占比 · {src} · 弦粗 = 占比 · 每根弦轮流被拨一次"), ls="0.18em"))
    body.append(f'<rect width="{W}" height="{H}" rx="8" fill="url(#svig)"/>')
    body.append(f'<g clip-path="none"><rect class="grain" x="-200" y="-200" width="{W+400}" height="{H+400}" '
                'fill="url(#grain)" opacity="0.35"/></g>')
    body.append(f'<rect width="{W}" height="{H}" rx="8" fill="url(#scan2)"/>')
    return (svg_open(W, H, "以光为弦 — 语言占比可视化(每根弦轮流振动)",
                     "".join(css), "".join(defs)) + "\n".join(body) + "\n</svg>\n")


# ═══════════════════════ 展签(展品说明牌) ═══════════════════════

def gen_plaque(cfg: dict, live: dict) -> str:
    W, H = 1000, 148
    ex = cfg["exhibit"]
    css = ["@keyframes hp{50%{opacity:0.25}}.hp{animation:hp 4.2s ease-in-out infinite}"]
    defs = [grain_defs()]
    body = [f'<rect width="{W}" height="{H}" rx="8" fill="{INK1}"/>',
            f'<rect x="10" y="10" width="{W-20}" height="{H-20}" rx="6" fill="none" stroke="{LINE_SOFT}"/>']
    # 左:展品编号与名称
    body.append(text_el(44, 46, 8.5, FAINT, esc(f"展品 №{ex['no']} · EXHIBIT"), ls="0.3em"))
    body.append(text_el(44, 82, 23, TEXT, esc(ex["title"]), ls="0.22em", ff=SERIF))
    body.append(text_el(44, 110, 8, FAINT, esc(ex["title_en"]), ls="0.3em"))
    body.append(f'<line x1="330" y1="30" x2="330" y2="{H-30}" stroke="{LINE_SOFT}"/>')
    # 中:工艺参数(博物馆式说明)
    for i, spec in enumerate(ex["specs"]):
        y = 46 + i * 21
        body.append(text_el(362, y, 9, "rgba(233,238,244,0.36)", esc(spec[0]), ls="0.24em"))
        body.append(text_el(438, y, 9.5, MUTED, esc(spec[1]), ls="0.1em"))
    body.append(f'<line x1="694" y1="30" x2="694" y2="{H-30}" stroke="{LINE_SOFT}"/>')
    # 右:一句话
    for i, ln in enumerate(ex["quote"]):
        body.append(text_el(W - 48, 60 + i * 27, 12.5, MUTED, esc(ln), ls="0.14em",
                            ff=SERIF, anchor="end"))
    body.append(f'<rect class="hp" x="{W-56}" y="{H-44}" width="7" height="7" '
                f'transform="rotate(45 {W-52.5} {H-40.5})" fill="{LAMP}" opacity="0.7"/>')
    body.append(f'<rect class="grain" x="-200" y="-200" width="{W+400}" height="{H+400}" '
                'fill="url(#grain)" opacity="0.35"/>')
    css.append(GRAIN_CSS)
    return (svg_open(W, H, f"展签:{ex['title']} — {ex['title_en']}", "".join(css), "".join(defs))
            + "\n".join(body) + "\n</svg>\n")


# ═══════════════════════ 04 · CRT 终端 ═══════════════════════

def gen_terminal(cfg: dict, live: dict) -> str:
    W, H = 1000, 312
    css = [
        "@keyframes crtflick{0%,100%{opacity:1}50%{opacity:0.986}}"
        ".crt{animation:crtflick 0.14s steps(2,end) infinite}",
        "@keyframes band{from{transform:translateY(-70px)}to{transform:translateY(330px)}}"
        ".band{animation:band 7.5s linear infinite}",
        "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}.cursor{animation:blink 1.06s steps(1,end) infinite}",
    ]
    defs = [
        scan_defs("scan3", 0.06), grain_defs(),
        '<filter id="phos"><feDropShadow dx="0" dy="0" stdDeviation="5" flood-color="rgba(126,232,207,0.35)"/></filter>',
        '<linearGradient id="bandg" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="rgba(210,240,230,0)"/>'
        '<stop offset="0.5" stop-color="rgba(210,240,230,0.028)"/>'
        '<stop offset="1" stop-color="rgba(210,240,230,0)"/></linearGradient>',
        '<radialGradient id="tube" cx="0.5" cy="0.42" r="0.9">'
        '<stop offset="0.62" stop-color="rgba(2,8,7,0)"/>'
        '<stop offset="1" stop-color="rgba(2,8,7,0.5)"/></radialGradient>',
        f'<clipPath id="screen"><rect x="26" y="22" width="{W-52}" height="{H-44}" rx="7"/></clipPath>',
    ]

    body = [f'<rect width="{W}" height="{H}" rx="10" fill="#081210"/>',
            f'<rect x="8" y="6" width="{W-16}" height="{H-12}" rx="9" fill="#04090b" '
            'stroke="rgba(233,238,244,0.10)"/>',
            f'<rect x="26" y="22" width="{W-52}" height="{H-44}" rx="7" fill="#050d0c"/>',
            '<g class="crt" clip-path="url(#screen)">']

    prompt_user, host = cfg["login"], "workshop"
    lang0 = live["languages"][0] if live["languages"] else {"name": "svelte", "bytes": 1}
    total = sum(x["bytes"] for x in live["languages"]) or 1
    lines = [
        [("p", f"{prompt_user}@{host}"), ("f", ":~ "), ("l", "$ "), ("t", "whoami")],
        [("o", cfg["whoami_cjk"])],
        [("p", f"{prompt_user}@{host}"), ("f", ":~ "), ("l", "$ "), ("t", "uptime")],
        [("o", f"{live['days_in_darkroom']} nights at the workbench · "
               f"load {lang0['name'].lower()} {lang0['bytes'] / total * 100:.0f}% · "
               f"{live['pushes_recent']} pushes recent")],
        [("p", f"{prompt_user}@{host}"), ("f", ":~ "), ("l", "$ "), ("t", "tail -f /var/log/craft.log")],
    ]
    for ln in cfg["craft_log"][:3]:
        lines.append([("d", f"[{ln['tag']}] "), ("o", ln["text"])])
    lines.append([("d", "[dev]   "),
                  ("o", f"develop №{live['develop_no']:03d} · assets re-rendered · {live['develop_ts']}")])

    colmap = {"p": PHOS, "f": "rgba(126,232,207,0.45)", "l": LAMP,
              "t": "#d9efe8", "o": "rgba(126,232,207,0.85)", "d": "rgba(242,192,105,0.8)"}
    x0, y0, lh, fsz = 46, 56, 22, 12.5
    char_w = fsz * 0.602

    def width_of(s: str) -> float:
        return sum((char_w * (1.66 if ord(c) > 0x2E80 else 1)) for c in s)

    # 打字原理:屏幕是纯色,给命令文本盖一块同色矩形,
    # 用 steps(字符数) 把矩形整块向右挪走 → 逐字揭开,无缝且纯 CSS。
    css.append("@keyframes pop{to{opacity:1}}.pop{opacity:0;animation:pop 0.01s steps(1,end) both}")
    t = 0.5
    text_parts, covers = [], []
    for i, segs in enumerate(lines):
        y = y0 + i * lh
        tspans = "".join(f'<tspan fill="{colmap[c]}">{esc(s)}</tspan>' for c, s in segs)
        typed = segs[-1][0] == "t"
        if typed:
            cmd = segs[-1][1]
            wpre = width_of("".join(s for _, s in segs[:-1]))
            wcmd = width_of(cmd)
            dur = len(cmd) * 0.055
            css.append(f"@keyframes cv{i}{{to{{transform:translateX({fnum(wcmd + 30)}px)}}}}"
                       f".cv{i}{{animation:cv{i} {fnum(dur)}s steps({len(cmd)},end) {fnum(t)}s forwards}}")
            covers.append(f'<rect class="cv{i}" x="{fnum(x0 + wpre - 2)}" y="{y - 16}" '
                          f'width="{fnum(wcmd + 26)}" height="{lh + 2}" fill="#050d0c"/>')
            text_parts.append(f'<g class="pop" style="animation-delay:{fnum(max(t - 0.02, 0))}s">'
                              f'<text x="{x0}" y="{y}" font-size="{fsz}" font-family="{MONO}" '
                              f'letter-spacing="0.04em">{tspans}</text></g>')
            t += dur + 0.3
        else:
            text_parts.append(f'<g class="pop" style="animation-delay:{fnum(t)}s">'
                              f'<text x="{x0}" y="{y}" font-size="{fsz}" font-family="{MONO}" '
                              f'letter-spacing="0.04em">{tspans}</text></g>')
            t += 0.36

    cur_y = y0 + len(lines) * lh
    prompt_w = width_of(f"{prompt_user}@{host}:~ $ ")
    text_parts.append(
        f'<g class="pop" style="animation-delay:{fnum(t + 0.2)}s">'
        f'<text x="{x0}" y="{cur_y}" font-size="{fsz}" font-family="{MONO}">'
        f'<tspan fill="{colmap["p"]}">{prompt_user}@{host}</tspan>'
        f'<tspan fill="{colmap["f"]}">:~ </tspan><tspan fill="{colmap["l"]}">$ </tspan></text>'
        f'<rect class="cursor" x="{fnum(x0 + prompt_w + 4)}" y="{cur_y - 12}" width="{fnum(char_w)}" '
        f'height="15" fill="{PHOS}" opacity="0.9"/></g>')
    body.append('<g filter="url(#phos)">' + "".join(text_parts) + "</g>")
    body.append("".join(covers))

    body.append(f'<rect class="band" x="26" y="0" width="{W-52}" height="70" fill="url(#bandg)"/>')
    body.append(f'<rect x="26" y="22" width="{W-52}" height="{H-44}" fill="url(#scan3)"/>')
    body.append(f'<rect class="grain" x="-200" y="-200" width="{W+400}" height="{H+400}" '
                'fill="url(#grain)" opacity="0.3"/>')
    body.append(f'<rect x="26" y="22" width="{W-52}" height="{H-44}" rx="7" fill="url(#tube)"/>')
    body.append("</g>")
    body.append(text_el(40, 17, 8, FAINT, "CRT-0031 · PHOSPHOR TERMINAL", ls="0.3em"))
    body.append(f'<circle cx="{W-52}" cy="14" r="2.2" fill="{PHOS}" opacity="0.8"/>')
    body.append(text_el(W - 62, 17, 8, FAINT, "ON AIR", ls="0.3em", anchor="end"))
    return (svg_open(W, H, "磷光终端 — 一台还亮着的机器", "".join(css), "".join(defs))
            + "\n".join(body) + "\n</svg>\n")


# ═══════════════════════ 05 · 显影隧道(页脚) ═══════════════════════

def gen_tunnel(live: dict) -> str:
    W, H = 1000, 240
    cx, cy = 500, 108
    k = 0.62
    ratio = 1 / k
    css = [GRAIN_CSS,
           f".dolly{{transform-origin:{cx}px {cy}px;animation:dolly 5.2s linear infinite}}"
           f"@keyframes dolly{{from{{transform:scale(1)}}to{{transform:scale({fnum(ratio)})}}}}",
           "@keyframes drift2{0%,88%,100%{transform:translate(0,0)}90%{transform:translate(1.2px,-0.8px)}"
           "92%{transform:translate(-1px,0.6px)}94%{transform:translate(0.6px,0.4px)}}"
           ".glitch{animation:drift2 7s steps(1,end) infinite}"]
    defs = [grain_defs(), scan_defs("scan4", 0.04),
            '<radialGradient id="tvig" cx="0.5" cy="0.45" r="0.72">'
            '<stop offset="0.5" stop-color="rgba(1,4,9,0)"/>'
            '<stop offset="1" stop-color="rgba(1,4,9,0.62)"/></radialGradient>',
            '<radialGradient id="core" cx="0.5" cy="0.5" r="0.5">'
            f'<stop offset="0" stop-color="{LAMP}" stop-opacity="0.16"/>'
            f'<stop offset="0.5" stop-color="{FOG}" stop-opacity="0.05"/>'
            '<stop offset="1" stop-color="rgba(0,0,0,0)"/></radialGradient>',
            f'<clipPath id="tclip"><rect width="{W}" height="{H}" rx="8"/></clipPath>']

    body = [f'<rect width="{W}" height="{H}" rx="8" fill="{INK0}"/>',
            '<g clip-path="url(#tclip)">']
    # 透视导轨
    for ex, ey in [(60, 236), (940, 236), (60, 4), (940, 4)]:
        body.append(f'<line x1="{cx}" y1="{cy}" x2="{ex}" y2="{ey}" stroke="rgba(233,238,244,0.05)"/>')

    rings = []
    base_w, base_h = 920, 196
    for i in range(8):
        s = k ** i
        w2, h2 = base_w * s, base_h * s
        rx = 10 * s
        op = (0.9 if i == 0 else 0.75) * (0.35 + 0.65 * s)   # 越深越暗,像雾里
        for dx, col, o2 in ((-1.6 * s - 0.4, TAIL, 0.30), (1.6 * s + 0.4, FOG, 0.30), (0, CREAM, 0.34)):
            rings.append(
                f'<rect x="{fnum(cx - w2 / 2 + dx)}" y="{fnum(cy - h2 / 2)}" width="{fnum(w2)}" '
                f'height="{fnum(h2)}" rx="{fnum(rx)}" fill="none" stroke="{col}" '
                f'stroke-width="{fnum(max(0.7, 1.5 * s))}" opacity="{fnum(o2 * op)}"/>')
    body.append(f'<g class="dolly">{"".join(rings)}</g>')
    body.append(f'<ellipse cx="{cx}" cy="{cy}" rx="150" ry="64" fill="url(#core)"/>')

    body.append(f'<g class="glitch">'
                + text_el(cx, cy - 2, 14.5, MUTED, esc("隧道尽头 · 显影未完"), ls="0.42em",
                          ff=SERIF, anchor="middle")
                + text_el(cx, cy + 20, 7.5, FAINT, "THE TUNNEL KEEPS DEVELOPING", ls="0.44em", anchor="middle")
                + "</g>")

    body.append(text_el(cx, H - 26, 8.5, FAINT,
                        esc(f"© {live['develop_date'][:4]} CINEXUL · 手写 SVG · 零依赖 · "
                            f"GITHUB ACTIONS 每 6 小时自动冲洗 · 显影批号 №{live['develop_no']:03d}"),
                        ls="0.2em", anchor="middle"))
    body.append(f'<rect class="grain" x="-200" y="-200" width="{W+400}" height="{H+400}" '
                'fill="url(#grain)" opacity="0.45"/>')
    body.append(f'<rect width="{W}" height="{H}" fill="url(#scan4)"/>')
    body.append(f'<rect width="{W}" height="{H}" fill="url(#tvig)"/>')
    body.append("</g>")
    body.append(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="8" fill="none" stroke="{LINE_SOFT}"/>')
    return (svg_open(W, H, "显影隧道 — 页脚", "".join(css), "".join(defs))
            + "\n".join(body) + "\n</svg>\n")


# ═══════════════════════ 分节标题 · 导航月牌 ═══════════════════════

def gen_header(num: int, cjk: str, en: str, light: bool) -> str:
    W, H = 1000, 46
    ink = L_INK if light else TEXT
    faint = L_FAINT if light else FAINT
    line = L_LINE if light else LINE
    accent = L_ACCENT if light else LAMP
    css = [f"@keyframes hp{{50%{{opacity:0.25}}}}.hp{{animation:hp 4.2s ease-in-out infinite}}"]
    defs = [f'<linearGradient id="hr" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{line}"/>'
            f'<stop offset="1" stop-color="rgba(0,0,0,0)" stop-opacity="0"/></linearGradient>']
    cjk_w = len(cjk) * 14.5 * (1 + 0.3) + 10
    en_x = 66 + cjk_w + 18
    body = [
        f'<rect x="1" y="12" width="30" height="21" rx="2" fill="none" stroke="{line}"/>',
        text_el(16, 27, 9.5, faint, f"{num:02d}", ls="0.1em", anchor="middle"),
        text_el(46, 29, 14.5, ink, esc(cjk), ls="0.3em", ff=SERIF),
        text_el(en_x, 28, 8, faint, esc(en), ls="0.42em"),
        f'<line x1="{fnum(en_x + len(en) * 8 * 0.75 + 26)}" y1="23" x2="{W - 26}" y2="23" stroke="url(#hr)"/>',
        f'<rect class="hp" x="{W - 14}" y="19" width="8" height="8" transform="rotate(45 {W - 10} 23)" '
        f'fill="{accent}" opacity="0.7"/>',
    ]
    return (svg_open(W, H, f"{cjk} — {en}", "".join(css), "".join(defs))
            + "\n".join(body) + "\n</svg>\n")


# ═══════════════════════ 主流程 ═══════════════════════

def main() -> None:
    cfg = json.loads((ROOT / "profile" / "config.json").read_text("utf-8"))
    live = json.loads((ROOT / "profile" / "live.json").read_text("utf-8"))
    ASSETS.mkdir(exist_ok=True)

    out: dict[str, str] = {
        "hero.svg": gen_hero(cfg, live),
        "plaque.svg": gen_plaque(cfg, live),
        "strings.svg": gen_strings(live),
        "terminal.svg": gen_terminal(cfg, live),
        "tunnel.svg": gen_tunnel(live),
    }
    for num, cjk, en in [(1, "展品", "EXHIBIT №001 — SIX-PIECE BURR"),
                         (2, "以光为弦", "LANGUAGES AS STRINGS"),
                         (3, "还亮着的机器", "THE MACHINE STILL ON")]:
        out[f"h{num}.svg"] = gen_header(num, cjk, en, light=False)
        out[f"h{num}-light.svg"] = gen_header(num, cjk, en, light=True)

    for name, content in out.items():
        (ASSETS / name).write_text(content, "utf-8")
    total = sum(len(v.encode()) for v in out.values())
    print(f"rendered {len(out)} svgs, {total / 1024:.0f} KB total")


if __name__ == "__main__":
    main()

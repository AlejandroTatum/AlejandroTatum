#!/usr/bin/env python3
"""Build the terminal-styled SVGs used by the profile README.

The look mirrors the portfolio (AlejandroTatum.github.io, src/app/terminal.css):
same palette, JetBrains Mono + Press Start 2P, window chrome with three dots.

GitHub serves README images through <img>, where browsers ignore @font-face
and block external resources. So every glyph is converted to a vector path
(fontTools) and every bitmap is embedded as a data URI.

Usage:
  python3 scripts/build_readme_assets.py --portfolio ../AlejandroTatum.github.io

Inputs:
  scripts/fonts/JetBrainsMono-wght.ttf, scripts/fonts/PressStart2P-Regular.ttf
    (SIL OFL fonts from Google Fonts; not committed, see .gitignore)
  <portfolio>/public/pixel/alejandro-pixel-portrait.png
  <portfolio>/public/previews/{cataclub,horno}.png
Outputs:
  assets/readme/{header,cataclub,horno}.svg
"""
import argparse
import base64
import io
from pathlib import Path

from PIL import Image
from fontTools.misc.transform import Transform
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "scripts" / "fonts"
OUT = ROOT / "assets" / "readme"

# terminal.css palette
BG = "#131017"
PANEL = "#191420"
PANEL2 = "#201828"
BORDER = "#382e45"
BORDER_BRIGHT = "#584872"
TEXT = "#eae3f0"
DIM = "#a99dbb"
FAINT = "#8b7fa6"
ROSE = "#ff9ec7"
CYAN = "#7ce8d8"
GREEN = "#9fe8a8"
PEACH = "#ffd6a5"
PURPLE = "#c4b5fd"

# ---------------------------------------------------------------- fonts ----
_pixel = TTFont(FONTS / "PressStart2P-Regular.ttf")
_mono_var = TTFont(FONTS / "JetBrainsMono-wght.ttf")
_instances: dict[tuple[str, int], tuple] = {}


def _font(key: str, weight: int):
    if (key, weight) not in _instances:
        f = _pixel if key == "pixel" else instantiateVariableFont(_mono_var, {"wght": weight}, inplace=False)
        _instances[(key, weight)] = (f.getGlyphSet(), f.getBestCmap(), f["head"].unitsPerEm, f["hmtx"])
    return _instances[(key, weight)]


def text_width(text: str, key: str, size: float, weight: int = 400, ls: float = 0.0) -> float:
    _, cmap, upm, hmtx = _font(key, weight)
    return sum(hmtx[cmap[ord(c)]][0] for c in text) * size / upm + ls * max(len(text) - 1, 0)


def text(x: float, y: float, runs, key: str = "mono", size: float = 15, weight: int = 400,
         ls: float = 0.0, anchor: str | None = None) -> str:
    """Render runs [(text, fill), ...] as paths; y is the baseline."""
    gs, cmap, upm, hmtx = _font(key, weight)
    scale = size / upm
    if anchor == "middle":
        x -= text_width("".join(t for t, _ in runs), key, size, weight, ls) / 2
    elif anchor == "end":
        x -= text_width("".join(t for t, _ in runs), key, size, weight, ls)
    parts = []
    for chunk, fill in runs:
        for ch in chunk:
            name = cmap.get(ord(ch))
            if name is None:
                x += size * 0.6
                continue
            pen = SVGPathPen(gs, ntos=lambda v: f"{v:.1f}")
            gs[name].draw(TransformPen(pen, Transform(scale, 0, 0, -scale, x, y)))
            if d := pen.getCommands():
                parts.append(f'<path d="{d}" fill="{fill}"/>')
            x += hmtx[name][0] * scale + ls
    return "".join(parts)


def wrap(line: str, key: str, size: float, max_width: float, weight: int = 400) -> list[str]:
    words, lines, cur = line.split(), [], ""
    for w in words:
        cand = f"{cur} {w}".strip()
        if cur and text_width(cand, key, size, weight) > max_width:
            lines.append(cur)
            cur = w
        else:
            cur = cand
    return lines + [cur] if cur else lines


# --------------------------------------------------------------- frame -----
STYLE = """<style>
.blink{animation:blink 1.05s steps(2,jump-none) infinite}
@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}
.pulse{animation:pulse 2.6s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:.5}50%{opacity:1}}
@media (prefers-reduced-motion: reduce){.blink,.pulse{animation:none}}
</style>"""

DEFS = """<pattern id="scan" width="4" height="3" patternUnits="userSpaceOnUse">
  <rect width="4" height="1" fill="rgba(4,2,8,0.14)"/>
</pattern>
<radialGradient id="vig" cx="50%" cy="46%" r="72%">
  <stop offset="60%" stop-color="rgba(6,4,10,0)"/>
  <stop offset="100%" stop-color="rgba(6,4,10,0.4)"/>
</radialGradient>
<filter id="glow" x="-20%" y="-60%" width="140%" height="220%">
  <feGaussianBlur stdDeviation="7" result="b"/>
  <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>"""


def svg(label: str, w: int, h: int, body: str, fill: str = BG) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{label}">
<title>{label}</title>
{STYLE}
<defs>{DEFS}
<clipPath id="frame"><rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="12"/></clipPath>
</defs>
<g clip-path="url(#frame)">
<rect width="{w}" height="{h}" fill="{fill}"/>
{body}
<rect width="{w}" height="{h}" fill="url(#scan)"/>
<rect width="{w}" height="{h}" fill="url(#vig)"/>
</g>
<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="12" fill="none" stroke="{BORDER}" stroke-width="2"/>
</svg>
"""


def dots(x: float, y: float, size: float = 10) -> str:
    gap = size * 1.7
    return "".join(
        f'<rect x="{x + i * gap}" y="{y}" width="{size}" height="{size}" rx="2.5" fill="{c}"/>'
        for i, c in enumerate((ROSE, CYAN, PURPLE))
    )


def mini_window(x: float, y: float, w: float, img_h: float, title: str, href: str, pixelated: bool = False,
                brackets: bool = False) -> str:
    """Portfolio-style inner window: title bar, then an embedded image."""
    bar = 34
    out = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{bar + img_h}" rx="8" fill="{PANEL2}" stroke="{BORDER_BRIGHT}"/>',
        dots(x + 14, y + 12),
        text(x + 70, y + 22, [(title, FAINT)], size=12, ls=1.6),
        f'<line x1="{x}" y1="{y + bar}" x2="{x + w}" y2="{y + bar}" stroke="{BORDER}"/>',
        f'<clipPath id="shot-{int(x)}"><rect x="{x + 1}" y="{y + bar}" width="{w - 2}" height="{img_h - 1}" rx="7"/></clipPath>',
        f'<image x="{x}" y="{y + bar}" width="{w}" height="{img_h}" preserveAspectRatio="xMidYMid slice"'
        f'{" image-rendering=\"pixelated\"" if pixelated else ""} clip-path="url(#shot-{int(x)})" href="{href}"/>',
    ]
    if brackets:
        l, top, bottom = 16, y + bar + 10, y + bar + img_h - 10
        for cx, cy, sx, sy in [(x + 10, top, 1, 1), (x + w - 10, top, -1, 1), (x + 10, bottom, 1, -1), (x + w - 10, bottom, -1, -1)]:
            out.append(f'<path d="M {cx + sx * l} {cy} H {cx} V {cy + sy * l}" fill="none" stroke="{CYAN}" stroke-width="2.5"/>')
    return "\n".join(out)


def data_uri(img: Image.Image, fmt: str, **save) -> str:
    buf = io.BytesIO()
    img.save(buf, fmt, **save)
    mime = "image/png" if fmt == "PNG" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(buf.getvalue()).decode()}"


# --------------------------------------------------------------- header ----
def build_header(portfolio: Path) -> str:
    portrait = Image.open(portfolio / "public/pixel/alejandro-pixel-portrait.png").convert("RGB")
    portrait = portrait.resize((portrait.width // 4, portrait.height // 4), Image.NEAREST)
    portrait = portrait.quantize(colors=160, method=Image.MEDIANCUT)
    portrait_uri = data_uri(portrait, "PNG", optimize=True)

    W, H = 1000, 520
    b = [
        f'<rect width="{W}" height="44" fill="{PANEL2}"/>',
        f'<line x1="0" y1="44" x2="{W}" y2="44" stroke="{BORDER}"/>',
        text(24, 28, [("alejandro", CYAN), ("@", FAINT), ("github", ROSE), (":~", FAINT)], size=14),
        text(W - 24, 28, [("~/profile", FAINT)], size=12.5, anchor="end"),
        text(52, 100, [("$ ", ROSE), ("whoami --verbose", CYAN), ("  # profile", FAINT)], size=17, weight=600),
        text(52, 168, [("Alejandro", TEXT)], key="pixel", size=38),
        f'<g filter="url(#glow)">{text(52, 222, [("Padilla", ROSE)], key="pixel", size=38)}</g>',
        text(52, 266, [("Full-Stack Developer", CYAN)], size=19, weight=700),
        text(52, 306, [("From a business problem to a", TEXT)], size=21, weight=700),
        text(52, 334, [("system in production.", TEXT)], size=21, weight=700),
    ]
    rows = [
        ("stack", "FastAPI · Next.js · PostgreSQL · Docker"),
        ("ai", "LLM · agents · YOLO"),
        ("base", "Ecuador · remote · US hours"),
        ("status", "open · part-time / contract"),
    ]
    for i, (key, val) in enumerate(rows):
        y = 380 + i * 27
        b.append(f'<rect x="52" y="{y - 8}" width="5" height="5" fill="{FAINT}"/>')
        b.append(text(68, y, [(key, ROSE)], size=14.5, weight=700))
        b.append(text(160, y, [(val, DIM)], size=14.5))
    cursor_x = 160 + text_width(rows[-1][1], "mono", 14.5) + 4
    b.append(f'<rect class="blink" x="{cursor_x:.1f}" y="{380 + 3 * 27 - 13}" width="8" height="16" fill="{ROSE}"/>')

    # right column: pixel portrait viewer, as in the portfolio hero
    b.append(mini_window(612, 112, 336, 251, "ALEJANDRO.PNG — PIXEL VIEWER", portrait_uri, pixelated=True, brackets=True))
    # live status strip, derived from the same facts as the portfolio hero
    b.append(f'<rect x="612" y="420" width="336" height="44" rx="6" fill="{PANEL}" stroke="{BORDER}"/>')
    b.append(f'<rect class="pulse" x="628" y="438" width="8" height="8" rx="2" fill="{GREEN}"/>')
    b.append(text(646, 447, [("online", GREEN), (" · 2 client sites live · 1 demo", DIM)], size=13))
    return svg("Alejandro Padilla, full-stack developer: from a business problem to a system in production",
               W, H, "\n".join(b))


# --------------------------------------------------------- project card ----
def build_card(rank: str, rank_color: str, name: str, context: str, host: str, tags: list[str],
               shot: Path, label: str) -> str:
    img = Image.open(shot).convert("RGB")
    img = img.resize((720, int(720 * img.height / img.width)), Image.LANCZOS)
    shot_uri = data_uri(img, "JPEG", quality=82, optimize=True, progressive=True)

    W, H = 1000, 360
    b = []
    # rank chip + name + context
    b.append(f'<rect x="40" y="40" width="54" height="44" rx="6" fill="{PANEL2}" stroke="{rank_color}"/>')
    b.append(text(67, 70, [(rank, rank_color)], key="pixel", size=15, anchor="middle"))
    b.append(text(112, 70, [("▸ ", CYAN), (name, CYAN)], size=24, weight=700))
    b.append(text(112, 98, [(context, FAINT)], size=14))
    # live status
    b.append(f'<rect class="pulse" x="40" y="132" width="9" height="9" rx="2" fill="{GREEN}"/>')
    b.append(text(58, 141, [("# ", FAINT), ("live · client site", PEACH)], size=15))
    # tags as bordered chips, wrapped inside the info column
    x, y = 40, 170
    for tag in tags:
        tw = text_width(tag, "mono", 14) + 22
        if x + tw > 450:
            x, y = 40, y + 40
        b.append(f'<rect x="{x}" y="{y}" width="{tw:.1f}" height="30" rx="4" fill="{PANEL}" stroke="{BORDER_BRIGHT}"/>')
        b.append(text(x + 11, y + 20, [(tag, DIM)], size=14))
        x += tw + 10
    # site button
    btn_y = H - 40 - 48
    b.append(f'<rect x="40" y="{btn_y}" width="410" height="48" rx="6" fill="{PANEL}" stroke="{BORDER_BRIGHT}"/>')
    b.append(text(245, btn_y + 30, [("[ ", FAINT), (f"open {host} ↗", CYAN), (" ]", FAINT)],
                  size=16, weight=700, anchor="middle"))
    # preview window (screenshot from production)
    img_h = round(440 * img.height / img.width)
    b.append(mini_window(520, (H - 34 - img_h) / 2, 440, img_h, f"{host.upper()} — LIVE", shot_uri))
    return svg(label, W, H, "\n".join(b), fill=BG)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--portfolio", type=Path, required=True, help="path to the AlejandroTatum.github.io checkout")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    assets = {
        "header.svg": build_header(args.portfolio),
        "cataclub.svg": build_card(
            "01", ROSE, "cataclub", "Client project", "cataclub.com",
            ["Next.js", "FastAPI", "PostgreSQL", "Celery", "Docker"],
            args.portfolio / "public/previews/cataclub.png",
            "Cata Club: live client system on cataclub.com, built with Next.js, FastAPI and PostgreSQL",
        ),
        "horno.svg": build_card(
            "02", CYAN, "El Horno del Pingüino", "Client project", "elhornodelpinguino.com",
            ["Astro", "Next.js", "Prisma", "PostgreSQL"],
            args.portfolio / "public/previews/horno.png",
            "El Horno del Pingüino: live client storefront on elhornodelpinguino.com, built with Astro and a Next.js admin",
        ),
    }
    for name, content in assets.items():
        (OUT / name).write_text(content)
        print(f"{name}: {len(content.encode()) / 1024:.0f} KB")


if __name__ == "__main__":
    main()

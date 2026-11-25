"""Runs, colors, gradients, animation and image-to-block rendering."""
from .common import *
from .specs import *
from .readouts import *
from .system import *
from .security import *
from .logos import *
from .validation import *
from .model import *


# run = (text, fg, bg, bold); colors are "#rrggbb" or "aN" (terminal ANSI palette index)
def R(t, fg=None, bg=None, b=False): return (t, fg, bg, b)
def merge(runs):
    out = []
    for r in runs:
        if out and out[-1][1:] == r[1:]: out[-1] = (out[-1][0] + r[0],) + r[1:]
        else: out.append(r)
    return out
def rlen(row): return sum(len(r[0]) for r in row)

IMGCACHE = {}
def downscale(img, w, h):
    """Clean downscale: premultiplied alpha + repeated smooth halving (area-style averaging, no aliasing)."""
    img = img.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    ign, smooth = Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation
    while img.width() >= w * 2 and img.height() >= h * 2:
        img = img.scaled(max(w, img.width() // 2), max(h, img.height() // 2), ign, smooth)
    return img.scaled(w, h, ign, smooth).convertToFormat(QImage.Format.Format_ARGB32)

def img2rows(img, w, bg="#1e1e1e"):
    """Half-block art: every character cell = 2 square pixels (top = fg, bottom = bg). Soft alpha edges blend into `bg`."""
    h = max(2, round(img.height() * w / img.width() / 2) * 2); s = downscale(img, w, h)
    def px(x, y):
        c = s.pixelColor(x, y); a = c.alphaF()
        if a < 0.04: return None
        return c.name() if a > 0.98 else lerp(bg, c.name(), a)
    rows = []
    for y in range(0, h, 2):
        row = []
        for x in range(w):
            a, b = px(x, y), px(x, y + 1)
            if a and b: row.append(R("█", a) if a == b else R("▀", a, b))
            elif a: row.append(R("▀", a))
            elif b: row.append(R("▄", b))
            else: row.append(R(" "))
        rows.append(merge(row))
    return rows

# Sharp mode: quadrant blocks. Every character cell = 2x2 pixels (twice the horizontal detail of half-blocks); the best
# 2-colour split of those 4 pixels is chosen per cell. Bits: 1 = top-left, 2 = top-right, 4 = bottom-left, 8 = bottom-right.
QUAD = {"▘": 1, "▝": 2, "▀": 3, "▖": 4, "▌": 5, "▞": 6, "▛": 7, "▗": 8, "▚": 9, "▐": 10, "▜": 11, "▄": 12, "▙": 13, "▟": 14, "█": 15}
QCHAR = {v: k for k, v in QUAD.items()}; QCHAR[0] = " "
PARTS = [(m, [i for i in range(4) if m >> i & 1], [i for i in range(4) if not m >> i & 1]) for m in range(1, 8)]
def hexc(c): return "#%02x%02x%02x" % tuple(round(v) for v in c)

def fit_cell(q):
    """q = 4 pixels (TL, TR, BL, BR) as (r,g,b) or None (transparent) -> one character cell."""
    vis = [i for i in range(4) if q[i]]
    if not vis: return R(" ")
    n = len(vis); S = [sum(q[i][k] for i in vis) for k in range(3)]; mean = [v / n for v in S]
    if n < 4: return R(QCHAR[sum(1 << i for i in vis)], hexc(mean))          # transparent corner: draw only the visible part
    if sum(v * v for i in vis for v in q[i]) - sum(v * v for v in S) / 4 < 40: return R("█", hexc(mean))   # flat area
    best = None
    for m, a, b in PARTS:
        sa = [sum(q[i][k] for i in a) for k in range(3)]; sb = [S[k] - sa[k] for k in range(3)]
        sc = sum(v * v for v in sa) / len(a) + sum(v * v for v in sb) / len(b)        # max of this == min squared error
        if not best or sc > best[0]: best = (sc, m, sa, len(a), sb, len(b))
    _, m, sa, na, sb, nb = best
    return R(QCHAR[m], hexc([v / na for v in sa]), hexc([v / nb for v in sb]))

def sharpen(px, W, h, k):
    """Light unsharp mask (restores the crispness smooth downscaling takes away). Transparent pixels are ignored."""
    out = [r[:] for r in px]
    for y in range(h):
        for x in range(W):
            c = px[y][x]
            if c is None: continue
            n = [px[yy][xx] for xx, yy in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)) if 0 <= xx < W and 0 <= yy < h and px[yy][xx]]
            if n: out[y][x] = tuple(min(255, max(0, c[i] + k * (c[i] - sum(v[i] for v in n) / len(n)))) for i in range(3))
    return out

def img2rows_quad(img, w, bg="#1e1e1e", sharp=0.5):
    """Same cell grid / size as img2rows, but with 2x2 pixels per cell instead of 1x2."""
    h = max(2, round(img.height() * w / img.width() / 2) * 2); W = 2 * w
    s = downscale(img, W, h); st = s.bytesPerLine(); raw = bytes(s.constBits().asstring(s.sizeInBytes()))
    b = QColor(bg); bgc = (b.red(), b.green(), b.blue()); px = []
    for y in range(h):
        row = []; o = y * st
        for x in range(W):
            bl, gr, rd, a = raw[o + 4 * x: o + 4 * x + 4]                       # ARGB32 = B,G,R,A bytes (not premultiplied)
            if a < 10: row.append(None)
            elif a > 250: row.append((rd, gr, bl))
            else: f = a / 255; row.append((bgc[0] + (rd - bgc[0]) * f, bgc[1] + (gr - bgc[1]) * f, bgc[2] + (bl - bgc[2]) * f))
        px.append(row)
    if sharp: px = sharpen(px, W, h, sharp)
    return [merge([fit_cell((px[2 * cy][2 * cx], px[2 * cy][2 * cx + 1], px[2 * cy + 1][2 * cx], px[2 * cy + 1][2 * cx + 1]))
                   for cx in range(w)]) for cy in range(h // 2)]

def image_frames(path, w, bg="#1e1e1e", sharp=True):
    key = (str(path), path.stat().st_mtime, w, bg, sharp)
    if key in IMGCACHE: return IMGCACHE[key]
    imgs = []; mv = QMovie(str(path))
    if mv.isValid() and mv.frameCount() > 1:
        mv.jumpToFrame(0); first = mv.currentImage(); fc = mv.frameCount()
        cells = max(1, w * round(first.height() * w / max(1, first.width())) // 2)
        n = min(fc, max(2, min(24, 1_500_000 // ((60 if sharp else 45) * cells))))
        for k in range(n): mv.jumpToFrame(k * fc // n); imgs.append(mv.currentImage())     # spread over the whole loop, not just the first frames
    else: imgs = [QImage(str(path))]
    conv = (lambda i: img2rows_quad(i, w, bg)) if sharp else (lambda i: img2rows(i, w, bg))
    IMGCACHE[key] = [conv(i) for i in imgs if not i.isNull() and i.width() > 0] or [[[R("(unreadable image)")]]]
    return IMGCACHE[key]

def lerp(c1, c2, t):
    a, b = QColor(c1), QColor(c2)
    return QColor(round(a.red() + (b.red() - a.red()) * t), round(a.green() + (b.green() - a.green()) * t),
                  round(a.blue() + (b.blue() - a.blue()) * t)).name()
def grad(stops, t):
    t = min(max(t, 0.0), 1.0)
    if len(stops) == 1: return stops[0]
    x = t * (len(stops) - 1); i = min(int(x), len(stops) - 2); return lerp(stops[i], stops[i + 1], x - i)
def shade(c, f):
    q = QColor(c); h, s, l, _ = q.getHslF(); q.setHslF(max(h, 0.0), s, min(1.0, max(0.0, l * f))); return q.name()
def hue(h): return QColor.fromHsvF(h % 1.0, 0.75, 1.0).name()
def posf(x, y, w, h, d):
    if d == "vertical": return y / max(1, h - 1)
    if d == "diagonal": return (x / max(1, w - 1) + y / max(1, h - 1)) / 2
    if d == "radial": return min(1.0, (((x - w / 2) / (w / 2 or 1)) ** 2 + ((y - h / 2) / (h / 2 or 1)) ** 2) ** 0.5)
    return x / max(1, w - 1)

def render_logo(lines, cells, mode, stops, direction, anim):
    """Text logo -> (frames, final_index). mode: solid | gradient | cells (hand-painted)."""
    h = len(lines); w = max((len(l) for l in lines), default=0); lines = [l.ljust(w) for l in lines]
    stops = [c for c in stops if c] or ["#3daee9"]; N = 1 if anim == "none" else (24 if anim == "typewriter" else 16)
    d = direction if direction in GRADS and direction != "none" else "horizontal"
    nb = [(x, y) for y in range(h) for x in range(w) if lines[y][x] != " "]; rnd = random.Random(7); frames = []
    def base(x, y, u):
        if mode == "cells" and cells and y < len(cells) and x < len(cells[y]) and cells[y][x]: return cells[y][x]
        if mode == "gradient":
            if u is None: return grad(stops, posf(x, y, w, h, d))
            return grad(stops + stops[:1], (posf(x, y, w, h, d) + u) % 1)
        return stops[0]
    for t in range(N):
        ph = t / N; show = None; spark = set()
        if anim == "typewriter": show = set(nb[: round(len(nb) * min(t, 15) / 15)])
        if anim == "sparkle" and nb: spark = set(rnd.sample(nb, max(1, len(nb) // 14)))
        rows = []
        for y in range(h):
            row = []
            for x in range(w):
                ch = lines[y][x]
                if ch == " " or (show is not None and (x, y) not in show): row.append(R(" ")); continue
                if anim == "rainbow": col = hue((x + 2 * y) / (w + 2 * h + 1) + ph)
                elif anim == "scroll" and mode == "gradient": col = base(x, y, ph)
                else:
                    col = base(x, y, None)
                    if anim == "pulse": col = shade(col, 1 + 0.35 * math.sin(2 * math.pi * ph))
                    elif anim in ("wave", "scroll"): col = shade(col, 1 + 0.4 * math.sin(2 * math.pi * (x / max(w, 1) * 1.5 + y / max(h, 1) - ph)))
                    elif anim == "scanline": col = shade(col, 1 + 0.9 * max(0.0, 1 - abs(y - (ph * (h + 4) - 2)) / 2))
                    elif anim == "sparkle" and (x, y) in spark: col, ch = "#ffffff", "*"
                row.append(R(ch, col, None, True))
            rows.append(merge(row))
        frames.append(rows)
    return frames, (N - 1 if anim == "typewriter" else 0)

def logo_frames(g, n, O, classic):
    p = n["params"]
    if n["type"] == "clogo":
        d = p["data"]; lines, cells, mode, stops, direction = d["rows"], d.get("cells"), d["mode"], d["stops"], d["direction"]
        anim = d["anim"] if p["animation"] == "design" else p["animation"]
    else:
        src = p["source"]
        if src == "auto":
            d = osrel(); ids = (d.get("ID", "") + d.get("ID_LIKE", "")).lower()
            src = "arch" if re.search("arch|cachyos|manjaro|endeavour", ids) else "tux"
        if src == "file":
            path = g.asset(p["file"])
            if path and path.exists() and path.suffix.lower() in IMG: return image_frames(path, int(p["width"]), O["bg"], p["mode"] != "blocks-basic"), 0
            lines = path.read_text(errors="replace").splitlines() if path and path.exists() else ["(no file)"]
        else: lines = LOGOS.get(src, LOGOS["tux"])
        g_ = p["gradient"]; mode = "gradient" if g_ != "none" else "solid"; cells = None; direction = g_
        stops = [p["color"], p["color2"], p["color3"]] if g_ != "none" else [p["color"]]
        anim = O["animation"] if p["animation"] == "inherit" else p["animation"]
    if classic: anim = "none"; mode = "cells" if mode == "cells" else "solid"
    return render_logo(lines or [" "], cells, mode, stops, direction, anim)

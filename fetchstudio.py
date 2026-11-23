#!/usr/bin/env python3
"""Fetch Studio - node-based neofetch/fastfetch designer with a 1:1 terminal preview (PyQt6)."""
import sys, os, re, json, shutil, zipfile, platform, subprocess, threading, uuid
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, QSettings
from PyQt6.QtGui import (QAction, QColor, QFont, QFontMetricsF, QImage, QKeySequence,
                         QMovie, QPainter, QPainterPath, QPen)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsPathItem, QGraphicsEllipseItem, QMenu, QToolBar, QSplitter, QVBoxLayout,
    QHBoxLayout, QFormLayout, QComboBox, QLineEdit, QPushButton, QSpinBox, QCheckBox,
    QColorDialog, QFileDialog, QInputDialog, QMessageBox, QLabel, QFrame, QScrollArea)

APP = "Fetch Studio"
DATA = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "fetchstudio"
PROJ, ACTIVE = DATA / "projects", DATA / "active"
MARK_B, MARK_E = "# >>> fetchstudio >>>", "# <<< fetchstudio <<<"
PAL = ["#2e3436", "#cc0000", "#4e9a06", "#c4a000", "#3465a4", "#75507b", "#06989a", "#d3d7cf",
       "#555753", "#ef2929", "#8ae234", "#fce94f", "#729fcf", "#ad7fa8", "#34e2e2", "#eeeeec"]
IMG = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
# name -> (window title shown in preview, font size, executable used for detection)
TERMS = {
    "GNOME Terminal": ("Terminal", 11, "gnome-terminal"), "Console (kgx)": ("Console", 11, "kgx"),
    "Konsole": ("Konsole", 10, "konsole"), "Xfce Terminal": ("Terminal", 10, "xfce4-terminal"),
    "MATE Terminal": ("Terminal", 10, "mate-terminal"), "QTerminal": ("QTerminal", 10, "qterminal"),
    "LXTerminal": ("LXTerminal", 10, "lxterminal"), "Tilix": ("Tilix", 11, "tilix"),
    "Deepin Terminal": ("Deepin Terminal", 11, "deepin-terminal"),
    "COSMIC Terminal": ("COSMIC Terminal", 11, "cosmic-term"),
    "Pantheon Terminal": ("Terminal", 10, "io.elementary.terminal")}

# ------------------------------------------------------------------ node specs
def P(key, label, kind, default, opts=None): return (key, label, kind, default, opts)
FIELDS = ["OS", "Host", "Kernel", "Uptime", "Packages", "Shell", "DE", "Session", "Terminal",
          "CPU", "GPU", "Memory", "Disk", "Resolution", "Locale", "Custom"]
SPEC = {
    "output": ("Output", "#c0392b", [
        P("preset", "Preset", "combo", "classic", ["classic", "advanced", "custom"]),
        P("gap", "Logo gap", "int", 3, (1, 12)), P("separator", "Separator (custom)", "text", ": "),
        P("bg", "Background", "color", "#1e1e1e"), P("fg", "Default text", "color", "#d0d0d0"),
        P("animation", "Logo animation", "combo", "none", ["none", "rainbow"]),
        P("fps", "Animation FPS", "int", 8, (1, 30))]),
    "logo": ("Logo", "#2980b9", [
        P("source", "Source", "combo", "auto", ["auto", "tux", "arch", "file"]),
        P("file", "Image / GIF / text file", "file", ""), P("width", "Image width (cols)", "int", 36, (8, 80)),
        P("color", "Text logo color", "color", "#3daee9")]),
    "title": ("Title", "#27ae60", [P("color", "Color", "color", "#3daee9"), P("underline", "Underline", "check", True)]),
    "info": ("Info", "#8e44ad", [
        P("field", "Field", "combo", "OS", FIELDS), P("label", "Label (blank = field)", "text", ""),
        P("key_color", "Label color", "color", "#3daee9"), P("val_color", "Value color", "color", "#d0d0d0"),
        P("command", "Command (Custom field)", "text", "echo hello")]),
    "colors": ("Color bar", "#d35400", [P("rows", "Rows", "combo", "2", ["1", "2"])]),
    "text": ("Text", "#7f8c8d", [P("text", "Text", "text", "Hello"), P("color", "Color", "color", "#d0d0d0")]),
}
LOGOS = {
    "tux": ["    .--.    ", "   |o_o |   ", "   |:_/ |   ", "  //   \\ \\  ", " (|     | ) ",
            "/'\\_   _/`\\", "\\___)=(___/ "],
    "arch": ["      /\\      ", "     /  \\     ", "    /    \\    ", "   /  ,,  \\   ",
             "  /  |  |  \\  ", " /_-''    ''-_\\"]}
SH = {  # shell snippets: run for the live preview AND baked into the generated script
    "Title": 'echo "$(id -un)@$(hostname 2>/dev/null || cat /etc/hostname)"',
    "OS": 'echo "${PRETTY_NAME:-$(uname -s)} $(uname -m)"',
    "Host": 'cat /sys/devices/virtual/dmi/id/product_name 2>/dev/null || echo unknown',
    "Kernel": "uname -r",
    "Uptime": r"""awk '{s=int($1);d=int(s/86400);h=int(s%86400/3600);m=int(s%3600/60);o="";if(d)o=d"d ";if(h)o=o h"h ";print o m"m"}' /proc/uptime""",
    "Packages": r"""if command -v dpkg-query >/dev/null;then echo "$(dpkg-query -f '.\n' -W|wc -l) (dpkg)";elif command -v pacman >/dev/null;then echo "$(pacman -Qq|wc -l) (pacman)";elif command -v rpm >/dev/null;then echo "$(rpm -qa|wc -l) (rpm)";elif command -v apk >/dev/null;then echo "$(apk info|wc -l) (apk)";else echo n/a;fi""",
    "Shell": 'basename "$SHELL"',
    "DE": 'echo "${XDG_CURRENT_DESKTOP:-${DESKTOP_SESSION:-n/a}}"',
    "Session": 'echo "${XDG_SESSION_TYPE:-n/a}"',
    "Terminal": r"""t=${TERM_PROGRAM:-$(ps -o comm= -p "$(ps -o ppid= -p $PPID 2>/dev/null|tr -d ' ')" 2>/dev/null)}; echo "${t:-$TERM}" """,
    "CPU": r"""awk -F: '/model name/{gsub(/^ +/,"",$2);print $2;exit}' /proc/cpuinfo""",
    "GPU": r"""lspci 2>/dev/null | grep -iE 'vga|3d' | head -1 | cut -d: -f3 | sed 's/^ *//'""",
    "Memory": r"""free -m | awk '/Mem:/{printf "%dMiB / %dMiB", $3, $2}'""",
    "Disk": r"""df -h / | awk 'NR==2{print $3" / "$2" ("$5")"}'""",
    "Resolution": r"""xrandr 2>/dev/null | awk '/\*/{print $1; exit}'""",
    "Locale": 'echo "${LANG:-n/a}"'}

# ------------------------------------------------------------------ system helpers
def clean_env():
    e = dict(os.environ)
    if "LD_LIBRARY_PATH_ORIG" in e: e["LD_LIBRARY_PATH"] = e.pop("LD_LIBRARY_PATH_ORIG")
    else: e.pop("LD_LIBRARY_PATH", None)
    return e

CACHE, PENDING, STATE = {}, set(), {"dirty": False}
def value(key, snip):
    """Real value from this machine (async, cached). Same snippet is baked into the build."""
    if key in CACHE: return CACHE[key]
    if key not in PENDING:
        PENDING.add(key)
        def run():
            try:
                r = subprocess.run(["bash", "-c", ". /etc/os-release 2>/dev/null; " + snip],
                                   capture_output=True, text=True, timeout=5, env=clean_env())
                CACHE[key] = r.stdout.strip() or "n/a"
            except Exception: CACHE[key] = "n/a"
            STATE["dirty"] = True
        threading.Thread(target=run, daemon=True).start()
    return "…"

def osrel():
    d = {}
    for p in ("/etc/os-release", "/usr/lib/os-release"):
        try:
            for l in open(p):
                if "=" in l: k, v = l.strip().split("=", 1); d[k] = v.strip('"')
            break
        except OSError: pass
    return d

def distro_family():
    d = osrel(); ids = (d.get("ID", "") + " " + d.get("ID_LIKE", "")).lower()
    for key, name in (("cachyos", "CachyOS (Arch)"), ("arch", "Arch-based"), ("suse", "openSUSE"),
                      ("ubuntu", "Ubuntu/Debian-based"), ("debian", "Debian-based"), ("fedora", "Fedora/RHEL-based")):
        if key in ids: return name
    return d.get("PRETTY_NAME", "Linux")

# ------------------------------------------------------------------ model
class Graph:
    def __init__(s, name="project"):
        s.name = name; s.nodes = {}; s.edges = []; s.groups = {}; s.meta = {"terminal": "GNOME Terminal"}
    @property
    def dir(s): return PROJ / s.name
    def asset(s, rel): return (s.dir / rel) if rel else None
    def add(s, t, x, y, **over):
        i = uuid.uuid4().hex[:8]; params = {k: d for k, _, _, d, _ in SPEC[t][2]}; params.update(over)
        s.nodes[i] = dict(id=i, type=t, x=x, y=y, params=params, group=None); return i
    def dump(s): return dict(version=1, name=s.name, nodes=list(s.nodes.values()), edges=s.edges,
                             groups=s.groups, meta=s.meta)
    @staticmethod
    def load(d, name):
        g = Graph(name); g.nodes = {n["id"]: n for n in d["nodes"]}
        g.edges = [tuple(e) for e in d["edges"]]; g.groups = d.get("groups", {}); g.meta.update(d.get("meta", {}))
        for n in g.nodes.values():
            for k, _, _, df, _ in SPEC[n["type"]][2]: n["params"].setdefault(k, df)
        return g

KEYC = ["#3daee9", "#e74c3c", "#2ecc71", "#f1c40f", "#9b59b6", "#1abc9c", "#e67e22", "#5dade2",
        "#ec7063", "#58d68d", "#f4d03f", "#af7ac5", "#48c9b0"]
def default_graph(name, preset):
    g = Graph(name); oid = g.add("output", 260, 0, preset=preset)
    if preset == "custom": return g
    fl = ["OS", "Host", "Kernel", "Uptime", "Packages", "Shell", "DE", "CPU", "Memory"]
    if preset == "advanced":
        fl = ["OS", "Host", "Kernel", "Uptime", "Packages", "Shell", "DE", "Session", "Terminal",
              "CPU", "GPU", "Memory", "Disk", "Resolution", "Locale"]
    ids = [g.add("logo", -300, -420), g.add("title", -300, -300)]
    for i, f in enumerate(fl):
        ids.append(g.add("info", -300, -200 + i * 80, field=f,
                         key_color=KEYC[i % len(KEYC)] if preset == "advanced" else "#3daee9"))
    ids.append(g.add("colors", -300, -200 + len(fl) * 80))
    g.edges = [(i, oid) for i in ids]; return g

# ------------------------------------------------------------------ compiler (graph -> runs)
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
def img2rows(img, w):
    h = max(2, round(img.height() * w / img.width() / 2) * 2)
    s = img.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio,
                   Qt.TransformationMode.SmoothTransformation).convertToFormat(QImage.Format.Format_ARGB32)
    rows = []
    for y in range(0, h, 2):
        row = []
        for x in range(w):
            a, b = s.pixelColor(x, y), s.pixelColor(x, y + 1); ta, tb = a.alpha() > 60, b.alpha() > 60
            if ta and tb: row.append(R("▀", a.name(), b.name()))
            elif ta: row.append(R("▀", a.name()))
            elif tb: row.append(R("▄", b.name()))
            else: row.append(R(" "))
        rows.append(merge(row))
    return rows

def image_frames(path, w):
    key = (str(path), path.stat().st_mtime, w)
    if key in IMGCACHE: return IMGCACHE[key]
    imgs = []; mv = QMovie(str(path))
    if mv.isValid() and mv.frameCount() > 1:
        for i in range(min(mv.frameCount(), 24)): mv.jumpToFrame(i); imgs.append(mv.currentImage())
    else: imgs = [QImage(str(path))]
    IMGCACHE[key] = [img2rows(i, w) for i in imgs if not i.isNull()] or [[[R("(unreadable image)")]]]
    return IMGCACHE[key]

def hue(h): return QColor.fromHsvF(h % 1.0, 0.75, 1.0).name()
def logo_frames(g, n, anim):
    p = n["params"]; src = p["source"]
    if src == "auto":
        d = osrel(); ids = (d.get("ID", "") + d.get("ID_LIKE", "")).lower()
        src = "arch" if re.search("arch|cachyos|manjaro|endeavour", ids) else "tux"
    if src == "file":
        path = g.asset(p["file"])
        if path and path.exists() and path.suffix.lower() in IMG: return image_frames(path, int(p["width"]))
        lines = path.read_text(errors="replace").splitlines() if path and path.exists() else ["(no file)"]
    else: lines = LOGOS.get(src, LOGOS["tux"])
    w = max(len(l) for l in lines); lines = [l.ljust(w) for l in lines]
    if anim == "rainbow":
        tot = w + 2 * len(lines)
        return [[merge([R(c, hue((x + 2 * y) / tot + t / 12)) if c != " " else R(" ") for x, c in enumerate(l)])
                 for y, l in enumerate(lines)] for t in range(12)]
    return [[[R(l, p["color"], None, True)] for l in lines]]

def compile_graph(g):
    out = next((n for n in g.nodes.values() if n["type"] == "output"), None)
    if not out: return None
    O = out["params"]; adv = O["preset"] == "advanced"; rows, funcs, logo = [], {}, None
    for n in sorted((g.nodes[a] for a, b in g.edges if b == out["id"] and a in g.nodes), key=lambda n: (n["y"], n["x"])):
        p, t = n["params"], n["type"]
        if t == "logo": logo = logo or n
        elif t == "title":
            funcs["Title"] = SH["Title"]; rows.append([R("{{Title}}", p["color"], None, True)])
            if p["underline"]:
                funcs["TitleU"] = 'u=$(%s); printf -v s "%%*s" "${#u}" ""; echo "${s// /%s}"' % (SH["Title"], "─" if adv else "-")
                rows.append([R("{{TitleU}}", O["fg"])])
        elif t == "info":
            f = p["field"]
            if f == "Custom": key = "c%d" % abs(hash(p["command"])); funcs[key] = p["command"]
            else: key = f; funcs[key] = SH[f]
            sep = O["separator"] if O["preset"] == "custom" else ": "
            rows.append(([R("◆ ", p["key_color"])] if adv else []) +
                        [R(p["label"] or f, p["key_color"], None, True), R(sep, O["fg"]), R("{{%s}}" % key, p["val_color"])])
        elif t == "colors":
            rows.append([])
            for r in range(int(p["rows"])): rows.append([R("   ", None, "a%d" % (i + 8 * r)) for i in range(8)])
        elif t == "text": rows.append([R(p["text"], p["color"])])
    frames = logo_frames(g, logo, O["animation"]) if logo else [[]]
    return dict(O=O, frames=frames, rows=rows, funcs=funcs)

def resolve(runs, funcs):
    return [(re.sub(r"\{\{(\w+)\}\}", lambda m: value(m[1], funcs[m[1]]), t), fg, bg, b) for t, fg, bg, b in runs]

def compose(c, fi):
    fr = c["frames"][fi % len(c["frames"])]
    lw = max((rlen(r) for f in c["frames"] for r in f), default=0); gap = int(c["O"]["gap"])
    res = []
    for i in range(max(len(fr), len(c["rows"]))):
        left = list(fr[i]) if i < len(fr) else []
        row = left + [R(" " * (lw - rlen(left) + gap))]
        if i < len(c["rows"]): row += resolve(c["rows"][i], c["funcs"])
        res.append(row)
    return res

# ------------------------------------------------------------------ build: standalone bash script + shell hooks
def esc(t): return t.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
def sgr(fg, bg, b):
    c = ["1"] if b else []
    for col, base in ((fg, 3), (bg, 4)):
        if not col: continue
        if col[0] == "a": n = int(col[1:]); c.append(str(base * 10 + (60 if n >= 8 else 0) + n % 8))
        else: q = QColor(col); c.append(f"{base}8;2;{q.red()};{q.green()};{q.blue()}")
    return "\\033[" + ";".join(c) + "m" if c else ""
def lit(r):
    st = sgr(r[1], r[2], r[3]); return st + esc(r[0]) + ("\\033[0m" if st else "")
def info_expr(row):
    parts = []
    for t, fg, bg, b in row:
        st = sgr(fg, bg, b)
        if st: parts.append("$'%s'" % st)
        for i, seg in enumerate(re.split(r"\{\{(\w+)\}\}", t)):
            if i % 2 == 0:
                if seg: parts.append("$'%s'" % esc(seg))
            else: parts.append('"$(f_%s)"' % seg)
        if st: parts.append("$'\\033[0m'")
    return "".join(parts)

def gen_script(c):
    O = c["O"]; frames = c["frames"]
    L = ["#!/usr/bin/env bash", "# Generated by Fetch Studio. Standalone - the app does not need to be running.",
         ". /etc/os-release 2>/dev/null"]
    for k, sn in c["funcs"].items(): L.append("f_%s(){\n%s\n}" % (k, sn))
    L.append("INFO=()")
    for row in c["rows"]: L.append("INFO+=(%s)" % (info_expr(row) or '""'))
    lw = max((rlen(r) for f in frames for r in f), default=0); gap = int(O["gap"])
    for i, fr in enumerate(frames):
        L.append("FR%d=(" % i)
        for row in fr: L.append("  " + "".join("$'%s'" % lit(r) for r in row) + "$'%s'" % (" " * (lw - rlen(row) + gap)))
        L.append(")")
    L.append("PAD=$'%s'" % (" " * (lw + gap)))
    L.append(r"""NF=__NF__
H=${#INFO[@]}; ((${#FR0[@]}>H)) && H=${#FR0[@]}
render(){ local -n F=$1; local i; for((i=0;i<H;i++)); do printf '%s%s\033[0m\n' "${F[i]-$PAD}" "${INFO[i]-}"; done; }
if ((NF>1)) && [ -t 1 ]; then
  printf '\033[?25l'; trap 'printf "\033[?25h"' EXIT
  for ((k=0;k<NF*2;k++)); do render FR$((k % NF)); sleep __DELAY__; printf '\033[%dA' "$H"; done
  printf '\033[?25h'
fi
render FR0""".replace("__NF__", str(len(frames))).replace("__DELAY__", "%.3f" % (1 / max(1, int(O["fps"])))))
    return "\n".join(L) + "\n"

def strip_block(t): return re.sub(re.escape(MARK_B) + r".*?" + re.escape(MARK_E) + r"\n?", "", t, flags=re.S)
def hook_files():
    home = Path.home(); sh = os.path.basename(os.environ.get("SHELL", ""))
    f = [("sh", home / ".bashrc")]                       # Debian/Ubuntu, Arch, openSUSE, Fedora
    zr = Path(os.environ.get("ZDOTDIR", home)) / ".zshrc"
    if sh == "zsh" or zr.exists(): f.append(("sh", zr))
    if sh == "fish" or shutil.which("fish"):             # CachyOS ships fish by default
        f.append(("fish", home / ".config/fish/conf.d/fetchstudio.fish"))
    return f
def install_hooks():
    script = str(ACTIVE / "fetch.sh"); done = []
    for kind, path in hook_files():
        body = ('case $- in *i*) [ -x "%s" ] && "%s";; esac' % (script, script)) if kind == "sh" else \
               ('status is-interactive; and test -x "%s"; and "%s"' % (script, script))
        path.parent.mkdir(parents=True, exist_ok=True)
        txt = strip_block(path.read_text()).rstrip("\n") if path.exists() else ""
        path.write_text((txt + "\n\n" if txt else "") + f"{MARK_B}\n{body}\n{MARK_E}\n"); done.append(path)
    return done
def remove_hooks():
    for kind, path in hook_files():
        if path.exists():
            t = strip_block(path.read_text())
            if kind == "fish" and not t.strip(): path.unlink()
            else: path.write_text(t)
    (ACTIVE / "fetch.sh").unlink(missing_ok=True)

# ------------------------------------------------------------------ terminal preview (cell-exact painter)
class TermView(QWidget):
    def __init__(s):
        super().__init__(); s.rows = []; s.bg = "#1e1e1e"; s.fg = "#d0d0d0"; s.title = "Terminal"; s.fsize = 11
        s.setMinimumSize(460, 320)
    def set(s, rows, bg, fg, title, fsize): s.rows, s.bg, s.fg, s.title, s.fsize = rows, bg, fg, title, fsize; s.update()
    def col(s, c): return QColor(PAL[int(c[1:])]) if c[0] == "a" else QColor(c)
    def paintEvent(s, e):
        p = QPainter(s); f = QFont("Monospace", s.fsize); f.setStyleHint(QFont.StyleHint.Monospace); f.setFixedPitch(True)
        fm = QFontMetricsF(f); cw, ch, asc = fm.horizontalAdvance("M"), float(round(fm.height())), fm.ascent()
        bar = 28; p.fillRect(s.rect(), QColor("#2b2b2b")); p.fillRect(0, 0, s.width(), bar, QColor("#3c3c3c"))
        p.setFont(QFont("Sans", 9)); p.setPen(QColor("#ddd"))
        p.drawText(QRectF(0, 0, s.width(), bar), Qt.AlignmentFlag.AlignCenter, s.title)
        for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")): p.setBrush(QColor(c)); p.setPen(Qt.PenStyle.NoPen); p.drawEllipse(10 + i * 18, 9, 11, 11)
        p.fillRect(0, bar, s.width(), s.height() - bar, QColor(s.bg))
        user, host = os.environ.get("USER", "user"), platform.node()
        prompt = [R(f"{user}@{host}", "a10", None, True), R(":"), R("~", "a12", None, True), R("$ ")]
        x0, y0 = 10, bar + 8; x = y = 0
        for y, row in enumerate(list(s.rows) + [prompt]):
            x = x0; ty = y0 + y * ch
            for t, fg, bg, b in row:
                col = s.col(fg or s.fg); f.setBold(b); p.setFont(f)
                for c in t:
                    r = QRectF(x, ty, cw, ch)
                    if bg: p.fillRect(r, s.col(bg))
                    if c == "▀": p.fillRect(QRectF(x, ty, cw, ch / 2), col)
                    elif c == "▄": p.fillRect(QRectF(x, ty + ch / 2, cw, ch / 2), col)
                    elif c == "█": p.fillRect(r, col)
                    elif c != " ": p.setPen(col); p.drawText(QPointF(x, ty + asc), c)
                    x += cw
        p.fillRect(QRectF(x, y0 + y * ch, cw, ch), QColor(s.fg))

# ------------------------------------------------------------------ graph items
class Port(QGraphicsEllipseItem):
    def __init__(s, node, out):
        super().__init__(-7, -7, 14, 14, node); s.node, s.out = node, out
        s.setBrush(QColor("#eee")); s.setPen(QPen(QColor("#222"), 2)); s.setZValue(3)
        s.setCursor(Qt.CursorShape.CrossCursor)
    def mousePressEvent(s, e):
        if e.button() == Qt.MouseButton.LeftButton: s.scene().begin_link(s); e.accept()
    def mouseMoveEvent(s, e): s.scene().drag_link(e.scenePos())
    def mouseReleaseEvent(s, e): s.scene().end_link(e.scenePos())

class NodeItem(QGraphicsItem):
    W, H = 176, 64
    def __init__(s, d):
        super().__init__(); s.d = d; s.edges = []; s.ready = False
        s.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
                   QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        s.setPos(d["x"], d["y"]); s.port = Port(s, d["type"] != "output")
        s.port.setPos(s.W if s.port.out else 0, s.H / 2 + 8); s.ready = True
    def boundingRect(s): return QRectF(-8, -8, s.W + 16, s.H + 16)
    def summary(s):
        p, t = s.d["params"], s.d["type"]
        v = {"info": p.get("label") or p.get("field"), "logo": p.get("source"), "title": "user@host",
             "output": f'{p.get("preset")} / {p.get("animation")}', "text": p.get("text"),
             "colors": f'{p.get("rows")} row(s)'}.get(t, "")
        return str(v)[:24]
    def paint(s, p, o, w):
        title, col, _ = SPEC[s.d["type"]]; p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#2b2b30")); p.setPen(QPen(QColor("#ffd33d") if s.isSelected() else QColor("#555"), 2))
        p.drawRoundedRect(QRectF(0, 0, s.W, s.H), 8, 8)
        p.setBrush(QColor(col)); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(0, 0, s.W, 22), 8, 8); p.drawRect(QRectF(0, 12, s.W, 10))
        p.setPen(QColor("white")); p.drawText(QRectF(8, 0, s.W, 22), Qt.AlignmentFlag.AlignVCenter, title)
        p.setPen(QColor("#bbb")); p.drawText(QRectF(12, 26, s.W - 24, s.H - 28), Qt.AlignmentFlag.AlignVCenter, s.summary())
    def itemChange(s, ch, v):
        if ch == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged and s.ready:
            s.d["x"], s.d["y"] = v.x(), v.y()
            for e in s.edges: e.refresh()
            if s.scene(): s.scene().moved()
        return super().itemChange(ch, v)

class EdgeItem(QGraphicsPathItem):
    def __init__(s, a, b):
        super().__init__(); s.a, s.b = a, b; s.setPen(QPen(QColor("#9ab"), 2.5)); s.setZValue(-1)
        a.edges.append(s); b.edges.append(s)
    def refresh(s):
        p1, p2 = s.a.scene().anchor_for(s.a), s.b.port.scenePos(); dx = max(40, abs(p2.x() - p1.x()) / 2)
        path = QPainterPath(p1); path.cubicTo(p1 + QPointF(dx, 0), p2 - QPointF(dx, 0), p2); s.setPath(path)

class GroupItem(QGraphicsItem):
    def __init__(s, gid, scn): super().__init__(); s.gid, s.scn, s.box = gid, scn, QRectF(); s.setZValue(-2)
    def info(s): return s.scn.g.groups[s.gid]
    def collapsed(s): return s.info()["collapsed"]
    def members(s): return [n for n in s.scn.nitems.values() if n.d["group"] == s.gid]
    def anchor(s): return QPointF(s.box.right(), s.box.center().y())
    def boundingRect(s): return s.box.adjusted(-2, -2, 2, 2)
    def refresh(s):
        m = s.members(); s.prepareGeometryChange()
        if not m: s.box = QRectF(); return
        if s.collapsed():
            x, y = s.info()["pos"]; s.box = QRectF(x, y, 176, 34)
            for n in m: n.setVisible(False)
        else:
            r = m[0].sceneBoundingRect()
            for n in m[1:]: r = r.united(n.sceneBoundingRect())
            s.box = r.adjusted(-8, -30, 8, 8)
            for n in m: n.setVisible(True)
        s.update()
    def paint(s, p, o, w):
        p.setRenderHint(QPainter.RenderHint.Antialiasing); c = QColor("#e67e22"); f = QColor(c)
        f.setAlpha(120 if s.collapsed() else 28); p.setBrush(f); p.setPen(QPen(c, 1.5, Qt.PenStyle.DashLine))
        p.drawRoundedRect(s.box, 10, 10); p.setPen(QColor("#f5cba7"))
        txt = ("▸ %s  (%d nodes)" % (s.info()["name"], len(s.members()))) if s.collapsed() else "▾ " + s.info()["name"]
        p.drawText(QRectF(s.box.left() + 10, s.box.top(), s.box.width(), 30 if not s.collapsed() else 34),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, txt)

class GraphScene(QGraphicsScene):
    def __init__(s, win):
        super().__init__(); s.win = win; s.g = None; s.nitems = {}; s.gitems = {}; s.link = s.tmp = None
        s.setSceneRect(-4000, -4000, 8000, 8000)
    def drawBackground(s, p, r):
        p.fillRect(r, QColor("#1a1a1e")); p.setPen(QPen(QColor("#26262c"), 1)); st = 40
        x = int(r.left()) // st * st
        while x < r.right(): p.drawLine(x, int(r.top()), x, int(r.bottom())); x += st
        y = int(r.top()) // st * st
        while y < r.bottom(): p.drawLine(int(r.left()), y, int(r.right()), y); y += st
    def load(s, g):
        s.clear(); s.g = g; s.nitems = {}; s.gitems = {}; s.link = s.tmp = None
        for i, d in g.nodes.items(): n = NodeItem(d); s.addItem(n); s.nitems[i] = n
        for gid in g.groups: gi = GroupItem(gid, s); s.addItem(gi); s.gitems[gid] = gi
        for a, b in g.edges:
            if a in s.nitems and b in s.nitems: s.add_edge(a, b)
        s.refresh_groups()
    def add_edge(s, a, b): e = EdgeItem(s.nitems[a], s.nitems[b]); s.addItem(e); e.refresh()
    def anchor_for(s, n):
        gi = s.gitems.get(n.d["group"])
        return gi.anchor() if gi and gi.collapsed() else n.port.scenePos()
    def refresh_groups(s):
        for gi in s.gitems.values(): gi.refresh()
        for n in s.nitems.values():
            for e in n.edges: e.refresh()
    def moved(s): s.refresh_groups(); s.win.touch()
    def add_node(s, t, pos):
        i = s.g.add(t, pos.x(), pos.y()); n = NodeItem(s.g.nodes[i]); s.addItem(n); s.nitems[i] = n
        s.clearSelection(); n.setSelected(True); s.win.touch()
    # links
    def begin_link(s, port):
        s.link = port; s.tmp = QGraphicsPathItem(); s.tmp.setPen(QPen(QColor("#ffd33d"), 2, Qt.PenStyle.DashLine)); s.addItem(s.tmp)
    def drag_link(s, pos):
        if s.tmp: pa = QPainterPath(s.link.scenePos()); pa.lineTo(pos); s.tmp.setPath(pa)
    def end_link(s, pos):
        if s.tmp: s.removeItem(s.tmp); s.tmp = None
        for it in s.items(pos):
            if isinstance(it, Port) and it is not s.link and it.out != s.link.out:
                o, i = (s.link, it) if s.link.out else (it, s.link)
                k = (o.node.d["id"], i.node.d["id"])
                if k not in s.g.edges: s.g.edges.append(k); s.add_edge(*k); s.win.touch()
                break
        s.link = None
    def remove_edge(s, e):
        e.a.edges.remove(e); e.b.edges.remove(e); s.removeItem(e)
        k = (e.a.d["id"], e.b.d["id"])
        if k in s.g.edges: s.g.edges.remove(k)
        s.win.touch()
    def sel_nodes(s): return [i for i in s.selectedItems() if isinstance(i, NodeItem) and i.d["type"] != "output"]
    def delete_selected(s):
        for n in s.sel_nodes():
            for e in list(n.edges): s.remove_edge(e)
            s.removeItem(n); del s.nitems[n.d["id"]]; del s.g.nodes[n.d["id"]]
        s.prune_groups(); s.win.touch()
    def prune_groups(s):
        for gid in list(s.g.groups):
            if not any(n.d["group"] == gid for n in s.nitems.values()):
                s.removeItem(s.gitems.pop(gid)); del s.g.groups[gid]
        s.refresh_groups()
    def group_selected(s):
        sel = s.sel_nodes()
        if len(sel) < 2: return
        name, ok = QInputDialog.getText(s.win, "Group nodes", "Group name:", text="Group")
        if not ok: return
        gid = uuid.uuid4().hex[:6]; s.g.groups[gid] = dict(name=name or "Group", collapsed=False, pos=[0, 0])
        gi = GroupItem(gid, s); s.addItem(gi); s.gitems[gid] = gi
        for n in sel: n.d["group"] = gid
        s.prune_groups(); s.win.touch()
    def toggle_group(s, gid):
        gi, info = s.gitems[gid], s.g.groups[gid]
        if not info["collapsed"]: info["pos"] = [gi.box.left(), gi.box.top()]
        info["collapsed"] = not info["collapsed"]; s.refresh_groups(); s.win.touch()
    def rename_group(s, gid):
        name, ok = QInputDialog.getText(s.win, "Rename group", "Name:", text=s.g.groups[gid]["name"])
        if ok and name: s.g.groups[gid]["name"] = name; s.gitems[gid].update(); s.win.touch()
    def ungroup(s, gid):
        for n in s.nitems.values():
            if n.d["group"] == gid: n.d["group"] = None
        s.gitems[gid].refresh(); s.prune_groups(); s.win.touch()

class GraphView(QGraphicsView):
    """left-drag pan | shift+left-drag box select | right-click menu | wheel scroll | ctrl+wheel zoom"""
    def __init__(s, scene, win):
        super().__init__(scene); s.win = win; s._pan = None
        s.setRenderHints(QPainter.RenderHint.Antialiasing)
        s.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        s.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate); s.centerOn(0, 0)
    def _on_item(s, pos):
        return any(isinstance(i, (NodeItem, Port)) or (isinstance(i, GroupItem) and i.collapsed()) for i in s.items(pos))
    def mousePressEvent(s, e):
        if e.button() == Qt.MouseButton.RightButton: e.accept(); return
        if e.button() == Qt.MouseButton.LeftButton and not s._on_item(e.position().toPoint()):
            if e.modifiers() & Qt.KeyboardModifier.ShiftModifier: s.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            else:
                s._pan = e.position().toPoint(); s.setCursor(Qt.CursorShape.ClosedHandCursor)
                s.scene().clearSelection(); e.accept(); return
        super().mousePressEvent(e)
    def mouseMoveEvent(s, e):
        if s._pan is not None:
            p = e.position().toPoint(); d = p - s._pan; s._pan = p
            s.horizontalScrollBar().setValue(s.horizontalScrollBar().value() - d.x())
            s.verticalScrollBar().setValue(s.verticalScrollBar().value() - d.y())
            if abs(d.x()) + abs(d.y()): s.win.flags["panned"] = True
            return
        super().mouseMoveEvent(e)
    def mouseReleaseEvent(s, e):
        if s._pan is not None: s._pan = None; s.unsetCursor(); return
        super().mouseReleaseEvent(e); s.setDragMode(QGraphicsView.DragMode.NoDrag)
    def wheelEvent(s, e):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            f = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
            if 0.25 < s.transform().m11() * f < 3: s.scale(f, f)
            s.win.flags["panned"] = True; e.accept()
        else: super().wheelEvent(e)
    def keyPressEvent(s, e):
        if e.key() == Qt.Key.Key_Delete: s.scene().delete_selected()
        else: super().keyPressEvent(e)
    def mouseDoubleClickEvent(s, e):
        for i in s.items(e.position().toPoint()):
            if isinstance(i, GroupItem): s.scene().toggle_group(i.gid); return
        super().mouseDoubleClickEvent(e)
    def contextMenuEvent(s, e):
        sc = s.scene(); items = s.items(e.pos()); sp = s.mapToScene(e.pos()); m = QMenu(s)
        for i in items:
            if isinstance(i, NodeItem) and not i.isSelected(): sc.clearSelection(); i.setSelected(True); break
        add = m.addMenu("Add node")
        for t, (title, _, _) in SPEC.items():
            if t != "output": add.addAction(title, lambda t=t: sc.add_node(t, sp))
        m.addAction("Group selected nodes", sc.group_selected)
        gid = next((i.gid for i in items if isinstance(i, GroupItem)), None) or \
              next((i.d["group"] for i in items if isinstance(i, NodeItem) and i.d["group"]), None)
        if gid:
            m.addSeparator(); c = sc.g.groups[gid]["collapsed"]
            m.addAction("Expand group" if c else "Collapse group", lambda: sc.toggle_group(gid))
            m.addAction("Rename group…", lambda: sc.rename_group(gid)); m.addAction("Ungroup", lambda: sc.ungroup(gid))
        ed = next((i for i in items if isinstance(i, EdgeItem)), None)
        if ed: m.addSeparator(); m.addAction("Remove connection", lambda: sc.remove_edge(ed))
        m.addSeparator(); m.addAction("Delete selected nodes", sc.delete_selected); m.exec(e.globalPos())

# ------------------------------------------------------------------ properties panel
class PropPanel(QScrollArea):
    def __init__(s, win): super().__init__(); s.win = win; s.d = None; s.setWidgetResizable(True); s.show_node(None)
    def show_node(s, d):
        s.d = d; w = QWidget(); f = QFormLayout(w)
        if not d: f.addRow(QLabel("Select a node to edit its properties.")); s.setWidget(w); return
        f.addRow(QLabel("<b>%s</b>" % SPEC[d["type"]][0]))
        for key, label, kind, default, opts in SPEC[d["type"]][2]:
            v = d["params"][key]
            if kind == "combo":
                x = QComboBox(); x.addItems(opts); x.setCurrentText(str(v)); x.currentTextChanged.connect(lambda t, k=key: s.set(k, t))
            elif kind == "int":
                x = QSpinBox(); x.setRange(*opts); x.setValue(int(v)); x.valueChanged.connect(lambda t, k=key: s.set(k, t))
            elif kind == "check":
                x = QCheckBox(); x.setChecked(bool(v)); x.toggled.connect(lambda t, k=key: s.set(k, t))
            elif kind == "text":
                x = QLineEdit(str(v)); x.textChanged.connect(lambda t, k=key: s.set(k, t))
            elif kind == "color":
                x = QPushButton(v); s.paint_btn(x, v); x.clicked.connect(lambda _, k=key, b=x: s.pick_color(k, b))
            else:
                x = QPushButton(v or "Choose file…"); x.clicked.connect(lambda _: s.pick_file())
            f.addRow(label, x)
        s.setWidget(w)
    def paint_btn(s, b, c):
        q = QColor(c); b.setStyleSheet("background:%s;color:%s" % (c, "#000" if q.lightness() > 128 else "#fff"))
    def set(s, k, v): s.d["params"][k] = v; s.win.node_changed(s.d)
    def pick_color(s, k, b):
        c = QColorDialog.getColor(QColor(s.d["params"][k]), s)
        if c.isValid(): b.setText(c.name()); s.paint_btn(b, c.name()); s.set(k, c.name())
    def pick_file(s):
        fn, _ = QFileDialog.getOpenFileName(s, "Logo image, GIF or text file", "", "Images/Text (*.png *.jpg *.jpeg *.gif *.webp *.bmp *.txt);;All (*)")
        if fn: s.d["params"]["file"] = s.win.import_asset(fn); s.d["params"]["source"] = "file"; s.win.node_changed(s.d); s.show_node(s.d)

# ------------------------------------------------------------------ interactive lesson
class Lesson(QWidget):
    def __init__(s, win):
        super().__init__(win); s.w = win; s.active = False; s.i = 0
        s.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        s.panel = QFrame(win); s.panel.setStyleSheet("QFrame{background:#22252b;border:2px solid #ffd33d;border-radius:8px}QLabel{border:0}")
        v = QVBoxLayout(s.panel); s.cnt = QLabel(); s.lbl = QLabel(); s.lbl.setWordWrap(True); v.addWidget(s.cnt); v.addWidget(s.lbl)
        r = QHBoxLayout(); s.back, s.nxt, s.quit = QPushButton("◂ Back"), QPushButton("Next ▸"), QPushButton("Save && exit lesson")
        for b in (s.back, s.nxt, s.quit): r.addWidget(b)
        v.addLayout(r); s.back.clicked.connect(lambda: s.go(-1)); s.nxt.clicked.connect(lambda: s.go(1)); s.quit.clicked.connect(s.stop)
        s.timer = QTimer(s); s.timer.timeout.connect(s.poll); s.hide(); s.panel.hide()
    def steps(s):
        w = s.w; outp = lambda: next((n for n in w.g.nodes.values() if n["type"] == "output"), None)
        return [
            (lambda: w.view, "Welcome! This is the node graph. Drag with the LEFT mouse button on empty space to pan, or hold Ctrl and scroll to zoom. Try it now.", lambda: w.flags["panned"]),
            (lambda: w.view, "Right-click empty canvas ▸ Add node ▸ Title. Then right-click again and add an Info node.", lambda: w.has("title") and w.has("info")),
            (lambda: w.props, "Click your Info node, then change 'Field' here to something other than OS (e.g. Kernel).", lambda: any(n["type"] == "info" and n["params"]["field"] != "OS" for n in w.g.nodes.values())),
            (lambda: w.view, "Drag from a node's round right-hand port to the Output node's left-hand port to connect them. Connect both Title and Info.", lambda: w.linked("title") and w.linked("info")),
            (lambda: w.term, "This is your live 1:1 terminal preview. Now add a Logo node and connect it to Output too.", lambda: w.linked("logo")),
            (lambda: w.view, "Hold Shift and drag a box around two nodes, then right-click ▸ Group selected nodes.", lambda: bool(w.g.groups)),
            (lambda: w.view, "Right-click the group ▸ Collapse group (or double-click it).", lambda: any(g["collapsed"] for g in w.g.groups.values())),
            (lambda: w.view, "Expand it again the same way.", lambda: bool(w.g.groups) and not any(g["collapsed"] for g in w.g.groups.values())),
            (lambda: w.props, "Select the Output node and set Logo animation to 'rainbow' (or try the other presets).", lambda: outp() and outp()["params"]["animation"] == "rainbow"),
            (lambda: w.bar("Save"), "Press Ctrl+S (or click Save) to save your project. It also auto-saves every 10 minutes.", lambda: w.flags["saved"] > 0),
            (lambda: w.bar("Export"), "Click Export to create a shareable fetchstudio(name).zip with your graph and images.", lambda: w.flags["exported"]),
            (lambda: w.bar("Build"), "Click Build. This installs a standalone script and shell hook, so new terminals show your fetch without this app.", lambda: w.flags["built"])]
    def start(s, restart=False):
        s.i = 0 if restart else int(s.w.cfg.value("lesson/step", 0)); s.i = min(s.i, len(s.steps()) - 1)
        s.active = True; s.show(); s.panel.show(); s.timer.start(250); s.poll()
    def stop(s): s.w.cfg.setValue("lesson/step", s.i); s.active = False; s.timer.stop(); s.hide(); s.panel.hide()
    def go(s, d):
        if s.i + d >= len(s.steps()):
            s.w.cfg.setValue("lesson/done", True); s.w.cfg.setValue("lesson/step", 0); s.stop()
            QMessageBox.information(s.w, APP, "Lesson complete! Reopen it any time from the Lesson button."); return
        s.i = max(0, s.i + d); s.w.cfg.setValue("lesson/step", s.i); s.poll()
    def poll(s):
        if not s.active: return
        st = s.steps(); s.setGeometry(s.w.rect()); s.raise_(); s.panel.raise_()
        s.cnt.setText("<b>Lesson %d / %d</b>" % (s.i + 1, len(st))); s.lbl.setText(st[s.i][1])
        ok = bool(st[s.i][2]()); s.nxt.setEnabled(ok); s.nxt.setText("Finish ✓" if s.i == len(st) - 1 else ("Next ▸" if ok else "Complete the step…"))
        s.back.setEnabled(s.i > 0); pw = min(560, s.w.width() - 40); s.panel.setFixedWidth(pw); s.panel.adjustSize()
        s.panel.move((s.w.width() - pw) // 2, s.w.height() - s.panel.height() - 16); s.update()
    def paintEvent(s, e):
        if not s.active: return
        t = s.steps()[s.i][0](); pt = t.mapTo(s.w, t.rect().topLeft())
        hole = QPainterPath(); hole.addRoundedRect(QRectF(pt.x() - 4, pt.y() - 4, t.width() + 8, t.height() + 8), 8, 8)
        full = QPainterPath(); full.addRect(QRectF(s.rect())); p = QPainter(s)
        p.fillPath(full.subtracted(hole), QColor(0, 0, 0, 140)); p.setPen(QPen(QColor("#ffd33d"), 3)); p.drawPath(hole)

# ------------------------------------------------------------------ main window
def clean_name(n): return re.sub(r"[^\w.-]+", "_", n.strip()) or "project"
class Main(QMainWindow):
    def __init__(s):
        super().__init__(); s.cfg = QSettings("GriffinLinux", "FetchStudio"); s.g = None; s.dirty = False
        s.comp = None; s.fi = 0; s.flags = dict(saved=0, exported=False, built=False, panned=False)
        s.scene = GraphScene(s); s.view = GraphView(s.scene, s); s.props = PropPanel(s); s.term = TermView()
        s.tcombo = QComboBox(); s.tcombo.addItems(list(TERMS)); s.tcombo.currentTextChanged.connect(s.set_terminal)
        right = QWidget(); v = QVBoxLayout(right); v.addWidget(QLabel("Live preview — terminal:")); v.addWidget(s.tcombo)
        v.addWidget(s.term, 3); v.addWidget(s.props, 2)
        sp = QSplitter(); sp.addWidget(s.view); sp.addWidget(right); sp.setSizes([760, 560]); s.setCentralWidget(sp)
        s.tb = QToolBar(); s.tb.setMovable(False); s.addToolBar(s.tb); s.acts = {}
        for name, key, fn in (("New", "Ctrl+N", s.new_project), ("Open", "Ctrl+O", s.open_project), ("Save", "Ctrl+S", lambda: s.save()),
                              ("Import", "Ctrl+I", s.import_zip), ("Export", "Ctrl+E", s.export_zip), ("Build", "Ctrl+B", s.build),
                              ("Remove", "", s.remove_build), ("Lesson", "F1", lambda: s.lesson.start())):
            a = QAction(name, s); a.triggered.connect(fn)
            if key: a.setShortcut(QKeySequence(key))
            s.tb.addAction(a); s.acts[name] = a
        s.scene.selectionChanged.connect(s.on_sel); s.lesson = Lesson(s)
        s.timer = QTimer(s); s.timer.timeout.connect(s.tick)
        s.auto = QTimer(s); s.auto.timeout.connect(lambda: s.dirty and s.g and s.save(auto=True)); s.auto.start(600_000)
        s.setStyleSheet("QMainWindow,QWidget{background:#202226;color:#ddd}QToolBar{background:#2a2d33;spacing:6px}"
                        "QPushButton,QComboBox,QLineEdit,QSpinBox{background:#33363d;border:1px solid #555;padding:3px}")
        s.resize(1360, 820); PROJ.mkdir(parents=True, exist_ok=True)
        last = s.cfg.value("last", "")
        if last and (PROJ / last / "project.json").exists(): s.open_graph(s.read(last))
        else: s.open_graph(default_graph("my-first-fetch", "custom")); s.save()
        if not s.cfg.value("lesson/done", False, type=bool): QTimer.singleShot(500, lambda: s.lesson.start())
    # helpers
    def bar(s, n): return s.tb.widgetForAction(s.acts[n])
    def has(s, t): return any(n["type"] == t for n in s.g.nodes.values())
    def linked(s, t): return any(s.g.nodes[a]["type"] == t and s.g.nodes[b]["type"] == "output" for a, b in s.g.edges if a in s.g.nodes and b in s.g.nodes)
    def read(s, name): return Graph.load(json.loads((PROJ / name / "project.json").read_text()), name)
    def on_sel(s):
        sel = [i for i in s.scene.selectedItems() if isinstance(i, NodeItem)]; s.props.show_node(sel[0].d if len(sel) == 1 else None)
    def set_terminal(s, t): s.g.meta["terminal"] = t; s.touch() if s.g else None
    def title(s): s.setWindowTitle("%s — %s%s" % (APP, s.g.name, " *" if s.dirty else ""))
    def node_changed(s, d): s.scene.nitems[d["id"]].update(); s.touch()
    def touch(s): s.dirty = True; s.recompile(); s.title()
    def recompile(s):
        s.comp = compile_graph(s.g); s.fi = 0
        n = len(s.comp["frames"]) if s.comp else 1
        s.timer.start(int(1000 / max(1, int(s.comp["O"]["fps"]))) if n > 1 else 300); s.render()
    def tick(s):
        if s.comp and len(s.comp["frames"]) > 1: s.fi += 1; s.render()
        elif STATE["dirty"]: s.render()
    def render(s):
        STATE["dirty"] = False; t = TERMS.get(s.g.meta.get("terminal"), TERMS["GNOME Terminal"])
        if not s.comp: s.term.set([], "#1e1e1e", "#d0d0d0", t[0], t[1]); return
        O = s.comp["O"]; s.term.set(compose(s.comp, s.fi), O["bg"], O["fg"], t[0], t[1])
    def import_asset(s, path):
        d = s.g.dir / "assets"; d.mkdir(parents=True, exist_ok=True); name = Path(path).name; dst = d / name; k = 1
        while dst.exists() and not dst.samefile(path): dst = d / f"{k}_{name}"; k += 1
        if not dst.exists(): shutil.copy(path, dst)
        return "assets/" + dst.name
    # project lifecycle
    def open_graph(s, g):
        s.g = g; s.scene.blockSignals(True); s.scene.load(g); s.scene.blockSignals(False); s.props.show_node(None)
        s.tcombo.blockSignals(True); s.tcombo.setCurrentText(g.meta.get("terminal", "GNOME Terminal")); s.tcombo.blockSignals(False)
        s.dirty = False; s.cfg.setValue("last", g.name); s.recompile(); s.title()
    def maybe_save(s):
        if not s.dirty: return True
        r = QMessageBox.question(s, APP, "Save changes to “%s”?" % s.g.name,
                                 QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        if r == QMessageBox.StandardButton.Save: s.save(); return True
        return r == QMessageBox.StandardButton.Discard
    def save(s, auto=False):
        s.g.dir.mkdir(parents=True, exist_ok=True); (s.g.dir / "project.json").write_text(json.dumps(s.g.dump(), indent=1))
        s.dirty = False; s.cfg.setValue("last", s.g.name); s.title()
        if not auto: s.flags["saved"] += 1
    def new_project(s):
        if not s.maybe_save(): return
        name, ok = QInputDialog.getText(s, "New project", "Project name:", text="my-fetch")
        if not ok or not name.strip(): return
        pr, ok = QInputDialog.getItem(s, "New project", "Start from preset:", ["classic", "advanced", "custom"], 0, False)
        if not ok: return
        name = clean_name(name)
        while (PROJ / name).exists(): name += "-2"
        s.open_graph(default_graph(name, pr)); s.save()
    def open_project(s):
        if not s.maybe_save(): return
        names = sorted(p.parent.name for p in PROJ.glob("*/project.json"))
        n, ok = QInputDialog.getItem(s, "Open project", "Project:", names, 0, False) if names else ("", False)
        if ok: s.open_graph(s.read(n))
    def export_zip(s):
        s.save(); fn, _ = QFileDialog.getSaveFileName(s, "Export", str(Path.home() / f"fetchstudio({s.g.name}).zip"), "Zip (*.zip)")
        if not fn: return
        with zipfile.ZipFile(fn, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("project.json", json.dumps(s.g.dump(), indent=1))
            for f in (s.g.dir / "assets").glob("*"): z.write(f, "assets/" + f.name)
        s.flags["exported"] = True; QMessageBox.information(s, APP, "Exported:\n" + fn)
    def import_zip(s):
        if not s.maybe_save(): return
        fn, _ = QFileDialog.getOpenFileName(s, "Import fetchstudio zip", str(Path.home()), "Zip (*.zip)")
        if not fn: return
        try:
            with zipfile.ZipFile(fn) as z:
                data = json.loads(z.read("project.json")); name = clean_name(data.get("name", "imported"))
                while (PROJ / name).exists(): name += "-imported"
                (PROJ / name / "assets").mkdir(parents=True)
                for m in z.namelist():
                    if m.startswith("assets/") and not m.endswith("/"):          # basename only: no path traversal
                        (PROJ / name / "assets" / Path(m).name).write_bytes(z.read(m))
                data["name"] = name; (PROJ / name / "project.json").write_text(json.dumps(data, indent=1))
            s.open_graph(s.read(name))
        except Exception as ex: QMessageBox.warning(s, APP, "Could not import:\n%s" % ex)
    def build(s):
        c = compile_graph(s.g)
        if not c: QMessageBox.warning(s, APP, "Add an Output node first."); return
        s.save(); ACTIVE.mkdir(parents=True, exist_ok=True); (DATA / "built").mkdir(exist_ok=True)
        text = gen_script(c)
        for p in (ACTIVE / "fetch.sh", DATA / "built" / (s.g.name + ".sh")): p.write_text(text); p.chmod(0o755)
        files = install_hooks(); s.flags["built"] = True
        found = [n for n, (_, _, exe) in TERMS.items() if shutil.which(exe)]
        QMessageBox.information(s, APP, "Built for %s.\n\nScript: %s\nShell hooks:\n  %s\n\nTerminals found here: %s\n\nOpen a new terminal to see it. "
                                "The app is no longer needed; use Build again after editing, or Remove to uninstall." %
                                (distro_family(), ACTIVE / "fetch.sh", "\n  ".join(map(str, files)), ", ".join(found) or "none detected"))
    def remove_build(s): remove_hooks(); QMessageBox.information(s, APP, "Fetch Studio hooks and script removed.")
    def closeEvent(s, e):
        if s.maybe_save(): s.lesson.stop() if s.lesson.active else None; e.accept()
        else: e.ignore()

def main():
    app = QApplication(sys.argv); app.setApplicationName(APP); w = Main(); w.show(); sys.exit(app.exec())
if __name__ == "__main__": main()

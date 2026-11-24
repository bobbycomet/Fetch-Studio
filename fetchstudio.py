#!/usr/bin/env python3
"""Fetch Studio - node-based neofetch/fastfetch designer with a 1:1 terminal preview (PyQt6)."""
import sys, os, re, json, shutil, zipfile, platform, subprocess, threading, uuid, copy, random, math
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, QRect, QSize, QSettings, QMimeData, pyqtSignal
from PyQt6.QtGui import (QAction, QColor, QFont, QFontMetricsF, QImage, QKeySequence,
                         QMovie, QPainter, QPainterPath, QPen)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsPathItem, QGraphicsEllipseItem, QMenu, QToolBar, QSplitter, QVBoxLayout,
    QHBoxLayout, QFormLayout, QComboBox, QLineEdit, QPushButton, QSpinBox, QCheckBox,
    QColorDialog, QFileDialog, QInputDialog, QMessageBox, QLabel, QFrame, QScrollArea,
    QTabWidget, QListWidget, QListWidgetItem, QButtonGroup)

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
class Par:
    def __init__(s, key, label, kind, default, opts=None, fancy=False):
        s.key, s.label, s.kind, s.default, s.opts, s.fancy = key, label, kind, default, opts, fancy
P = Par
FIELDS = ["OS", "Host", "Kernel", "Uptime", "Packages", "Shell", "DE", "Session", "Terminal", "CPU", "GPU",
          "Memory", "Disk", "Swap", "Load", "Battery", "LocalIP", "Resolution", "Locale", "Custom"]
ANIMS = ["none", "rainbow", "scroll", "pulse", "wave", "typewriter", "sparkle", "scanline"]
GRADS = ["none", "horizontal", "vertical", "diagonal", "radial"]
METRICS = {"Memory": "PCT_Memory", "Disk": "PCT_Disk", "CPU load": "PCT_CPU", "Swap": "PCT_Swap", "Battery": "PCT_Battery"}
BARCH = {"blocks": ("█", "░"), "dots": ("●", "○"), "lines": ("━", "─"), "ascii": ("#", "-")}
FANCY_NODES = {"bar", "divider"}          # hidden in classic mode
THEMES = {
    "dracula": dict(bg="#282a36", fg="#f8f8f2", dim="#44475a", acc=["#bd93f9", "#ff79c6", "#8be9fd", "#50fa7b", "#f1fa8c", "#ffb86c"]),
    "nord": dict(bg="#2e3440", fg="#d8dee9", dim="#4c566a", acc=["#88c0d0", "#81a1c1", "#8fbcbb", "#a3be8c", "#ebcb8b", "#b48ead"]),
    "gruvbox": dict(bg="#282828", fg="#ebdbb2", dim="#504945", acc=["#fabd2f", "#fb4934", "#b8bb26", "#83a598", "#d3869b", "#fe8019"]),
    "catppuccin": dict(bg="#1e1e2e", fg="#cdd6f4", dim="#45475a", acc=["#cba6f7", "#f38ba8", "#a6e3a1", "#89b4fa", "#f9e2af", "#fab387"]),
    "tokyo night": dict(bg="#1a1b26", fg="#c0caf5", dim="#414868", acc=["#7aa2f7", "#bb9af7", "#7dcfff", "#9ece6a", "#e0af68", "#f7768e"])}
SPEC = {
    "output": ("Output", "#c0392b", [
        P("preset", "Preset", "combo", "classic", ["classic", "advanced", "custom"]),
        P("theme", "Color theme", "combo", "none", ["none"] + list(THEMES)),
        P("gap", "Logo gap", "int", 3, (1, 12)), P("separator", "Separator (custom)", "text", ": "),
        P("bg", "Background", "color", "#1e1e1e"), P("fg", "Default text", "color", "#d0d0d0"),
        P("animation", "Default logo animation", "combo", "none", ANIMS, True),
        P("fps", "Animation FPS", "int", 12, (1, 30), True),
        P("lifetime", "Lifetime: intro=plays at launch, live=until 1st command", "combo", "intro", ["intro", "live"], True),
        P("loops", "Intro loops (1 = play once)", "int", 1, (1, 6), True)]),
    "logo": ("Logo", "#2980b9", [
        P("source", "Source", "combo", "auto", ["auto", "tux", "arch", "file"]),
        P("file", "Image / GIF / text file", "file", ""), P("width", "Image width (cols) — higher = sharper", "int", 72, (8, 200)),
        P("color", "Color", "color", "#3daee9"),
        P("gradient", "Gradient", "combo", "none", GRADS, True), P("color2", "Gradient color 2", "color", "#bb9af7", True),
        P("color3", "Gradient color 3", "color", "#f7768e", True),
        P("animation", "Animation", "combo", "inherit", ["inherit"] + ANIMS, True)]),
    "clogo": ("Custom Logo", "#16a085", [
        P("animation", "Animation", "combo", "design", ["design"] + ANIMS, True),
        P("data", "", "hidden", None),
        P("_edit", "Edit in ASCII Designer…", "action", "edit"), P("_export", "Export node (.fsnode)…", "action", "export")]),
    "title": ("Title", "#27ae60", [P("color", "Color", "color", "#3daee9"), P("underline", "Underline", "check", True)]),
    "info": ("Info", "#8e44ad", [
        P("field", "Field", "combo", "OS", FIELDS), P("label", "Label (blank = field)", "text", ""),
        P("key_color", "Label color", "color", "#3daee9"), P("val_color", "Value color", "color", "#d0d0d0"),
        P("command", "Command (Custom field)", "text", "echo hello")]),
    "bar": ("Meter bar", "#1abc9c", [
        P("metric", "Metric", "combo", "Memory", list(METRICS)), P("label", "Label (blank = metric)", "text", ""),
        P("width", "Bar width", "int", 16, (6, 40)), P("style", "Style", "combo", "blocks", list(BARCH)),
        P("key_color", "Label color", "color", "#3daee9"), P("c1", "Low color", "color", "#2ecc71"),
        P("c2", "Mid color", "color", "#f1c40f"), P("c3", "High color", "color", "#e74c3c"),
        P("empty", "Empty color", "color", "#44475a")]),
    "divider": ("Divider", "#5d6d7e", [
        P("char", "Character", "text", "─"), P("width", "Width", "int", 30, (4, 80)), P("label", "Label", "text", ""),
        P("color", "Color", "color", "#3daee9"), P("color2", "End color", "color", "#bb9af7"),
        P("gradient", "Gradient", "check", True)]),
    "colors": ("Color bar", "#d35400", [P("rows", "Rows", "combo", "2", ["1", "2"])]),
    "text": ("Text", "#7f8c8d", [P("text", "Text", "text", "Hello"), P("color", "Color", "color", "#d0d0d0")]),
}
STYLE = """
QMainWindow, QWidget { background:#171d25; color:#c7d5e0; font-size:13px; }
QToolBar { background:#1b2838; border-bottom:2px solid #2a475e; spacing:5px; padding:5px; }
QToolButton { background:#2a475e; border:1px solid #3d6c8d; border-radius:5px; padding:5px 13px; color:#e5eef5; font-weight:600; }
QToolButton:hover { background:#3d6c8d; }
QToolButton:checked { background:#66c0f4; color:#0e1621; border-color:#9bd8ff; }
QPushButton, QComboBox, QLineEdit, QSpinBox { background:#1f3347; border:1px solid #35566f; border-radius:4px; padding:4px 9px; }
QPushButton:hover { background:#2a475e; border-color:#66c0f4; }
QPushButton:checked { background:#66c0f4; color:#0e1621; }
QPushButton:disabled, QComboBox:disabled { color:#5a6b78; background:#18232f; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border-color:#66c0f4; }
QComboBox QAbstractItemView { background:#1b2838; selection-background-color:#2a475e; border:1px solid #3d6c8d; }
QTabWidget::pane { border:0; }
QTabBar { background:#0e1621; }
QTabBar::tab { background:#2a475e; color:#c7d5e0; padding:9px 24px; margin:5px 3px 0 3px; border-top-left-radius:9px; border-top-right-radius:9px; font-weight:700; }
QTabBar::tab:hover { background:#3d6c8d; }
QTabBar::tab:selected { background:#66c0f4; color:#0e1621; }
QScrollArea { border:0; }
QScrollBar:vertical { background:#171d25; width:11px; } QScrollBar:horizontal { background:#171d25; height:11px; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal { background:#35566f; border-radius:5px; min-height:26px; min-width:26px; }
QScrollBar::handle:hover { background:#66c0f4; }
QScrollBar::add-line, QScrollBar::sub-line { width:0; height:0; }
QSplitter::handle { background:#2a475e; }
QListWidget { background:#111821; border:1px solid #2a475e; border-radius:4px; }
QListWidget::item:selected { background:#66c0f4; color:#0e1621; } QListWidget::item:hover { background:#2a475e; }
QLabel#h { color:#66c0f4; font-weight:800; padding-top:4px; }
QMenu { background:#1b2838; border:1px solid #3d6c8d; padding:4px; } QMenu::item { padding:5px 20px; border-radius:3px; } QMenu::item:selected { background:#2a475e; }
QToolTip { background:#1b2838; color:#e5eef5; border:1px solid #66c0f4; }
"""

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
    "Terminal": r"""t=${TERM_PROGRAM:-}; [ -z "$t" ] && [ -n "$KONSOLE_VERSION" ] && t=Konsole
[ -z "$t" ] && [ -n "$KITTY_WINDOW_ID" ] && t=kitty
[ -z "$t" ] && [ -n "$ALACRITTY_SOCKET" ] && t=Alacritty
if [ -z "$t" ]; then p=$$; for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
  p=$(ps -o ppid= -p "$p" 2>/dev/null | tr -d ' '); { [ -z "$p" ] || [ "$p" -le 1 ]; } && break
  case "$(cat /proc/$p/comm 2>/dev/null)" in
    konsole) t=Konsole;; gnome-terminal*) t="GNOME Terminal";; kgx) t="GNOME Console";; xfce4-terminal) t="Xfce Terminal";;
    mate-terminal) t="MATE Terminal";; qterminal) t=QTerminal;; lxterminal) t=LXTerminal;; tilix) t=Tilix;;
    deepin-terminal) t="Deepin Terminal";; cosmic-term) t="COSMIC Terminal";; io.elementary.t*|pantheon-term*) t="Pantheon Terminal";;
    alacritty) t=Alacritty;; kitty) t=kitty;; wezterm*) t=WezTerm;; foot) t=foot;; xterm) t=xterm;; urxvt*) t=urxvt;;
    terminator) t=Terminator;; guake) t=Guake;; yakuake) t=Yakuake;; ptyxis) t=Ptyxis;; ghostty) t=Ghostty;; terminology) t=Terminology;;
  esac; [ -n "$t" ] && break; done; fi
echo "${t:-$TERM}" """,
    "CPU": r"""awk -F: '/model name/{gsub(/^ +/,"",$2);print $2;exit}' /proc/cpuinfo""",
    "GPU": r"""lspci 2>/dev/null | grep -iE 'vga|3d' | head -1 | cut -d: -f3 | sed 's/^ *//'""",
    "Memory": r"""free -m | awk '/Mem:/{printf "%dMiB / %dMiB", $3, $2}'""",
    "Disk": r"""df -h / | awk 'NR==2{print $3" / "$2" ("$5")"}'""",
    "Resolution": r"""xrandr 2>/dev/null | awk '/\*/{print $1; exit}'""",
    "Locale": 'echo "${LANG:-n/a}"',
    "Swap": r"""free -m | awk '/Swap:/{printf "%dMiB / %dMiB", $3, $2}'""",
    "Load": "cut -d' ' -f1-3 /proc/loadavg",
    "Battery": r"""r=n/a; for b in /sys/class/power_supply/BAT*; do [ -r "$b/capacity" ] && { r="$(cat "$b/capacity")% $(cat "$b/status")"; break; }; done; echo "$r" """,
    "LocalIP": r"""x=$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++)if($i=="src"){print $(i+1);exit}}'); echo "${x:-$(hostname -I 2>/dev/null | awk '{print $1}')}" """,
    "PCT_Memory": r"""free | awk '/Mem:/{printf "%d",$3*100/$2}'""",
    "PCT_Disk": r"""df / | awk 'NR==2{gsub("%","",$5);print $5}'""",
    "PCT_CPU": r"""awk -v n="$(nproc)" '{p=$1*100/n; if(p>100)p=100; printf "%d",p}' /proc/loadavg""",
    "PCT_Swap": r"""free | awk '/Swap:/{if($2>0)printf "%d",$3*100/$2; else print 0}'""",
    "PCT_Battery": r"""for b in /sys/class/power_supply/BAT*; do [ -r "$b/capacity" ] && { cat "$b/capacity"; break; }; done"""}

# ------------------------------------------------------------------ system helpers
def clean_env():
    e = dict(os.environ)
    if "LD_LIBRARY_PATH_ORIG" in e: e["LD_LIBRARY_PATH"] = e.pop("LD_LIBRARY_PATH_ORIG")
    else: e.pop("LD_LIBRARY_PATH", None)
    return e

CACHE, PENDING, STATE = {}, set(), {"dirty": False}
PREVIEW = {"terminal": None}
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
        i = uuid.uuid4().hex[:8]; params = {p.key: copy.deepcopy(p.default) for p in SPEC[t][2]}; params.update(over)
        if t == "clogo" and params.get("data") is None: params["data"] = new_logo()
        s.nodes[i] = dict(id=i, type=t, x=x, y=y, params=params, group=None); return i
    def dump(s): return dict(version=1, name=s.name, nodes=list(s.nodes.values()), edges=s.edges,
                             groups=s.groups, meta=s.meta)
    @staticmethod
    def load(d, name):
        g = Graph(name); g.nodes = {n["id"]: n for n in d["nodes"]}
        g.edges = [tuple(e) for e in d["edges"]]; g.groups = d.get("groups", {}); g.meta.update(d.get("meta", {}))
        for n in g.nodes.values():
            if n["type"] == "output" and not g.meta.get("anim_v2"):
                if n["params"].get("loops") == 2 and n["params"].get("fps") == 8: n["params"]["loops"], n["params"]["fps"] = 1, 12
                g.meta["anim_v2"] = True
            for pr in SPEC[n["type"]][2]: n["params"].setdefault(pr.key, copy.deepcopy(pr.default))
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

def image_frames(path, w, bg="#1e1e1e"):
    key = (str(path), path.stat().st_mtime, w, bg)
    if key in IMGCACHE: return IMGCACHE[key]
    imgs = []; mv = QMovie(str(path))
    if mv.isValid() and mv.frameCount() > 1:
        first = mv.currentImage(); mv.jumpToFrame(0); first = mv.currentImage()
        cells = max(1, w * round(first.height() * w / max(1, first.width())) // 2)
        for i in range(min(mv.frameCount(), max(2, min(24, 1_500_000 // (45 * cells))))): mv.jumpToFrame(i); imgs.append(mv.currentImage())
    else: imgs = [QImage(str(path))]
    IMGCACHE[key] = [img2rows(i, w, bg) for i in imgs if not i.isNull() and i.width() > 0] or [[[R("(unreadable image)")]]]
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
            if path and path.exists() and path.suffix.lower() in IMG: return image_frames(path, int(p["width"]), O["bg"]), 0
            lines = path.read_text(errors="replace").splitlines() if path and path.exists() else ["(no file)"]
        else: lines = LOGOS.get(src, LOGOS["tux"])
        g_ = p["gradient"]; mode = "gradient" if g_ != "none" else "solid"; cells = None; direction = g_
        stops = [p["color"], p["color2"], p["color3"]] if g_ != "none" else [p["color"]]
        anim = O["animation"] if p["animation"] == "inherit" else p["animation"]
    if classic: anim = "none"; mode = "cells" if mode == "cells" else "solid"
    return render_logo(lines or [" "], cells, mode, stops, direction, anim)

def compile_graph(g):
    out = next((n for n in g.nodes.values() if n["type"] == "output"), None)
    if not out: return None
    classic = bool(g.meta.get("classic")); O = dict(out["params"])
    if classic:
        O["animation"] = "none"; O["lifetime"] = "intro"
        if O["preset"] == "advanced": O["preset"] = "classic"
    adv = O["preset"] == "advanced"; sep = O["separator"] if O["preset"] == "custom" else ": "
    rows, funcs, bars, logo = [], {}, {}, None
    for n in sorted((g.nodes[a] for a, b in g.edges if b == out["id"] and a in g.nodes), key=lambda n: (n["y"], n["x"])):
        p, t = n["params"], n["type"]
        if t in FANCY_NODES and classic: continue
        if t in ("logo", "clogo"): logo = logo or n
        elif t == "title":
            funcs["Title"] = SH["Title"]; rows.append([R("{{Title}}", p["color"], None, True)])
            if p["underline"]:
                funcs["TitleU"] = 'u=$(%s); printf -v s "%%*s" "${#u}" ""; echo "${s// /%s}"' % (SH["Title"], "─" if adv else "-")
                rows.append([R("{{TitleU}}", O["fg"])])
        elif t == "info":
            f = p["field"]
            if f == "Custom": key = "c%d" % abs(hash(p["command"])); funcs[key] = p["command"]
            else: key = f; funcs[key] = SH[f]
            rows.append(([R("◆ ", p["key_color"])] if adv else []) +
                        [R(p["label"] or f, p["key_color"], None, True), R(sep, O["fg"]), R("{{%s}}" % key, p["val_color"])])
        elif t == "bar":
            key = METRICS[p["metric"]]; funcs[key] = SH[key]; fc, ec = BARCH[p["style"]]; w = int(p["width"]); bn = "BAR%d" % len(bars)
            bars[bn] = dict(key=key, w=w, fill=fc, empty=ec, ec=p["empty"],
                            colors=[grad([p["c1"], p["c2"], p["c3"]], i / max(1, w - 1)) for i in range(w)])
            rows.append([R(p["label"] or p["metric"], p["key_color"], None, True), R(sep, O["fg"]),
                         R("{{%s}}" % bn), R(" {{%s}}%%" % key, O["fg"])])
        elif t == "divider":
            w = int(p["width"]); s_ = ((p["char"] or "─")[0]) * w; lab = p["label"]
            if lab: lab = " " + lab[: w - 4] + " "; i0 = (w - len(lab)) // 2; s_ = s_[:i0] + lab + s_[i0 + len(lab):]
            rows.append(merge([R(c, grad([p["color"], p["color2"]], i / max(1, w - 1)) if p["gradient"] else p["color"]) for i, c in enumerate(s_)]))
        elif t == "colors":
            rows.append([])
            for r in range(int(p["rows"])): rows.append([R("   ", None, "a%d" % (i + 8 * r)) for i in range(8)])
        elif t == "text": rows.append([R(p["text"], p["color"])])
    frames, final = logo_frames(g, logo, O, classic) if logo else ([[]], 0)
    return dict(O=O, frames=frames, final=final, rows=rows, funcs=funcs, bars=bars, classic=classic)

TOK = re.compile(r"\{\{(\w+)\}\}")
def resolve(runs, c):
    out = []
    for t, fg, bg, b in runs:
        pos = 0
        for m in TOK.finditer(t):
            if m.start() > pos: out.append((t[pos:m.start()], fg, bg, b))
            k = m[1]
            if k in c["bars"]:
                br = c["bars"][k]; v = value(br["key"], c["funcs"][br["key"]]); n = (int(v) if v.isdigit() else 0) * br["w"] // 100
                out += [R(br["fill"], br["colors"][i]) if i < n else R(br["empty"], br["ec"]) for i in range(br["w"])]
            elif k == "Terminal" and PREVIEW["terminal"]: out.append((PREVIEW["terminal"], fg, bg, b))
            else: out.append((value(k, c["funcs"][k]), fg, bg, b))
            pos = m.end()
        if pos < len(t): out.append((t[pos:], fg, bg, b))
    return merge(out)

def compose(c, fi):
    fr = c["frames"][fi % len(c["frames"])]
    lw = max((rlen(r) for f in c["frames"] for r in f), default=0); gap = int(c["O"]["gap"])
    res = []
    for i in range(max(len(fr), len(c["rows"]))):
        left = list(fr[i]) if i < len(fr) else []
        row = left + [R(" " * (lw - rlen(left) + gap))]
        if i < len(c["rows"]): row += resolve(c["rows"][i], c)
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
def info_expr(row, bars):
    parts = []
    for t, fg, bg, b in row:
        st = sgr(fg, bg, b)
        if st: parts.append("$'%s'" % st)
        pos = 0
        for m in TOK.finditer(t):
            if m.start() > pos: parts.append("$'%s'" % esc(t[pos:m.start()]))
            k = m[1]
            if k in bars:
                br = bars[k]
                parts.append('"$(bar "$(f_%s)" %d $\'%s\' $\'%s\' $\'%s\' BARC_%s)"' % (
                    br["key"], br["w"], esc(br["fill"]), esc(br["empty"]), sgr(br["ec"], None, False), k))
            else: parts.append('"$(f_%s)"' % k)
            pos = m.end()
        if pos < len(t): parts.append("$'%s'" % esc(t[pos:]))
        if st: parts.append("$'\\033[0m'")
    return "".join(parts)

BAR_FN = r"""bar(){ local p=${1:-0} w=$2 fc=$3 ec=$4 col=$5; local -n C=$6; local n i s=""
  [[ $p =~ ^[0-9]+$ ]] || p=0; n=$((p*w/100))
  for ((i=0;i<w;i++)); do if ((i<n)); then s+="${C[i]}$fc"; else s+="$col$ec"; fi; done
  printf '%s\033[0m' "$s"; }"""

TAIL = r"""NF=__NF__; NI=__NI__; FIN=__FIN__; MODE=__MODE__
H=${#INFO[@]}; ((${#FR0[@]}>H)) && H=${#FR0[@]}
render(){ local -n F=$1; local i; for ((i=0;i<H;i++)); do printf '%s%s\033[0m\n' "${F[i]-$PAD}" "${INFO[i]-}"; done; }
draw(){ local -n F=$1; local i o=$'\033'7
  for ((i=0;i<${#F[@]};i++)); do o+=$'\033['$((top+i))';1H'"${F[i]}"$'\033[0m'; done
  o+=$'\033'8; printf '%s' "$o"; }
live(){   # keeps animating in place until the first command runs (scrolling would corrupt it)
  render FR$FIN
  [ -r /dev/tty ] || return
  local row _e _c; printf '\033[6n' >/dev/tty
  IFS='[;' read -rs -d R -t 1 _e row _c </dev/tty || return
  top=$((row - H)); sp=$PPID; ((top>=1)) || return
  (
    idle(){ local s; s=$(</proc/$sp/stat) 2>/dev/null || return 1; s=${s##*) }; set -- $s; [ "$3" = "$6" ]; }
    for _i in $(seq 20); do idle && break; sleep 0.1; done
    k=0
    while kill -0 "$sp" 2>/dev/null && idle; do draw FR$((k % NF)) || break; k=$((k+1)); sleep __DELAY__; done
  ) >/dev/tty 2>/dev/null &
  disown 2>/dev/null
}
if ((NF>1)) && [ -t 1 ]; then
  if [ "$MODE" = live ]; then live
  else
    printf '\033[?25l'; trap 'printf "\033[?25h"' EXIT
    for ((k=0;k<NI*__LOOPS__;k++)); do render FR$((k % NI)); sleep __DELAY__; printf '\033[%dA' "$H"; done
    printf '\033[?25h'; render FR$FIN
  fi
else render FR$FIN; fi"""

def gen_script(c):
    O = c["O"]; frames = c["frames"]
    L = ["#!/usr/bin/env bash", "# Generated by Fetch Studio. Standalone - the app does not need to be running.",
         ". /etc/os-release 2>/dev/null", BAR_FN]
    for k, sn in c["funcs"].items(): L.append("f_%s(){\n%s\n}" % (k, sn))
    for bn, b in c["bars"].items(): L.append("BARC_%s=(%s)" % (bn, " ".join("$'%s'" % sgr(col, None, False) for col in b["colors"])))
    L.append("INFO=()")
    for row in c["rows"]: L.append("INFO+=(%s)" % (info_expr(row, c["bars"]) or '""'))
    lw = max((rlen(r) for f in frames for r in f), default=0); gap = int(O["gap"])
    for i, fr in enumerate(frames):
        L.append("FR%d=(" % i)
        for row in fr: L.append("  " + "".join("$'%s'" % lit(r) for r in row) + "$'%s'" % (" " * (lw - rlen(row) + gap)))
        L.append(")")
    L.append("PAD=$'%s'" % (" " * (lw + gap)))
    L.append(TAIL.replace("__NF__", str(len(frames))).replace("__FIN__", str(c["final"])).replace("__NI__", str(len(frames) - 8 if c["final"] else len(frames))).replace("__MODE__", O["lifetime"])
             .replace("__LOOPS__", str(int(O["loops"]))).replace("__DELAY__", "%.3f" % (1 / max(1, int(O["fps"])))))
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
        maxc = max((rlen(r) for r in s.rows), default=0); nrows = len(s.rows) + 1
        sc = min(1.0, (s.width() - 20) / max(1.0, maxc * cw), (s.height() - bar - 16) / max(1.0, nrows * ch))
        p.translate(10, bar + 8); p.scale(sc, sc); x0, y0 = 0, 0; x = y = 0
        for y, row in enumerate(list(s.rows) + [prompt]):
            x = x0; ty = y0 + y * ch
            for t, fg, bg, b in row:
                col = s.col(fg or s.fg); f.setBold(b); p.setFont(f)
                for c in t:
                    ix, iy = round(x), round(ty); iw, ih = round(x + cw) - ix, round(ty + ch) - iy; hm = round(ty + ch / 2) - iy
                    if bg: p.fillRect(QRect(ix, iy, iw, ih), s.col(bg))
                    if c == "▀": p.fillRect(QRect(ix, iy, iw, hm), col)
                    elif c == "▄": p.fillRect(QRect(ix, iy + hm, iw, ih - hm), col)
                    elif c == "█": p.fillRect(QRect(ix, iy, iw, ih), col)
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
             "colors": f'{p.get("rows")} row(s)', "clogo": (p.get("data") or {}).get("name"),
             "bar": p.get("metric"), "divider": p.get("label") or "divider"}.get(t, "")
        return str(v)[:24]
    def paint(s, p, o, w):
        title, col, _ = SPEC[s.d["type"]]; p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#233446")); p.setPen(QPen(QColor("#66c0f4") if s.isSelected() else QColor("#3d5a73"), 2))
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
        p.fillRect(r, QColor("#0f131a")); p.setPen(QPen(QColor("#171d27"), 1)); st = 40
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
    def add_node(s, t, pos, **over):
        i = s.g.add(t, pos.x(), pos.y(), **over); n = NodeItem(s.g.nodes[i]); s.addItem(n); s.nitems[i] = n
        s.clearSelection(); n.setSelected(True); s.win.touch(); return i
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
            if isinstance(i, NodeItem) and i.d["type"] == "clogo": s.win.edit_in_designer(i.d); return
        for i in s.items(e.position().toPoint()):
            if isinstance(i, GroupItem): s.scene().toggle_group(i.gid); return
        super().mouseDoubleClickEvent(e)
    def contextMenuEvent(s, e):
        sc = s.scene(); items = s.items(e.pos()); sp = s.mapToScene(e.pos()); m = QMenu(s)
        for i in items:
            if isinstance(i, NodeItem) and not i.isSelected(): sc.clearSelection(); i.setSelected(True); break
        add = m.addMenu("Add node")
        for t, (title, _, _) in SPEC.items():
            if t == "output" or (t in FANCY_NODES and s.win.classic): continue
            add.addAction(title, lambda _=False, t=t: sc.add_node(t, sp))
        lib = add.addMenu("Library (.fsnode)")
        for pth in lib_list(): lib.addAction(pth.stem, lambda _=False, pth=pth: sc.win.add_library_node(pth))
        lib.addSeparator(); lib.addAction("Import .fsnode…", sc.win.import_node_file)
        m.addAction("Group selected nodes", sc.group_selected)
        nd = next((i for i in items if isinstance(i, NodeItem) and i.d["type"] == "clogo"), None)
        if nd: m.addAction("Edit in ASCII Designer", lambda _=False, d=nd.d: sc.win.edit_in_designer(d))
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
    def later_refresh(s): QTimer.singleShot(0, lambda: s.show_node(s.d if s.d and s.d["id"] in s.win.g.nodes else None))
    def show_node(s, d):
        s.d = d; w = QWidget(); f = QFormLayout(w)
        if not d: f.addRow(QLabel("Select a node to edit its properties.")); s.setWidget(w); return
        f.addRow(hdr(SPEC[d["type"]][0]))
        for par in SPEC[d["type"]][2]:
            if par.kind == "hidden" or (s.win.classic and par.fancy): continue
            key, v = par.key, d["params"][par.key]
            if par.kind == "combo":
                x = QComboBox(); x.addItems(par.opts); x.setCurrentText(str(v)); x.currentTextChanged.connect(lambda t, k=key: s.set(k, t))
            elif par.kind == "int":
                x = QSpinBox(); x.setRange(*par.opts); x.setValue(int(v)); x.valueChanged.connect(lambda t, k=key: s.set(k, t))
            elif par.kind == "check":
                x = QCheckBox(); x.setChecked(bool(v)); x.toggled.connect(lambda t, k=key: s.set(k, t))
            elif par.kind == "text":
                x = QLineEdit(str(v)); x.textChanged.connect(lambda t, k=key: s.set(k, t))
            elif par.kind == "color":
                x = QPushButton(v); s.paint_btn(x, v); x.clicked.connect(lambda _, k=key, b=x: s.pick_color(k, b))
            elif par.kind == "action":
                b = QPushButton(par.label); b.clicked.connect(lambda _, a=par.default: s.win.edit_in_designer(s.d) if a == "edit" else s.win.export_node(s.d))
                f.addRow(b); continue
            else:
                x = QPushButton(v or "Choose file…"); x.clicked.connect(lambda _: s.pick_file())
            f.addRow(par.label, x)
        s.setWidget(w)
    def paint_btn(s, b, c):
        q = QColor(c); b.setStyleSheet("background:%s;color:%s" % (c, "#000" if q.lightness() > 128 else "#fff"))
    def set(s, k, v):
        s.d["params"][k] = v
        if k == "theme" and v != "none": s.win.apply_theme(v); s.later_refresh()
        s.win.node_changed(s.d)
    def pick_color(s, k, b):
        c = QColorDialog.getColor(QColor(s.d["params"][k]), s)
        if c.isValid(): b.setText(c.name()); s.paint_btn(b, c.name()); s.set(k, c.name())
    def pick_file(s):
        fn, _ = QFileDialog.getOpenFileName(s, "Logo image, GIF or text file", "", "Images/Text (*.png *.jpg *.jpeg *.gif *.webp *.bmp *.txt);;All (*)")
        if fn: s.d["params"]["file"] = s.win.import_asset(fn); s.d["params"]["source"] = "file"; s.win.node_changed(s.d); s.later_refresh()

# ------------------------------------------------------------------ custom logo nodes (.fsnode "plugins")
HEXRE = re.compile(r"^#[0-9a-fA-F]{6}$")
LIB = DATA / "nodes"
def new_logo(name="My Logo", lines=None):
    lines = lines or [r"  /\_/\  ", " ( o.o ) ", "  > ^ <  "]
    w = max(len(l) for l in lines)
    return dict(name=name, author="", w=w, h=len(lines), rows=[l.ljust(w) for l in lines], cells=None, mode="solid",
                stops=["#3daee9", "#bb9af7", "#f7768e"], direction="horizontal", anim="none")

def sanitize_logo(d):
    """Plugin files are pure data and are validated; they can never contain code."""
    w, h = int(d["w"]), int(d["h"])
    if not (1 <= w <= 160 and 1 <= h <= 80): raise ValueError("logo size out of range")
    rows = [str(r)[:w].ljust(w) for r in list(d["rows"])[:h]]; rows += [" " * w] * (h - len(rows))
    rows = ["".join(ch if ch.isprintable() else " " for ch in r) for r in rows]
    cells = None
    if d.get("cells"):
        cl = [list(r) for r in list(d["cells"])[:h]]; cl += [[] for _ in range(h - len(cl))]
        cells = [[(c if isinstance(c, str) and HEXRE.match(c) else "") for c in (r + [""] * w)[:w]] for r in cl]
    stops = [c for c in d.get("stops", []) if isinstance(c, str) and HEXRE.match(c)][:3] or ["#3daee9"]
    pick = lambda v, ok, df: v if v in ok else df
    return dict(name=str(d.get("name", "Logo"))[:40], author=str(d.get("author", ""))[:40], w=w, h=h, rows=rows, cells=cells,
                mode=pick(d.get("mode"), ("solid", "gradient", "cells"), "solid"), stops=stops,
                direction=pick(d.get("direction"), GRADS[1:], "horizontal"), anim=pick(d.get("anim"), ANIMS, "none"))

def write_fsnode(logo, path):
    Path(path).write_text(json.dumps(dict(format="fetchstudio-node", version=1, kind="logo", name=logo["name"],
                                          author=logo["author"], data=logo), indent=1))
def lib_save(logo):
    LIB.mkdir(parents=True, exist_ok=True); p = LIB / (clean_name(logo["name"]) + ".fsnode"); write_fsnode(logo, p); return p
def lib_list(): return sorted(LIB.glob("*.fsnode")) if LIB.exists() else []
def lib_read(path):
    d = json.loads(Path(path).read_text())
    if d.get("format") != "fetchstudio-node" or d.get("kind") != "logo": raise ValueError("not a Fetch Studio logo node")
    return sanitize_logo(d["data"])

# ------------------------------------------------------------------ ASCII designer
GLYPHS = {
    "ASCII": [chr(c) for c in range(33, 127)],
    "Box drawing": [chr(c) for c in range(0x2500, 0x2580)],
    "Blocks & shades": [chr(c) for c in range(0x2580, 0x25A0)],
    "Geometric": [chr(c) for c in range(0x25A0, 0x2600)],
    "Arrows": [chr(c) for c in range(0x2190, 0x2200)],
    "Symbols": [chr(c) for c in range(0x2600, 0x2640)] + [chr(c) for c in range(0x2700, 0x2740)],
    "Braille": [chr(c) for c in range(0x2800, 0x2900)],
    "Math & misc": list("±×÷∞≈≠≤≥∑√∂∆∫°•·…§¶©®™€£¥¢µπΩαβγδλΣ∴∵⊕⊗⌘⌥⏎⎈"),
}
STARTERS = {
    "Cat": [r" /\_/\  ", r"( o.o ) ", r" > ^ <  "],
    "Tux": LOGOS["tux"], "Arch-style": LOGOS["arch"],
    "Heart": ["  _   _  ", r" / \_/ \ ", r" \     / ", r"  \   /  ", r"   \ /   ", "    v    "],
    "Rocket": ["    ^    ", r"   / \   ", "  |   |  ", "  | O |  ", r" /|   |\ ", r"/_|___|_\ ", r"   /_\   "],
    "Computer": [" .----------. ", " | > _      | ", " |          | ", " '----------' ", "   _|____|_   ", r"  /________\  "],
    "Mug": ["   ( (    ", "    ) )   ", "  ........ ", "  |      |]", r"  \      / ", "   `----'  "],
    "Mountains": ["      /\\        ", r"     /  \    /\  ", r"    /    \  /  \ ", r" /\/  /\  \/    \ ", r"/  \_/  \__/\____\ "],
    "Blank 24x10": [" " * 24] * 10}

class GlyphList(QListWidget):
    def __init__(s):
        super().__init__(); s.setViewMode(QListWidget.ViewMode.IconMode); s.setResizeMode(QListWidget.ResizeMode.Adjust)
        s.setGridSize(QSize(34, 34)); s.setMovement(QListWidget.Movement.Static); s.setDragEnabled(True)
        s.setDragDropMode(QListWidget.DragDropMode.DragOnly); s.setFont(QFont("Monospace", 14)); s.setUniformItemSizes(True)
    def mimeData(s, items): m = QMimeData(); m.setText(items[0].text()); return m

class DesignCanvas(QWidget):
    changed = pyqtSignal(); dropped = pyqtSignal(); picked = pyqtSignal(str)
    M = 10
    def __init__(s):
        super().__init__(); s.setAcceptDrops(True); s.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        s.tool, s.glyph, s.color = "draw", "#", "#3daee9"; s.mode, s.stops, s.direction = "solid", ["#3daee9"], "horizontal"
        s.sel = s.lift = s.start = None; s.off = (0, 0); s.cur = (0, 0); s.undo, s.redo = [], []; s.drops = 0
        s.font = QFont("Monospace", 14); s.font.setStyleHint(QFont.StyleHint.Monospace); fm = QFontMetricsF(s.font)
        s.cw, s.chh, s.asc = fm.horizontalAdvance("M"), float(round(fm.height())), fm.ascent(); s.set_grid(new_logo())
    W = property(lambda s: len(s.rows[0]) if s.rows else 0)
    H = property(lambda s: len(s.rows))
    def set_grid(s, d):
        s.rows = [list(r) for r in d["rows"]]
        s.cols = [list(r) for r in d["cells"]] if d.get("cells") else [[""] * d["w"] for _ in s.rows]
        s.sel = s.lift = None; s.undo.clear(); s.redo.clear(); s.fit()
    def fit(s): s.setMinimumSize(int(s.W * s.cw + 2 * s.M), int(s.H * s.chh + 2 * s.M)); s.update()
    def state(s): return ([r[:] for r in s.rows], [r[:] for r in s.cols])
    def snap(s): s.undo = (s.undo + [s.state()])[-100:]; s.redo.clear()
    def restore(s, st): s.rows, s.cols = [r[:] for r in st[0]], [r[:] for r in st[1]]; s.fit(); s.changed.emit()
    def do_undo(s):
        if s.undo: s.redo.append(s.state()); s.restore(s.undo.pop())
    def do_redo(s):
        if s.redo: s.undo.append(s.state()); s.restore(s.redo.pop())
    def resize_grid(s, w, h):
        s.snap(); s.rows = [(r + [" "] * w)[:w] for r in s.rows[:h]] + [[" "] * w for _ in range(h - len(s.rows))]
        s.cols = [(r + [""] * w)[:w] for r in s.cols[:h]] + [[""] * w for _ in range(h - len(s.cols))]; s.fit(); s.changed.emit()
    def cell(s, pos, clamp=False):
        x, y = int((pos.x() - s.M) // s.cw), int((pos.y() - s.M) // s.chh)
        if clamp: return (min(max(x, 0), s.W - 1), min(max(y, 0), s.H - 1))
        return (x, y) if 0 <= x < s.W and 0 <= y < s.H else None
    def col(s, x, y):
        if s.mode == "cells" and s.cols[y][x]: return s.cols[y][x]
        if s.mode == "gradient": return grad(s.stops, posf(x, y, s.W, s.H, s.direction if s.direction != "none" else "horizontal"))
        return s.stops[0] if s.stops else "#dddddd"
    def put(s, x, y, ch=None, col=None):
        if ch is not None: s.rows[y][x] = ch
        if col is not None: s.cols[y][x] = col
    def apply(s, x, y):
        if s.tool == "draw": s.put(x, y, s.glyph, s.color if s.mode == "cells" else None)
        elif s.tool == "erase": s.put(x, y, " ", "")
        elif s.tool == "paint": s.put(x, y, None, s.color)
        s.changed.emit()
    def lift_sel(s):
        r = s.sel; xs, ys = range(r.left(), r.right() + 1), range(r.top(), r.bottom() + 1)
        s.lift = ([[s.rows[y][x] for x in xs] for y in ys], [[s.cols[y][x] for x in xs] for y in ys])
        for y in ys:
            for x in xs: s.rows[y][x] = " "; s.cols[y][x] = ""
    def mousePressEvent(s, e):
        s.setFocus(); c = s.cell(e.position(), clamp=s.tool == "select")
        if not c or e.button() != Qt.MouseButton.LeftButton: return
        s.cur = c; x, y = c
        if s.tool == "select":
            if s.sel and s.sel.contains(x, y): s.snap(); s.lift_sel(); s.start = c; s.off = (0, 0)
            else: s.sel = QRect(x, y, 1, 1); s.start = c; s.lift = None
        elif s.tool == "pick":
            s.glyph = s.rows[y][x]; s.color = s.cols[y][x] or s.color; s.picked.emit(s.glyph)
        else: s.snap(); s.apply(x, y)
        s.update()
    def mouseMoveEvent(s, e):
        if not (e.buttons() & Qt.MouseButton.LeftButton): return
        c = s.cell(e.position(), clamp=s.tool == "select")
        if not c: return
        if s.tool == "select" and s.start:
            if s.lift: s.off = (c[0] - s.start[0], c[1] - s.start[1])
            else: s.sel = QRect(min(c[0], s.start[0]), min(c[1], s.start[1]), abs(c[0] - s.start[0]) + 1, abs(c[1] - s.start[1]) + 1)
        elif s.tool in ("draw", "erase", "paint"): s.cur = c; s.apply(*c)
        s.update()
    def mouseReleaseEvent(s, e):
        if s.lift:
            r = s.sel; ox, oy = s.off
            for dy, (rr, cc) in enumerate(zip(*s.lift)):
                for dx, (ch, co) in enumerate(zip(rr, cc)):
                    tx, ty = r.left() + dx + ox, r.top() + dy + oy
                    if ch != " " and 0 <= tx < s.W and 0 <= ty < s.H: s.rows[ty][tx] = ch; s.cols[ty][tx] = co
            s.sel = r.translated(ox, oy); s.lift = None; s.off = (0, 0); s.changed.emit()
        s.start = None; s.update()
    def dragEnterEvent(s, e):
        if e.mimeData().hasText(): e.acceptProposedAction()
    dragMoveEvent = dragEnterEvent
    def dropEvent(s, e):
        c = s.cell(e.position())
        if c and e.mimeData().text():
            s.snap(); s.put(c[0], c[1], e.mimeData().text()[0], s.color if s.mode == "cells" else None)
            s.drops += 1; s.cur = c; s.dropped.emit(); s.changed.emit(); s.update(); e.acceptProposedAction()
    def keyPressEvent(s, e):
        k, m = e.key(), e.modifiers(); x, y = s.cur
        if m & Qt.KeyboardModifier.ControlModifier:
            if k == Qt.Key.Key_Z: s.do_undo()
            elif k == Qt.Key.Key_Y: s.do_redo()
            else: super().keyPressEvent(e)
            return
        arrows = {Qt.Key.Key_Left: (-1, 0), Qt.Key.Key_Right: (1, 0), Qt.Key.Key_Up: (0, -1), Qt.Key.Key_Down: (0, 1)}
        if k in arrows: s.cur = (min(max(x + arrows[k][0], 0), s.W - 1), min(max(y + arrows[k][1], 0), s.H - 1))
        elif k == Qt.Key.Key_Delete and s.sel:
            s.snap()
            for yy in range(s.sel.top(), s.sel.bottom() + 1):
                for xx in range(s.sel.left(), s.sel.right() + 1): s.rows[yy][xx] = " "; s.cols[yy][xx] = ""
            s.changed.emit()
        elif k == Qt.Key.Key_Backspace: s.snap(); x = max(0, x - 1); s.put(x, y, " ", ""); s.cur = (x, y); s.changed.emit()
        elif k in (Qt.Key.Key_Return, Qt.Key.Key_Enter): s.cur = (0, min(s.H - 1, y + 1))
        elif e.text() and e.text().isprintable():
            s.snap(); s.put(x, y, e.text()[0], s.color if s.mode == "cells" else None); s.cur = (min(s.W - 1, x + 1), y); s.changed.emit()
        else: super().keyPressEvent(e); return
        s.update()
    def glyph_at(s, p, x, y, ch, col):
        rx, ry = s.M + x * s.cw, s.M + y * s.chh; c = QColor(col)
        if ch == "█": p.fillRect(QRectF(rx, ry, s.cw, s.chh), c)
        elif ch == "▀": p.fillRect(QRectF(rx, ry, s.cw, s.chh / 2), c)
        elif ch == "▄": p.fillRect(QRectF(rx, ry + s.chh / 2, s.cw, s.chh / 2), c)
        else: p.setPen(c); p.drawText(QPointF(rx, ry + s.asc), ch)
    def paintEvent(s, e):
        p = QPainter(s); p.fillRect(s.rect(), QColor("#0e1218")); p.setFont(s.font); M = s.M
        p.fillRect(QRectF(M, M, s.W * s.cw, s.H * s.chh), QColor("#161c26")); p.setPen(QPen(QColor("#202a38"), 1))
        for x in range(s.W + 1): p.drawLine(int(M + x * s.cw), M, int(M + x * s.cw), int(M + s.H * s.chh))
        for y in range(s.H + 1): p.drawLine(M, int(M + y * s.chh), int(M + s.W * s.cw), int(M + y * s.chh))
        for y in range(s.H):
            for x in range(s.W):
                if s.rows[y][x] != " ": s.glyph_at(p, x, y, s.rows[y][x], s.col(x, y))
        r = s.sel
        if s.lift and r:
            for dy, row in enumerate(s.lift[0]):
                for dx, ch in enumerate(row):
                    tx, ty = r.left() + dx + s.off[0], r.top() + dy + s.off[1]
                    if ch != " " and 0 <= tx < s.W and 0 <= ty < s.H: s.glyph_at(p, tx, ty, ch, s.lift[1][dy][dx] or s.col(tx, ty))
        if r:
            r = r.translated(*s.off) if s.lift else r
            p.setPen(QPen(QColor("#66c0f4"), 2, Qt.PenStyle.DashLine)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(QRectF(M + r.left() * s.cw, M + r.top() * s.chh, r.width() * s.cw, r.height() * s.chh))
        if s.tool == "draw" and s.hasFocus():
            p.setPen(QPen(QColor("#ffd33d"), 1)); p.drawRect(QRectF(M + s.cur[0] * s.cw, M + s.cur[1] * s.chh, s.cw, s.chh))
    def to_logo(s):
        has = any(c for r in s.cols for c in r)
        return dict(w=s.W, h=s.H, rows=["".join(r) for r in s.rows], cells=[r[:] for r in s.cols] if has else None)

def hdr(t): l = QLabel(t); l.setObjectName("h"); return l

class AsciiDesigner(QWidget):
    def __init__(s, win):
        super().__init__(); s.w = win; s.editing = None; s.frames, s.final, s.fi = [[]], 0, 0
        s.recent = list("#@*/\\|_-█░▒▓▀▄"); s.stops = ["#3daee9", "#bb9af7", "#f7768e"]
        s.canvas = DesignCanvas(); s.pal = GlyphList(); s.term = TermView(); s.term.setMinimumSize(300, 230)
        # --- left: symbol palette
        left = QWidget(); lv = QVBoxLayout(left); lv.addWidget(hdr("Symbols — click to pick, drag onto canvas"))
        s.cat = QComboBox(); s.cat.addItems(["Recent"] + list(GLYPHS)); s.cat.currentTextChanged.connect(s.fill_pal)
        lv.addWidget(s.cat); lv.addWidget(s.pal, 1); s.brush = QLabel("Brush: #"); lv.addWidget(s.brush)
        s.pal.currentItemChanged.connect(lambda it, _: it and s.set_glyph(it.text()))
        # --- middle: tools + canvas
        mid = QWidget(); mv = QVBoxLayout(mid); tr = QHBoxLayout(); s.tools = QButtonGroup(s)
        for label, key, tip in (("✎ Draw", "draw", "Place the selected symbol. You can also just type on the keyboard."),
                                ("⌫ Erase", "erase", ""), ("◐ Paint", "paint", "Color cells (set color mode to 'cells')"),
                                ("⌖ Pick", "pick", "Pick up a symbol/color from the canvas"),
                                ("⬚ Select/Move", "select", "Drag a box, then drag inside it to rearrange. Delete clears it.")):
            b = QPushButton(label); b.setCheckable(True); b.setToolTip(tip); b.setChecked(key == "draw")
            b.clicked.connect(lambda _, k=key: setattr(s.canvas, "tool", k)); s.tools.addButton(b); tr.addWidget(b)
        s.tools.setExclusive(True)
        s.sp_w, s.sp_h = QSpinBox(), QSpinBox(); s.sp_w.setRange(4, 120); s.sp_h.setRange(2, 60)
        rb = QPushButton("Resize"); rb.clicked.connect(lambda: s.canvas.resize_grid(s.sp_w.value(), s.sp_h.value()))
        ub, rbk = QPushButton("↶"), QPushButton("↷"); ub.clicked.connect(s.canvas.do_undo); rbk.clicked.connect(s.canvas.do_redo)
        for x in (QLabel("  W"), s.sp_w, QLabel("H"), s.sp_h, rb, ub, rbk): tr.addWidget(x)
        tr.addStretch(); mv.addLayout(tr); sa = QScrollArea(); sa.setWidgetResizable(True); sa.setWidget(s.canvas); mv.addWidget(sa, 1)
        # --- right: style, starters, files, preview
        right = QWidget(); rv = QVBoxLayout(right); f = QFormLayout()
        s.ed_name, s.ed_author = QLineEdit("My Logo"), QLineEdit(); f.addRow("Node name", s.ed_name); f.addRow("Author", s.ed_author)
        s.cb_start = QComboBox(); s.cb_start.addItems(list(STARTERS)); sb = QPushButton("Load starter"); sb.clicked.connect(s.load_starter)
        row = QHBoxLayout(); row.addWidget(s.cb_start, 1); row.addWidget(sb); f.addRow("Starter art", row)
        s.cb_mode = QComboBox(); s.cb_mode.addItems(["solid", "gradient", "cells"]); s.cb_mode.setToolTip("cells = hand-painted per-cell colors")
        s.cb_dir = QComboBox(); s.cb_dir.addItems(GRADS[1:]); s.cb_anim = QComboBox(); s.cb_anim.addItems(ANIMS)
        s.cbtn = []; crow = QHBoxLayout()
        for i in range(3):
            b = QPushButton(); b.setFixedWidth(46); b.clicked.connect(lambda _, i=i: s.pick_stop(i)); s.cbtn.append(b); crow.addWidget(b)
        pb = QPushButton("Paint color"); pb.clicked.connect(s.pick_paint); crow.addWidget(pb)
        f.addRow("Color mode", s.cb_mode); f.addRow("Colors 1-3", crow); f.addRow("Gradient", s.cb_dir); f.addRow("Animation", s.cb_anim)
        for c in (s.cb_mode, s.cb_dir, s.cb_anim): c.currentTextChanged.connect(s.style_changed)
        rv.addWidget(hdr("Logo style")); rv.addLayout(f); rv.addWidget(hdr("Live preview (same renderer as the build)")); rv.addWidget(s.term, 1)
        s.lbl_edit = QLabel("New node"); rv.addWidget(s.lbl_edit)
        s.btn_save = QPushButton("★ Save as node (adds to graph)"); s.btn_save.clicked.connect(s.save_node); rv.addWidget(s.btn_save)
        fr = QHBoxLayout(); s.cb_lib = QComboBox(); lb = QPushButton("Load"); lb.clicked.connect(s.load_lib); fr.addWidget(s.cb_lib, 1); fr.addWidget(lb); rv.addLayout(fr)
        for label, fn in (("Export .fsnode…", s.export_fsnode), ("Import .fsnode…", s.import_fsnode),
                          ("Image → ASCII…", s.import_image), ("Import text art…", s.import_text)):
            b = QPushButton(label); b.clicked.connect(fn); rv.addWidget(b)
        sp = QSplitter(); sp.addWidget(left); sp.addWidget(mid); sp.addWidget(right); sp.setSizes([260, 640, 400])
        lay = QHBoxLayout(s); lay.setContentsMargins(0, 0, 0, 0); lay.addWidget(sp)
        s.dbt = QTimer(s); s.dbt.setSingleShot(True); s.dbt.setInterval(120); s.dbt.timeout.connect(s.restart_preview)
        s.canvas.changed.connect(s.dbt.start); s.canvas.picked.connect(s.set_glyph)
        s.timer = QTimer(s); s.timer.timeout.connect(s.tick); s.timer.start(110)
        s.cat.setCurrentText("ASCII"); s.fill_pal(); s.load_logo(new_logo()); s.refresh_lib()
    def hl(s, b, c):
        q = QColor(c); b.setStyleSheet("background:%s;color:%s" % (c, "#000" if q.lightness() > 128 else "#fff")); b.setText(" ")
    def fill_pal(s, *_):
        s.pal.clear(); cat = s.cat.currentText()
        for ch in (s.recent if cat == "Recent" else GLYPHS[cat]):
            if ch.isprintable():
                it = QListWidgetItem(ch); it.setTextAlignment(Qt.AlignmentFlag.AlignCenter); it.setToolTip("U+%04X" % ord(ch)); s.pal.addItem(it)
    def set_glyph(s, ch):
        s.canvas.glyph = ch; s.brush.setText("Brush: " + ch); s.recent = ([ch] + [c for c in s.recent if c != ch])[:40]
    def pick_stop(s, i):
        c = QColorDialog.getColor(QColor(s.stops[i]), s)
        if c.isValid(): s.stops[i] = c.name(); s.hl(s.cbtn[i], c.name()); s.style_changed()
    def pick_paint(s):
        c = QColorDialog.getColor(QColor(s.canvas.color), s)
        if c.isValid(): s.canvas.color = c.name()
    def style_changed(s, *_):
        c = s.canvas; c.mode, c.stops, c.direction = s.cb_mode.currentText(), list(s.stops), s.cb_dir.currentText(); c.update(); s.dbt.start()
    def refresh_classic(s):
        on = s.w.classic
        for c in (s.cb_dir, s.cb_anim): c.setEnabled(not on)
        s.restart_preview()
    def restart_preview(s):
        c = s.canvas; mode = s.cb_mode.currentText(); anim = "none" if s.w.classic else s.cb_anim.currentText()
        if s.w.classic and mode == "gradient": mode = "solid"
        s.frames, s.final = render_logo(["".join(r) for r in c.rows], c.cols if mode == "cells" else None, mode, s.stops, s.cb_dir.currentText(), anim)
        s.fi = 0
    def tick(s):
        if not s.isVisible(): return
        s.term.set(s.frames[s.fi % len(s.frames)], "#1e1e1e", "#d0d0d0", "Preview", 11); s.fi += 1
    def logo(s):
        d = s.canvas.to_logo(); d.update(name=s.ed_name.text().strip() or "My Logo", author=s.ed_author.text().strip(),
                                         mode=s.cb_mode.currentText(), stops=list(s.stops), direction=s.cb_dir.currentText(), anim=s.cb_anim.currentText())
        return d
    def load_logo(s, d, editing=None):
        d = sanitize_logo(d); s.canvas.set_grid(d); s.editing = editing; s.stops = (d["stops"] + ["#bb9af7", "#f7768e"])[:3]
        for wd, v in ((s.cb_mode, d["mode"]), (s.cb_dir, d["direction"]), (s.cb_anim, d["anim"])): wd.blockSignals(True); wd.setCurrentText(v); wd.blockSignals(False)
        for i in range(3): s.hl(s.cbtn[i], s.stops[i])
        s.ed_name.setText(d["name"]); s.ed_author.setText(d["author"]); s.sp_w.setValue(d["w"]); s.sp_h.setValue(d["h"])
        s.lbl_edit.setText("Editing an existing graph node" if editing else "New node"); s.style_changed(); s.refresh_classic()
    def load_starter(s):
        lines = STARTERS[s.cb_start.currentText()]; d = new_logo(s.ed_name.text() or "My Logo", lines)
        d.update(author=s.ed_author.text(), mode=s.cb_mode.currentText(), stops=list(s.stops), direction=s.cb_dir.currentText(), anim=s.cb_anim.currentText())
        s.canvas.snap(); keep = (s.canvas.undo, s.editing); s.load_logo(d, s.editing); s.canvas.undo = keep[0]
    def save_node(s):
        try: d = sanitize_logo(s.logo())
        except Exception as ex: QMessageBox.warning(s, APP, str(ex)); return
        s.editing = s.w.designer_save(d, s.editing); s.lbl_edit.setText("Editing an existing graph node"); s.refresh_lib()
    def refresh_lib(s): s.cb_lib.clear(); [s.cb_lib.addItem(p.stem, str(p)) for p in lib_list()]
    def load_lib(s):
        p = s.cb_lib.currentData()
        if p: s.try_load(lambda: lib_read(p))
    def try_load(s, fn):
        try: s.load_logo(fn())
        except Exception as ex: QMessageBox.warning(s, APP, "Could not load:\n%s" % ex)
    def export_fsnode(s):
        d = sanitize_logo(s.logo()); fn, _ = QFileDialog.getSaveFileName(s, "Export node", str(Path.home() / (clean_name(d["name"]) + ".fsnode")), "Fetch Studio node (*.fsnode)")
        if fn: write_fsnode(d, fn)
    def import_fsnode(s):
        fn, _ = QFileDialog.getOpenFileName(s, "Import node", str(Path.home()), "Fetch Studio node (*.fsnode)")
        if not fn: return
        try: d = lib_read(fn); lib_save(d); s.load_logo(d); s.refresh_lib()
        except Exception as ex: QMessageBox.warning(s, APP, "Could not import:\n%s" % ex)
    def import_text(s):
        fn, _ = QFileDialog.getOpenFileName(s, "Text art", str(Path.home()), "Text (*.txt *.asc *.nfo);;All (*)")
        if fn:
            lines = [l.rstrip("\n")[:160] for l in Path(fn).read_text(errors="replace").splitlines()[:80]] or [" "]
            s.try_load(lambda: dict(new_logo(Path(fn).stem, lines), stops=s.stops, mode=s.cb_mode.currentText(), anim=s.cb_anim.currentText()))
    def import_image(s):
        fn, _ = QFileDialog.getOpenFileName(s, "Image", str(Path.home()), "Images (*.png *.jpg *.jpeg *.gif *.webp *.bmp)")
        if not fn: return
        img = QImage(fn)
        if img.isNull(): return
        w = 48; h = max(1, round(img.height() * w / img.width() * 0.5)); sm = img.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation).convertToFormat(QImage.Format.Format_ARGB32)
        ramp = " .:-=+*#%@"; rows, cells = [], []
        for y in range(h):
            r, c = "", []
            for x in range(w):
                px = sm.pixelColor(x, y); on = px.alpha() > 60
                r += ramp[int(px.lightnessF() * (len(ramp) - 1))] if on else " "; c.append(px.name() if on else "")
            rows.append(r); cells.append(c)
        d = new_logo(Path(fn).stem, rows); d.update(cells=cells, mode="cells", stops=s.stops); s.try_load(lambda: d)

# ------------------------------------------------------------------ interactive lesson
class Lesson(QWidget):
    def __init__(s, win):
        super().__init__(win); s.w = win; s.active = False; s.i = 0
        s.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        s.panel = QFrame(win); s.panel.setStyleSheet("QFrame{background:#1b2838;border:2px solid #66c0f4;border-radius:8px}QLabel{border:0}")
        v = QVBoxLayout(s.panel); s.cnt = QLabel(); s.lbl = QLabel(); s.lbl.setWordWrap(True); v.addWidget(s.cnt); v.addWidget(s.lbl)
        r = QHBoxLayout(); s.back, s.nxt, s.quit = QPushButton("◂ Back"), QPushButton("Next ▸"), QPushButton("Save && exit lesson")
        for b in (s.back, s.nxt, s.quit): r.addWidget(b)
        v.addLayout(r); s.back.clicked.connect(lambda: s.go(-1)); s.nxt.clicked.connect(lambda: s.go(1)); s.quit.clicked.connect(s.stop)
        s.timer = QTimer(s); s.timer.timeout.connect(s.poll); s.hide(); s.panel.hide()
    def steps(s):   # (target widget, text, done?, tab to show: 0 graph / 1 designer / None leave as is)
        w = s.w; outp = lambda: next((n for n in w.g.nodes.values() if n["type"] == "output"), None); d = w.designer
        return [
            (lambda: w.view, "Welcome! This is the node graph. Drag with the LEFT mouse button on empty space to pan, or hold Ctrl and scroll to zoom. Try it now.", lambda: w.flags["panned"], 0),
            (lambda: w.view, "Right-click empty canvas ▸ Add node ▸ Title. Then right-click again and add an Info node.", lambda: w.has("title") and w.has("info"), 0),
            (lambda: w.props, "Click your Info node, then change 'Field' here to something other than OS (e.g. Kernel).", lambda: any(n["type"] == "info" and n["params"]["field"] != "OS" for n in w.g.nodes.values()), 0),
            (lambda: w.view, "Drag from a node's round right-hand port to the Output node's left-hand port to connect them. Connect both Title and Info.", lambda: w.linked("title") and w.linked("info"), 0),
            (lambda: w.term, "This is your live 1:1 terminal preview. Now add a Logo node and connect it to Output too.", lambda: w.linked("logo") or w.linked("clogo"), 0),
            (lambda: w.view, "Hold Shift and drag a box around two nodes, then right-click ▸ Group selected nodes.", lambda: bool(w.g.groups), 0),
            (lambda: w.view, "Right-click the group ▸ Collapse group (or double-click it).", lambda: any(g["collapsed"] for g in w.g.groups.values()), 0),
            (lambda: w.view, "Expand it again the same way.", lambda: bool(w.g.groups) and not any(g["collapsed"] for g in w.g.groups.values()), 0),
            (lambda: w.props, "Select the Output node and pick a Color theme (try 'dracula'). In Classic mode, effects are hidden — theme still works.", lambda: outp() and outp()["params"]["theme"] != "none", 0),
            (lambda: w.tabs.tabBar(), "Now the fun part: click the ASCII Designer tab to draw your own logo.", lambda: w.tabs.currentIndex() == 1, None),
            (lambda: d.pal, "Pick a symbol category, then DRAG a symbol from this palette onto the canvas. (You can also type on the keyboard.)", lambda: d.canvas.drops > 0, 1),
            (lambda: d.canvas, "Use ⬚ Select/Move to drag a box around part of your art and move it. Load 'starter art' to edit something ready-made. Continue when you are happy.", lambda: True, 1),
            (lambda: d.cb_anim, "Choose an animation (e.g. rainbow) and a gradient. In Classic mode these are disabled, so you can continue.", lambda: w.classic or d.cb_anim.currentText() != "none", 1),
            (lambda: d.btn_save, "Click 'Save as node'. It is added to your graph and connected to Output, and saved to your node library as a shareable .fsnode.", lambda: w.flags["design_saved"], 1),
            (lambda: w.bar("Save"), "Press Ctrl+S (or click Save) to save your project. It also auto-saves every 10 minutes.", lambda: w.flags["saved"] > 0, None),
            (lambda: w.bar("Export"), "Click Export to create a shareable fetchstudio(name).zip with your graph, custom logo and images.", lambda: w.flags["exported"], None),
            (lambda: w.bar("Build"), "Click Build. This installs a standalone script and shell hook, so new terminals show your fetch without this app.", lambda: w.flags["built"], None)]
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
        st = s.steps(); tab = st[s.i][3]
        if tab is not None and s.w.tabs.currentIndex() != tab: s.w.tabs.setCurrentIndex(tab)
        s.setGeometry(s.w.rect()); s.raise_(); s.panel.raise_()
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
        s.comp = None; s.fi = 0; s.flags = dict(saved=0, exported=False, built=False, panned=False, design_saved=False)
        s.scene = GraphScene(s); s.view = GraphView(s.scene, s); s.props = PropPanel(s); s.term = TermView()
        s.tcombo = QComboBox(); s.tcombo.addItems(list(TERMS)); s.tcombo.currentTextChanged.connect(s.set_terminal)
        right = QWidget(); v = QVBoxLayout(right); v.addWidget(hdr("Live preview — terminal")); v.addWidget(s.tcombo)
        v.addWidget(s.term, 3); v.addWidget(s.props, 2)
        sp = QSplitter(); sp.addWidget(s.view); sp.addWidget(right); sp.setSizes([760, 560])
        s.designer = AsciiDesigner(s); s.tabs = QTabWidget()
        s.tabs.addTab(sp, "◈  Node Graph"); s.tabs.addTab(s.designer, "✎  ASCII Designer"); s.setCentralWidget(s.tabs)
        s.tb = QToolBar(); s.tb.setMovable(False); s.addToolBar(s.tb); s.acts = {}
        for name, key, fn in (("New", "Ctrl+N", s.new_project), ("Open", "Ctrl+O", s.open_project), ("Save", "Ctrl+S", lambda: s.save()),
                              ("Import", "Ctrl+I", s.import_zip), ("Export", "Ctrl+E", s.export_zip), ("Build", "Ctrl+B", s.build),
                              ("Remove", "", s.remove_build), ("Lesson", "F1", lambda: s.lesson.start())):
            a = QAction(name, s); a.triggered.connect(fn)
            if key: a.setShortcut(QKeySequence(key))
            s.tb.addAction(a); s.acts[name] = a
        a = QAction("Classic mode", s); a.setCheckable(True); a.toggled.connect(s.set_classic)
        a.setToolTip("Classic: just ASCII art and system readouts. No gradients, animation or modern nodes.")
        s.tb.addSeparator(); s.tb.addAction(a); s.acts["Classic"] = a
        s.scene.selectionChanged.connect(s.on_sel); s.lesson = Lesson(s)
        s.timer = QTimer(s); s.timer.timeout.connect(s.tick)
        s.auto = QTimer(s); s.auto.timeout.connect(lambda: s.dirty and s.g and s.save(auto=True)); s.auto.start(600_000)
        s.setStyleSheet(STYLE); s.resize(1400, 860); PROJ.mkdir(parents=True, exist_ok=True)
        last = s.cfg.value("last", "")
        if last and (PROJ / last / "project.json").exists(): s.open_graph(s.read(last))
        else: s.open_graph(default_graph("my-first-fetch", "custom")); s.save()
        if not s.cfg.value("lesson/done", False, type=bool): QTimer.singleShot(500, lambda: s.lesson.start())
    # helpers
    classic = property(lambda s: bool(s.g and s.g.meta.get("classic")))
    def bar(s, n): return s.tb.widgetForAction(s.acts[n])
    def has(s, t): return any(n["type"] == t for n in s.g.nodes.values())
    def linked(s, t): return any(s.g.nodes[a]["type"] == t and s.g.nodes[b]["type"] == "output" for a, b in s.g.edges if a in s.g.nodes and b in s.g.nodes)
    def read(s, name): return Graph.load(json.loads((PROJ / name / "project.json").read_text()), name)
    def on_sel(s):
        try: sel = [i for i in s.scene.selectedItems() if isinstance(i, NodeItem)]
        except RuntimeError: return
        s.props.show_node(sel[0].d if len(sel) == 1 else None)
    def set_terminal(s, t):
        if s.g: s.g.meta["terminal"] = t; s.touch()
    def set_classic(s, on):
        if not s.g: return
        s.g.meta["classic"] = bool(on); s.designer.refresh_classic(); s.props.later_refresh(); s.touch()
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
        STATE["dirty"] = False; PREVIEW["terminal"] = s.g.meta.get("terminal"); t = TERMS.get(s.g.meta.get("terminal"), TERMS["GNOME Terminal"])
        if not s.comp: s.term.set([], "#1e1e1e", "#d0d0d0", t[0], t[1]); return
        O = s.comp["O"]; s.term.set(compose(s.comp, s.fi), O["bg"], O["fg"], t[0], t[1])
    def import_asset(s, path):
        d = s.g.dir / "assets"; d.mkdir(parents=True, exist_ok=True); name = Path(path).name; dst = d / name; k = 1
        while dst.exists() and not dst.samefile(path): dst = d / f"{k}_{name}"; k += 1
        if not dst.exists(): shutil.copy(path, dst)
        return "assets/" + dst.name
    # themes + custom logo nodes
    def apply_theme(s, name):
        T = THEMES[name]; ac = T["acc"]; i = 0
        for n in sorted(s.g.nodes.values(), key=lambda n: n["y"]):
            p, t = n["params"], n["type"]
            if t == "output": p["bg"], p["fg"] = T["bg"], T["fg"]
            elif t == "logo": p["color"], p["color2"], p["color3"] = ac[0], ac[1], ac[2]
            elif t == "title": p["color"] = ac[0]
            elif t == "info":
                adv = next((o["params"]["preset"] == "advanced" for o in s.g.nodes.values() if o["type"] == "output"), False)
                p["key_color"] = ac[i % len(ac)] if adv else ac[0]; p["val_color"] = T["fg"]; i += 1
            elif t == "bar": p["key_color"], p["c1"], p["c2"], p["c3"], p["empty"] = ac[0], ac[3], ac[4], ac[1], T["dim"]
            elif t == "divider": p["color"], p["color2"] = ac[0], ac[1]
            elif t == "text": p["color"] = T["fg"]
            if n["id"] in s.scene.nitems: s.scene.nitems[n["id"]].update()
    def edit_in_designer(s, d): s.designer.load_logo(d["params"]["data"], d["id"]); s.tabs.setCurrentIndex(1)
    def export_node(s, d):
        logo = sanitize_logo(d["params"]["data"]); fn, _ = QFileDialog.getSaveFileName(s, "Export node", str(Path.home() / (clean_name(logo["name"]) + ".fsnode")), "Fetch Studio node (*.fsnode)")
        if fn: write_fsnode(logo, fn)
    def add_logo_node(s, logo):
        c = s.view.mapToScene(s.view.viewport().rect().center()); i = s.scene.add_node("clogo", c, data=copy.deepcopy(logo))
        o = next((k for k, n in s.g.nodes.items() if n["type"] == "output"), None)
        if o and (i, o) not in s.g.edges: s.g.edges.append((i, o)); s.scene.add_edge(i, o)
        return i
    def add_library_node(s, path):
        try: s.add_logo_node(lib_read(path))
        except Exception as ex: QMessageBox.warning(s, APP, "Could not load node:\n%s" % ex)
    def import_node_file(s):
        fn, _ = QFileDialog.getOpenFileName(s, "Import node", str(Path.home()), "Fetch Studio node (*.fsnode)")
        if fn:
            try: logo = lib_read(fn); lib_save(logo); s.add_logo_node(logo); s.designer.refresh_lib()
            except Exception as ex: QMessageBox.warning(s, APP, "Could not import:\n%s" % ex)
    def designer_save(s, logo, editing=None):
        lib_save(logo); n = s.scene.nitems.get(editing) if editing else None
        if n: n.d["params"]["data"] = copy.deepcopy(logo); n.update(); i = editing
        else: i = s.add_logo_node(logo)
        s.flags["design_saved"] = True; s.touch(); s.tabs.setCurrentIndex(0)
        s.scene.clearSelection(); s.scene.nitems[i].setSelected(True); return i
    # project lifecycle
    def open_graph(s, g):
        s.g = g; s.scene.blockSignals(True); s.scene.load(g); s.scene.blockSignals(False); s.props.show_node(None)
        s.tcombo.blockSignals(True); s.tcombo.setCurrentText(g.meta.get("terminal", "GNOME Terminal")); s.tcombo.blockSignals(False)
        s.acts["Classic"].blockSignals(True); s.acts["Classic"].setChecked(bool(g.meta.get("classic"))); s.acts["Classic"].blockSignals(False)
        s.designer.refresh_classic(); s.dirty = False; s.cfg.setValue("last", g.name); s.recompile(); s.title()
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
        pr, ok = QInputDialog.getItem(s, "New project", "Start from preset:", ["classic (simple, no effects)", "advanced", "custom"], 0, False)
        if not ok: return
        name = clean_name(name)
        while (PROJ / name).exists(): name += "-2"
        g = default_graph(name, pr.split()[0]); g.meta["classic"] = pr.startswith("classic"); s.open_graph(g); s.save()
    def open_project(s):
        if not s.maybe_save(): return
        names = sorted(p.parent.name for p in PROJ.glob("*/project.json"))
        n, ok = QInputDialog.getItem(s, "Open project", "Project:", names, 0, False) if names else ("", False)
        if ok: s.open_graph(s.read(n))
    def export_zip(s):
        s.save(); fn, _ = QFileDialog.getSaveFileName(s, "Export", str(Path.home() / f"fetchstudio({s.g.name}).zip"), "Zip (*.zip)")
        if not fn: return
        with zipfile.ZipFile(fn, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("project.json", json.dumps(s.g.dump(), indent=1))       # custom logo nodes are embedded in the graph JSON
            for f in (s.g.dir / "assets").glob("*"): z.write(f, "assets/" + f.name)
        s.flags["exported"] = True; QMessageBox.information(s, APP, "Exported:\n" + fn)
    def import_zip(s):
        if not s.maybe_save(): return
        fn, _ = QFileDialog.getOpenFileName(s, "Import fetchstudio zip", str(Path.home()), "Zip (*.zip)")
        if not fn: return
        try:
            with zipfile.ZipFile(fn) as z:
                data = json.loads(z.read("project.json")); name = clean_name(data.get("name", "imported"))
                for n in data["nodes"]:
                    if n["type"] == "clogo": n["params"]["data"] = sanitize_logo(n["params"]["data"])
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
        anim = "" if len(c["frames"]) < 2 else ("\n\nAnimation: stays live until you run your first command (a terminal cannot redraw text that has scrolled away)."
                                                if c["O"]["lifetime"] == "live" else "\n\nAnimation: plays at launch, then stops on the final frame.")
        QMessageBox.information(s, APP, "Built for %s.\n\nScript: %s\nShell hooks:\n  %s\n\nTerminals found here: %s%s\n\nOpen a new terminal to see it. "
                                "The app is no longer needed; use Build again after editing, or Remove to uninstall." %
                                (distro_family(), ACTIVE / "fetch.sh", "\n  ".join(map(str, files)), ", ".join(found) or "none detected", anim))
    def remove_build(s): remove_hooks(); QMessageBox.information(s, APP, "Fetch Studio hooks and script removed.")
    def closeEvent(s, e):
        if s.maybe_save(): s.lesson.stop() if s.lesson.active else None; e.accept()
        else: e.ignore()

def main():
    app = QApplication(sys.argv); app.setApplicationName(APP); w = Main(); w.show(); sys.exit(app.exec())
if __name__ == "__main__": main()

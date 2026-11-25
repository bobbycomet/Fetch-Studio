"""Node specifications: parameters, readout groups, themes, UI stylesheet."""
from .common import *


# ------------------------------------------------------------------ node specs
class Par:
    def __init__(s, key, label, kind, default, opts=None, fancy=False, when=None):
        s.key, s.label, s.kind, s.default, s.opts, s.fancy, s.when = key, label, kind, default, opts, fancy, when
P = Par
FIELDS = ["OS", "Host", "Board", "BIOS", "Chassis", "Kernel", "Init", "Uptime", "Packages", "Shell", "DE", "Session", "Terminal",
          "CPU", "CPUTemp", "GPU", "GPUTemp", "Fans", "SuperIO", "Memory", "Swap", "Disk", "Load", "Procs", "Battery",
          "LocalIP", "Resolution", "Locale", "Weather", "Environment", "Clock", "Storage", "Network", "Hardware", "Services", "Custom"]
FIELD_LABELS = {"Board": "Motherboard", "BIOS": "BIOS", "Chassis": "Chassis (desktop/laptop)", "Init": "Init system", "CPUTemp": "CPU Temp",
                "GPUTemp": "GPU Temp", "Fans": "Fan Speed (case fans)", "SuperIO": "Super I/O chip", "Procs": "Processes",
                "LocalIP": "Local IP", "DE": "DE", "Weather": "Weather (needs internet)", "Custom": "Custom command",
                "Environment": "▸ Environment (weather, sunrise…)", "Clock": "▸ Clock & date (pick items)", "Storage": "▸ Storage (pick items)",
                "Network": "▸ Network (pick items)", "Hardware": "▸ Hardware (pick items)", "Services": "▸ Services (pick items)"}
SHORT_LABELS = {"Board": "Motherboard", "Chassis": "Chassis", "Init": "Init", "CPUTemp": "CPU Temp", "GPUTemp": "GPU Temp",
                "Fans": "Fans", "SuperIO": "Super I/O", "Procs": "Processes", "LocalIP": "Local IP"}   # default on-screen label
# Grouped readouts: ONE Info node, pick any sub-options with tick boxes. (key in SH, menu text, on-screen name)
GROUPS = {
    "Environment": [("Wx_Cond", "Weather conditions", "Weather"), ("Wx_Temp", "Temperature", "Temperature"), ("Wx_Loc", "Location", "Location"),
                    ("Wx_Rise", "Sunrise", "Sunrise"), ("Wx_Set", "Sunset", "Sunset")],
    "Clock": [("Clock_Time", "Local time", "Time"), ("Clock_Date", "Date", "Date"), ("Clock_TZ", "Time zone", "Time zone"),
              ("Clock_Week", "Week number", "Week"), ("Cal", "Calendar (month grid, 8 lines)", "Calendar")],
    "Storage": [("Stor_FS", "Filesystem type", "Filesystem"), ("Stor_Mount", "Mount point (root drive)", "Mount"),
                ("Stor_Type", "SSD / HDD / NVMe", "Drive type"), ("Stor_Model", "Drive model (NVMe included)", "Drive"),
                ("Stor_Temp", "Drive temperature", "Drive Temp"), ("Stor_IO", "Read / write totals since boot", "Disk I/O"),
                ("Stor_Total", "Total available storage", "Storage")],
    "Network": [("Net_If", "Active interface", "Interface"), ("Net_Type", "Connection type (Ethernet / Wi-Fi / VPN)", "Connection"),
                ("Net_SSID", "Wi-Fi SSID", "SSID"), ("Net_Speed", "Link speed", "Link speed"), ("Net_Public", "Public IP (internet)", "Public IP"),
                ("Net_VPN", "VPN status", "VPN"), ("Net_Rate", "Download / upload throughput (~0.2 s sample)", "Throughput")],
    "Hardware": [("HW_Arch", "CPU architecture", "Arch"), ("HW_Microcode", "CPU microcode version", "Microcode"),
                 ("HW_RAM", "RAM type and speed (needs DMI access)", "RAM"), ("Board", "Motherboard", "Motherboard"),
                 ("HW_Driver", "GPU driver (and version)", "GPU driver"), ("HW_VRAM", "GPU VRAM", "VRAM"), ("HW_PCI", "PCI device count", "PCI devices")],
    "Services": [("Svc_Init", "Init system version", "Init"), ("Svc_Running", "Running service count", "Running services"),
                 ("Svc_Failed", "Failed service count", "Failed services"), ("Svc_Targets", "Active system targets", "Targets"),
                 ("Uptime", "Uptime", "Uptime"), ("Svc_Boot", "Booted at (last boot)", "Booted")]}
GROUP_LABEL = {"Environment": "Env", "Clock": "Clock", "Storage": "Storage", "Network": "Network", "Hardware": "Hardware", "Services": "Services"}
GROUP_DEFAULT = {"Environment": ["Wx_Cond", "Wx_Temp"], "Clock": ["Clock_Time", "Clock_Date"], "Storage": ["Stor_Type", "Stor_Total"],
                 "Network": ["Net_If", "Net_Type", "Net_Public"], "Hardware": ["HW_Arch", "HW_RAM"], "Services": ["Svc_Running", "Svc_Failed"]}
GROUP_KEYS = tuple(GROUPS)
PLAIN_FIELDS = tuple(f for f in FIELDS if f not in GROUPS)

# Data that never changes while the machine is up is cached on disk until reboot (0); slow-but-changing data for N minutes.
# Everything NOT listed here (CPU frequency, load, GPU use, temperatures, throughput, clock...) is read live every time.
CLASS = {"GPU": 0, "HW_Microcode": 0, "HW_RAM": 0, "HW_Driver": 0, "HW_VRAM": 0, "HW_PCI": 0, "Svc_Init": 0,
         "Stor_Type": 0, "Stor_Model": 0, "Svc_Running": 1, "Svc_Failed": 1, "Svc_Targets": 1, "Net_SSID": 1}
def san(t): return str(t).replace("{{", "{ {")        # user text can never inject internal {{tokens}}
ANIMS = ["none", "rainbow", "scroll", "pulse", "wave", "typewriter", "sparkle", "scanline"]
GRADS = ["none", "horizontal", "vertical", "diagonal", "radial"]
METRICS = {"Memory": "PCT_Memory", "Disk": "PCT_Disk", "CPU load": "PCT_CPU", "Swap": "PCT_Swap", "Battery": "PCT_Battery",
           "CPU frequency": "PCT_CPUFreq", "GPU": "PCT_GPU", "Net download": "PCT_NetDown", "Net upload": "PCT_NetUp"}
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
        P("mode", "Image mode: auto = real graphics (kitty / iTerm2 / sixel) where the terminal supports them, else sharp blocks", "combo", "auto",
          ["auto", "kitty", "iterm", "sixel", "blocks", "blocks-basic"], False, ("source", "file")),
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
        P("field", "Readout", "fieldlist", "OS", FIELDS), P("label", "Label (blank = default)", "text", ""),
        P("items", "Show (tick what you want; only ticked items appear)", "groupitems", [], None, False, ("field", GROUP_KEYS)),
        P("layout", "Layout: stacked = one line per item, inline = one line", "combo", "stacked", ["stacked", "inline"], False, ("field", GROUP_KEYS)),
        P("names", "Show item names", "check", True, None, False, ("field", GROUP_KEYS)),
        P("override", "Show this text instead of the real value (display only; your system is NOT changed)", "text", "", None, False, ("field", PLAIN_FIELDS)),
        P("location", "Weather location (blank = auto by IP)", "text", "", None, False, ("field", ("Weather", "Environment"))),
        P("units", "Weather units", "combo", "auto", ["auto", "metric", "imperial"], False, ("field", ("Weather", "Environment"))),
        P("command", "Command to run", "text", "echo hello", None, False, ("field", "Custom")),
        P("key_color", "Label color", "color", "#3daee9"), P("val_color", "Value color", "color", "#d0d0d0")]),
    "bar": ("Meter bar", "#1abc9c", [
        P("metrics", "Meters (tick one or more; each gets its own bar)", "multi", ["Memory"], list(METRICS)),
        P("label", "Label (blank = meter name; used when one meter is ticked)", "text", ""),
        P("width", "Bar width", "int", 16, (6, 40)), P("style", "Style", "combo", "blocks", list(BARCH)),
        P("key_color", "Label color", "color", "#3daee9"), P("c1", "Low color", "color", "#2ecc71"),
        P("c2", "Mid color", "color", "#f1c40f"), P("c3", "High color", "color", "#e74c3c"),
        P("empty", "Empty color", "color", "#44475a")]),
    "divider": ("Divider", "#5d6d7e", [
        P("char", "Character", "text", "─"), P("width", "Width", "int", 30, (4, 80)), P("label", "Label", "text", ""),
        P("color", "Color", "color", "#3daee9"), P("color2", "End color", "color", "#bb9af7"),
        P("gradient", "Gradient", "check", True)]),
    "colors": ("Color bar", "#d35400", [P("rows", "Rows", "combo", "2", ["1", "2"])]),
    "text": ("Custom String", "#7f8c8d", [P("text", "Text — {OS} {Kernel} {CPUTemp} {Weather}… insert live values", "text", "Hello"),
                                        P("color", "Color", "color", "#d0d0d0"), P("bold", "Bold", "check", False)]),
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

# Properties inspector: which tab each parameter lives on (keys not listed fall into the first tab).
TABS = {
    "output": [("Layout", ["preset", "gap", "separator"]), ("Colors", ["theme", "bg", "fg"]),
               ("Animation", ["animation", "fps", "lifetime", "loops"])],
    "logo": [("Source", ["source", "file", "width", "mode"]), ("Colors", ["color", "gradient", "color2", "color3"]),
             ("Animation", ["animation"])],
    "clogo": [("Logo", ["animation", "_edit", "_export"])],
    "title": [("Title", ["underline"]), ("Colors", ["color"])],
    "info": [("Readout", ["field", "label", "override", "location", "units", "command"]),
             ("Items", ["items", "layout", "names"]), ("Colors", ["key_color", "val_color"])],
    "bar": [("Meters", ["metrics", "label", "width", "style"]), ("Colors", ["key_color", "c1", "c2", "c3", "empty"])],
    "divider": [("Line", ["char", "width", "label"]), ("Colors", ["color", "gradient", "color2"])],
    "colors": [("Color bar", ["rows"])],
    "text": [("Text", ["text", "bold"]), ("Colors", ["color"])]}

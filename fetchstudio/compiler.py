"""Graph -> rows of styled runs, and run resolution for the preview."""
from .common import *
from .specs import *
from .readouts import *
from .system import *
from .security import *
from .logos import *
from .validation import *
from .model import *
from .render import *
from .graphics import *


# ------------------------------------------------------------------ compiler (graph -> runs)
def wx_key(key, p): return "%s_%d" % (key, abs(hash((p["location"], p["units"]))) % 100000) if key.startswith("Wx_") else key

def group_rows(p, O, adv, sep, funcs):
    """One Info node set to a group (Clock, Storage...) -> only the ticked items, stacked (a line each) or inline (one line)."""
    sel = [i for i in GROUPS[p["field"]] if i[0] in (p.get("items") or [])]
    kc, vc, fg = p["key_color"], p["val_color"], O["fg"]; names = bool(p.get("names", True)); stacked = p.get("layout") != "inline"
    mark = [R("◆ ", kc)] if adv else []; rows, inline, tail = [], [], []
    def val(key):
        k = wx_key(key, p); funcs[k] = weather_item(p["location"], p["units"], key) if key.startswith("Wx_") else SH[key]
        return R("{{%s}}" % k, vc)
    for key, _, short in sel:
        if key == "Cal":                                          # month grid: 8 fixed lines, shown after the other items when inline
            for i in range(8): funcs["Cal%d" % i] = SH["Cal%d" % i]; (rows if stacked else tail).append([R("{{Cal%d}}" % i, vc)])
        elif stacked: rows.append(mark + ([R(san(short), kc, None, True), R(sep, fg)] if names else []) + [val(key)])
        else: inline.append((short, key))
    if inline:
        runs = mark + [R(san(p["label"] or GROUP_LABEL[p["field"]]), kc, None, True), R(sep, fg)]
        for n, (short, key) in enumerate(inline):
            if n: runs.append(R(" · ", fg))
            if names: runs.append(R(san(short) + " ", kc))
            runs.append(val(key))
        rows.append(runs)
    return rows + tail

def compile_graph(g, build=False, skip_cmds=()):
    """build=True also produces the block-character fallback for a graphics logo (the preview doesn't need it)."""
    out = next((n for n in g.nodes.values() if n["type"] == "output"), None)
    if not out: return None
    classic = bool(g.meta.get("classic")); O = dict(out["params"])
    if classic:
        O["animation"] = "none"; O["lifetime"] = "intro"
        if O["preset"] == "advanced": O["preset"] = "classic"
    adv = O["preset"] == "advanced"; sep = O["separator"] if O["preset"] == "custom" else ": "
    rows, funcs, bars, logo, custom = [], {}, {}, None, {}
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
            f = p["field"]; ov = san(p.get("override") or "")
            if f in GROUPS: rows += group_rows(p, O, adv, sep, funcs); continue
            if ov: val = R(ov, p["val_color"])                       # display-only name; nothing on the system is touched
            else:
                if f == "Custom":                                  # never runs unless the user trusted this exact command
                    cmd = p["command"]; key = "c%d" % abs(hash(cmd)); custom[key] = cmd
                    funcs[key] = "echo n/a" if (cmd in skip_cmds or (build and cmd_status(cmd) != "trusted")) else wrap_command(cmd)
                elif f == "Weather": key = "w%d" % abs(hash((p["location"], p["units"]))); funcs[key] = weather_item(p["location"], p["units"], "Weather")
                else: key = f; funcs[key] = SH[f]
                val = R("{{%s}}" % key, p["val_color"])
            lab = san(p["label"] or SHORT_LABELS.get(f, f))
            rows.append(([R("◆ ", p["key_color"])] if adv else []) + [R(lab, p["key_color"], None, True), R(sep, O["fg"]), val])
        elif t == "bar":
            ms = [m for m in METRICS if m in (p.get("metrics") or [])]; fc, ec = BARCH[p["style"]]; w = int(p["width"])
            for m in ms:                                              # every ticked meter gets its own bar line
                key = METRICS[m]; funcs[key] = SH[key]; bn = "BAR%d" % len(bars)
                bars[bn] = dict(key=key, w=w, fill=fc, empty=ec, ec=p["empty"],
                                colors=[grad([p["c1"], p["c2"], p["c3"]], i / max(1, w - 1)) for i in range(w)])
                rows.append([R(san(p["label"] if len(ms) == 1 and p["label"] else m), p["key_color"], None, True), R(sep, O["fg"]),
                             R("{{%s}}" % bn), R(" {{%s}}%%" % key, O["fg"])])
        elif t == "divider":
            w = int(p["width"]); s_ = ((p["char"] or "─")[0]) * w; lab = san(p["label"])
            if lab: lab = " " + lab[: w - 4] + " "; i0 = (w - len(lab)) // 2; s_ = s_[:i0] + lab + s_[i0 + len(lab):]
            rows.append(merge([R(c, grad([p["color"], p["color2"]], i / max(1, w - 1)) if p["gradient"] else p["color"]) for i, c in enumerate(s_)]))
        elif t == "colors":
            rows.append([])
            for r in range(int(p["rows"])): rows.append([R("   ", None, "a%d" % (i + 8 * r)) for i in range(8)])
        elif t == "text":
            txt = san(p["text"]); row = []; pos = 0; ph = {k.lower(): k for k in list(SH) if not k.startswith(("PCT_", "Cal")) and k != "TitleU"}
            for m in re.finditer(r"\{(\w+)\}", txt):
                k = ph.get(m[1].lower())
                if not k: continue
                if m.start() > pos: row.append(R(txt[pos:m.start()], p["color"], None, p["bold"]))
                funcs[k] = SH[k]; row.append(R("{{%s}}" % k, p["color"], None, p["bold"])); pos = m.end()
            if pos < len(txt): row.append(R(txt[pos:], p["color"], None, p["bold"]))
            rows.append(row or [R("")])
    gfx = gimgs = None                       # graphics-protocol logo (kitty / iTerm2 / sixel), blocks stay the fallback
    if logo and logo["type"] == "logo" and not classic and logo["params"]["source"] == "file" and logo["params"]["mode"] in GFX_MODES:
        pth = g.asset(logo["params"]["file"])
        if pth and pth.exists() and pth.suffix.lower() in IMG:
            sz = QImageReader(str(pth)).size(); cols = int(logo["params"]["width"])
            if sz.width() > 0: gfx = dict(path=pth, cols=cols, rows=max(1, round(sz.height() * cols / sz.width() / 2)), mode=logo["params"]["mode"])
    if gfx and not build:
        gimgs = gfx_images(gfx["path"], gfx["cols"])
        if gimgs: frames, final = [[[R(" " * gfx["cols"])] for _ in range(gfx["rows"])]], 0     # blank space; the preview paints the image over it
        else: gfx = None
    if not (gfx and not build): frames, final = logo_frames(g, logo, O, classic) if logo else ([[]], 0)
    return dict(O=O, frames=frames, final=final, rows=rows, funcs=funcs, bars=bars, classic=classic, gfx=gfx, gimgs=gimgs, custom=custom)

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
            elif k in c.get("custom", {}):                    # custom command: preview only runs trusted ones
                st = cmd_status(c["custom"][k])
                out.append((value(k, c["funcs"][k]) if st == "trusted" else {"untrusted": "[not trusted]", "blocked": "[blocked]", "empty": "n/a"}[st], fg, bg, b))
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

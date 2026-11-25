"""Custom logo nodes (.fsnode plugins). Pure data, validated, never code."""
from .common import *
from .specs import *
from .readouts import *
from .system import *
from .security import *


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

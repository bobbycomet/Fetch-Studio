"""Graph model and default project templates."""
from .common import *
from .specs import *
from .readouts import *
from .system import *
from .security import *
from .logos import *
from .validation import *


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
            if n["type"] == "bar" and "metrics" not in n["params"]: n["params"]["metrics"] = [n["params"].pop("metric", "Memory")]   # pre-multi-meter projects
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

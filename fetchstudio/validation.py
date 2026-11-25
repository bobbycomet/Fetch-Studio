"""Strict validation for project files and project ZIP archives.

Nothing from an imported project is used until it has been checked here: node types, parameters, graph connections, IDs,
sizes, ZIP entry names and decompressed sizes. Malformed input is rejected with a readable ProjectError; valid input is
returned in a normalized form (defaults filled in, unknown keys dropped).
"""
from .common import *
from .specs import *
from .system import clean_name
from .logos import sanitize_logo, new_logo

MAX_PROJECT_JSON = 2 * 1024 * 1024
MAX_ZIP_ENTRIES = 300
MAX_ASSET_BYTES = 16 * 1024 * 1024
MAX_TEXT_ASSET_BYTES = 256 * 1024
MAX_ZIP_TOTAL = 64 * 1024 * 1024
MAX_RATIO = 200                       # decompressed / compressed, only enforced above 1 MiB
MAX_NODES, MAX_EDGES, MAX_GROUPS, MAX_TEXT = 500, 2000, 100, 4000
MAX_PIXELS, MAX_DIM, MAX_FRAMES = 40_000_000, 16000, 1000
ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
ASSET_RE = re.compile(r"^assets/([^/\\\x00-\x1f:]{1,200})$")
ALL_ITEM_KEYS = {i[0] for items in GROUPS.values() for i in items}
TEXT_EXT = {".txt"}

class ProjectError(ValueError):
    """The project or archive is malformed, unsafe or too large."""

def _fail(msg): raise ProjectError(msg)
def _num(v, lim=1e6): return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and abs(v) <= lim

def _asset_name(v, where):
    m = ASSET_RE.match(v)
    if not m or m[1] in (".", "..") or m[1].startswith("."): _fail("%s: invalid asset path %r" % (where, v[:80]))
    return v

def _param(ntype, par, v, where):
    k = par.kind
    if k == "combo":
        if isinstance(v, (int, float)) and not isinstance(v, bool): v = str(int(v))
        if not isinstance(v, str) or v not in par.opts: _fail("%s: %r is not a valid value for '%s'" % (where, str(v)[:40], par.key))
        return v
    if k == "int":
        if isinstance(v, float) and v.is_integer(): v = int(v)
        if not isinstance(v, int) or isinstance(v, bool) or not par.opts[0] <= v <= par.opts[1]:
            _fail("%s: '%s' must be a whole number from %d to %d" % (where, par.key, *par.opts))
        return v
    if k == "check":
        if not isinstance(v, bool): _fail("%s: '%s' must be true or false" % (where, par.key))
        return v
    if k == "text":
        if not isinstance(v, str) or len(v) > MAX_TEXT or "\x00" in v: _fail("%s: '%s' must be text under %d characters" % (where, par.key, MAX_TEXT))
        return v
    if k == "color":
        if not isinstance(v, str) or not HEX_RE.match(v): _fail("%s: '%s' must be a #rrggbb color" % (where, par.key))
        return v
    if k == "file":
        if not isinstance(v, str): _fail("%s: '%s' must be text" % (where, par.key))
        return _asset_name(v, where) if v else ""
    if k == "fieldlist":
        if not isinstance(v, str) or v not in par.opts: _fail("%s: unknown readout %r" % (where, str(v)[:40]))
        return v
    if k in ("multi", "groupitems"):
        allowed = set(par.opts) if k == "multi" else ALL_ITEM_KEYS
        if not isinstance(v, list) or len(v) > 64 or any(not isinstance(x, str) or x not in allowed for x in v):
            _fail("%s: '%s' has an invalid selection" % (where, par.key))
        return list(dict.fromkeys(v))
    if k == "hidden":
        if v is None: return new_logo() if ntype == "clogo" else None
        try: return sanitize_logo(v)
        except Exception as ex: _fail("%s: invalid custom logo (%s)" % (where, ex))
    return copy.deepcopy(par.default)                       # 'action' rows hold no data

def validate_project(data, name=None):
    """-> normalized project dict (same shape as Graph.dump()). Raises ProjectError."""
    if not isinstance(data, dict): _fail("project.json is not a JSON object")
    nodes_in, edges_in = data.get("nodes"), data.get("edges")
    if not isinstance(nodes_in, list) or not isinstance(edges_in, list): _fail("project has no node or edge list")
    if len(nodes_in) > MAX_NODES: _fail("too many nodes (%d, limit %d)" % (len(nodes_in), MAX_NODES))
    if len(edges_in) > MAX_EDGES: _fail("too many connections (%d, limit %d)" % (len(edges_in), MAX_EDGES))
    groups_in = data.get("groups", {}); meta_in = data.get("meta", {})
    if not isinstance(groups_in, dict) or not isinstance(meta_in, dict) or len(groups_in) > MAX_GROUPS: _fail("malformed groups or settings")
    groups = {}
    for gid, gi in groups_in.items():
        if not isinstance(gid, str) or not ID_RE.match(gid) or not isinstance(gi, dict): _fail("malformed group %r" % str(gid)[:20])
        nm, col, pos = gi.get("name", "Group"), gi.get("collapsed", False), gi.get("pos", [0, 0])
        if not isinstance(nm, str) or len(nm) > 80 or not isinstance(col, bool) or not (isinstance(pos, list) and len(pos) == 2 and all(_num(c) for c in pos)):
            _fail("malformed group %r" % gid)
        groups[gid] = dict(name=nm, collapsed=col, pos=[float(c) for c in pos])
    nodes, ids, out_id = [], set(), None
    for i, n in enumerate(nodes_in):
        if not isinstance(n, dict): _fail("node #%d is not an object" % (i + 1))
        nid, t = n.get("id"), n.get("type")
        if not isinstance(nid, str) or not ID_RE.match(nid): _fail("node #%d has an invalid id" % (i + 1))
        if nid in ids: _fail("duplicate node id %r" % nid)
        if t not in SPEC: _fail("node %r has an unknown type %r" % (nid, str(t)[:30]))
        if not _num(n.get("x")) or not _num(n.get("y")): _fail("node %r has an invalid position" % nid)
        grp = n.get("group")
        if grp is not None and (not isinstance(grp, str) or grp not in groups): _fail("node %r refers to a missing group" % nid)
        pin = n.get("params", {})
        if not isinstance(pin, dict): _fail("node %r has malformed parameters" % nid)
        pin = dict(pin)
        if t == "bar" and "metrics" not in pin and "metric" in pin: pin["metrics"] = [pin["metric"]]      # projects from before multi-meter bars
        params = {}
        for par in SPEC[t][2]:
            params[par.key] = _param(t, par, pin[par.key], "%s node %s" % (SPEC[t][0], nid)) if par.key in pin else \
                              (new_logo() if t == "clogo" and par.kind == "hidden" else copy.deepcopy(par.default))
        if t == "output":
            if out_id: _fail("more than one Output node")
            out_id = nid
        ids.add(nid); nodes.append(dict(id=nid, type=t, x=float(n["x"]), y=float(n["y"]), params=params, group=grp))
    if not out_id: _fail("the project has no Output node")
    edges, seen = [], set()
    for i, e in enumerate(edges_in):
        if not (isinstance(e, (list, tuple)) and len(e) == 2 and all(isinstance(x, str) for x in e)): _fail("connection #%d is malformed" % (i + 1))
        a, b = e
        if a not in ids or b not in ids: _fail("connection #%d refers to a missing node" % (i + 1))
        if b != out_id or a == out_id: _fail("connection #%d must lead into the Output node" % (i + 1))
        if (a, b) in seen: _fail("duplicate connection #%d" % (i + 1))
        seen.add((a, b)); edges.append([a, b])
    used = {n["group"] for n in nodes if n["group"]}
    groups = {g: v for g, v in groups.items() if g in used}
    term = meta_in.get("terminal", "GNOME Terminal")
    meta = dict(terminal=term if term in TERMS else "GNOME Terminal")
    for k in ("classic", "anim_v2"):
        if k in meta_in:
            if not isinstance(meta_in[k], bool): _fail("setting '%s' must be true or false" % k)
            meta[k] = meta_in[k]
    nm = clean_name(str(name if name is not None else data.get("name", "imported")))[:60]
    return dict(version=1, name=nm, nodes=nodes, edges=edges, groups=groups, meta=meta)

def load_project_file(path, name):
    """Read and validate a project.json from disk (the user's own projects get the same checks)."""
    p = Path(path)
    try:
        if p.stat().st_size > MAX_PROJECT_JSON: _fail("project.json is larger than %d MB" % (MAX_PROJECT_JSON >> 20))
        data = json.loads(p.read_text())
    except (OSError, ValueError, RecursionError) as ex: _fail("cannot read project: %s" % ex)
    return validate_project(data, name)

def _entry_ok(zi):
    n = zi.filename
    if n == "assets/": return "dir"
    if n == "project.json": return "project"
    if n.startswith("/") or "\\" in n or ".." in n.split("/") or any(ord(c) < 32 for c in n): _fail("unsafe ZIP entry name %r" % n[:60])
    m = ASSET_RE.match(n)
    if not m or m[1].startswith("."): _fail("unexpected ZIP entry %r (only project.json and assets/<file> are allowed)" % n[:60])
    if Path(m[1]).suffix.lower() not in IMG | TEXT_EXT: _fail("asset %r has a file type that is not allowed" % m[1][:60])
    return "asset"

def _read_bounded(z, zi, limit):
    with z.open(zi) as f: raw = f.read(limit + 1)             # never trust the size in the header
    if len(raw) > limit: _fail("%r is larger than its limit when decompressed" % zi.filename[:60])
    return raw

def _check_image(name, raw):
    ba = QByteArray(raw); buf = QBuffer(ba); buf.open(QIODevice.OpenModeFlag.ReadOnly)
    r = QImageReader(buf); sz = r.size()
    if not r.canRead() or sz.width() <= 0 or sz.height() <= 0: _fail("asset %r is not a readable image" % name)
    if sz.width() > MAX_DIM or sz.height() > MAX_DIM or sz.width() * sz.height() > MAX_PIXELS: _fail("image %r is too large (%dx%d)" % (name, sz.width(), sz.height()))
    if r.imageCount() > MAX_FRAMES: _fail("animation %r has too many frames" % name)
    buf.close()

def read_project_zip(path):
    """-> (normalized project dict, {asset file name: bytes}, [warnings]). Raises ProjectError before anything is written."""
    try: zf = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as ex: _fail("not a valid ZIP file (%s)" % ex)
    with zf as z:
        infos = z.infolist()
        if len(infos) > MAX_ZIP_ENTRIES: _fail("the archive has too many entries (%d, limit %d)" % (len(infos), MAX_ZIP_ENTRIES))
        names, total, kinds = set(), 0, {}
        for zi in infos:
            kind = _entry_ok(zi)
            if zi.filename.lower() in names: _fail("duplicate ZIP entry %r" % zi.filename[:60])
            names.add(zi.filename.lower())
            if kind == "dir": continue
            if zi.flag_bits & 0x1: _fail("encrypted ZIP entries are not supported")
            if (zi.external_attr >> 16) & 0o170000 == 0o120000: _fail("ZIP entry %r is a symbolic link" % zi.filename[:60])
            lim = MAX_PROJECT_JSON if kind == "project" else (MAX_TEXT_ASSET_BYTES if Path(zi.filename).suffix.lower() in TEXT_EXT else MAX_ASSET_BYTES)
            if zi.file_size > lim: _fail("%r is too large (%d bytes, limit %d)" % (zi.filename[:60], zi.file_size, lim))
            if zi.file_size > (1 << 20) and zi.compress_size and zi.file_size / zi.compress_size > MAX_RATIO: _fail("%r has a suspicious compression ratio" % zi.filename[:60])
            total += zi.file_size; kinds[zi.filename] = (kind, lim)
        if total > MAX_ZIP_TOTAL: _fail("the archive expands to more than %d MB" % (MAX_ZIP_TOTAL >> 20))
        if "project.json" not in kinds: _fail("the archive has no project.json")
        try: data = json.loads(_read_bounded(z, z.getinfo("project.json"), MAX_PROJECT_JSON))
        except (ValueError, RecursionError) as ex: _fail("project.json is not valid JSON (%s)" % ex)
        proj = validate_project(data)
        assets, got, warns = {}, 0, []
        for fn, (kind, lim) in kinds.items():
            if kind != "asset": continue
            raw = _read_bounded(z, z.getinfo(fn), lim); got += len(raw)
            if got > MAX_ZIP_TOTAL: _fail("the archive expands to more than %d MB" % (MAX_ZIP_TOTAL >> 20))
            base = fn.split("/", 1)[1]
            if Path(base).suffix.lower() in IMG: _check_image(base, raw)
            assets[base] = raw
    for n in proj["nodes"]:
        f = n["params"].get("file", "") if n["type"] == "logo" else ""
        if f and f.split("/", 1)[1] not in assets: warns.append("A logo refers to %s, which is not in the archive." % f)
    return proj, assets, warns

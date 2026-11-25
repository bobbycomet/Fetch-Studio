"""System helpers: environment, update check, preview value cache, os-release."""
from .common import *
from .specs import *
from .readouts import *


# ------------------------------------------------------------------ system helpers
def clean_env():
    e = dict(os.environ)
    if "LD_LIBRARY_PATH_ORIG" in e: e["LD_LIBRARY_PATH"] = e.pop("LD_LIBRARY_PATH_ORIG")
    else: e.pop("LD_LIBRARY_PATH", None)
    return e

def vtuple(v):
    """'v1.2.3' / '1.2.3-beta' -> (1, 2, 3) for comparison."""
    return tuple(int(x) for x in re.findall(r"\d+", str(v).split("-")[0])[:4]) or (0,)

def fetch_latest_release():
    """Latest published (non-draft, non-prerelease) GitHub release -> (tag, page url)."""
    import urllib.request
    req = urllib.request.Request("https://api.github.com/repos/%s/releases/latest" % GH_REPO,
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": "FetchStudio/" + VERSION})
    with urllib.request.urlopen(req, timeout=8) as r: d = json.load(r)
    return str(d.get("tag_name", "")), str(d.get("html_url") or RELEASES_URL)

CACHE, PENDING, STATE = {}, set(), {"dirty": False, "gen": 0}
PREVIEW = {"terminal": None}
def refresh_values():
    """Forget every fetched readout so the preview reads them again (after installing cal, on the Refresh button...).
    Both the cache AND the set of requests in flight must be cleared, or a key stays 'pending' and shows '…' forever."""
    STATE["gen"] += 1; CACHE.clear(); PENDING.clear(); STATE["dirty"] = True

def value(key, snip):
    """Real value from this machine (async, cached). Same snippet is baked into the build."""
    if key in CACHE: return CACHE[key]
    if key not in PENDING:
        PENDING.add(key); gen = STATE["gen"]
        def run():
            try:
                r = subprocess.run(["bash", "-c", ". /etc/os-release 2>/dev/null; " + snip],
                                   capture_output=True, text=True, timeout=5, env=clean_env())
                out = r.stdout.rstrip("\n"); res = out if out != "" else "n/a"          # same rule as the script: only newlines are trimmed
            except Exception: res = "n/a"
            if gen == STATE["gen"]: CACHE[key] = res; STATE["dirty"] = True                # a refresh in between makes this answer stale: drop it
        threading.Thread(target=run, daemon=True).start()
    return "…"

def osrel():
    d = {}
    for p in ("/etc/os-release", "/usr/lib/os-release"):
        try:
            with open(p) as fh:
                for l in fh:
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

# ------------------------------------------------------------------ main window
def clean_name(n): return re.sub(r"[^\w.-]+", "_", n.strip()) or "project"

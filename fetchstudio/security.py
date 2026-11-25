"""Trust boundary for custom shell commands.

The Info node's "Custom command" runs through bash every time a terminal opens, so a project file that contains one
is executable content. The rules (enforced here, used by the editor, the preview and Build):

* A command never runs in the live preview and is never baked into a build until the user has trusted it.
* Trust is per command text (SHA-256), stored on this computer only. Importing a project never trusts anything.
* Commands that try to elevate privileges (sudo, su, doas, pkexec, run0...) are blocked outright.
* Commands run as the current user, in their own `bash -c`, with a 5 second limit and no stdin.
"""
from .common import *
from .system import *

ELEVATION = re.compile(r"(^|[\s;&|(){}`$<>])(sudo|su|doas|pkexec|run0|gksu|gksudo|kdesu|kdesudo)(?=$|[\s;&|(){}`<>])")
TRUST_FILE = DATA / "trusted_commands.json"
_TRUST = {"loaded": False, "hashes": set()}

def cmd_hash(cmd): return hashlib.sha256(str(cmd).strip().encode("utf-8", "replace")).hexdigest()

def _load():
    if _TRUST["loaded"]: return
    _TRUST["loaded"] = True
    try:
        d = json.loads(TRUST_FILE.read_text())
        _TRUST["hashes"] = {h for h in d.get("trusted", []) if isinstance(h, str) and re.fullmatch(r"[0-9a-f]{64}", h)}
    except (OSError, ValueError, AttributeError): _TRUST["hashes"] = set()

def _save():
    try:
        TRUST_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = TRUST_FILE.with_suffix(".tmp"); tmp.write_text(json.dumps({"trusted": sorted(_TRUST["hashes"])}, indent=1))
        os.chmod(tmp, 0o600); os.replace(tmp, TRUST_FILE)
    except OSError: pass                                  # trust then only lasts for this session

def is_elevated(cmd): return bool(ELEVATION.search(str(cmd)))
def is_trusted(cmd): _load(); return cmd_hash(cmd) in _TRUST["hashes"]

def trust_command(cmd):
    """Only ever called after an explicit user action (button or dialog). Elevated commands cannot be trusted."""
    if not str(cmd).strip() or is_elevated(cmd): return False
    _load(); _TRUST["hashes"].add(cmd_hash(cmd)); _save(); return True

def cmd_status(cmd):
    """'empty' | 'blocked' | 'trusted' | 'untrusted'"""
    if not str(cmd).strip(): return "empty"
    if is_elevated(cmd): return "blocked"
    return "trusted" if is_trusted(cmd) else "untrusted"

def custom_commands(g, connected_only=False):
    """Every Info node set to 'Custom command' -> [{'node', 'cmd', 'status'}]."""
    out_ids = {n["id"] for n in g.nodes.values() if n["type"] == "output"}
    linked = {a for a, b in g.edges if b in out_ids}
    res = []
    for n in g.nodes.values():
        p = n["params"]
        if n["type"] != "info" or p.get("field") != "Custom" or not str(p.get("command", "")).strip(): continue
        if connected_only and n["id"] not in linked: continue
        res.append(dict(node=n["id"], cmd=str(p["command"]), status=cmd_status(p["command"])))
    return res

def wrap_command(cmd):
    """The form baked into the script and used by the preview: own bash -c (a syntax error cannot break the whole script),
    5 s limit when `timeout` exists, no stdin, errors silenced."""
    q = shlex.quote(str(cmd))
    return '$(command -v timeout >/dev/null 2>&1 && echo timeout 5) bash -c %s </dev/null 2>/dev/null' % q

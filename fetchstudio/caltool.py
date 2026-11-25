"""Support for the `cal` command (Clock > Calendar readout): detection, manual commands, polkit helper."""
from .common import *
from .system import osrel, clean_env

HELPER = Path("/usr/libexec/fetchstudio/fetchstudio-cal-helper")
POLICY = Path("/usr/share/polkit-1/actions/io.github.bobbycomet.fetchstudio.policy")
_BASE = Path(sys._MEIPASS) / "fetchstudio" if hasattr(sys, "_MEIPASS") else Path(__file__).resolve().parent      # PyInstaller / AppImage / source
RESOURCE_DIR = _BASE / "helper"
HELPER_FILES = ("fetchstudio-cal-helper", "io.github.bobbycomet.fetchstudio.policy", "install-helper.sh")
FAMILIES = {"debian": {"debian", "ubuntu", "linuxmint", "pop", "elementary"}, "fedora": {"fedora", "rhel", "centos", "almalinux", "rocky"},
            "arch": {"arch", "manjaro", "endeavouros", "cachyos"}, "suse": {"suse", "opensuse", "opensuse-leap", "opensuse-tumbleweed"}}
MANUAL = {"debian": "sudo apt update && sudo apt install ncal", "fedora": "sudo dnf install util-linux",
          "arch": "sudo pacman -S util-linux", "suse": "sudo zypper install util-linux"}
FAMILY_NAMES = {"debian": "Ubuntu, Debian, Linux Mint, Pop!_OS", "fedora": "Fedora, RHEL, CentOS, AlmaLinux, Rocky Linux",
                "arch": "Arch Linux, Manjaro, EndeavourOS", "suse": "openSUSE Tumbleweed and Leap"}

def have_cal(): return shutil.which("cal") is not None

def family():
    d = osrel(); ids = set((d.get("ID", "") + " " + d.get("ID_LIKE", "")).lower().split())
    return next((f for f, names in FAMILIES.items() if ids & names), None)

def manual_command():
    """The command to run by hand on this distribution (None if the distribution is not recognized)."""
    return MANUAL.get(family())

def _root_owned(p, directory=False):
    try:
        st = p.stat()
        return st.st_uid == 0 and not st.st_mode & 0o022 and (p.is_dir() if directory else p.is_file())
    except OSError: return False

def helper_installed():
    """True only when the helper and its polkit policy are installed and cannot be modified by non-root users."""
    return _root_owned(HELPER) and _root_owned(HELPER.parent, True) and POLICY.is_file() and shutil.which("pkexec") is not None

def install_cal():
    """Run the helper through pkexec (polkit asks for the administrator password). -> (ok, message). Blocking: call from a thread."""
    if not helper_installed(): return False, "The Fetch Studio helper is not installed."
    r, err = _admin(["pkexec", str(HELPER), "install"])
    if r is None: return False, err
    if r.returncode == 0 and have_cal(): return True, "The cal command is now installed."
    return _fail(r, "Installation")

def extract_helper(dest):
    """Copy the helper files to a normal folder so they can be installed with `sudo sh install-helper.sh` (an AppImage's
    own files live in a mount that root cannot read)."""
    dest = Path(dest).expanduser(); dest.mkdir(parents=True, exist_ok=True)
    for f in HELPER_FILES:
        shutil.copy(RESOURCE_DIR / f, dest / f)
        if f != "io.github.bobbycomet.fetchstudio.policy": (dest / f).chmod(0o755)
    return dest

# ---- one-click helper setup: the app installs its own helper through pkexec's generic administrator prompt
MARKER = Path("/var/lib/fetchstudio/cal-installed-by-helper")
POLICY_FILES = ("io.github.bobbycomet.fetchstudio.policy",)

def helper_script(action="install", libexec="/usr/libexec/fetchstudio", policydir="/usr/share/polkit-1/actions"):
    """A self-contained root shell script that installs (or removes) the helper and policy. It is handed to
    `pkexec /bin/sh -s` on stdin, so root never executes or reads a file that a normal user could modify in between."""
    q = shlex.quote
    if action == "remove":
        return "set -eu\nrm -f %s/fetchstudio-cal-helper %s/%s\nrmdir %s 2>/dev/null || true\n" % (q(libexec), q(policydir), POLICY_FILES[0], q(libexec))
    hp, pp = (RESOURCE_DIR / "fetchstudio-cal-helper").read_text(), (RESOURCE_DIR / POLICY_FILES[0]).read_text()
    for body in (hp, pp): assert "FS_EOF_" not in body
    return ("set -eu\numask 022\ninstall -d -m 0755 -o root -g root %(l)s %(p)s\n"
            "cat > %(l)s/fetchstudio-cal-helper <<'FS_EOF_HELPER'\n%(h)sFS_EOF_HELPER\n"
            "cat > %(p)s/%(pf)s <<'FS_EOF_POLICY'\n%(po)sFS_EOF_POLICY\n"
            "chown root:root %(l)s/fetchstudio-cal-helper %(p)s/%(pf)s\n"
            "chmod 0755 %(l)s/fetchstudio-cal-helper\nchmod 0644 %(p)s/%(pf)s\n") % dict(l=q(libexec), p=q(policydir), pf=POLICY_FILES[0], h=hp if hp.endswith("\n") else hp + "\n", po=pp if pp.endswith("\n") else pp + "\n")

def _admin(cmd, stdin_text=None, timeout=900):
    try: r = subprocess.run(cmd, input=stdin_text, capture_output=True, text=True, timeout=timeout, env=clean_env(), **({} if stdin_text is not None else {"stdin": subprocess.DEVNULL}))
    except subprocess.TimeoutExpired: return None, "It took too long and was stopped."
    except OSError as ex: return None, "Could not start pkexec: %s" % ex
    return r, ""

def _fail(r, what):
    if r.returncode in (126, 127): return False, "Authentication was cancelled or refused."
    tail = (r.stderr or r.stdout or "").strip().splitlines()[-3:]
    return False, "%s failed (exit %d).\n%s" % (what, r.returncode, "\n".join(tail))

def pkexec_available(): return shutil.which("pkexec") is not None

def setup_helper():
    """Install the helper and its polkit policy (one administrator prompt). -> (ok, message). Blocking: use a thread."""
    if not pkexec_available(): return False, "pkexec (polkit) is not installed on this system."
    r, err = _admin(["pkexec", "/bin/sh", "-s"], helper_script("install"))
    if r is None: return False, err
    if r.returncode == 0 and helper_installed(): return True, "The Fetch Studio helper is installed."
    return _fail(r, "Helper setup")

def remove_helper():
    if not pkexec_available(): return False, "pkexec (polkit) is not installed on this system."
    r, err = _admin(["pkexec", "/bin/sh", "-s"], helper_script("remove"))
    if r is None: return False, err
    if r.returncode == 0 and not helper_installed(): return True, "The Fetch Studio helper was removed."
    return _fail(r, "Removing the helper")

def cal_removable():
    """Offer 'Uninstall cal' only where cal is its own package (Debian family) AND the helper installed it."""
    return family() == "debian" and MARKER.exists() and have_cal()

def remove_cal():
    if not helper_installed(): return False, "The Fetch Studio helper is not installed."
    r, err = _admin(["pkexec", str(HELPER), "remove-cal"])
    if r is None: return False, err
    if r.returncode == 0 and not have_cal(): return True, "The cal command was removed."
    return _fail(r, "Removing cal")

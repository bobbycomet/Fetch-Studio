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
    try: r = subprocess.run(["pkexec", str(HELPER), "install"], capture_output=True, text=True, timeout=900, env=clean_env(), stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired: return False, "The installation took too long and was stopped."
    except OSError as ex: return False, "Could not start pkexec: %s" % ex
    if r.returncode == 0 and have_cal(): return True, "The cal command is now installed."
    if r.returncode in (126, 127): return False, "Authentication was cancelled or refused."
    tail = (r.stderr or r.stdout or "").strip().splitlines()[-3:]
    return False, "Installation failed (exit %d).\n%s" % (r.returncode, "\n".join(tail))

def extract_helper(dest):
    """Copy the helper files to a normal folder so they can be installed with `sudo sh install-helper.sh` (an AppImage's
    own files live in a mount that root cannot read)."""
    dest = Path(dest).expanduser(); dest.mkdir(parents=True, exist_ok=True)
    for f in HELPER_FILES:
        shutil.copy(RESOURCE_DIR / f, dest / f)
        if f != "io.github.bobbycomet.fetchstudio.policy": (dest / f).chmod(0o755)
    return dest

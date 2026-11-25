"""Shell snippets for every readout (shared by the live preview and the generated script)."""
from .common import *
from .specs import *

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
    "CPUTemp": r"""t=""; for z in /sys/class/hwmon/hwmon*; do case "$(cat "$z/name" 2>/dev/null)" in coretemp|k10temp|zenpower|cpu_thermal|cpu-thermal) t=$(cat "$z/temp1_input" 2>/dev/null); break;; esac; done
[ -z "$t" ] && t=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null)
[ -n "$t" ] && awk -v t="$t" 'BEGIN{printf "%.0f°C", t/1000}' || echo n/a""",
    "GPUTemp": r"""r=""; if command -v nvidia-smi >/dev/null 2>&1; then t=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader 2>/dev/null | head -1); [ -n "$t" ] && r="${t}°C"; fi
if [ -z "$r" ]; then for z in /sys/class/hwmon/hwmon*; do case "$(cat "$z/name" 2>/dev/null)" in amdgpu|nouveau|radeon) t=$(cat "$z/temp1_input" 2>/dev/null); [ -n "$t" ] && r=$(awk -v t="$t" 'BEGIN{printf "%.0f°C", t/1000}'); break;; esac; done; fi
echo "${r:-n/a}" """,
    "BIOS": r"""d=/sys/class/dmi/id; v="$(cat $d/bios_vendor 2>/dev/null) $(cat $d/bios_version 2>/dev/null)"; y=$(cat $d/bios_date 2>/dev/null); v=$(echo $v); echo "${v:-n/a}${y:+ ($y)}" """,
    "Board": r"""d=/sys/class/dmi/id; v=$(echo $(cat $d/board_vendor 2>/dev/null) $(cat $d/board_name 2>/dev/null)); echo "${v:-n/a}" """,
    "SuperIO": r"""r=""; for z in /sys/class/hwmon/hwmon*; do n=$(cat "$z/name" 2>/dev/null); case "$n" in nct*|it8*|w836*|w837*|f718*|f81*|sch5*|smsc*|dme1737|pc87*|vt1211|lm78|lm80|lm85|adt7*|max6*) r=$n; break;; esac; done; echo "${r:-n/a (driver not loaded)}" """,
    "Fans": r"""r=""; c=0; for f in /sys/class/hwmon/hwmon*/fan*_input; do [ -r "$f" ] || continue; v=$(cat "$f" 2>/dev/null); if [ "${v:-0}" -gt 0 ] 2>/dev/null && [ $c -lt 4 ]; then r="$r${r:+, }$v RPM"; c=$((c+1)); fi; done; echo "${r:-n/a}" """,
    "Chassis": r"""c=$(cat /sys/class/dmi/id/chassis_type 2>/dev/null); case "$c" in 8|9|10|14) r=Laptop;; 11) r=Handheld;; 30|31|32) r="Tablet / 2-in-1";; 3|4|5|6|7|15|16) r=Desktop;; 13) r="All-in-One";; 17|23|24|25|28) r=Server;; 35|36) r="Mini PC";; *) r="";; esac
[ -z "$r" ] && { ls /sys/class/power_supply/BAT* >/dev/null 2>&1 && r=Laptop || r=Desktop; }; echo "$r" """,
    "Init": r"""c=$(ps -p 1 -o comm= 2>/dev/null | tr -d ' '); [ -z "$c" ] && c=$(cat /proc/1/comm 2>/dev/null)
if [ "$c" = init ] || [ -z "$c" ]; then if [ -d /run/openrc ]; then c=OpenRC; elif [ -d /run/runit ] || [ -d /etc/runit ]; then c=runit; else c=SysVinit; fi; fi; echo "$c" """,
    "Procs": "ps -e -o pid= | wc -l | tr -d ' '",
    "PCT_Memory": r"""free | awk '/Mem:/{printf "%d",$3*100/$2}'""",
    "PCT_Disk": r"""df / | awk 'NR==2{gsub("%","",$5);print $5}'""",
    "PCT_CPU": r"""awk -v n="$(nproc)" '{p=$1*100/n; if(p>100)p=100; printf "%d",p}' /proc/loadavg""",
    "PCT_Swap": r"""free | awk '/Swap:/{if($2>0)printf "%d",$3*100/$2; else print 0}'""",
    "PCT_Battery": r"""for b in /sys/class/power_supply/BAT*; do [ -r "$b/capacity" ] && { cat "$b/capacity"; break; }; done"""}

CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "fetchstudio"

NET_TPL = r'''f="${XDG_CACHE_HOME:-$HOME/.cache}/fetchstudio/@TAG@"; mkdir -p "${f%/*}" 2>/dev/null
fetch(){ @FETCH@; }
failed(){ [ -e "$f.fail" ] && [ -z "$(find "$f.fail" -mmin +10 2>/dev/null)" ]; }
store(){ r=$(fetch); if [ -n "$r" ]; then printf '%s' "$r" > "$f"; rm -f "$f.fail"; else : > "$f.fail"; fi; }
if [ ! -s "$f" ]; then failed || store
elif [ -n "$(find "$f" -mmin +@TTL@ 2>/dev/null)" ] && ! failed; then ( store ) >/dev/null 2>&1 & fi
cat "$f" 2>/dev/null || echo n/a'''

def cached_net(tag, fetch, ttl=30):
    """Internet lookups. Cached on disk for ttl minutes; a stale value is shown instantly while a background refresh runs;
    after a failed lookup the network is not tried again for 10 minutes, so being offline never costs a wait on every new terminal
    (only the very first lookup can wait, at most 3 s). Offline with nothing cached shows n/a."""
    return NET_TPL.replace("@TAG@", tag).replace("@FETCH@", fetch).replace("@TTL@", str(ttl))

def wx_url(loc, units):
    from urllib.parse import quote
    u = {"metric": "&m", "imperial": "&u"}.get(units, "")
    return "https://wttr.in/%s?format=%%C%%7C%%t%%7C%%l%%7C%%S%%7C%%s%s" % (quote(loc.strip()), u)   # one request: cond|temp|place|sunrise|sunset

WX_AWK = {"Weather": '{print $1" "$2}', "Wx_Cond": "{print $1}", "Wx_Temp": "{print $2}", "Wx_Loc": "{print $3}",
          "Wx_Rise": "{print substr($4,1,5)}", "Wx_Set": "{print substr($5,1,5)}"}
def weather_item(loc, units, key):
    """Every weather item reads the same cached wttr.in answer, so any number of them costs one request per 30 minutes."""
    h = hashlib.md5((loc + units).encode()).hexdigest()[:8]
    fetch = 'r=$(curl -fsS -m 3 "' + wx_url(loc, units) + '" 2>/dev/null | head -c 200); case $r in *"|"*"|"*"|"*"|"*) printf "%s" "$r";; esac'
    awk = WX_AWK[key]
    if key == "Wx_Loc" and loc.strip(): awk = "{print ($3!=\"\"?$3:l)}"
    av = " -v l=" + shlex.quote(loc.strip()) if key == "Wx_Loc" and loc.strip() else ""
    return ("w=$(\n" + cached_net("wx_" + h, fetch) + "\n)\n"
            "case \"$w\" in n/a|\"\") echo n/a;; *) printf '%s' \"$w\" | awk -F'|'" + av + " '" + awk + "';; esac")

HUM = r'''function h(b,  i,u,f){split("B KiB MiB GiB TiB PiB",u," ");i=1;while(b>=1024&&i<6){b/=1024;i++};f=(i>2)?"%.1f %s":"%.0f %s";return sprintf(f,b,u[i])}'''
ROOTDISK = r'''src=$(findmnt -no SOURCE / 2>/dev/null | head -1); src=${src%%\[*}
dk=$(lsblk -nrs -o NAME,TYPE "$src" 2>/dev/null | awk '$2=="disk"{print $1; exit}')
'''
NETIF = r'''ifc=$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++)if($i=="dev"){print $(i+1);exit}}')
'''
NETRATE = NETIF + r'''st="${XDG_CACHE_HOME:-$HOME/.cache}/fetchstudio/netrate"; mkdir -p "${st%/*}" 2>/dev/null   # one 0.2 s sample, shared for 2 s by every net item
read -r t _ < /proc/uptime; pi=; pt=0; dr=; dx=
[ -r "$st" ] && read -r pi pt dr dx < "$st"
if [ -n "$ifc" ] && { [ "$pi" != "$ifc" ] || ! awk -v a="$t" -v b="$pt" 'BEGIN{exit !(a>=b && a-b<2)}'; }; then
  read -r r1 x1 < <(awk -v i="$ifc" '{sub(":"," ")} $1==i{print $2,$10}' /proc/net/dev); sleep 0.2
  read -r r2 x2 < <(awk -v i="$ifc" '{sub(":"," ")} $1==i{print $2,$10}' /proc/net/dev)
  read -r dr dx < <(awk -v a="${r1:-0}" -v b="${r2:-0}" -v c="${x1:-0}" -v d="${x2:-0}" 'BEGIN{printf "%d %d",(b-a)*5,(d-c)*5}')
  read -r t _ < /proc/uptime; printf '%s %s %s %s\n' "$ifc" "$t" "$dr" "$dx" > "$st" 2>/dev/null
fi
'''
NETSPEED = r'''if [ -d /sys/class/net/$ifc/wireless ]; then sp=$(iw dev "$ifc" link 2>/dev/null | awk '/@DIR@ bitrate/{printf "%d",$3; exit}'); else sp=$(cat /sys/class/net/$ifc/speed 2>/dev/null); fi
[ "${sp:-0}" -gt 0 ] 2>/dev/null && [ -n "$@VAR@" ] && awk -v r="$@VAR@" -v s="$sp" 'BEGIN{p=r*8/(s*1000000)*100; if(p>100)p=100; printf "%d",p}'
'''

SH.update({
    "Weather": weather_item("", "auto", "Weather"),
    **{k: weather_item("", "auto", k) for k in ("Wx_Cond", "Wx_Temp", "Wx_Loc", "Wx_Rise", "Wx_Set")},
    # --- Clock (cheap, live)
    "Clock_Time": "date +%H:%M", "Clock_Date": "date '+%a %d %b %Y'", "Clock_TZ": "date '+%Z (UTC%:z)'",
    "Clock_Week": "echo $((10#$(date +%V)))",
    **{"Cal%d" % i: "cal 2>/dev/null | sed -n '%dp' | grep . || echo ' '" % (i + 1) for i in range(8)},
    # --- Storage (everything is about the drive that holds /)
    "Stor_FS": "findmnt -no FSTYPE / 2>/dev/null | head -1",
    "Stor_Mount": ROOTDISK + '[ -n "$src" ] && echo "/ ($src)"',
    "Stor_Type": ROOTDISK + r'''case "$dk" in "") r="";; nvme*) r="NVMe SSD";; mmcblk*) r="eMMC / SD";; vd*|xvd*) r=Virtual;;
  *) case "$(cat /sys/block/$dk/queue/rotational 2>/dev/null)" in 0) r=SSD;; 1) r=HDD;; *) r="";; esac;; esac; echo "$r"''',
    "Stor_Model": ROOTDISK + r'''[ -n "$dk" ] && echo $(cat /sys/block/$dk/device/model 2>/dev/null)''',
    "Stor_Temp": ROOTDISK + r"""t=$(cat /sys/block/$dk/device/hwmon*/temp1_input 2>/dev/null | head -1)
[ -n "$t" ] && awk -v t="$t" 'BEGIN{printf "%.0f°C", t/1000}'""",
    "Stor_IO": ROOTDISK + r'''awk -v d="$dk" '@HUM@ $3==d{R=$6*512;W=$10*512;f=1} END{if(f)printf "R %s / W %s (since boot)",h(R),h(W)}' /proc/diskstats'''.replace("@HUM@", HUM),
    "Stor_Total": "df -lP -B1 -x tmpfs -x devtmpfs -x squashfs -x overlay -x efivarfs -x ramfs -x iso9660 2>/dev/null | awk '" + HUM +
                  " NR>1 && !s[$1]++ {t+=$2;a+=$4} END{if(t)printf \"%s free of %s\",h(a),h(t)}'",
    # --- Network (the interface that carries the default route)
    "Net_If": NETIF + 'echo "$ifc"',
    "Net_Type": NETIF + r'''n=$ifc; case $n in "") r="";; wg*|tun*|tap*|tailscale*|ppp*|nordlynx|proton*|mullvad*|zt*) r=VPN;;
  *) if [ -d /sys/class/net/$n/wireless ]; then r=Wi-Fi; elif [ -d /sys/class/net/$n/bridge ]; then r=Bridge
     elif [ "$(cat /sys/class/net/$n/type 2>/dev/null)" = 1 ]; then r=Ethernet; else r=""; fi;; esac; echo "$r"''',
    "Net_SSID": NETIF + r'''s=""; if [ -d /sys/class/net/$ifc/wireless ]; then s=$(iwgetid -r 2>/dev/null)
  [ -z "$s" ] && s=$(nmcli -t -f active,ssid dev wifi 2>/dev/null | awk -F: '$1=="yes"{print $2;exit}')
  [ -z "$s" ] && s=$(iw dev "$ifc" link 2>/dev/null | awk -F': ' '/SSID/{print $2;exit}'); fi; echo "$s"''',
    "Net_Speed": NETIF + r'''if [ -d /sys/class/net/$ifc/wireless ]; then v=$(iw dev "$ifc" link 2>/dev/null | awk '/tx bitrate/{print $3, $4; exit}')
else sp=$(cat /sys/class/net/$ifc/speed 2>/dev/null); [ "${sp:-0}" -gt 0 ] 2>/dev/null && v="$sp Mb/s"; fi; echo "$v"''',
    "Net_Public": 'w=$(\n' + cached_net("pubip", 'r=$(curl -fsS -m 3 https://api.ipify.org 2>/dev/null | head -c 64); case $r in ""|*[!0-9a-fA-F:.]*) ;; *) printf "%s" "$r";; esac') + '\n)\necho "$w"',
    "Net_VPN": r'''command -v ip >/dev/null 2>&1 && { v=$(ip -o link show up 2>/dev/null | awk -F': ' '{print $2}' | sed 's/@.*//' | grep -E '^(wg|tun|tap|tailscale|ppp|nordlynx|proton|mullvad|zt)' | head -1)
  if [ -n "$v" ]; then echo "Active ($v)"; else echo Off; fi; }''',
    "Net_Rate": NETRATE + '[ -n "$dr" ] && awk -v a="$dr" -v b="$dx" \'' + HUM + ' BEGIN{printf "↓ %s/s  ↑ %s/s",h(a),h(b)}\'',
    # --- Hardware identity
    "HW_Arch": "uname -m",
    "HW_Microcode": r'''awk -F': ' '/^microcode/{print $2; exit}' /proc/cpuinfo''',
    "HW_RAM": r"""command -v dmidecode >/dev/null 2>&1 && dmidecode -t 17 2>/dev/null | awk -F': ' '/^[ \t]*Type: /&&$2!~/Unknown|Other|Empty/{t=$2} /^[ \t]*Configured (Memory|Clock) Speed: /&&$2!~/Unknown/{s=$2} /^[ \t]*Speed: /&&$2!~/Unknown/&&!s2{s2=$2} END{if(t)print t, (s?s:s2)}'""",
    "HW_Driver": r'''d=""; if command -v nvidia-smi >/dev/null 2>&1; then v=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1); [ -n "$v" ] && d="nvidia $v"; fi
[ -z "$d" ] && d=$(lspci -k 2>/dev/null | awk '/^[^ \t]/{f=($0 ~ /VGA|3D controller|Display controller/)} f&&/Kernel driver in use:/{print $NF; exit}')
echo "$d"''',
    "HW_VRAM": r'''r=""; command -v nvidia-smi >/dev/null 2>&1 && r=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader 2>/dev/null | head -1)
if [ -z "$r" ]; then for f in /sys/class/drm/card*/device/mem_info_vram_total; do [ -r "$f" ] || continue; b=$(cat "$f" 2>/dev/null)
  if [ "${b:-0}" -gt 0 ] 2>/dev/null; then r=$(awk -v b="$b" 'BEGIN{printf "%.0f MiB", b/1048576}'); break; fi; done; fi; echo "$r"''',
    "HW_PCI": "ls /sys/bus/pci/devices 2>/dev/null | wc -l",
    # --- Services (systemd; other init systems show n/a for the counts)
    "Svc_Init": r'''c=$(ps -p 1 -o comm= 2>/dev/null | tr -d ' '); case "$c" in systemd) systemctl --version 2>/dev/null | awk 'NR==1{print $1, $2}';;
  *) if command -v openrc >/dev/null 2>&1; then openrc --version 2>/dev/null | awk 'NR==1{print "OpenRC", $3}'; else echo "$c"; fi;; esac''',
    "Svc_Running": "command -v systemctl >/dev/null 2>&1 && systemctl list-units --type=service --state=running --no-legend --plain 2>/dev/null | grep -c .",
    "Svc_Failed": "command -v systemctl >/dev/null 2>&1 && systemctl list-units --type=service --state=failed --no-legend --plain 2>/dev/null | grep -c .",
    "Svc_Targets": r'''command -v systemctl >/dev/null 2>&1 && { l=$(systemctl list-units --type=target --state=active --no-legend --plain 2>/dev/null | awk '{sub(/\.target$/,"",$1);print $1}')
  if [ -n "$l" ]; then n=$(echo "$l" | wc -l); k=$(echo "$l" | grep -xE 'graphical|multi-user|network-online|rescue|emergency|sleep|suspend|hibernate' | paste -sd, - | sed 's/,/, /g'); echo "${k:+$k }($n active)"; fi; }''',
    "Svc_Boot": r'''uptime -s 2>/dev/null || date -d "@$(awk '/^btime/{print $2}' /proc/stat)" '+%Y-%m-%d %H:%M:%S' 2>/dev/null''',
    # --- Live meters (percent). Nothing here is cached.
    "PCT_CPUFreq": r"""c=/sys/devices/system/cpu; paste -d' ' <(cat $c/cpu[0-9]*/cpufreq/scaling_cur_freq 2>/dev/null) <(cat $c/cpu[0-9]*/cpufreq/cpuinfo_max_freq 2>/dev/null) | awk '{a+=$1;m+=$2} END{if(m>0)printf "%d",a*100/m}'""",
    "PCT_GPU": r'''r=""; command -v nvidia-smi >/dev/null 2>&1 && r=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' ')
if [ -z "$r" ]; then for f in /sys/class/drm/card*/device/gpu_busy_percent; do [ -r "$f" ] && { r=$(cat "$f" 2>/dev/null); break; }; done; fi; echo "$r"''',
    "PCT_NetDown": NETRATE + NETSPEED.replace("@DIR@", "rx").replace("@VAR@", "dr"),
    "PCT_NetUp": NETRATE + NETSPEED.replace("@DIR@", "tx").replace("@VAR@", "dx")})

"""Graphics-protocol logos (kitty / iTerm2 / sixel)."""
from .common import *
from .specs import *
from .readouts import *
from .system import *
from .security import *
from .logos import *
from .validation import *
from .model import *
from .render import *


# ------------------------------------------------------------------ graphics-protocol logos (kitty / iTerm2 / sixel)
# Like fastfetch's logo types: real pixels where the terminal supports them, block characters everywhere else.
# kitty + iTerm2 are sized in cells (exact fit); sixel is sized in pixels, so a few widths are pre-built and the script
# picks the closest one to the terminal's real cell size.
GFX_MODES = ("auto", "kitty", "iterm", "sixel")
SIXV = (8, 10, 12, 16, 20)               # sixel variants: pixels per cell column
GFXCACHE = {}
SIX_TR = bytes((i + 63) & 0xFF for i in range(256)); SIX_RLE = re.compile(rb"(.)\1{3,}", re.S)

def png_bytes(img):
    ba = QByteArray(); buf = QBuffer(ba); buf.open(QIODevice.OpenModeFlag.WriteOnly); img.save(buf, "PNG"); buf.close(); return bytes(ba)

def gfx_images(path, cols):
    """Frames at the pixel size sent to the terminal (also used by the preview). GIFs are sampled across the whole loop."""
    key = (str(path), path.stat().st_mtime, cols)
    if key in GFXCACHE: return GFXCACHE[key]
    mv = QMovie(str(path)); src = []
    if mv.isValid() and mv.frameCount() > 1:
        fc = mv.frameCount(); n = min(fc, 36)
        for k in range(n): mv.jumpToFrame(k * fc // n); src.append(mv.currentImage())
    else: src = [QImage(str(path))]
    src = [i for i in src if not i.isNull() and i.width() > 0]; out = []
    tw = min(cols * 10, 480 if len(src) > 1 else 900)
    for im in src:
        w = min(tw, im.width()); h = max(1, round(im.height() * w / im.width()))
        out.append(downscale(im, w, h) if w < im.width() else im.convertToFormat(QImage.Format.Format_ARGB32))
    GFXCACHE[key] = out; return out

def kitty_seq(png, cols, rows, iid=24751):
    """kitty graphics protocol: PNG in <=4096-byte base64 chunks, placed at the cursor over cols x rows cells. q=2 = no replies, C=1 = don't move cursor."""
    b = base64.b64encode(png).decode(); parts = [b[i:i + 4096] for i in range(0, len(b), 4096)] or [""]; out = []
    for n, ch in enumerate(parts):
        m = 1 if n < len(parts) - 1 else 0
        ctl = "a=T,f=100,t=d,q=2,i=%d,p=1,c=%d,r=%d,C=1,m=%d" % (iid, cols, rows, m) if n == 0 else "q=2,m=%d" % m
        out.append("\033_G%s;%s\033\\" % (ctl, ch))
    return "".join(out)

def iterm_seq(raw, cols, rows):
    return "\033]1337;File=inline=1;size=%d;width=%d;height=%d;preserveAspectRatio=0:%s\a" % (len(raw), cols, rows, base64.b64encode(raw).decode())

def sixel_seq(img):
    """Sixel: palette-quantised (Qt), transparent pixels left untouched so the terminal background shows through."""
    W, H = img.width(), img.height(); a = img.convertToFormat(QImage.Format.Format_ARGB32)
    sa = a.bytesPerLine(); ar = bytes(a.constBits().asstring(a.sizeInBytes()))
    flat = QImage(W, H, QImage.Format.Format_RGB32); flat.fill(QColor("#000000")); p = QPainter(flat); p.drawImage(0, 0, a); p.end()
    q = flat.convertToFormat(QImage.Format.Format_Indexed8, Qt.ImageConversionFlag.DiffuseDither)
    sq = q.bytesPerLine(); qb = bytes(q.constBits().asstring(q.sizeInBytes())); table = q.colorTable(); used = set(); body = []
    for y0 in range(0, H, 6):
        d = {}
        for x in range(W):
            for dy in range(min(6, H - y0)):
                y = y0 + dy
                if ar[y * sa + 4 * x + 3] < 128: continue
                d.setdefault(qb[y * sq + x], bytearray(W))[x] |= 1 << dy
        for ci, bits in d.items():
            used.add(ci); line = bytes(bits).translate(SIX_TR).rstrip(b"?")
            body.append(b"#%d" % ci + SIX_RLE.sub(lambda m: b"!%d%c" % (len(m[0]), m[1][0]), line) + b"$")
        body.append(b"-")
    pal = b"".join(b"#%d;2;%d;%d;%d" % (i, round(QColor(table[i]).red() * 100 / 255), round(QColor(table[i]).green() * 100 / 255),
                                         round(QColor(table[i]).blue() * 100 / 255)) for i in sorted(used))
    return b"\033P0;1;0q" + b'"1;1;%d;%d' % (W, H) + pal + b"".join(body) + b"\033\\"

def gfx_assets(c):
    """-> ({filename: bytes}, meta) for the build. Nothing is baked into the script itself, so it stays small and fast to start."""
    g = c["gfx"]; mode, cols, rows, path = g["mode"], g["cols"], g["rows"], g["path"]
    files, meta = {}, dict(have=[], nk=1, sxv=[], sxw=[], sxh=[]); imgs = gfx_images(path, cols)
    if not imgs: return {}, None
    if mode in ("auto", "kitty"):
        for k, im in enumerate(imgs): files["kitty_%d" % k] = kitty_seq(png_bytes(im), cols, rows)
        meta["nk"] = len(imgs); meta["have"].append("kitty")
    if mode in ("auto", "iterm"):       # a GIF is handed over as-is so the terminal animates it by itself (like fastfetch's iterm type)
        raw = path.read_bytes() if len(imgs) > 1 and path.suffix.lower() == ".gif" and path.stat().st_size <= 8_000_000 else png_bytes(imgs[0])
        files["iterm"] = iterm_seq(raw, cols, rows); meta["have"].append("iterm")
    if mode in ("auto", "sixel"):       # first frame only
        src = QImage(str(path)).convertToFormat(QImage.Format.Format_ARGB32)
        for cw in SIXV:
            pw = cols * cw
            if pw > 1600: continue
            ph = max(1, round(pw * src.height() / src.width()))
            im = downscale(src, pw, ph) if pw < src.width() else src.scaled(pw, ph, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
            files["six_%d" % cw] = sixel_seq(im); meta["sxv"].append(cw); meta["sxw"].append(pw); meta["sxh"].append(ph)
        if meta["sxv"]: meta["have"].append("sixel")
    if not meta["have"]: return {}, None
    return {k: (v.encode("ascii") if isinstance(v, str) else v) for k, v in files.items()}, meta

GFX_SH = r"""G=__G__; GMODE=__GMODE__; HAVE=__HAVE__; GAP=__GAP__; COLS=__COLS__; ROWS=__ROWS__; NK=__NK__; LIFE=__LIFE__; LOOPS=__LOOPS__; DELAY=__DELAY__
SXV=(__SXV__); SXW=(__SXW__); SXH=(__SXH__)
SAVE=$'\033'7; REST=$'\033'8
have(){ case " $HAVE " in *" $1 "*) return 0;; esac; return 1; }
gfx_proto(){   # which graphics protocol does THIS terminal speak? sets GP, or fails -> block characters
  GP=; [ -t 1 ] || return 1
  case $GMODE in kitty|iterm|sixel) have "$GMODE" && GP=$GMODE; [ -n "$GP" ]; return;; esac
  [ -n "$TMUX$STY" ] && return 1
  if have kitty && { [ -n "$KITTY_WINDOW_ID" ] || [ "$TERM" = xterm-kitty ] || [ "$TERM" = xterm-ghostty ] || [ "$TERM_PROGRAM" = ghostty ] || [ "$TERM_PROGRAM" = WezTerm ]; }; then GP=kitty; return 0; fi
  if have iterm && [ "$TERM_PROGRAM" = iTerm.app ]; then GP=iterm; return 0; fi
  have sixel || return 1
  case $TERM in linux|dumb|"") return 1;; esac
  [ -r /dev/tty ] || return 1
  local r; printf '\033[c' >/dev/tty; IFS= read -rs -d c -t 0.4 r </dev/tty || return 1      # DA1 reply lists 4 when sixel is supported
  case ";${r#*\?};" in *";4;"*) GP=sixel; return 0;; esac
  return 1
}
gfx_size(){    # image size in cells (kitty/iTerm2: fixed; sixel: from the terminal's real cell size)
  GCOLS=$COLS; GROWS=$ROWS; GFILE=
  [ "$GP" = sixel ] || return 0
  local cw=10 ch=20 a= b= e v=0 best=999 d i
  if [ -r /dev/tty ]; then printf '\033[16t' >/dev/tty; IFS=';' read -rs -d t -t 0.4 e a b </dev/tty 2>/dev/null; fi
  [[ $a =~ ^[0-9]+$ && $b =~ ^[0-9]+$ ]] && ((a>0 && b>0)) && { ch=$a; cw=$b; }
  for i in "${!SXV[@]}"; do d=$((cw-SXV[i])); ((d<0)) && d=$((-d)); ((d<best)) && { best=$d; v=$i; }; done
  GFILE=six_${SXV[v]}; GCOLS=$(( (SXW[v]+cw-1)/cw )); GROWS=$(( (SXH[v]+ch-1)/ch ))
}
gfx_emit(){ case $GP in kitty) cat "$G/kitty_$1";; iterm) cat "$G/iterm";; sixel) cat "$G/$GFILE";; esac; }
gfx_anim(){    # kitty only: re-send frames at the same spot until the first command runs (intro: LOOPS times)
  local sp=$PPID
  (
    idle(){ local s; s=$(</proc/$sp/stat) 2>/dev/null || return 1; s=${s##*) }; set -- $s; [ "$3" = "$6" ]; }
    for _i in $(seq 20); do idle && break; sleep 0.1; done
    k=1; n=0
    while kill -0 "$sp" 2>/dev/null && idle && { [ "$LIFE" = live ] || ((n<NK*LOOPS)); }; do
      printf '%s\033[%d;1H' "$SAVE" "$top"; cat "$G/kitty_$((k%NK))"; printf '%s' "$REST"; k=$((k+1)); n=$((n+1)); sleep $DELAY
    done
    if [ "$LIFE" != live ] && kill -0 "$sp" 2>/dev/null && idle; then printf '%s\033[%d;1H' "$SAVE" "$top"; cat "$G/kitty_0"; printf '%s' "$REST"; fi
  ) >/dev/tty 2>/dev/null &
  disown 2>/dev/null
}
gfx_main(){
  local n=${#INFO[@]} H=$GROWS i off row e c; top=
  off=$((GCOLS+GAP)); ((n>H)) && H=$n
  for ((i=0;i<H;i++)); do printf '\n'; done; printf '\033[%dA' "$H"             # reserve the lines, back to the top
  if [ "$GP" = kitty ] && ((NK>1)) && [ -r /dev/tty ]; then
    printf '\033[6n' >/dev/tty; IFS='[;' read -rs -d R -t 1 e row c </dev/tty && top=$row
  fi
  printf '%s' "$SAVE"; gfx_emit 0; printf '%s' "$REST"                          # image at the top-left, cursor restored
  for ((i=0;i<n;i++)); do printf '\033[%dC%s\033[0m\n' "$off" "${INFO[i]}"; done
  for ((i=n;i<H;i++)); do printf '\n'; done
  [[ $top =~ ^[0-9]+$ ]] && gfx_anim
  return 0
}
if gfx_proto; then gfx_size; gfx_main; exit 0; fi"""

"""Shared widgets: header label and the cell-exact terminal preview."""
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
from .compiler import *
from .build import *
from .caltool import *


# ------------------------------------------------------------------ terminal preview (cell-exact painter)
class TermView(QWidget):
    def __init__(s):
        super().__init__(); s.rows = []; s.bg = "#1e1e1e"; s.fg = "#d0d0d0"; s.title = "Terminal"; s.fsize = 11; s.overlay = None
        s.setMinimumSize(460, 320)
    def set(s, rows, bg, fg, title, fsize, overlay=None):      # overlay = (QImage, cols, rows): a graphics-protocol logo painted over the blank cells
        s.rows, s.bg, s.fg, s.title, s.fsize, s.overlay = rows, bg, fg, title, fsize, overlay; s.update()
    def col(s, c): return QColor(PAL[int(c[1:])]) if c[0] == "a" else QColor(c)
    def paintEvent(s, e):
        p = QPainter(s); f = QFont("Monospace", s.fsize); f.setStyleHint(QFont.StyleHint.Monospace); f.setFixedPitch(True)
        fm = QFontMetricsF(f); cw, ch, asc = fm.horizontalAdvance("M"), float(round(fm.height())), fm.ascent()
        bar = 28; p.fillRect(s.rect(), QColor("#2b2b2b")); p.fillRect(0, 0, s.width(), bar, QColor("#3c3c3c"))
        p.setFont(QFont("Sans", 9)); p.setPen(QColor("#ddd"))
        p.drawText(QRectF(0, 0, s.width(), bar), Qt.AlignmentFlag.AlignCenter, s.title)
        for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")): p.setBrush(QColor(c)); p.setPen(Qt.PenStyle.NoPen); p.drawEllipse(10 + i * 18, 9, 11, 11)
        p.fillRect(0, bar, s.width(), s.height() - bar, QColor(s.bg))
        user, host = os.environ.get("USER", "user"), platform.node()
        prompt = [R(f"{user}@{host}", "a10", None, True), R(":"), R("~", "a12", None, True), R("$ ")]
        maxc = max((rlen(r) for r in s.rows), default=0); nrows = len(s.rows) + 1
        sc = min(1.0, (s.width() - 20) / max(1.0, maxc * cw), (s.height() - bar - 16) / max(1.0, nrows * ch))
        p.translate(10, bar + 8); p.scale(sc, sc); x0, y0 = 0, 0; x = y = 0
        if s.overlay:
            im, oc, orr = s.overlay; p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            p.drawImage(QRectF(0, 0, oc * cw, orr * ch), im)
        for y, row in enumerate(list(s.rows) + [prompt]):
            x = x0; ty = y0 + y * ch
            for t, fg, bg, b in row:
                col = s.col(fg or s.fg); f.setBold(b); p.setFont(f)
                for c in t:
                    ix, iy = round(x), round(ty); iw, ih = round(x + cw) - ix, round(ty + ch) - iy; hm = round(ty + ch / 2) - iy
                    if bg: p.fillRect(QRect(ix, iy, iw, ih), s.col(bg))
                    q = QUAD.get(c)
                    if q == 15: p.fillRect(QRect(ix, iy, iw, ih), col)
                    elif q:                                              # half / quadrant blocks, drawn cell-exact
                        hw = round(x + cw / 2) - ix
                        for bit, rx, ry, rw, rh in ((1, ix, iy, hw, hm), (2, ix + hw, iy, iw - hw, hm),
                                                    (4, ix, iy + hm, hw, ih - hm), (8, ix + hw, iy + hm, iw - hw, ih - hm)):
                            if q & bit: p.fillRect(QRect(rx, ry, rw, rh), col)
                    elif c != " ": p.setPen(col); p.drawText(QPointF(x, ty + asc), c)
                    x += cw
        p.fillRect(QRectF(x, y0 + y * ch, cw, ch), QColor(s.fg))

def hdr(t): l = QLabel(t); l.setObjectName("h"); return l

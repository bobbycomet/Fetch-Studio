"""ASCII Designer tab."""
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
from .widgets import *
from .graphitems import *
from .inspector import *


# ------------------------------------------------------------------ ASCII designer
GLYPHS = {
    "ASCII": [chr(c) for c in range(33, 127)],
    "Box drawing": [chr(c) for c in range(0x2500, 0x2580)],
    "Blocks & shades": [chr(c) for c in range(0x2580, 0x25A0)],
    "Geometric": [chr(c) for c in range(0x25A0, 0x2600)],
    "Arrows": [chr(c) for c in range(0x2190, 0x2200)],
    "Symbols": [chr(c) for c in range(0x2600, 0x2640)] + [chr(c) for c in range(0x2700, 0x2740)],
    "Braille": [chr(c) for c in range(0x2800, 0x2900)],
    "Math & misc": list("±×÷∞≈≠≤≥∑√∂∆∫°•·…§¶©®™€£¥¢µπΩαβγδλΣ∴∵⊕⊗⌘⌥⏎⎈"),
}
STARTERS = {
    "Cat": [r" /\_/\  ", r"( o.o ) ", r" > ^ <  "],
    "Tux": LOGOS["tux"], "Arch-style": LOGOS["arch"],
    "Heart": ["  _   _  ", r" / \_/ \ ", r" \     / ", r"  \   /  ", r"   \ /   ", "    v    "],
    "Rocket": ["    ^    ", r"   / \   ", "  |   |  ", "  | O |  ", r" /|   |\ ", r"/_|___|_\ ", r"   /_\   "],
    "Computer": [" .----------. ", " | > _      | ", " |          | ", " '----------' ", "   _|____|_   ", r"  /________\  "],
    "Mug": ["   ( (    ", "    ) )   ", "  ........ ", "  |      |]", r"  \      / ", "   `----'  "],
    "Mountains": ["      /\\        ", r"     /  \    /\  ", r"    /    \  /  \ ", r" /\/  /\  \/    \ ", r"/  \_/  \__/\____\ "],
    "Blank 24x10": [" " * 24] * 10}

class GlyphList(QListWidget):
    def __init__(s):
        super().__init__(); s.setViewMode(QListWidget.ViewMode.IconMode); s.setResizeMode(QListWidget.ResizeMode.Adjust)
        s.setGridSize(QSize(34, 34)); s.setMovement(QListWidget.Movement.Static); s.setDragEnabled(True)
        s.setDragDropMode(QListWidget.DragDropMode.DragOnly); s.setFont(QFont("Monospace", 14)); s.setUniformItemSizes(True)
    def mimeData(s, items): m = QMimeData(); m.setText(items[0].text()); return m

class DesignCanvas(QWidget):
    changed = pyqtSignal(); dropped = pyqtSignal(); picked = pyqtSignal(str)
    M = 10
    def __init__(s):
        super().__init__(); s.setAcceptDrops(True); s.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        s.tool, s.glyph, s.color = "draw", "#", "#3daee9"; s.mode, s.stops, s.direction = "solid", ["#3daee9"], "horizontal"
        s.sel = s.lift = s.start = None; s.off = (0, 0); s.cur = (0, 0); s.undo, s.redo = [], []; s.drops = 0
        s.font = QFont("Monospace", 14); s.font.setStyleHint(QFont.StyleHint.Monospace); fm = QFontMetricsF(s.font)
        s.cw, s.chh, s.asc = fm.horizontalAdvance("M"), float(round(fm.height())), fm.ascent(); s.set_grid(new_logo())
    W = property(lambda s: len(s.rows[0]) if s.rows else 0)
    H = property(lambda s: len(s.rows))
    def set_grid(s, d):
        s.rows = [list(r) for r in d["rows"]]
        s.cols = [list(r) for r in d["cells"]] if d.get("cells") else [[""] * d["w"] for _ in s.rows]
        s.sel = s.lift = None; s.undo.clear(); s.redo.clear(); s.fit()
    def fit(s): s.setMinimumSize(int(s.W * s.cw + 2 * s.M), int(s.H * s.chh + 2 * s.M)); s.update()
    def state(s): return ([r[:] for r in s.rows], [r[:] for r in s.cols])
    def snap(s): s.undo = (s.undo + [s.state()])[-100:]; s.redo.clear()
    def restore(s, st): s.rows, s.cols = [r[:] for r in st[0]], [r[:] for r in st[1]]; s.fit(); s.changed.emit()
    def do_undo(s):
        if s.undo: s.redo.append(s.state()); s.restore(s.undo.pop())
    def do_redo(s):
        if s.redo: s.undo.append(s.state()); s.restore(s.redo.pop())
    def resize_grid(s, w, h):
        s.snap(); s.rows = [(r + [" "] * w)[:w] for r in s.rows[:h]] + [[" "] * w for _ in range(h - len(s.rows))]
        s.cols = [(r + [""] * w)[:w] for r in s.cols[:h]] + [[""] * w for _ in range(h - len(s.cols))]; s.fit(); s.changed.emit()
    def cell(s, pos, clamp=False):
        x, y = int((pos.x() - s.M) // s.cw), int((pos.y() - s.M) // s.chh)
        if clamp: return (min(max(x, 0), s.W - 1), min(max(y, 0), s.H - 1))
        return (x, y) if 0 <= x < s.W and 0 <= y < s.H else None
    def col(s, x, y):
        if s.mode == "cells" and s.cols[y][x]: return s.cols[y][x]
        if s.mode == "gradient": return grad(s.stops, posf(x, y, s.W, s.H, s.direction if s.direction != "none" else "horizontal"))
        return s.stops[0] if s.stops else "#dddddd"
    def put(s, x, y, ch=None, col=None):
        if ch is not None: s.rows[y][x] = ch
        if col is not None: s.cols[y][x] = col
    def apply(s, x, y):
        if s.tool == "draw": s.put(x, y, s.glyph, s.color if s.mode == "cells" else None)
        elif s.tool == "erase": s.put(x, y, " ", "")
        elif s.tool == "paint": s.put(x, y, None, s.color)
        s.changed.emit()
    def lift_sel(s):
        r = s.sel; xs, ys = range(r.left(), r.right() + 1), range(r.top(), r.bottom() + 1)
        s.lift = ([[s.rows[y][x] for x in xs] for y in ys], [[s.cols[y][x] for x in xs] for y in ys])
        for y in ys:
            for x in xs: s.rows[y][x] = " "; s.cols[y][x] = ""
    def mousePressEvent(s, e):
        s.setFocus(); c = s.cell(e.position(), clamp=s.tool == "select")
        if not c or e.button() != Qt.MouseButton.LeftButton: return
        s.cur = c; x, y = c
        if s.tool == "select":
            if s.sel and s.sel.contains(x, y): s.snap(); s.lift_sel(); s.start = c; s.off = (0, 0)
            else: s.sel = QRect(x, y, 1, 1); s.start = c; s.lift = None
        elif s.tool == "pick":
            s.glyph = s.rows[y][x]; s.color = s.cols[y][x] or s.color; s.picked.emit(s.glyph)
        else: s.snap(); s.apply(x, y)
        s.update()
    def mouseMoveEvent(s, e):
        if not (e.buttons() & Qt.MouseButton.LeftButton): return
        c = s.cell(e.position(), clamp=s.tool == "select")
        if not c: return
        if s.tool == "select" and s.start:
            if s.lift: s.off = (c[0] - s.start[0], c[1] - s.start[1])
            else: s.sel = QRect(min(c[0], s.start[0]), min(c[1], s.start[1]), abs(c[0] - s.start[0]) + 1, abs(c[1] - s.start[1]) + 1)
        elif s.tool in ("draw", "erase", "paint"): s.cur = c; s.apply(*c)
        s.update()
    def mouseReleaseEvent(s, e):
        if s.lift:
            r = s.sel; ox, oy = s.off
            for dy, (rr, cc) in enumerate(zip(*s.lift)):
                for dx, (ch, co) in enumerate(zip(rr, cc)):
                    tx, ty = r.left() + dx + ox, r.top() + dy + oy
                    if ch != " " and 0 <= tx < s.W and 0 <= ty < s.H: s.rows[ty][tx] = ch; s.cols[ty][tx] = co
            s.sel = r.translated(ox, oy); s.lift = None; s.off = (0, 0); s.changed.emit()
        s.start = None; s.update()
    def dragEnterEvent(s, e):
        if e.mimeData().hasText(): e.acceptProposedAction()
    dragMoveEvent = dragEnterEvent
    def dropEvent(s, e):
        c = s.cell(e.position())
        if c and e.mimeData().text():
            s.snap(); s.put(c[0], c[1], e.mimeData().text()[0], s.color if s.mode == "cells" else None)
            s.drops += 1; s.cur = c; s.dropped.emit(); s.changed.emit(); s.update(); e.acceptProposedAction()
    def keyPressEvent(s, e):
        k, m = e.key(), e.modifiers(); x, y = s.cur
        if m & Qt.KeyboardModifier.ControlModifier:
            if k == Qt.Key.Key_Z: s.do_undo()
            elif k == Qt.Key.Key_Y: s.do_redo()
            else: super().keyPressEvent(e)
            return
        arrows = {Qt.Key.Key_Left: (-1, 0), Qt.Key.Key_Right: (1, 0), Qt.Key.Key_Up: (0, -1), Qt.Key.Key_Down: (0, 1)}
        if k in arrows: s.cur = (min(max(x + arrows[k][0], 0), s.W - 1), min(max(y + arrows[k][1], 0), s.H - 1))
        elif k == Qt.Key.Key_Delete and s.sel:
            s.snap()
            for yy in range(s.sel.top(), s.sel.bottom() + 1):
                for xx in range(s.sel.left(), s.sel.right() + 1): s.rows[yy][xx] = " "; s.cols[yy][xx] = ""
            s.changed.emit()
        elif k == Qt.Key.Key_Backspace: s.snap(); x = max(0, x - 1); s.put(x, y, " ", ""); s.cur = (x, y); s.changed.emit()
        elif k in (Qt.Key.Key_Return, Qt.Key.Key_Enter): s.cur = (0, min(s.H - 1, y + 1))
        elif e.text() and e.text().isprintable():
            s.snap(); s.put(x, y, e.text()[0], s.color if s.mode == "cells" else None); s.cur = (min(s.W - 1, x + 1), y); s.changed.emit()
        else: super().keyPressEvent(e); return
        s.update()
    def glyph_at(s, p, x, y, ch, col):
        rx, ry = s.M + x * s.cw, s.M + y * s.chh; c = QColor(col)
        if ch == "█": p.fillRect(QRectF(rx, ry, s.cw, s.chh), c)
        elif ch == "▀": p.fillRect(QRectF(rx, ry, s.cw, s.chh / 2), c)
        elif ch == "▄": p.fillRect(QRectF(rx, ry + s.chh / 2, s.cw, s.chh / 2), c)
        else: p.setPen(c); p.drawText(QPointF(rx, ry + s.asc), ch)
    def paintEvent(s, e):
        p = QPainter(s); p.fillRect(s.rect(), QColor("#0e1218")); p.setFont(s.font); M = s.M
        p.fillRect(QRectF(M, M, s.W * s.cw, s.H * s.chh), QColor("#161c26")); p.setPen(QPen(QColor("#202a38"), 1))
        for x in range(s.W + 1): p.drawLine(int(M + x * s.cw), M, int(M + x * s.cw), int(M + s.H * s.chh))
        for y in range(s.H + 1): p.drawLine(M, int(M + y * s.chh), int(M + s.W * s.cw), int(M + y * s.chh))
        for y in range(s.H):
            for x in range(s.W):
                if s.rows[y][x] != " ": s.glyph_at(p, x, y, s.rows[y][x], s.col(x, y))
        r = s.sel
        if s.lift and r:
            for dy, row in enumerate(s.lift[0]):
                for dx, ch in enumerate(row):
                    tx, ty = r.left() + dx + s.off[0], r.top() + dy + s.off[1]
                    if ch != " " and 0 <= tx < s.W and 0 <= ty < s.H: s.glyph_at(p, tx, ty, ch, s.lift[1][dy][dx] or s.col(tx, ty))
        if r:
            r = r.translated(*s.off) if s.lift else r
            p.setPen(QPen(QColor("#66c0f4"), 2, Qt.PenStyle.DashLine)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(QRectF(M + r.left() * s.cw, M + r.top() * s.chh, r.width() * s.cw, r.height() * s.chh))
        if s.tool == "draw" and s.hasFocus():
            p.setPen(QPen(QColor("#ffd33d"), 1)); p.drawRect(QRectF(M + s.cur[0] * s.cw, M + s.cur[1] * s.chh, s.cw, s.chh))
    def to_logo(s):
        has = any(c for r in s.cols for c in r)
        return dict(w=s.W, h=s.H, rows=["".join(r) for r in s.rows], cells=[r[:] for r in s.cols] if has else None)

class AsciiDesigner(QWidget):
    def __init__(s, win):
        super().__init__(); s.w = win; s.editing = None; s.frames, s.final, s.fi = [[]], 0, 0
        s.recent = list("#@*/\\|_-█░▒▓▀▄"); s.stops = ["#3daee9", "#bb9af7", "#f7768e"]
        s.canvas = DesignCanvas(); s.pal = GlyphList(); s.term = TermView(); s.term.setMinimumSize(300, 230)
        # --- left: symbol palette
        left = QWidget(); lv = QVBoxLayout(left); lv.addWidget(hdr("Symbols — click to pick, drag onto canvas"))
        s.cat = QComboBox(); s.cat.addItems(["Recent"] + list(GLYPHS)); s.cat.currentTextChanged.connect(s.fill_pal)
        lv.addWidget(s.cat); lv.addWidget(s.pal, 1); s.brush = QLabel("Brush: #"); lv.addWidget(s.brush)
        s.pal.currentItemChanged.connect(lambda it, _: it and s.set_glyph(it.text()))
        # --- middle: tools + canvas
        mid = QWidget(); mv = QVBoxLayout(mid); tr = QHBoxLayout(); s.tools = QButtonGroup(s)
        for label, key, tip in (("✎ Draw", "draw", "Place the selected symbol. You can also just type on the keyboard."),
                                ("⌫ Erase", "erase", ""), ("◐ Paint", "paint", "Color cells (set color mode to 'cells')"),
                                ("⌖ Pick", "pick", "Pick up a symbol/color from the canvas"),
                                ("⬚ Select/Move", "select", "Drag a box, then drag inside it to rearrange. Delete clears it.")):
            b = QPushButton(label); b.setCheckable(True); b.setToolTip(tip); b.setChecked(key == "draw")
            b.clicked.connect(lambda _, k=key: setattr(s.canvas, "tool", k)); s.tools.addButton(b); tr.addWidget(b)
        s.tools.setExclusive(True)
        s.sp_w, s.sp_h = QSpinBox(), QSpinBox(); s.sp_w.setRange(4, 120); s.sp_h.setRange(2, 60)
        rb = QPushButton("Resize"); rb.clicked.connect(lambda: s.canvas.resize_grid(s.sp_w.value(), s.sp_h.value()))
        ub, rbk = QPushButton("↶"), QPushButton("↷"); ub.clicked.connect(s.canvas.do_undo); rbk.clicked.connect(s.canvas.do_redo)
        for x in (QLabel("  W"), s.sp_w, QLabel("H"), s.sp_h, rb, ub, rbk): tr.addWidget(x)
        tr.addStretch(); mv.addLayout(tr); sa = QScrollArea(); sa.setWidgetResizable(True); sa.setWidget(s.canvas); mv.addWidget(sa, 1)
        # --- right: style, starters, files, preview
        right = QWidget(); rv = QVBoxLayout(right); f = QFormLayout()
        s.ed_name, s.ed_author = QLineEdit("My Logo"), QLineEdit(); f.addRow("Node name", s.ed_name); f.addRow("Author", s.ed_author)
        s.cb_start = QComboBox(); s.cb_start.addItems(list(STARTERS)); sb = QPushButton("Load starter"); sb.clicked.connect(s.load_starter)
        row = QHBoxLayout(); row.addWidget(s.cb_start, 1); row.addWidget(sb); f.addRow("Starter art", row)
        s.cb_mode = QComboBox(); s.cb_mode.addItems(["solid", "gradient", "cells"]); s.cb_mode.setToolTip("cells = hand-painted per-cell colors")
        s.cb_dir = QComboBox(); s.cb_dir.addItems(GRADS[1:]); s.cb_anim = QComboBox(); s.cb_anim.addItems(ANIMS)
        s.cbtn = []; crow = QHBoxLayout()
        for i in range(3):
            b = QPushButton(); b.setFixedWidth(46); b.clicked.connect(lambda _, i=i: s.pick_stop(i)); s.cbtn.append(b); crow.addWidget(b)
        pb = QPushButton("Paint color"); pb.clicked.connect(s.pick_paint); crow.addWidget(pb)
        f.addRow("Color mode", s.cb_mode); f.addRow("Colors 1-3", crow); f.addRow("Gradient", s.cb_dir); f.addRow("Animation", s.cb_anim)
        for c in (s.cb_mode, s.cb_dir, s.cb_anim): c.currentTextChanged.connect(s.style_changed)
        rv.addWidget(hdr("Logo style")); rv.addLayout(f); rv.addWidget(hdr("Live preview (same renderer as the build)")); rv.addWidget(s.term, 1)
        s.lbl_edit = QLabel("New node"); rv.addWidget(s.lbl_edit)
        s.btn_save = QPushButton("★ Save as node (adds to graph)"); s.btn_save.clicked.connect(s.save_node); rv.addWidget(s.btn_save)
        fr = QHBoxLayout(); s.cb_lib = QComboBox(); lb = QPushButton("Load"); lb.clicked.connect(s.load_lib); fr.addWidget(s.cb_lib, 1); fr.addWidget(lb); rv.addLayout(fr)
        for label, fn in (("Export .fsnode…", s.export_fsnode), ("Import .fsnode…", s.import_fsnode),
                          ("Image → ASCII…", s.import_image), ("Import text art…", s.import_text)):
            b = QPushButton(label); b.clicked.connect(fn); rv.addWidget(b)
        sp = QSplitter(); sp.addWidget(left); sp.addWidget(mid); sp.addWidget(right); sp.setSizes([260, 640, 400])
        lay = QHBoxLayout(s); lay.setContentsMargins(0, 0, 0, 0); lay.addWidget(sp)
        s.dbt = QTimer(s); s.dbt.setSingleShot(True); s.dbt.setInterval(120); s.dbt.timeout.connect(s.restart_preview)
        s.canvas.changed.connect(s.dbt.start); s.canvas.picked.connect(s.set_glyph)
        s.timer = QTimer(s); s.timer.timeout.connect(s.tick); s.timer.start(110)
        s.cat.setCurrentText("ASCII"); s.fill_pal(); s.load_logo(new_logo()); s.refresh_lib()
    def hl(s, b, c):
        q = QColor(c); b.setStyleSheet("background:%s;color:%s" % (c, "#000" if q.lightness() > 128 else "#fff")); b.setText(" ")
    def fill_pal(s, *_):
        s.pal.clear(); cat = s.cat.currentText()
        for ch in (s.recent if cat == "Recent" else GLYPHS[cat]):
            if ch.isprintable():
                it = QListWidgetItem(ch); it.setTextAlignment(Qt.AlignmentFlag.AlignCenter); it.setToolTip("U+%04X" % ord(ch)); s.pal.addItem(it)
    def set_glyph(s, ch):
        s.canvas.glyph = ch; s.brush.setText("Brush: " + ch); s.recent = ([ch] + [c for c in s.recent if c != ch])[:40]
    def pick_stop(s, i):
        c = QColorDialog.getColor(QColor(s.stops[i]), s)
        if c.isValid(): s.stops[i] = c.name(); s.hl(s.cbtn[i], c.name()); s.style_changed()
    def pick_paint(s):
        c = QColorDialog.getColor(QColor(s.canvas.color), s)
        if c.isValid(): s.canvas.color = c.name()
    def style_changed(s, *_):
        c = s.canvas; c.mode, c.stops, c.direction = s.cb_mode.currentText(), list(s.stops), s.cb_dir.currentText(); c.update(); s.dbt.start()
    def refresh_classic(s):
        on = s.w.classic
        for c in (s.cb_dir, s.cb_anim): c.setEnabled(not on)
        s.restart_preview()
    def restart_preview(s):
        c = s.canvas; mode = s.cb_mode.currentText(); anim = "none" if s.w.classic else s.cb_anim.currentText()
        if s.w.classic and mode == "gradient": mode = "solid"
        s.frames, s.final = render_logo(["".join(r) for r in c.rows], c.cols if mode == "cells" else None, mode, s.stops, s.cb_dir.currentText(), anim)
        s.fi = 0
    def tick(s):
        if not s.isVisible(): return
        s.term.set(s.frames[s.fi % len(s.frames)], "#1e1e1e", "#d0d0d0", "Preview", 11); s.fi += 1
    def logo(s):
        d = s.canvas.to_logo(); d.update(name=s.ed_name.text().strip() or "My Logo", author=s.ed_author.text().strip(),
                                         mode=s.cb_mode.currentText(), stops=list(s.stops), direction=s.cb_dir.currentText(), anim=s.cb_anim.currentText())
        return d
    def load_logo(s, d, editing=None):
        d = sanitize_logo(d); s.canvas.set_grid(d); s.editing = editing; s.stops = (d["stops"] + ["#bb9af7", "#f7768e"])[:3]
        for wd, v in ((s.cb_mode, d["mode"]), (s.cb_dir, d["direction"]), (s.cb_anim, d["anim"])): wd.blockSignals(True); wd.setCurrentText(v); wd.blockSignals(False)
        for i in range(3): s.hl(s.cbtn[i], s.stops[i])
        s.ed_name.setText(d["name"]); s.ed_author.setText(d["author"]); s.sp_w.setValue(d["w"]); s.sp_h.setValue(d["h"])
        s.lbl_edit.setText("Editing an existing graph node" if editing else "New node"); s.style_changed(); s.refresh_classic()
    def load_starter(s):
        lines = STARTERS[s.cb_start.currentText()]; d = new_logo(s.ed_name.text() or "My Logo", lines)
        d.update(author=s.ed_author.text(), mode=s.cb_mode.currentText(), stops=list(s.stops), direction=s.cb_dir.currentText(), anim=s.cb_anim.currentText())
        s.canvas.snap(); keep = (s.canvas.undo, s.editing); s.load_logo(d, s.editing); s.canvas.undo = keep[0]
    def save_node(s):
        try: d = sanitize_logo(s.logo())
        except Exception as ex: QMessageBox.warning(s, APP, str(ex)); return
        s.editing = s.w.designer_save(d, s.editing); s.lbl_edit.setText("Editing an existing graph node"); s.refresh_lib()
    def refresh_lib(s): s.cb_lib.clear(); [s.cb_lib.addItem(p.stem, str(p)) for p in lib_list()]
    def load_lib(s):
        p = s.cb_lib.currentData()
        if p: s.try_load(lambda: lib_read(p))
    def try_load(s, fn):
        try: s.load_logo(fn())
        except Exception as ex: QMessageBox.warning(s, APP, "Could not load:\n%s" % ex)
    def export_fsnode(s):
        d = sanitize_logo(s.logo()); fn, _ = QFileDialog.getSaveFileName(s, "Export node", str(Path.home() / (clean_name(d["name"]) + ".fsnode")), "Fetch Studio node (*.fsnode)")
        if fn: write_fsnode(d, fn)
    def import_fsnode(s):
        fn, _ = QFileDialog.getOpenFileName(s, "Import node", str(Path.home()), "Fetch Studio node (*.fsnode)")
        if not fn: return
        try: d = lib_read(fn); lib_save(d); s.load_logo(d); s.refresh_lib()
        except Exception as ex: QMessageBox.warning(s, APP, "Could not import:\n%s" % ex)
    def import_text(s):
        fn, _ = QFileDialog.getOpenFileName(s, "Text art", str(Path.home()), "Text (*.txt *.asc *.nfo);;All (*)")
        if fn:
            lines = [l.rstrip("\n")[:160] for l in Path(fn).read_text(errors="replace").splitlines()[:80]] or [" "]
            s.try_load(lambda: dict(new_logo(Path(fn).stem, lines), stops=s.stops, mode=s.cb_mode.currentText(), anim=s.cb_anim.currentText()))
    def import_image(s):
        fn, _ = QFileDialog.getOpenFileName(s, "Image", str(Path.home()), "Images (*.png *.jpg *.jpeg *.gif *.webp *.bmp)")
        if not fn: return
        img = QImage(fn)
        if img.isNull(): return
        w = 48; h = max(1, round(img.height() * w / img.width() * 0.5)); sm = img.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation).convertToFormat(QImage.Format.Format_ARGB32)
        ramp = " .:-=+*#%@"; rows, cells = [], []
        for y in range(h):
            r, c = "", []
            for x in range(w):
                px = sm.pixelColor(x, y); on = px.alpha() > 60
                r += ramp[int(px.lightnessF() * (len(ramp) - 1))] if on else " "; c.append(px.name() if on else "")
            rows.append(r); cells.append(c)
        d = new_logo(Path(fn).stem, rows); d.update(cells=cells, mode="cells", stops=s.stops); s.try_load(lambda: d)

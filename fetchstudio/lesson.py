"""Interactive first-run lesson."""
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
from .designer import *


# ------------------------------------------------------------------ interactive lesson
class Lesson(QWidget):
    def __init__(s, win):
        super().__init__(win); s.w = win; s.active = False; s.i = 0
        s.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        s.panel = QFrame(win); s.panel.setStyleSheet("QFrame{background:#1b2838;border:2px solid #66c0f4;border-radius:8px}QLabel{border:0}")
        v = QVBoxLayout(s.panel); s.cnt = QLabel(); s.lbl = QLabel(); s.lbl.setWordWrap(True); v.addWidget(s.cnt); v.addWidget(s.lbl)
        r = QHBoxLayout(); s.back, s.nxt, s.quit = QPushButton("◂ Back"), QPushButton("Next ▸"), QPushButton("Save && exit lesson")
        for b in (s.back, s.nxt, s.quit): r.addWidget(b)
        v.addLayout(r); s.back.clicked.connect(lambda: s.go(-1)); s.nxt.clicked.connect(lambda: s.go(1)); s.quit.clicked.connect(s.stop)
        s.timer = QTimer(s); s.timer.timeout.connect(s.poll); s.hide(); s.panel.hide()
    def steps(s):   # (target widget, text, done?, tab to show: 0 graph / 1 designer / None leave as is)
        w = s.w; outp = lambda: next((n for n in w.g.nodes.values() if n["type"] == "output"), None); d = w.designer
        return [
            (lambda: w.view, "Welcome! This is the node graph. Drag with the LEFT mouse button on empty space to pan, or hold Ctrl and scroll to zoom. Try it now.", lambda: w.flags["panned"], 0),
            (lambda: w.view, "Right-click empty canvas ▸ Add node ▸ Title. Then right-click again and add an Info node.", lambda: w.has("title") and w.has("info"), 0),
            (lambda: w.props, "Click your Info node, then change 'Field' here to something other than OS (e.g. Kernel).", lambda: any(n["type"] == "info" and n["params"]["field"] != "OS" for n in w.g.nodes.values()), 0),
            (lambda: w.view, "Drag from a node's round right-hand port to the Output node's left-hand port to connect them. Connect both Title and Info.", lambda: w.linked("title") and w.linked("info"), 0),
            (lambda: w.term, "This is your live 1:1 terminal preview. Now add a Logo node and connect it to Output too.", lambda: w.linked("logo") or w.linked("clogo"), 0),
            (lambda: w.view, "Hold Shift and drag a box around two nodes, then right-click ▸ Group selected nodes.", lambda: bool(w.g.groups), 0),
            (lambda: w.view, "Right-click the group ▸ Collapse group (or double-click it).", lambda: any(g["collapsed"] for g in w.g.groups.values()), 0),
            (lambda: w.view, "Expand it again the same way.", lambda: bool(w.g.groups) and not any(g["collapsed"] for g in w.g.groups.values()), 0),
            (lambda: w.props, "Select the Output node and pick a Color theme (try 'dracula'). In Classic mode, effects are hidden — theme still works.", lambda: outp() and outp()["params"]["theme"] != "none", 0),
            (lambda: w.tabs.tabBar(), "Now the fun part: click the ASCII Designer tab to draw your own logo.", lambda: w.tabs.currentIndex() == 1, None),
            (lambda: d.pal, "Pick a symbol category, then DRAG a symbol from this palette onto the canvas. (You can also type on the keyboard.)", lambda: d.canvas.drops > 0, 1),
            (lambda: d.canvas, "Use ⬚ Select/Move to drag a box around part of your art and move it. Load 'starter art' to edit something ready-made. Continue when you are happy.", lambda: True, 1),
            (lambda: d.cb_anim, "Choose an animation (e.g. rainbow) and a gradient. In Classic mode these are disabled, so you can continue.", lambda: w.classic or d.cb_anim.currentText() != "none", 1),
            (lambda: d.btn_save, "Click 'Save as node'. It is added to your graph and connected to Output, and saved to your node library as a shareable .fsnode.", lambda: w.flags["design_saved"], 1),
            (lambda: w.bar("Save"), "Press Ctrl+S (or click Save) to save your project. It also auto-saves every 10 minutes.", lambda: w.flags["saved"] > 0, None),
            (lambda: w.bar("Export"), "Click Export to create a shareable fetchstudio(name).zip with your graph, custom logo and images.", lambda: w.flags["exported"], None),
            (lambda: w.bar("Build"), "Click Build. This installs a standalone script and shell hook, so new terminals show your fetch without this app.", lambda: w.flags["built"], None)]
    def start(s, restart=False):
        s.i = 0 if restart else int(s.w.cfg.value("lesson/step", 0)); s.i = min(s.i, len(s.steps()) - 1)
        s.active = True; s.show(); s.panel.show(); s.timer.start(250); s.poll()
    def stop(s): s.w.cfg.setValue("lesson/step", s.i); s.active = False; s.timer.stop(); s.hide(); s.panel.hide()
    def go(s, d):
        if s.i + d >= len(s.steps()):
            s.w.cfg.setValue("lesson/done", True); s.w.cfg.setValue("lesson/step", 0); s.stop()
            QMessageBox.information(s.w, APP, "Lesson complete! Reopen it any time from the Lesson button."); return
        s.i = max(0, s.i + d); s.w.cfg.setValue("lesson/step", s.i); s.poll()
    def poll(s):
        if not s.active: return
        st = s.steps(); tab = st[s.i][3]
        if tab is not None and s.w.tabs.currentIndex() != tab: s.w.tabs.setCurrentIndex(tab)
        s.setGeometry(s.w.rect()); s.raise_(); s.panel.raise_()
        s.cnt.setText("<b>Lesson %d / %d</b>" % (s.i + 1, len(st))); s.lbl.setText(st[s.i][1])
        ok = bool(st[s.i][2]()); s.nxt.setEnabled(ok); s.nxt.setText("Finish ✓" if s.i == len(st) - 1 else ("Next ▸" if ok else "Complete the step…"))
        s.back.setEnabled(s.i > 0); pw = min(560, s.w.width() - 40); s.panel.setFixedWidth(pw); s.panel.adjustSize()
        s.panel.move((s.w.width() - pw) // 2, s.w.height() - s.panel.height() - 16); s.update()
    def paintEvent(s, e):
        if not s.active: return
        t = s.steps()[s.i][0](); pt = t.mapTo(s.w, t.rect().topLeft())
        hole = QPainterPath(); hole.addRoundedRect(QRectF(pt.x() - 4, pt.y() - 4, t.width() + 8, t.height() + 8), 8, 8)
        full = QPainterPath(); full.addRect(QRectF(s.rect())); p = QPainter(s)
        p.fillPath(full.subtracted(hole), QColor(0, 0, 0, 140)); p.setPen(QPen(QColor("#ffd33d"), 3)); p.drawPath(hole)

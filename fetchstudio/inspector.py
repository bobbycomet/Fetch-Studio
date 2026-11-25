"""Properties inspector: one tab per topic (Readout, Items, Colors, Animation...) instead of one long form."""
from .common import *
from .specs import *
from .system import *
from .security import *
from .caltool import *
from .widgets import hdr

class PropPanel(QWidget):
    def __init__(s, win):
        super().__init__(); s.win = win; s.d = None; s.last_tab = {}; s.building = False; s.cmd_lbl = s.cmd_btn = None
        lay = QVBoxLayout(s); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(2)
        s.head = hdr(""); lay.addWidget(s.head)
        s.tabs = QTabWidget(); s.tabs.setDocumentMode(True); s.tabs.currentChanged.connect(s.remember_tab); lay.addWidget(s.tabs, 1)
        s.show_node(None)

    # ---- navigation
    def remember_tab(s, i):
        if not s.building and s.d and i >= 0: s.last_tab[s.d["type"]] = s.tabs.tabText(i)
    def later_refresh(s): QTimer.singleShot(0, lambda: s.show_node(s.d if s.d and s.d["id"] in s.win.g.nodes else None))

    def visible(s, par):
        if par.kind == "hidden" or (s.win.classic and par.fancy): return False
        if par.when:
            cur, need = s.d["params"].get(par.when[0]), par.when[1]
            if (cur not in need) if isinstance(need, (tuple, list)) else (cur != need): return False
        return True

    def show_node(s, d):
        s.building = True; s.d = d; s.cmd_lbl = s.cmd_btn = None
        while s.tabs.count(): w = s.tabs.widget(0); s.tabs.removeTab(0); w.deleteLater()
        if not d:
            s.head.setText("Properties"); s.add_page("", [QLabel("Select a node to edit its properties.")]); s.tabs.tabBar().setVisible(False)
            s.building = False; return
        t = d["type"]; s.head.setText(SPEC[t][0] + " node"); pars = {p.key: p for p in SPEC[t][2]}; spec = TABS.get(t, [("General", list(pars))])
        placed = {k for _, keys in spec for k in keys}; extra = [k for k in pars if k not in placed]
        for n, (title, keys) in enumerate(spec):
            keys = list(keys) + (extra if n == 0 else [])
            rows = [s.row(pars[k]) for k in keys if k in pars and s.visible(pars[k])]
            rows = [r for r in rows if r]
            if rows: s.add_page(title, [w for r in rows for w in r])
        s.tabs.tabBar().setVisible(s.tabs.count() > 1)
        want = s.last_tab.get(t)
        for i in range(s.tabs.count()):
            if s.tabs.tabText(i) == want: s.tabs.setCurrentIndex(i); break
        s.building = False

    def add_page(s, title, widgets):
        body = QWidget(); f = QFormLayout(body); f.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        for w in widgets:
            if isinstance(w, tuple): f.addRow(*w)
            else: f.addRow(w)
        sa = QScrollArea(); sa.setWidgetResizable(True); sa.setWidget(body)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); s.tabs.addTab(sa, title)

    # ---- one parameter -> list of form rows (a widget, or a (label, widget) pair)
    def row(s, par):
        d, key = s.d, par.key; v = d["params"][key]; k = par.kind
        if k == "combo":
            x = QComboBox(); x.addItems(par.opts); x.setCurrentText(str(v)); x.currentTextChanged.connect(lambda t, key=key: s.set(key, t))
        elif k == "int":
            x = QSpinBox(); x.setRange(*par.opts); x.setValue(int(v)); x.valueChanged.connect(lambda t, key=key: s.set(key, t))
        elif k == "check":
            x = QCheckBox(); x.setChecked(bool(v)); x.toggled.connect(lambda t, key=key: s.set(key, t))
        elif k == "text":
            x = QLineEdit(str(v)); x.textChanged.connect(lambda t, key=key: s.set(key, t))
        elif k == "color":
            x = QPushButton(v); s.paint_btn(x, v); x.clicked.connect(lambda _, key=key, b=x: s.pick_color(key, b))
        elif k == "fieldlist":
            x = QWidget(); xv = QVBoxLayout(x); xv.setContentsMargins(0, 0, 0, 0)
            flt = QLineEdit(); flt.setPlaceholderText("Search readouts…"); lst = QListWidget(); lst.setMinimumHeight(230)
            for opt in par.opts:
                it = QListWidgetItem(FIELD_LABELS.get(opt, opt)); it.setData(Qt.ItemDataRole.UserRole, opt); lst.addItem(it)
                if opt == v: lst.setCurrentItem(it); lst.scrollToItem(it)
            lst.currentItemChanged.connect(lambda it, _, key=key: it and s.set(key, it.data(Qt.ItemDataRole.UserRole)))
            flt.textChanged.connect(lambda t, l=lst: [l.item(i).setHidden(t.lower() not in l.item(i).text().lower()) for i in range(l.count())])
            xv.addWidget(flt); xv.addWidget(lst)
        elif k in ("multi", "groupitems"):
            opts = [(m, m) for m in par.opts] if k == "multi" else [(i[0], i[1]) for i in GROUPS.get(d["params"].get("field"), [])]
            x = QWidget(); xv = QVBoxLayout(x); xv.setContentsMargins(0, 0, 0, 0); xv.setSpacing(2)
            for val, lab in opts:
                cb = QCheckBox(lab); cb.setChecked(val in (v or [])); cb.toggled.connect(lambda on, key=key, val=val: s.toggle(key, val, on)); xv.addWidget(cb)
        elif k == "action":
            b = QPushButton(par.label); b.clicked.connect(lambda _, a=par.default: s.win.edit_in_designer(s.d) if a == "edit" else s.win.export_node(s.d)); return [b]
        else:
            x = QPushButton(v or "Choose file…"); x.clicked.connect(lambda _: s.pick_file())
        lb = QLabel(par.label); lb.setWordWrap(True); out = [(lb, x)]
        if key == "command": out += s.command_rows()
        if key == "items" and d["params"].get("field") == "Clock" and "Cal" in (v or []): out += s.cal_rows()
        return out

    # ---- custom command trust UI
    def command_rows(s):
        s.cmd_lbl = QLabel(); s.cmd_lbl.setWordWrap(True); s.cmd_lbl.setTextFormat(Qt.TextFormat.RichText)
        s.cmd_btn = QPushButton("Trust this command and run preview"); s.cmd_btn.clicked.connect(s.trust_current)
        s.update_cmd_status(); return [s.cmd_lbl, s.cmd_btn]
    def update_cmd_status(s):
        if not s.cmd_lbl or not s.d: return
        st = cmd_status(s.d["params"].get("command", ""))
        msg = {"empty": "Type a shell command. It runs as <b>you</b>, in its own bash, with a 5 second limit, every time a terminal opens.",
               "untrusted": "⚠ <b>Not trusted.</b> This command runs in your shell every time a terminal opens. It is <b>not run</b> in the preview or in a build until you trust it. "
                            "Only trust commands you wrote or have read.",
               "trusted": "✔ <b>Trusted on this computer.</b> Runs as your user (never elevated), 5 second limit, no input.",
               "blocked": "⛔ <b>Blocked.</b> Commands that use sudo, su, doas, pkexec or similar are not allowed: a terminal greeting must never ask for or use administrator rights."}[st]
        s.cmd_lbl.setText(msg); s.cmd_btn.setVisible(st == "untrusted")
    def trust_current(s):
        if s.d and trust_command(s.d["params"].get("command", "")): s.win.recompile(); s.win.node_changed(s.d); s.update_cmd_status()

    # ---- cal helper UI
    def cal_rows(s):
        lb = QLabel(); lb.setWordWrap(True)
        if have_cal(): lb.setText("✔ The <code>cal</code> command is installed."); return [lb]
        lb.setText("⚠ The <code>cal</code> command is not installed, so the calendar will be blank."); b = QPushButton("Install cal…"); b.clicked.connect(s.win.install_cal)
        return [lb, b]

    # ---- edits
    def paint_btn(s, b, c):
        q = QColor(c); b.setStyleSheet("background:%s;color:%s" % (c, "#000" if q.lightness() > 128 else "#fff"))
    def toggle(s, k, val, on):
        cur = list(s.d["params"].get(k) or [])
        if on and val not in cur: cur.append(val)
        if not on and val in cur: cur.remove(val)
        s.set(k, cur)
    def set(s, k, v):
        s.d["params"][k] = v
        if k == "field":
            if v in GROUPS:                                                    # first time on a group: start with a sensible handful ticked
                cur = list(s.d["params"].get("items") or [])
                if not any(i[0] in cur for i in GROUPS[v]): s.d["params"]["items"] = cur + GROUP_DEFAULT[v]
                s.last_tab["info"] = "Items"
            else: s.last_tab["info"] = "Readout"
        if k == "theme" and v != "none": s.win.apply_theme(v); s.later_refresh()
        if k in ("field", "source", "items"): s.later_refresh()                # show/hide Weather, Custom, image and cal options
        if k == "command": s.update_cmd_status()
        s.win.node_changed(s.d)
    def pick_color(s, k, b):
        c = QColorDialog.getColor(QColor(s.d["params"][k]), s)
        if c.isValid(): b.setText(c.name()); s.paint_btn(b, c.name()); s.set(k, c.name())
    def pick_file(s):
        fn, _ = QFileDialog.getOpenFileName(s, "Logo image, GIF or text file", "", "Images/Text (*.png *.jpg *.jpeg *.gif *.webp *.bmp *.txt);;All (*)")
        if fn: s.d["params"]["file"] = s.win.import_asset(fn); s.d["params"]["source"] = "file"; s.win.node_changed(s.d); s.later_refresh()

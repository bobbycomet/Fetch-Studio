"""Main window and application entry point."""
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
from .caltool import install_cal as _install_cal, remove_cal as _remove_cal
from .settings import SettingsDialog
from .widgets import *
from .graphitems import *
from .inspector import *
from .designer import *
from .lesson import *

class Main(QMainWindow):
    update_result = pyqtSignal(str, str, bool, str)      # tag, url, manual check?, error
    cal_done = pyqtSignal(bool, str)                     # ok, message (installing cal in a background thread)
    def __init__(s):
        super().__init__(); s.cfg = QSettings("GriffinLinux", "FetchStudio"); s.g = None; s.dirty = False
        s.comp = None; s.fi = 0; s.flags = dict(saved=0, exported=False, built=False, panned=False, design_saved=False)
        s.scene = GraphScene(s); s.view = GraphView(s.scene, s); s.props = PropPanel(s); s.term = TermView()
        s.tcombo = QComboBox(); s.tcombo.addItems(list(TERMS)); s.tcombo.currentTextChanged.connect(s.set_terminal)
        right = QWidget(); v = QVBoxLayout(right); v.addWidget(hdr("Live preview — terminal")); v.addWidget(s.tcombo)
        v.addWidget(s.term, 3); v.addWidget(s.props, 2)
        sp = QSplitter(); sp.addWidget(s.view); sp.addWidget(right); sp.setSizes([760, 560])
        s.designer = AsciiDesigner(s); s.tabs = QTabWidget()
        s.tabs.addTab(sp, "◈  Node Graph"); s.tabs.addTab(s.designer, "✎  ASCII Designer"); s.settings_dlg = SettingsDialog(s); s.tabs.addTab(s.settings_dlg, "⚙  Settings"); s.setCentralWidget(s.tabs)
        s.tb = QToolBar(); s.tb.setMovable(False); s.addToolBar(s.tb); s.acts = {}
        for name, key, fn in (("New", "Ctrl+N", s.new_project), ("Open", "Ctrl+O", s.open_project), ("Save", "Ctrl+S", lambda: s.save()),
                              ("Import", "Ctrl+I", s.import_zip), ("Export", "Ctrl+E", s.export_zip), ("Build", "Ctrl+B", s.build),
                              ("Remove", "", s.remove_build), ("Updates", "", lambda: s.check_updates(True)),
                              ("Refresh", "F5", s.refresh_preview), ("Lesson", "F1", lambda: s.lesson.start()), ("Settings", "", lambda: s.open_settings())):
            a = QAction(name, s); a.triggered.connect(fn)
            if key: a.setShortcut(QKeySequence(key))
            s.tb.addAction(a); s.acts[name] = a
        a = QAction("Classic mode", s); a.setCheckable(True); a.toggled.connect(s.set_classic)
        a.setToolTip("Classic: just ASCII art and system readouts. No gradients, animation or modern nodes.")
        s.tb.addSeparator(); s.tb.addAction(a); s.acts["Classic"] = a
        s.scene.selectionChanged.connect(s.on_sel); s.lesson = Lesson(s)
        s.timer = QTimer(s); s.timer.timeout.connect(s.tick)
        s.auto = QTimer(s); s.auto.timeout.connect(lambda: s.dirty and s.g and s.save(auto=True)); s.auto.start(600_000)
        s.setStyleSheet(STYLE); s.resize(1400, 860); PROJ.mkdir(parents=True, exist_ok=True)
        last = s.cfg.value("last", "")
        opened = False
        if last and (PROJ / last / "project.json").exists():
            try: s.open_graph(s.read(last)); opened = True
            except ProjectError as ex: QTimer.singleShot(0, lambda ex=ex: QMessageBox.warning(s, APP, "The last project could not be opened:\n%s" % ex))
        if not opened: s.open_graph(default_graph("my-first-fetch", "custom")); s.save()
        else: QTimer.singleShot(400, s.review_commands)
        if not s.cfg.value("lesson/done", False, type=bool): QTimer.singleShot(500, lambda: s.lesson.start())
        s.cal_done.connect(s.on_cal_done); s.update_result.connect(s.on_update_result); QTimer.singleShot(3000, lambda: s.check_updates(False))
    # update checker (GitHub releases)
    def check_updates(s, manual=False):
        def run():
            try: tag, url = fetch_latest_release(); s.update_result.emit(tag, url, manual, "")
            except Exception as ex: s.update_result.emit("", "", manual, str(ex))
        threading.Thread(target=run, daemon=True).start()
    def on_update_result(s, tag, url, manual, err):
        if err or not tag:
            if manual: QMessageBox.warning(s, APP, "Could not check for updates:\n%s" % (err or "no release found"))
            return                                                  # silent on startup (offline, rate limit, ...)
        if vtuple(tag) > vtuple(VERSION):
            m = QMessageBox(s); m.setWindowTitle(APP + " update"); m.setIcon(QMessageBox.Icon.Information)
            m.setTextFormat(Qt.TextFormat.RichText); m.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            m.setText("<b>Fetch Studio %s is available</b> (you have %s).<br><br>"
                      "<b>Recommended:</b> use <a href=\"%s\">Griffin Updater</a> to update Fetch Studio. "
                      "It keeps Fetch Studio up to date even when Fetch Studio is closed.<br><br>"
                      "Or update manually by replacing the AppImage from the "
                      "<a href=\"%s\">releases page</a>." % (tag.lstrip("vV"), VERSION, UPDATER_URL, url))
            m.exec()
        elif manual:
            QMessageBox.information(s, APP, "You are up to date (version %s)." % VERSION)
    # helpers
    classic = property(lambda s: bool(s.g and s.g.meta.get("classic")))
    def bar(s, n): return s.tb.widgetForAction(s.acts[n])
    def has(s, t): return any(n["type"] == t for n in s.g.nodes.values())
    def linked(s, t): return any(s.g.nodes[a]["type"] == t and s.g.nodes[b]["type"] == "output" for a, b in s.g.edges if a in s.g.nodes and b in s.g.nodes)
    def read(s, name): return Graph.load(load_project_file(PROJ / name / "project.json", name), name)      # validated like an import
    def on_sel(s):
        try: sel = [i for i in s.scene.selectedItems() if isinstance(i, NodeItem)]
        except RuntimeError: return
        s.props.show_node(sel[0].d if len(sel) == 1 else None)
    def set_terminal(s, t):
        if s.g: s.g.meta["terminal"] = t; s.touch()
    def set_classic(s, on):
        if not s.g: return
        s.g.meta["classic"] = bool(on); s.designer.refresh_classic(); s.props.later_refresh(); s.touch()
    def title(s): s.setWindowTitle("%s — %s%s" % (APP, s.g.name, " *" if s.dirty else ""))
    def node_changed(s, d): s.scene.nitems[d["id"]].update(); s.touch()
    def touch(s): s.dirty = True; s.recompile(); s.title()
    def recompile(s):
        s.comp = compile_graph(s.g); s.fi = 0
        n = s.nfr()
        s.timer.start(int(1000 / max(1, int(s.comp["O"]["fps"]))) if n > 1 else 300); s.render()
    def nfr(s):
        c = s.comp
        if not c: return 1
        return len(c["gimgs"]) if c.get("gfx") and c.get("gimgs") else len(c["frames"])
    def tick(s):
        if s.comp and s.nfr() > 1: s.fi += 1; s.render()
        elif STATE["dirty"]: s.render()
    def render(s):
        STATE["dirty"] = False; PREVIEW["terminal"] = s.g.meta.get("terminal"); t = TERMS.get(s.g.meta.get("terminal"), TERMS["GNOME Terminal"])
        if not s.comp: s.term.set([], "#1e1e1e", "#d0d0d0", t[0], t[1]); return
        c = s.comp; O = c["O"]; gi = c.get("gimgs")
        ov = (gi[s.fi % len(gi)], c["gfx"]["cols"], c["gfx"]["rows"]) if c.get("gfx") and gi else None
        s.term.set(compose(c, s.fi), O["bg"], O["fg"], t[0], t[1], ov)
    def import_asset(s, path):
        d = s.g.dir / "assets"; d.mkdir(parents=True, exist_ok=True); name = Path(path).name; dst = d / name; k = 1
        while dst.exists() and not dst.samefile(path): dst = d / f"{k}_{name}"; k += 1
        if not dst.exists(): shutil.copy(path, dst)
        return "assets/" + dst.name
    # themes + custom logo nodes
    def apply_theme(s, name):
        T = THEMES[name]; ac = T["acc"]; i = 0
        for n in sorted(s.g.nodes.values(), key=lambda n: n["y"]):
            p, t = n["params"], n["type"]
            if t == "output": p["bg"], p["fg"] = T["bg"], T["fg"]
            elif t == "logo": p["color"], p["color2"], p["color3"] = ac[0], ac[1], ac[2]
            elif t == "title": p["color"] = ac[0]
            elif t == "info":
                adv = next((o["params"]["preset"] == "advanced" for o in s.g.nodes.values() if o["type"] == "output"), False)
                p["key_color"] = ac[i % len(ac)] if adv else ac[0]; p["val_color"] = T["fg"]; i += 1
            elif t == "bar": p["key_color"], p["c1"], p["c2"], p["c3"], p["empty"] = ac[0], ac[3], ac[4], ac[1], T["dim"]
            elif t == "divider": p["color"], p["color2"] = ac[0], ac[1]
            elif t == "text": p["color"] = T["fg"]
            if n["id"] in s.scene.nitems: s.scene.nitems[n["id"]].update()
    def edit_in_designer(s, d): s.designer.load_logo(d["params"]["data"], d["id"]); s.tabs.setCurrentIndex(1)
    def export_node(s, d):
        logo = sanitize_logo(d["params"]["data"]); fn, _ = QFileDialog.getSaveFileName(s, "Export node", str(Path.home() / (clean_name(logo["name"]) + ".fsnode")), "Fetch Studio node (*.fsnode)")
        if fn: write_fsnode(logo, fn)
    def add_logo_node(s, logo):
        c = s.view.mapToScene(s.view.viewport().rect().center()); i = s.scene.add_node("clogo", c, data=copy.deepcopy(logo))
        o = next((k for k, n in s.g.nodes.items() if n["type"] == "output"), None)
        if o and (i, o) not in s.g.edges: s.g.edges.append((i, o)); s.scene.add_edge(i, o)
        return i
    def add_library_node(s, path):
        try: s.add_logo_node(lib_read(path))
        except Exception as ex: QMessageBox.warning(s, APP, "Could not load node:\n%s" % ex)
    def import_node_file(s):
        fn, _ = QFileDialog.getOpenFileName(s, "Import node", str(Path.home()), "Fetch Studio node (*.fsnode)")
        if fn:
            try: logo = lib_read(fn); lib_save(logo); s.add_logo_node(logo); s.designer.refresh_lib()
            except Exception as ex: QMessageBox.warning(s, APP, "Could not import:\n%s" % ex)
    def designer_save(s, logo, editing=None):
        lib_save(logo); n = s.scene.nitems.get(editing) if editing else None
        if n: n.d["params"]["data"] = copy.deepcopy(logo); n.update(); i = editing
        else: i = s.add_logo_node(logo)
        s.flags["design_saved"] = True; s.touch(); s.tabs.setCurrentIndex(0)
        s.scene.clearSelection(); s.scene.nitems[i].setSelected(True); return i
    # project lifecycle
    def open_graph(s, g):
        s.g = g; s.scene.blockSignals(True); s.scene.load(g); s.scene.blockSignals(False); s.props.show_node(None)
        s.tcombo.blockSignals(True); s.tcombo.setCurrentText(g.meta.get("terminal", "GNOME Terminal")); s.tcombo.blockSignals(False)
        s.acts["Classic"].blockSignals(True); s.acts["Classic"].setChecked(bool(g.meta.get("classic"))); s.acts["Classic"].blockSignals(False)
        s.designer.refresh_classic(); s.dirty = False; s.cfg.setValue("last", g.name); s.recompile(); s.title()
    def maybe_save(s):
        if not s.dirty: return True
        r = QMessageBox.question(s, APP, "Save changes to “%s”?" % s.g.name,
                                 QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        if r == QMessageBox.StandardButton.Save: s.save(); return True
        return r == QMessageBox.StandardButton.Discard
    def save(s, auto=False):
        s.g.dir.mkdir(parents=True, exist_ok=True); (s.g.dir / "project.json").write_text(json.dumps(s.g.dump(), indent=1))
        s.dirty = False; s.cfg.setValue("last", s.g.name); s.title()
        if not auto: s.flags["saved"] += 1
    def new_project(s):
        if not s.maybe_save(): return
        name, ok = QInputDialog.getText(s, "New project", "Project name:", text="my-fetch")
        if not ok or not name.strip(): return
        pr, ok = QInputDialog.getItem(s, "New project", "Start from preset:", ["classic (simple, no effects)", "advanced", "custom"], 0, False)
        if not ok: return
        name = clean_name(name)
        while (PROJ / name).exists(): name += "-2"
        g = default_graph(name, pr.split()[0]); g.meta["classic"] = pr.startswith("classic"); s.open_graph(g); s.save()
    def open_project(s):
        if not s.maybe_save(): return
        names = sorted(p.parent.name for p in PROJ.glob("*/project.json"))
        n, ok = QInputDialog.getItem(s, "Open project", "Project:", names, 0, False) if names else ("", False)
        if not ok: return
        try: s.open_graph(s.read(n))
        except ProjectError as ex: QMessageBox.warning(s, APP, "This project could not be opened:\n%s" % ex); return
        s.review_commands()
    def export_zip(s):
        s.save(); fn, _ = QFileDialog.getSaveFileName(s, "Export", str(Path.home() / f"fetchstudio({s.g.name}).zip"), "Zip (*.zip)")
        if not fn: return
        with zipfile.ZipFile(fn, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("project.json", json.dumps(s.g.dump(), indent=1))       # custom logo nodes are embedded in the graph JSON
            for f in (s.g.dir / "assets").glob("*"): z.write(f, "assets/" + f.name)
        s.flags["exported"] = True; n = len(custom_commands(s.g))
        QMessageBox.information(s, APP, "Exported:\n" + fn + ("\n\nThis project contains %d custom command(s). Whoever imports it will be asked to review and trust them before anything runs." % n if n else ""))
    def import_zip(s):
        if not s.maybe_save(): return
        fn, _ = QFileDialog.getOpenFileName(s, "Import fetchstudio zip", str(Path.home()), "Zip (*.zip)")
        if not fn: return
        try:
            data, assets, warns = read_project_zip(fn)                  # everything is validated before a single file is written
            name = data["name"]
            while (PROJ / name).exists(): name += "-imported"
            data["name"] = name; adir = PROJ / name / "assets"; adir.mkdir(parents=True)
            for base, raw in assets.items(): (adir / base).write_bytes(raw)
            (PROJ / name / "project.json").write_text(json.dumps(data, indent=1))
            s.open_graph(s.read(name))
        except ProjectError as ex: QMessageBox.warning(s, APP, "This project was not imported because it is invalid or unsafe:\n\n%s" % ex); return
        except Exception as ex: QMessageBox.warning(s, APP, "Could not import:\n%s" % ex); return
        if warns: QMessageBox.information(s, APP, "Imported with notes:\n\n" + "\n".join(warns[:8]))
        s.review_commands(imported=True)
    def review_commands(s, imported=False):
        """Custom commands are executable content: list them and let the user decide. Nothing runs or builds until trusted."""
        cmds = [c for c in custom_commands(s.g) if c["status"] in ("untrusted", "blocked")]
        if not cmds: return
        ok = [c for c in cmds if c["status"] == "untrusted"]; bad = [c for c in cmds if c["status"] == "blocked"]
        m = QMessageBox(s); m.setIcon(QMessageBox.Icon.Warning); m.setWindowTitle(APP + " — custom commands")
        m.setText("<b>This project contains %d custom command%s.</b>" % (len(cmds), "" if len(cmds) == 1 else "s"))
        m.setInformativeText(("It was imported from a file, so " if imported else "") + "the commands below run in your shell every time a terminal opens, "
                             "as your user. They are <b>not run</b> in the preview or in a build until you trust them. Only trust commands you wrote or have read."
                             + ("<br><br>%d command(s) use sudo/su/pkexec or similar and are blocked for good." % len(bad) if bad else ""))
        m.setDetailedText("\n\n".join(("[%s] %s" % ("blocked" if c["status"] == "blocked" else "not trusted", c["cmd"])) for c in cmds))
        keep = m.addButton("Keep disabled", QMessageBox.ButtonRole.RejectRole); yes = m.addButton("Trust %s" % ("it" if len(ok) == 1 else "all %d" % len(ok)), QMessageBox.ButtonRole.AcceptRole)
        yes.setVisible(bool(ok)); m.setDefaultButton(keep); m.exec()
        if m.clickedButton() is yes:
            for c in ok: trust_command(c["cmd"])
            s.recompile(); s.scene.update(); s.props.later_refresh()
    # settings + cal helper (every admin action runs in a thread; the result comes back through cal_done)
    def refresh_preview(s): refresh_values(); s.recompile(); s.scene.update()
    def open_settings(s): s.settings_dlg.refresh(); s.tabs.setCurrentWidget(s.settings_dlg)
    def install_cal(s): s.open_settings()                      # the Items tab "Install cal…" button just opens Settings
    def run_admin(s, fn):
        QApplication.setOverrideCursor(Qt.CursorShape.BusyCursor)
        threading.Thread(target=lambda: s.cal_done.emit(*fn()), daemon=True).start()
    def setup_helper_flow(s):
        if QMessageBox.question(s, APP, "Install the Fetch Studio helper?\n\nIt asks for your administrator password (through polkit) and installs a small root-owned helper that can only "
                                "install or remove the cal command. You can remove it again here at any time.") == QMessageBox.StandardButton.Yes: s.run_admin(setup_helper)
    def install_cal_flow(s):
        cmd = manual_command()
        if QMessageBox.question(s, APP, "Install the cal command now?%s\n\nYou will be asked for your administrator password." % ("\n(%s)" % cmd if cmd else "")) == QMessageBox.StandardButton.Yes: s.run_admin(_install_cal)
    def remove_cal_flow(s):
        if QMessageBox.question(s, APP, "Uninstall the cal command that Fetch Studio installed?\n\nThe calendar readout will be blank afterwards.") == QMessageBox.StandardButton.Yes: s.run_admin(_remove_cal)
    def remove_helper_flow(s):
        if QMessageBox.question(s, APP, "Remove the Fetch Studio helper?\n\nThe cal command itself stays installed.") == QMessageBox.StandardButton.Yes: s.run_admin(remove_helper)
    def on_cal_done(s, ok, msg):
        QApplication.restoreOverrideCursor(); (QMessageBox.information if ok else QMessageBox.warning)(s, APP, msg)
        refresh_values(); s.props.later_refresh(); s.recompile()
        s.settings_dlg.refresh()
    def confirm_commands(s):
        """Build gate for custom commands -> set of command texts to leave out, or None to cancel."""
        cmds = custom_commands(s.g, connected_only=True); skip = {c["cmd"] for c in cmds if c["status"] == "blocked"}
        pend = [c for c in cmds if c["status"] == "untrusted"]
        if not skip and not pend: return skip
        m = QMessageBox(s); m.setIcon(QMessageBox.Icon.Warning); m.setWindowTitle(APP + " — custom commands")
        m.setText("<b>Building will make your terminal run these commands.</b>")
        m.setInformativeText("They execute as your user, in bash, every time a terminal opens (5 second limit each). Fetch Studio never adds sudo or other elevation." +
                             ("\n\nBlocked (privilege escalation) and left out: %d." % len(skip) if skip else ""))
        m.setDetailedText("\n\n".join(("[%s] %s" % ("blocked" if c["status"] == "blocked" else "not trusted yet", c["cmd"])) for c in cmds if c["status"] != "trusted"))
        yes = m.addButton("Trust and build", QMessageBox.ButtonRole.AcceptRole) if pend else None
        without = m.addButton("Build without them", QMessageBox.ButtonRole.DestructiveRole); cancel = m.addButton(QMessageBox.StandardButton.Cancel)
        m.setDefaultButton(cancel); m.exec(); b = m.clickedButton()
        if b is cancel or b is None: return None
        if b is yes:
            for c in pend: trust_command(c["cmd"])
            s.recompile(); s.scene.update(); s.props.later_refresh()
        else: skip |= {c["cmd"] for c in pend}
        return skip
    def build(s):
        skip = s.confirm_commands()
        if skip is None: return
        c = compile_graph(s.g, True, skip)
        if not c: QMessageBox.warning(s, APP, "Add an Output node first."); return
        s.save(); ACTIVE.mkdir(parents=True, exist_ok=True); (DATA / "built").mkdir(exist_ok=True)
        gfiles, meta = {}, None
        if c.get("gfx"):
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)             # sixel variants take a few seconds to encode
            try: gfiles, meta = gfx_assets(c)
            finally: QApplication.restoreOverrideCursor()
        for sp, gd in ((ACTIVE / "fetch.sh", ACTIVE / "gfx"), (DATA / "built" / (s.g.name + ".sh"), DATA / "built" / (s.g.name + ".gfx"))):
            shutil.rmtree(gd, ignore_errors=True)
            if gfiles:
                gd.mkdir(parents=True)
                for fn, data in gfiles.items(): (gd / fn).write_bytes(data)
            sp.write_text(gen_script(c, gd, meta)); sp.chmod(0o755)
        files = install_hooks(); s.flags["built"] = True
        found = [n for n, (_, _, exe) in TERMS.items() if shutil.which(exe)]
        anim = "" if len(c["frames"]) < 2 else ("\n\nAnimation: stays live until you run your first command (a terminal cannot redraw text that has scrolled away)."
                                                if c["O"]["lifetime"] == "live" else "\n\nAnimation: plays at launch, then stops on the final frame.")
        if meta: anim += ("\n\nLogo: real graphics (%s) in terminals that support them, detected each time a terminal opens; "
                          "everywhere else the sharp block-character version is shown. Inside tmux/screen, blocks are used." % ", ".join(meta["have"]))
        ncmd = sum(1 for k in c["custom"] if c["funcs"][k] != "echo n/a")
        if ncmd: anim += "\n\nCustom commands included: %d (run as your user at every new terminal)." % ncmd
        if any(n["type"] == "info" and n["params"].get("field") == "Clock" and "Cal" in (n["params"].get("items") or []) for n in s.g.nodes.values()) and not have_cal():
            anim += "\n\nNote: the calendar needs the cal command, which is not installed. Select the Info node ▸ Items tab ▸ Install cal…"
        QMessageBox.information(s, APP, "Built for %s.\n\nScript: %s\nShell hooks:\n  %s\n\nTerminals found here: %s%s\n\nOpen a new terminal to see it. "
                                "The app is no longer needed; use Build again after editing, or Remove to uninstall." %
                                (distro_family(), ACTIVE / "fetch.sh", "\n  ".join(map(str, files)), ", ".join(found) or "none detected", anim))
    def remove_build(s): remove_hooks(); QMessageBox.information(s, APP, "Fetch Studio hooks and script removed.")
    def closeEvent(s, e):
        if s.maybe_save(): s.lesson.stop() if s.lesson.active else None; e.accept()
        else: e.ignore()

def main(argv=None):
    argv = sys.argv if argv is None else argv
    if "--version" in argv: print("%s %s" % (APP, VERSION)); return 0
    if "--extract-helper" in argv:                         # no GUI: copy the polkit helper files somewhere root can read them
        i = argv.index("--extract-helper"); dest = argv[i + 1] if len(argv) > i + 1 and not argv[i + 1].startswith("-") else str(Path.home() / "fetchstudio-helper")
        p = extract_helper(dest); print("Helper files copied to %s\nInstall them with:\n  cd \"%s\" && sudo sh install-helper.sh" % (p, p)); return 0
    app = QApplication(argv); app.setApplicationName(APP); w = Main(); w.show(); return app.exec()

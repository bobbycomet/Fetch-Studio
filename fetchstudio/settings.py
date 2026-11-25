"""Settings tab. Calendar support: opt-in helper setup, then Install cal / Uninstall cal / Remove helper buttons as they apply."""
from .common import *
from .caltool import *
from .caltool import install_cal as _install_cal, remove_cal as _remove_cal

class SettingsDialog(QWidget):    # a page of the main tab bar
    def __init__(s, win):
        super().__init__(); s.win = win
        s.lay = QVBoxLayout(s); s.lay.setSpacing(10); s.lay.setContentsMargins(24, 20, 24, 20)
        t = QLabel("<span style='font-size:15pt'><b>Settings</b></span><br><br><b>Calendar support</b>"); s.lay.addWidget(t)
        s.status = QLabel(); s.status.setWordWrap(True); s.status.setTextFormat(Qt.TextFormat.RichText); s.lay.addWidget(s.status)
        s.btns = QVBoxLayout(); s.btns.setAlignment(Qt.AlignmentFlag.AlignLeft); s.lay.addLayout(s.btns); s.lay.addStretch(1)
        s.ver = QLabel("%s %s" % (APP, VERSION)); s.ver.setStyleSheet("color:#888"); s.lay.addWidget(s.ver)
        s.refresh()

    def button(s, text, fn):
        b = QPushButton(text); b.clicked.connect(fn); s.btns.addWidget(b); b.show(); return b      # widgets added after the window is shown stay hidden unless shown explicitly

    def refresh(s):
        while s.btns.count():
            w = s.btns.takeAt(0).widget()
            if w: w.hide(); w.setParent(None); w.deleteLater()
        cal, helper, cmd = have_cal(), helper_installed(), manual_command()
        st = ["The Clock readout's calendar needs the <code>cal</code> command: <b>%s</b>." % ("installed ✔" if cal else "not installed")]
        if not pkexec_available():
            if not cal:
                st.append("This system has no <code>pkexec</code> (polkit), so Fetch Studio cannot install it for you." + ("<br>Run: <code>%s</code>" % cmd if cmd else ""))
                if cmd: s.button("Copy command", lambda: QApplication.clipboard().setText(cmd))
            s.status.setText("<br><br>".join(st)); return
        if cal:
            b = s.button("Install cal", lambda: None); b.setEnabled(False); b.setToolTip("cal is already installed")
        else:
            st.append("Fetch Studio can install it for you. The first time, it also sets up a small root-owned helper that can do only two things: install <code>cal</code> and remove it again. "
                      "You are asked for your administrator password once.")
            s.button("Install cal", s.win.install_cal_flow)
        if cal_removable(): s.button("Uninstall cal", s.win.remove_cal_flow)
        elif cal and family() != "debian": st.append("<span style='color:#888'><code>cal</code> is part of <code>util-linux</code> on this distribution, a core package, so Fetch Studio never removes it.</span>")
        if helper: st.append("Helper: <b>installed ✔</b>"); s.button("Remove helper", s.win.remove_helper_flow)
        s.status.setText("<br><br>".join(st))

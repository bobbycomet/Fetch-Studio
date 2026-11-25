import copy, io, json, os, sys, tempfile, unittest, zipfile
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PyQt6.QtWidgets import QApplication
APP = QApplication.instance() or QApplication([])
import fetchstudio.security as sec
from fetchstudio.validation import *
from fetchstudio.model import Graph, default_graph
from fetchstudio.compiler import compile_graph, compose
from fetchstudio.build import gen_script
from fetchstudio import caltool

def good():
    return default_graph("t", "advanced").dump()

def mkzip(path, entries):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for n, d in entries.items(): z.writestr(n, d if isinstance(d, (bytes, str)) else json.dumps(d))

class Validation(unittest.TestCase):
    def test_default_projects_valid(self):
        for p in ("classic", "advanced", "custom"): validate_project(default_graph("t", p).dump())
    def bad(self, mut, frag=""):
        d = copy.deepcopy(good()); mut(d)
        with self.assertRaises(ProjectError) as cm: validate_project(d)
        self.assertIn(frag, str(cm.exception))
    def test_unknown_type(self): self.bad(lambda d: d["nodes"][1].__setitem__("type", "evil"), "unknown type")
    def test_duplicate_ids(self): self.bad(lambda d: d["nodes"][2].__setitem__("id", d["nodes"][1]["id"]), "duplicate node id")
    def test_missing_output(self): self.bad(lambda d: d.__setitem__("nodes", [n for n in d["nodes"] if n["type"] != "output"]), "no Output")
    def test_two_outputs(self):
        def m(d): o = [n for n in d["nodes"] if n["type"] == "output"][0]; d["nodes"].append(dict(copy.deepcopy(o), id="zz"))
        self.bad(m, "more than one")
    def test_edge_missing_node(self): self.bad(lambda d: d["edges"].append(["nope", d["edges"][0][1]]), "missing node")
    def test_edge_wrong_direction(self): self.bad(lambda d: d["edges"].append([d["edges"][0][1], d["edges"][0][0]]), "into the Output")
    def test_duplicate_edge(self): self.bad(lambda d: d["edges"].append(list(d["edges"][0])), "duplicate connection")
    def test_bad_color(self): self.bad(lambda d: d["nodes"][1]["params"].__setitem__("color", "red; rm -rf ~"), "color")
    def test_bad_int(self): self.bad(lambda d: [n for n in d["nodes"] if n["type"] == "output"][0]["params"].__setitem__("gap", 9999), "whole number")
    def test_bad_combo(self): self.bad(lambda d: [n for n in d["nodes"] if n["type"] == "output"][0]["params"].__setitem__("preset", "x"), "valid value")
    def test_asset_traversal(self):
        def m(d): n = [n for n in d["nodes"] if n["type"] == "logo"][0]; n["params"]["file"] = "assets/../../../etc/passwd"
        self.bad(m, "asset path")
    def test_asset_abs(self):
        def m(d): n = [n for n in d["nodes"] if n["type"] == "logo"][0]; n["params"]["file"] = "/etc/passwd"
        self.bad(m, "asset path")
    def test_huge_text(self): self.bad(lambda d: [n for n in d["nodes"] if n["type"] == "title"][0]["params"].__setitem__("color", "#" + "a" * 5000), "color")
    def test_too_many_nodes(self): self.bad(lambda d: d.__setitem__("nodes", d["nodes"] * 200), "too many")
    def test_bad_group(self): self.bad(lambda d: d["nodes"][1].__setitem__("group", "ghost"), "missing group")
    def test_missing_params_filled(self):
        d = good()
        for n in d["nodes"]:
            if n["type"] == "info": n["params"] = {"field": "Kernel"}
        c = validate_project(d); i = [n for n in c["nodes"] if n["type"] == "info"][0]
        self.assertIn("key_color", i["params"])
    def test_unknown_params_dropped(self):
        d = good(); d["nodes"][1]["params"]["__evil"] = "x"; c = validate_project(d)
        self.assertNotIn("__evil", c["nodes"][1]["params"])
    def test_legacy_metric(self):
        d = default_graph("t", "custom").dump(); d["nodes"].append(dict(id="b1", type="bar", x=0, y=0, group=None, params={"metric": "Disk"}))
        d["edges"].append(["b1", [n for n in d["nodes"] if n["type"] == "output"][0]["id"]])
        c = validate_project(d); self.assertEqual([n for n in c["nodes"] if n["type"] == "bar"][0]["params"]["metrics"], ["Disk"])
    def test_roundtrip_graph_load(self):
        g = Graph.load(validate_project(good()), "t"); self.assertTrue(compile_graph(g))

class Zip(unittest.TestCase):
    def setUp(self): self.dir = tempfile.mkdtemp(); self.p = os.path.join(self.dir, "x.zip")
    def test_ok(self):
        mkzip(self.p, {"project.json": good()}); d, a, w = read_project_zip(self.p); self.assertEqual(a, {})
    def test_traversal_entry(self):
        mkzip(self.p, {"project.json": good(), "assets/../evil.png": b"x"})
        with self.assertRaises(ProjectError): read_project_zip(self.p)
    def test_unexpected_entry(self):
        mkzip(self.p, {"project.json": good(), "run.sh": b"#!/bin/sh"})
        with self.assertRaisesRegex(ProjectError, "unexpected ZIP entry"): read_project_zip(self.p)
    def test_nested_asset(self):
        mkzip(self.p, {"project.json": good(), "assets/a/b.png": b"x"})
        with self.assertRaises(ProjectError): read_project_zip(self.p)
    def test_bad_extension(self):
        mkzip(self.p, {"project.json": good(), "assets/a.sh": b"x"})
        with self.assertRaisesRegex(ProjectError, "not allowed"): read_project_zip(self.p)
    def test_not_image(self):
        mkzip(self.p, {"project.json": good(), "assets/a.png": b"not a png"})
        with self.assertRaisesRegex(ProjectError, "readable image"): read_project_zip(self.p)
    def test_real_png(self):
        from PyQt6.QtGui import QImage, QColor
        from PyQt6.QtCore import QBuffer, QByteArray, QIODevice
        im = QImage(8, 8, QImage.Format.Format_ARGB32); im.fill(QColor("red")); ba = QByteArray(); b = QBuffer(ba); b.open(QIODevice.OpenModeFlag.WriteOnly); im.save(b, "PNG")
        mkzip(self.p, {"project.json": good(), "assets/a.png": bytes(ba)}); d, a, w = read_project_zip(self.p); self.assertIn("a.png", a)
    def test_oversize_project(self):
        mkzip(self.p, {"project.json": " " * (3 * 1024 * 1024)})
        with self.assertRaisesRegex(ProjectError, "too large"): read_project_zip(self.p)
    def test_zip_bomb_ratio(self):
        mkzip(self.p, {"project.json": good(), "assets/bomb.txt": b"0" * (200 * 1024)})            # under the txt limit: fine
        read_project_zip(self.p)
        big = os.path.join(self.dir, "b.zip"); mkzip(big, {"project.json": good(), "assets/bomb.png": b"\0" * (15 * 1024 * 1024)})
        with self.assertRaisesRegex(ProjectError, "compression ratio"): read_project_zip(big)
    def test_too_many_entries(self):
        mkzip(self.p, dict({"project.json": good()}, **{"assets/%d.txt" % i: b"x" for i in range(400)}))
        with self.assertRaisesRegex(ProjectError, "too many entries"): read_project_zip(self.p)
    def test_not_a_zip(self):
        open(self.p, "wb").write(b"garbage")
        with self.assertRaises(ProjectError): read_project_zip(self.p)
    def test_duplicate_entries(self):
        with zipfile.ZipFile(self.p, "w") as z:
            z.writestr("project.json", json.dumps(good())); z.writestr("assets/a.txt", "a"); z.writestr("assets/A.txt", "b")
        with self.assertRaisesRegex(ProjectError, "duplicate ZIP entry"): read_project_zip(self.p)

class Security(unittest.TestCase):
    def setUp(self):
        sec.TRUST_FILE = type(sec.TRUST_FILE)(tempfile.mkdtemp()) / "trusted.json"; sec._TRUST.update(loaded=False, hashes=set())
    def test_elevation_detected(self):
        for c in ("sudo reboot", "echo hi; sudo id", "x && pkexec ls", "FOO=1 doas sh", "(su -c id)", "echo `sudo id`", "$(sudo id)", "su"):
            self.assertTrue(sec.is_elevated(c), c)
        for c in ("echo sudoku", "uname -r", "cat /etc/issue", "pseudo --x", "echo user"): self.assertFalse(sec.is_elevated(c), c)
    def test_trust_flow(self):
        self.assertEqual(sec.cmd_status("date"), "untrusted"); self.assertTrue(sec.trust_command("date")); self.assertEqual(sec.cmd_status("date"), "trusted")
        sec._TRUST.update(loaded=False, hashes=set()); self.assertEqual(sec.cmd_status("date"), "trusted")          # persisted
        self.assertFalse(sec.trust_command("sudo id")); self.assertEqual(sec.cmd_status("sudo id"), "blocked")
        self.assertEqual(sec.cmd_status("  "), "empty")
    def graph(self, cmd):
        g = default_graph("t", "custom"); o = [i for i, n in g.nodes.items() if n["type"] == "output"][0]
        i = g.add("info", 0, 0, field="Custom", command=cmd); g.edges.append((i, o)); return g
    def test_preview_never_runs_untrusted(self):
        marker = os.path.join(tempfile.mkdtemp(), "pwned"); g = self.graph("touch %s; echo x" % marker)
        c = compile_graph(g)
        import time
        for _ in range(3): compose(c, 0); time.sleep(0.3)
        self.assertFalse(os.path.exists(marker))
    def test_build_skips_untrusted(self):
        g = self.graph("echo hi"); s = gen_script(compile_graph(g, True)); self.assertNotIn("echo hi", s)
    def test_build_includes_trusted_wrapped(self):
        sec.trust_command("echo hi 'there'"); g = self.graph("echo hi 'there'"); s = gen_script(compile_graph(g, True))
        self.assertIn("bash -c", s); self.assertIn("Custom command", s); self.assertNotIn("sudo", s.replace("never writes sudo", ""))
    def test_blocked_never_built(self):
        g = self.graph("sudo id"); s = gen_script(compile_graph(g, True)); self.assertNotIn("sudo id", s)
    def test_syntax_error_command_cannot_break_script(self):
        import subprocess
        sec.trust_command("echo ) ( oops"); s = gen_script(compile_graph(self.graph("echo ) ( oops"), True))
        p = os.path.join(tempfile.mkdtemp(), "f.sh"); open(p, "w").write(s)
        r = subprocess.run(["bash", "-n", p], capture_output=True, text=True); self.assertEqual(r.returncode, 0, r.stderr)
    def test_generated_script_valid_bash(self):
        import subprocess
        for preset in ("classic", "advanced"):
            p = os.path.join(tempfile.mkdtemp(), "f.sh"); open(p, "w").write(gen_script(compile_graph(default_graph("t", preset), True)))
            self.assertEqual(subprocess.run(["bash", "-n", p]).returncode, 0)

class Cal(unittest.TestCase):
    def test_manual_commands(self):
        self.assertEqual(caltool.MANUAL["debian"], "sudo apt update && sudo apt install ncal"); self.assertIn("dnf install util-linux", caltool.MANUAL["fedora"])
        self.assertIn("pacman -S util-linux", caltool.MANUAL["arch"]); self.assertIn("zypper install util-linux", caltool.MANUAL["suse"])
    def test_helper_files_present_and_sane(self):
        import subprocess
        for f in caltool.HELPER_FILES: self.assertTrue((caltool.RESOURCE_DIR / f).is_file(), f)
        for f in ("fetchstudio-cal-helper", "install-helper.sh"): self.assertEqual(subprocess.run(["sh", "-n", str(caltool.RESOURCE_DIR / f)]).returncode, 0)
        pol = (caltool.RESOURCE_DIR / "io.github.bobbycomet.fetchstudio.policy").read_text()
        self.assertIn("/usr/libexec/fetchstudio/fetchstudio-cal-helper", pol); self.assertIn("exec.argv1", pol)
        import xml.dom.minidom; xml.dom.minidom.parseString(pol)
    def test_helper_rejects_bad_args_and_non_root(self):
        import subprocess
        h = str(caltool.RESOURCE_DIR / "fetchstudio-cal-helper")
        r = subprocess.run(["sh", h, "install"], capture_output=True, text=True)
        if os.geteuid() != 0: self.assertEqual(r.returncode, 2)
    def test_extract(self):
        d = caltool.extract_helper(tempfile.mkdtemp()); self.assertTrue((d / "install-helper.sh").exists())
    def test_helper_not_installed_here(self): self.assertFalse(caltool.helper_installed())

if __name__ == "__main__": unittest.main()

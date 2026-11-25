"""Node graph scene, items and view."""
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


# ------------------------------------------------------------------ graph items
class Port(QGraphicsEllipseItem):
    def __init__(s, node, out):
        super().__init__(-7, -7, 14, 14, node); s.node, s.out = node, out
        s.setBrush(QColor("#eee")); s.setPen(QPen(QColor("#222"), 2)); s.setZValue(3)
        s.setCursor(Qt.CursorShape.CrossCursor)
    def mousePressEvent(s, e):
        if e.button() == Qt.MouseButton.LeftButton: s.scene().begin_link(s); e.accept()
    def mouseMoveEvent(s, e): s.scene().drag_link(e.scenePos())
    def mouseReleaseEvent(s, e): s.scene().end_link(e.scenePos())

class NodeItem(QGraphicsItem):
    W, H = 176, 64
    def __init__(s, d):
        super().__init__(); s.d = d; s.edges = []; s.ready = False
        s.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
                   QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        s.setPos(d["x"], d["y"]); s.port = Port(s, d["type"] != "output")
        s.port.setPos(s.W if s.port.out else 0, s.H / 2 + 8); s.ready = True
    def boundingRect(s): return QRectF(-8, -8, s.W + 16, s.H + 16)
    def summary(s):
        p, t = s.d["params"], s.d["type"]
        if t == "info" and p.get("field") in GROUPS:
            n = sum(1 for i in GROUPS[p["field"]] if i[0] in (p.get("items") or [])); return ("%s · %d item%s" % (p["field"], n, "" if n == 1 else "s"))[:24]
        if t == "bar": return (", ".join(m for m in METRICS if m in (p.get("metrics") or [])) or "none selected")[:24]
        v = {"info": p.get("label") or FIELD_LABELS.get(p.get("field"), p.get("field")), "logo": p.get("source"), "title": "user@host",
             "output": f'{p.get("preset")} / {p.get("animation")}', "text": p.get("text"),
             "colors": f'{p.get("rows")} row(s)', "clogo": (p.get("data") or {}).get("name"),
             "divider": p.get("label") or "divider"}.get(t, "")
        return str(v)[:24]
    def paint(s, p, o, w):
        title, col, _ = SPEC[s.d["type"]]; p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#233446")); p.setPen(QPen(QColor("#66c0f4") if s.isSelected() else QColor("#3d5a73"), 2))
        p.drawRoundedRect(QRectF(0, 0, s.W, s.H), 8, 8)
        p.setBrush(QColor(col)); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(0, 0, s.W, 22), 8, 8); p.drawRect(QRectF(0, 12, s.W, 10))
        p.setPen(QColor("white")); p.drawText(QRectF(8, 0, s.W, 22), Qt.AlignmentFlag.AlignVCenter, title)
        p.setPen(QColor("#bbb")); p.drawText(QRectF(12, 26, s.W - 24, s.H - 28), Qt.AlignmentFlag.AlignVCenter, s.summary())
        if s.d["type"] == "info" and s.d["params"].get("field") == "Custom":          # custom command that will not run
            st = cmd_status(s.d["params"].get("command", ""))
            if st in ("untrusted", "blocked"):
                p.setPen(QColor("#ff9f43" if st == "untrusted" else "#ff6b6b"))
                p.drawText(QRectF(s.W - 70, 0, 64, 22), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, "⚠ cmd" if st == "untrusted" else "⛔ cmd")
    def itemChange(s, ch, v):
        if ch == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged and s.ready:
            s.d["x"], s.d["y"] = v.x(), v.y()
            for e in s.edges: e.refresh()
            if s.scene(): s.scene().moved()
        return super().itemChange(ch, v)

class EdgeItem(QGraphicsPathItem):
    def __init__(s, a, b):
        super().__init__(); s.a, s.b = a, b; s.setPen(QPen(QColor("#9ab"), 2.5)); s.setZValue(-1)
        a.edges.append(s); b.edges.append(s)
    def refresh(s):
        p1, p2 = s.a.scene().anchor_for(s.a), s.b.port.scenePos(); dx = max(40, abs(p2.x() - p1.x()) / 2)
        path = QPainterPath(p1); path.cubicTo(p1 + QPointF(dx, 0), p2 - QPointF(dx, 0), p2); s.setPath(path)

class GroupItem(QGraphicsItem):
    def __init__(s, gid, scn): super().__init__(); s.gid, s.scn, s.box = gid, scn, QRectF(); s.setZValue(-2)
    def info(s): return s.scn.g.groups[s.gid]
    def collapsed(s): return s.info()["collapsed"]
    def members(s): return [n for n in s.scn.nitems.values() if n.d["group"] == s.gid]
    def anchor(s): return QPointF(s.box.right(), s.box.center().y())
    def boundingRect(s): return s.box.adjusted(-2, -2, 2, 2)
    def refresh(s):
        m = s.members(); s.prepareGeometryChange()
        if not m: s.box = QRectF(); return
        if s.collapsed():
            x, y = s.info()["pos"]; s.box = QRectF(x, y, 176, 34)
            for n in m: n.setVisible(False)
        else:
            r = m[0].sceneBoundingRect()
            for n in m[1:]: r = r.united(n.sceneBoundingRect())
            s.box = r.adjusted(-8, -30, 8, 8)
            for n in m: n.setVisible(True)
        s.update()
    def paint(s, p, o, w):
        p.setRenderHint(QPainter.RenderHint.Antialiasing); c = QColor("#e67e22"); f = QColor(c)
        f.setAlpha(120 if s.collapsed() else 28); p.setBrush(f); p.setPen(QPen(c, 1.5, Qt.PenStyle.DashLine))
        p.drawRoundedRect(s.box, 10, 10); p.setPen(QColor("#f5cba7"))
        txt = ("▸ %s  (%d nodes)" % (s.info()["name"], len(s.members()))) if s.collapsed() else "▾ " + s.info()["name"]
        p.drawText(QRectF(s.box.left() + 10, s.box.top(), s.box.width(), 30 if not s.collapsed() else 34),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, txt)

class GraphScene(QGraphicsScene):
    def __init__(s, win):
        super().__init__(); s.win = win; s.g = None; s.nitems = {}; s.gitems = {}; s.link = s.tmp = None
        s.setSceneRect(-4000, -4000, 8000, 8000)
    def drawBackground(s, p, r):
        p.fillRect(r, QColor("#0f131a")); p.setPen(QPen(QColor("#171d27"), 1)); st = 40
        x = int(r.left()) // st * st
        while x < r.right(): p.drawLine(x, int(r.top()), x, int(r.bottom())); x += st
        y = int(r.top()) // st * st
        while y < r.bottom(): p.drawLine(int(r.left()), y, int(r.right()), y); y += st
    def load(s, g):
        s.clear(); s.g = g; s.nitems = {}; s.gitems = {}; s.link = s.tmp = None
        for i, d in g.nodes.items(): n = NodeItem(d); s.addItem(n); s.nitems[i] = n
        for gid in g.groups: gi = GroupItem(gid, s); s.addItem(gi); s.gitems[gid] = gi
        for a, b in g.edges:
            if a in s.nitems and b in s.nitems: s.add_edge(a, b)
        s.refresh_groups()
    def add_edge(s, a, b): e = EdgeItem(s.nitems[a], s.nitems[b]); s.addItem(e); e.refresh()
    def anchor_for(s, n):
        gi = s.gitems.get(n.d["group"])
        return gi.anchor() if gi and gi.collapsed() else n.port.scenePos()
    def refresh_groups(s):
        for gi in s.gitems.values(): gi.refresh()
        for n in s.nitems.values():
            for e in n.edges: e.refresh()
    def moved(s): s.refresh_groups(); s.win.touch()
    def add_node(s, t, pos, **over):
        i = s.g.add(t, pos.x(), pos.y(), **over); n = NodeItem(s.g.nodes[i]); s.addItem(n); s.nitems[i] = n
        s.clearSelection(); n.setSelected(True); s.win.touch(); return i
    # links
    def begin_link(s, port):
        s.link = port; s.tmp = QGraphicsPathItem(); s.tmp.setPen(QPen(QColor("#ffd33d"), 2, Qt.PenStyle.DashLine)); s.addItem(s.tmp)
    def drag_link(s, pos):
        if s.tmp: pa = QPainterPath(s.link.scenePos()); pa.lineTo(pos); s.tmp.setPath(pa)
    def end_link(s, pos):
        if s.tmp: s.removeItem(s.tmp); s.tmp = None
        for it in s.items(pos):
            if isinstance(it, Port) and it is not s.link and it.out != s.link.out:
                o, i = (s.link, it) if s.link.out else (it, s.link)
                k = (o.node.d["id"], i.node.d["id"])
                if k not in s.g.edges: s.g.edges.append(k); s.add_edge(*k); s.win.touch()
                break
        s.link = None
    def remove_edge(s, e):
        e.a.edges.remove(e); e.b.edges.remove(e); s.removeItem(e)
        k = (e.a.d["id"], e.b.d["id"])
        if k in s.g.edges: s.g.edges.remove(k)
        s.win.touch()
    def sel_nodes(s): return [i for i in s.selectedItems() if isinstance(i, NodeItem) and i.d["type"] != "output"]
    def delete_selected(s):
        for n in s.sel_nodes():
            for e in list(n.edges): s.remove_edge(e)
            s.removeItem(n); del s.nitems[n.d["id"]]; del s.g.nodes[n.d["id"]]
        s.prune_groups(); s.win.touch()
    def prune_groups(s):
        for gid in list(s.g.groups):
            if not any(n.d["group"] == gid for n in s.nitems.values()):
                s.removeItem(s.gitems.pop(gid)); del s.g.groups[gid]
        s.refresh_groups()
    def group_selected(s):
        sel = s.sel_nodes()
        if len(sel) < 2: return
        name, ok = QInputDialog.getText(s.win, "Group nodes", "Group name:", text="Group")
        if not ok: return
        gid = uuid.uuid4().hex[:6]; s.g.groups[gid] = dict(name=name or "Group", collapsed=False, pos=[0, 0])
        gi = GroupItem(gid, s); s.addItem(gi); s.gitems[gid] = gi
        for n in sel: n.d["group"] = gid
        s.prune_groups(); s.win.touch()
    def toggle_group(s, gid):
        gi, info = s.gitems[gid], s.g.groups[gid]
        if not info["collapsed"]: info["pos"] = [gi.box.left(), gi.box.top()]
        info["collapsed"] = not info["collapsed"]; s.refresh_groups(); s.win.touch()
    def rename_group(s, gid):
        name, ok = QInputDialog.getText(s.win, "Rename group", "Name:", text=s.g.groups[gid]["name"])
        if ok and name: s.g.groups[gid]["name"] = name; s.gitems[gid].update(); s.win.touch()
    def ungroup(s, gid):
        for n in s.nitems.values():
            if n.d["group"] == gid: n.d["group"] = None
        s.gitems[gid].refresh(); s.prune_groups(); s.win.touch()

class GraphView(QGraphicsView):
    """left-drag pan | shift+left-drag box select | right-click menu | wheel scroll | ctrl+wheel zoom"""
    def __init__(s, scene, win):
        super().__init__(scene); s.win = win; s._pan = None
        s.setRenderHints(QPainter.RenderHint.Antialiasing)
        s.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        s.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate); s.centerOn(0, 0)
    def _on_item(s, pos):
        return any(isinstance(i, (NodeItem, Port)) or (isinstance(i, GroupItem) and i.collapsed()) for i in s.items(pos))
    def mousePressEvent(s, e):
        if e.button() == Qt.MouseButton.RightButton: e.accept(); return
        if e.button() == Qt.MouseButton.LeftButton and not s._on_item(e.position().toPoint()):
            if e.modifiers() & Qt.KeyboardModifier.ShiftModifier: s.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            else:
                s._pan = e.position().toPoint(); s.setCursor(Qt.CursorShape.ClosedHandCursor)
                s.scene().clearSelection(); e.accept(); return
        super().mousePressEvent(e)
    def mouseMoveEvent(s, e):
        if s._pan is not None:
            p = e.position().toPoint(); d = p - s._pan; s._pan = p
            s.horizontalScrollBar().setValue(s.horizontalScrollBar().value() - d.x())
            s.verticalScrollBar().setValue(s.verticalScrollBar().value() - d.y())
            if abs(d.x()) + abs(d.y()): s.win.flags["panned"] = True
            return
        super().mouseMoveEvent(e)
    def mouseReleaseEvent(s, e):
        if s._pan is not None: s._pan = None; s.unsetCursor(); return
        super().mouseReleaseEvent(e); s.setDragMode(QGraphicsView.DragMode.NoDrag)
    def wheelEvent(s, e):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            f = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
            if 0.25 < s.transform().m11() * f < 3: s.scale(f, f)
            s.win.flags["panned"] = True; e.accept()
        else: super().wheelEvent(e)
    def keyPressEvent(s, e):
        if e.key() == Qt.Key.Key_Delete: s.scene().delete_selected()
        else: super().keyPressEvent(e)
    def mouseDoubleClickEvent(s, e):
        for i in s.items(e.position().toPoint()):
            if isinstance(i, NodeItem) and i.d["type"] == "clogo": s.win.edit_in_designer(i.d); return
        for i in s.items(e.position().toPoint()):
            if isinstance(i, GroupItem): s.scene().toggle_group(i.gid); return
        super().mouseDoubleClickEvent(e)
    def contextMenuEvent(s, e):
        sc = s.scene(); items = s.items(e.pos()); sp = s.mapToScene(e.pos()); m = QMenu(s)
        for i in items:
            if isinstance(i, NodeItem) and not i.isSelected(): sc.clearSelection(); i.setSelected(True); break
        add = m.addMenu("Add node")
        for t, (title, _, _) in SPEC.items():
            if t == "output" or (t in FANCY_NODES and s.win.classic): continue
            add.addAction(title, lambda _=False, t=t: sc.add_node(t, sp))
        lib = add.addMenu("Library (.fsnode)")
        for pth in lib_list(): lib.addAction(pth.stem, lambda _=False, pth=pth: sc.win.add_library_node(pth))
        lib.addSeparator(); lib.addAction("Import .fsnode…", sc.win.import_node_file)
        m.addAction("Group selected nodes", sc.group_selected)
        nd = next((i for i in items if isinstance(i, NodeItem) and i.d["type"] == "clogo"), None)
        if nd: m.addAction("Edit in ASCII Designer", lambda _=False, d=nd.d: sc.win.edit_in_designer(d))
        gid = next((i.gid for i in items if isinstance(i, GroupItem)), None) or \
              next((i.d["group"] for i in items if isinstance(i, NodeItem) and i.d["group"]), None)
        if gid:
            m.addSeparator(); c = sc.g.groups[gid]["collapsed"]
            m.addAction("Expand group" if c else "Collapse group", lambda: sc.toggle_group(gid))
            m.addAction("Rename group…", lambda: sc.rename_group(gid)); m.addAction("Ungroup", lambda: sc.ungroup(gid))
        ed = next((i for i in items if isinstance(i, EdgeItem)), None)
        if ed: m.addSeparator(); m.addAction("Remove connection", lambda: sc.remove_edge(ed))
        m.addSeparator(); m.addAction("Delete selected nodes", sc.delete_selected); m.exec(e.globalPos())

import os

import FreeCAD as App
import Part

if App.GuiUp:
    from PySide import QtCore, QtGui
    import FreeCADGui as Gui

from freecad.frameforgemod.ff_tools import ICONPATH, translate
from freecad.frameforgemod.frameforgemod_exceptions import FrameForgemodException

TOOL_ICON = os.path.join(ICONPATH, "vent.svg")
smEpsilon = App.Base.Precision.approximation()


def _getElementFromTNP(tnpName):
    names = tnpName.split(".")
    if len(names) > 1:
        App.Console.PrintWarning("Warning: Tnp Name still visible: " + tnpName + "\n")
    return names[len(names) - 1].lstrip("?")


def _smGetThickness(obj, foldface):
    normal = foldface.normalAt(0, 0)
    theVol = obj.Volume
    if theVol < 0.0001:
        raise FrameForgemodException(
            translate("frameforgemod", "Shape is not a real 3D-object or too small!"))
    estimated_thk = theVol / (foldface.Area)
    p1 = foldface.Vertexes[0].Point
    p2 = p1 + estimated_thk * -1.5 * normal
    e1 = Part.makeLine(p1, p2)
    thkedge = obj.common(e1)
    thk = thkedge.Length
    return thk


def _resolve_rib_edges(rib_obj, rib_names, ref_positions=None):
    edges = []
    for i, ename in enumerate(rib_names):
        edge = None
        try:
            edge = rib_obj.Shape.getElement(ename)
        except Exception:
            pass
        if edge is None:
            try:
                plain = _getElementFromTNP(ename)
                edge = rib_obj.Shape.getElement(plain)
            except Exception:
                pass
        if edge is None and ref_positions is not None and i < len(ref_positions):
            ref_pt = ref_positions[i]
            best_dist = float('inf')
            for e in rib_obj.Shape.Edges:
                try:
                    d = e.CenterOfMass.distanceToPoint(ref_pt)
                    if d < best_dist:
                        best_dist = d
                        edge = e
                except (Part.OCCError, AttributeError):
                    continue
            if best_dist > 0.1:
                edge = None
        if edge is not None:
            edges.append(edge)
    return edges


def _make_wire_from_edges(edges):
    if not edges:
        return None
    if len(edges) == 1:
        try:
            wire = Part.Wire(edges)
            face = Part.Face(wire)
            if abs(face.Area) > smEpsilon:
                return wire
        except Part.OCCError:
            pass
        return None
    try:
        sorted_result = Part.sortEdges(edges)
        if sorted_result:
            if isinstance(sorted_result[0], (list, tuple)):
                groups = sorted_result
            else:
                groups = [sorted_result]
            for group in groups:
                try:
                    wire = Part.Wire(group)
                    face = Part.Face(wire)
                    if abs(face.Area) > smEpsilon:
                        return wire
                except Part.OCCError:
                    continue
    except Exception:
        pass
    try:
        adj = {}
        for e in edges:
            verts = e.Vertexes
            if len(verts) < 2:
                continue
            p1 = verts[0].Point
            p2 = verts[-1].Point
            k1 = (round(p1.x, 6), round(p1.y, 6), round(p1.z, 6))
            k2 = (round(p2.x, 6), round(p2.y, 6), round(p2.z, 6))
            if k1 == k2:
                continue
            adj.setdefault(k1, []).append((k2, e))
            adj.setdefault(k2, []).append((k1, e))
        if not adj:
            return None
        for start_key in list(adj.keys()):
            ordered = []
            used_ids = set()
            curr = start_key
            for _ in range(len(edges) + 1):
                if curr not in adj:
                    break
                found = None
                for nxt_key, nxt_edge in adj[curr]:
                    if id(nxt_edge) not in used_ids:
                        found = (nxt_key, nxt_edge)
                        break
                if found is None:
                    break
                nxt_key, nxt_edge = found
                used_ids.add(id(nxt_edge))
                ordered.append(nxt_edge)
                curr = nxt_key
                if curr == start_key and len(ordered) >= 3:
                    break
            if len(ordered) >= 3 and curr == start_key:
                try:
                    wire = Part.Wire(ordered)
                    face = Part.Face(wire)
                    if abs(face.Area) > smEpsilon:
                        return wire
                except Part.OCCError:
                    continue
    except Exception:
        pass
    return None


def find_outer_wire(sketch_shape, rib_edges=None):
    if rib_edges:
        boundary_edges = []
        for e in sketch_shape.Edges:
            is_rib = any(e.isSame(re) for re in rib_edges)
            if not is_rib:
                boundary_edges.append(e)
        if boundary_edges:
            wire = _make_wire_from_edges(boundary_edges)
            if wire is not None:
                return wire
    best_wire = None
    best_area = 0.0
    for wire in sketch_shape.Wires:
        try:
            face = Part.Face(wire)
            area = abs(face.Area)
            if area > best_area:
                best_area = area
                best_wire = wire
        except Part.OCCError:
            continue
    if best_wire is not None and best_area > smEpsilon:
        return best_wire
    try:
        all_wire = _make_wire_from_edges(sketch_shape.Edges)
        if all_wire is not None:
            return all_wire
    except Exception:
        pass
    raise FrameForgemodException(
        translate("frameforgemod",
                  "Cannot find a valid closed boundary wire.\n"
                  "Make sure the boundary edges form a closed loop\n"
                  "and are not connected to rib edges."))


def make_rib_bar(edge, rib_width, sketch_normal, extrude_dir, bar_extend=1000):
    extend = bar_extend
    if isinstance(edge.Curve, Part.Line):
        v = edge.Vertexes
        if len(v) < 2:
            return None
        start = v[0].Point
        end = v[-1].Point
        if start.distanceToPoint(end) < 1e-7:
            return None
        direction = (end - start).normalize()
        perp = direction.cross(sketch_normal).normalize()
        half_w = rib_width / 2.0
        ext_dir = direction * extend
        s = start - ext_dir
        e = end + ext_dir
        p1 = s - perp * half_w
        p2 = s + perp * half_w
        p3 = e + perp * half_w
        p4 = e - perp * half_w
        try:
            wire = Part.makePolygon([p1, p2, p3, p4, p1])
            face = Part.Face(wire)
            return face.extrude(extrude_dir)
        except Part.OCCError:
            return None
    if isinstance(edge.Curve, (Part.Circle,)):
        circle = edge.Curve
        half_w = rib_width / 2.0
        inner_radius = max(circle.Radius - half_w, 0.001)
        outer_radius = circle.Radius + half_w
        inner = Part.Circle()
        inner.Center = circle.Center
        inner.Axis = sketch_normal
        inner.Radius = inner_radius
        outer = Part.Circle()
        outer.Center = circle.Center
        outer.Axis = sketch_normal
        outer.Radius = outer_radius
        inner_edge = Part.Edge(inner)
        outer_edge = Part.Edge(outer)
        try:
            inner_wire = Part.Wire(inner_edge)
            inner_wire.reverse()
            face = Part.Face([Part.Wire(outer_edge), inner_wire])
            return face.extrude(extrude_dir)
        except Part.OCCError:
            return None
    pts = edge.discretize(20)
    if len(pts) < 2:
        return None
    s_dir = (pts[1] - pts[0]).normalize() * extend
    e_dir = (pts[-1] - pts[-2]).normalize() * extend
    pts[0] = pts[0] - s_dir
    pts[-1] = pts[-1] + e_dir
    half_w = rib_width / 2.0
    left_pts = []
    right_pts = []
    for i, p in enumerate(pts):
        if i == 0:
            tangent = (pts[1] - pts[0]).normalize()
        elif i == len(pts) - 1:
            tangent = (pts[-1] - pts[-2]).normalize()
        else:
            tangent = (pts[i + 1] - pts[i - 1]).normalize()
        perp = tangent.cross(sketch_normal)
        if perp.Length < 1e-12:
            continue
        perp.normalize()
        left_pts.append(p + perp * half_w)
        right_pts.append(p - perp * half_w)
    if len(left_pts) < 2:
        return None
    all_pts = left_pts + right_pts[::-1] + [left_pts[0]]
    try:
        wire = Part.makePolygon(all_pts)
        face = Part.Face(wire)
        return face.extrude(extrude_dir)
    except Part.OCCError:
        return None


class VentFeature:
    def __init__(self, obj, selobj, sel_items, sketch):
        _tip = translate("App::Property", "Base Object (face to cut through)")
        obj.addProperty("App::PropertyLinkSub", "baseObject",
                        "Parameters", _tip).baseObject = (selobj, sel_items)

        _tip = translate("App::Property",
                         "Sketch containing the vent boundary")
        obj.addProperty("App::PropertyLink", "Sketch",
                        "Parameters", _tip).Sketch = sketch

        _tip = translate("App::Property",
                         "Edges in the sketch to use as ribs")
        obj.addProperty("App::PropertyLinkSub", "RibEdges",
                        "Parameters", _tip).RibEdges = (sketch, [])

        _tip = translate("App::Property",
                         "Reference positions of rib edges (for TNP recovery)")
        obj.addProperty("App::PropertyVectorList", "RibPositions",
                        "Parameters", _tip)

        obj.addProperty("App::PropertyDistance", "RibWidth",
                        "Parameters",
                        translate("App::Property", "Width of the vent ribs"))
        obj.RibWidth = 2.0

        obj.addProperty("App::PropertyDistance", "FilletRadius",
                        "Parameters",
                        translate("App::Property",
                                  "Fillet radius at rib intersections (0 = no fillet)"))
        obj.FilletRadius = 0.0

        obj.Proxy = self

    def execute(self, fp):
        base_obj = fp.baseObject[0]
        base = base_obj.Shape
        base_sub_names = fp.baseObject[1]
        if not base_sub_names:
            sketch = fp.Sketch
            if hasattr(sketch, "Support") and sketch.Support is not None:
                support = sketch.Support
                if isinstance(support, tuple) and len(support) > 1:
                    base_sub_names = list(support[1]) if isinstance(support[1], (list, tuple)) else [support[1]]
            if not base_sub_names:
                sk_pos = sketch.Placement.Base
                sk_rot = sketch.Placement.Rotation
                sk_normal = sk_rot.multVec(App.Vector(0, 0, 1))
                for i, f in enumerate(base.Faces):
                    if not hasattr(f.Surface, "Axis"):
                        continue
                    try:
                        f_normal = f.normalAt(0, 0)
                        f_pos = f.CenterOfMass
                        parallel = abs(f_normal.dot(sk_normal)) > 0.999
                        if not parallel:
                            continue
                        d1 = f_pos.dot(f_normal)
                        d2 = sk_pos.dot(sk_normal)
                        if abs(d1 - d2) < 0.1:
                            base_sub_names = ["Face{}".format(i + 1)]
                            break
                    except (Part.OCCError, AttributeError):
                        continue
        if not base_sub_names:
            raise FrameForgemodException(
                translate("frameforgemod",
                          "No face selected on the base object.\n"
                          "Please select a face on the object or map the sketch to a face."))
        base_face_name = base_sub_names[0]
        base_face = base.getElement(_getElementFromTNP(base_face_name))
        thk = _smGetThickness(base, base_face)
        if thk < smEpsilon:
            raise FrameForgemodException(
                translate("frameforgemod", "Could not determine material thickness."))

        sketch_obj = fp.Sketch
        sketch_shape = sketch_obj.Shape
        if sketch_shape is None or sketch_shape.isNull():
            raise FrameForgemodException(
                translate("frameforgemod", "Sketch shape is invalid."))
        App.Console.PrintMessage("Vent: sketch {} shape has {} edges, {} wires\n".format(
            sketch_obj.Name,
            len(sketch_shape.Edges),
            len(sketch_shape.Wires)))
        for i, w in enumerate(sketch_shape.Wires):
            App.Console.PrintMessage("  Wire {}: {} edges, closed={}\n".format(
                i, len(w.Edges), w.isClosed()))
        rib_width = fp.RibWidth.Value
        fillet_r = fp.FilletRadius.Value
        sk_rot = sketch_obj.Placement.Rotation
        sketch_normal = sk_rot.multVec(App.Vector(0, 0, 1))
        base_normal = base_face.normalAt(0, 0)
        extrude_dir = base_normal * -thk

        rib_edge_objs = []
        if fp.RibEdges is not None:
            rib_obj, rib_names = fp.RibEdges
            if rib_obj is not None and rib_names:
                ref_positions = getattr(fp, "RibPositions", None)
                rib_edge_objs = _resolve_rib_edges(rib_obj, list(rib_names), ref_positions)
                try:
                    shape_edges = rib_obj.Shape.Edges
                    edge_idx = {id(se): j for j, se in enumerate(shape_edges)}
                    new_names = []
                    for e in rib_edge_objs:
                        j = edge_idx.get(id(e))
                        if j is not None:
                            new_names.append("Edge{}".format(j + 1))
                    if new_names:
                        fp.RibEdges = (rib_obj, new_names)
                except Exception:
                    pass

        try:
            outer_wire = find_outer_wire(sketch_shape, rib_edge_objs)
        except FrameForgemodException:
            if rib_edge_objs:
                try:
                    fp.RibEdges = (fp.Sketch, [])
                    fp.RibPositions = []
                except Exception:
                    pass
                rib_edge_objs = []
                outer_wire = find_outer_wire(sketch_shape, [])
            else:
                raise
        if outer_wire is None:
            raise FrameForgemodException(
                translate("frameforgemod",
                          "Could not determine boundary wire from sketch.\n"
                          "Make sure the sketch has at least one closed wire."))
        boundary_face = Part.Face(outer_wire)
        try:
            cut_solid = boundary_face.extrude(extrude_dir)
            base_hole = base.cut(cut_solid)
        except Part.OCCError as e:
            raise FrameForgemodException(
                translate("frameforgemod", "Failed to cut boundary hole: ") + str(e))

        if not rib_edge_objs:
            fp.Shape = base_hole
            return

        bb = base.BoundBox
        bar_extend = max(bb.XLength, bb.YLength, bb.ZLength) * 5
        if bar_extend < 100:
            bar_extend = 100
        if bar_extend > 10000:
            bar_extend = 10000

        result = base_hole
        for edge in rib_edge_objs:
            bar = make_rib_bar(edge, rib_width, sketch_normal, extrude_dir, bar_extend)
            if bar is None:
                continue
            try:
                clipped = bar.common(base)
                if abs(clipped.Volume) < smEpsilon:
                    continue
                result = result.fuse(clipped)
            except Part.OCCError:
                continue

        if fillet_r > smEpsilon:
            try:
                sk_plane_pos = sketch_obj.Placement.Base
                fe = []
                for e in result.Edges:
                    v = e.Vertexes
                    if len(v) >= 2:
                        d_vec = v[-1].Point - v[0].Point
                        if d_vec.Length > smEpsilon:
                            edir = d_vec.normalize()
                            if abs(abs(edir.dot(sketch_normal)) - 1) < 0.1:
                                mp = v[0].Point + d_vec * 0.5
                                proj_dist = (mp - sk_plane_pos).dot(sketch_normal)
                                proj_mp = mp - sketch_normal * proj_dist
                                try:
                                    inside = boundary_face.isInside(proj_mp, thk, True)
                                except Exception:
                                    inside = False
                                if inside:
                                    fe.append(e)
                if fe:
                    result = result.makeFillet(fillet_r, fe)
            except Part.OCCError:
                pass

        try:
            result = result.removeSplitter()
        except Part.OCCError as e:
            raise FrameForgemodException(
                translate("frameforgemod", "Failed to fuse ribs: ") + str(e))

        fp.Shape = result


def _smHideObjects(*args):
    if App.GuiUp:
        for arg in args:
            if arg:
                obj = Gui.ActiveDocument.getObject(arg.Name)
                if obj:
                    obj.Visibility = False


def _smFindBody(obj):
    if obj.TypeId == 'PartDesign::Body':
        return obj
    if hasattr(obj, 'getParent'):
        p = obj.getParent()
        if p and p.TypeId == 'PartDesign::Body':
            return p
    if hasattr(obj, 'getParentGroup'):
        p = obj.getParentGroup()
        if p and p.TypeId == 'PartDesign::Body':
            return p
    if hasattr(obj, 'getParents'):
        parents = obj.getParents()
        if parents:
            return parents[0][0]
    doc = obj.Document if hasattr(obj, 'Document') else None
    if doc:
        for o in doc.Objects:
            if o.TypeId == 'PartDesign::Body' and hasattr(o, 'Group') and obj in o.Group:
                return o
    return None


if App.GuiUp:

    class VentViewProvider:
        def __init__(self, vobj):
            vobj.Proxy = self
            self.Object = vobj.Object

        def getIcon(self):
            return TOOL_ICON

        def attach(self, vobj):
            self.Object = vobj.Object

        def getDisplayModes(self, obj):
            return []

        def setDisplayMode(self, mode):
            return mode

        def onChanged(self, vp, prop):
            return

        def __getstate__(self):
            return None

        def __setstate__(self, state):
            return None

        def dumps(self):
            return None

        def loads(self, state):
            if state is not None:
                self.Object = App.ActiveDocument.getObject(state.get("ObjectName"))

        def claimChildren(self):
            objs = []
            if hasattr(self.Object, "baseObject") and self.Object.baseObject:
                objs.append(self.Object.baseObject[0])
            if hasattr(self.Object, "Sketch") and self.Object.Sketch:
                objs.append(self.Object.Sketch)
            return objs

        def setEdit(self, vobj, mode):
            if mode != 0:
                return None
            taskd = VentTaskPanel(vobj.Object)
            App.ActiveDocument.openTransaction(self.Object.Name)
            Gui.Control.showDialog(taskd)
            return True

        def unsetEdit(self, _vobj, _mode):
            return False

    class VentTaskPanel:
        def __init__(self, obj):
            self.obj = obj
            self._selection_mode = None
            self._pending_rib_edges = []

            self.form = QtGui.QWidget()
            self.form.setWindowTitle(translate("frameforgemod", "Vent"))
            layout = QtGui.QVBoxLayout(self.form)

            face_group = QtGui.QHBoxLayout()
            self.face_btn = QtGui.QPushButton(translate("frameforgemod", "Select Face"))
            self.face_txt = QtGui.QLineEdit()
            self.face_txt.setReadOnly(True)
            face_group.addWidget(self.face_btn)
            face_group.addWidget(self.face_txt)
            layout.addLayout(face_group)

            sketch_group = QtGui.QHBoxLayout()
            self.sketch_btn = QtGui.QPushButton(translate("frameforgemod", "Select Sketch"))
            self.sketch_txt = QtGui.QLineEdit()
            self.sketch_txt.setReadOnly(True)
            sketch_group.addWidget(self.sketch_btn)
            sketch_group.addWidget(self.sketch_txt)
            layout.addLayout(sketch_group)

            layout.addWidget(QtGui.QLabel(translate("frameforgemod", "Rib Edges (select from sketch):")))

            rib_sel_layout = QtGui.QHBoxLayout()
            self.rib_btn = QtGui.QPushButton(translate("frameforgemod", "Select Ribs"))
            self.rib_clear_btn = QtGui.QPushButton(translate("frameforgemod", "Clear"))
            rib_sel_layout.addWidget(self.rib_btn)
            rib_sel_layout.addWidget(self.rib_clear_btn)
            layout.addLayout(rib_sel_layout)

            self.rib_tree = QtGui.QTreeWidget()
            self.rib_tree.setHeaderLabels([
                translate("frameforgemod", "Object"),
                translate("frameforgemod", "Edge"),
            ])
            self.rib_tree.setRootIsDecorated(False)
            self.rib_tree.setIndentation(0)
            layout.addWidget(self.rib_tree)

            wg = QtGui.QHBoxLayout()
            wg.addWidget(QtGui.QLabel(translate("frameforgemod", "Rib Width:")))
            self.width_spin = QtGui.QDoubleSpinBox()
            self.width_spin.setDecimals(2)
            self.width_spin.setSingleStep(0.5)
            self.width_spin.setMinimum(0.1)
            self.width_spin.setMaximum(100.0)
            wg.addWidget(self.width_spin)
            layout.addLayout(wg)

            fg = QtGui.QHBoxLayout()
            fg.addWidget(QtGui.QLabel(translate("frameforgemod", "Fillet:")))
            self.fillet_spin = QtGui.QDoubleSpinBox()
            self.fillet_spin.setDecimals(2)
            self.fillet_spin.setSingleStep(0.5)
            self.fillet_spin.setMinimum(0.0)
            self.fillet_spin.setMaximum(50.0)
            fg.addWidget(self.fillet_spin)
            layout.addLayout(fg)

            layout.addStretch()

            self.face_btn.clicked.connect(lambda: self._start_pick('face'))
            self.sketch_btn.clicked.connect(lambda: self._start_pick('sketch'))
            self.rib_btn.clicked.connect(lambda: self._start_pick('ribs'))
            self.rib_clear_btn.clicked.connect(self._clear_ribs)
            self.width_spin.valueChanged.connect(self._on_width_changed)
            self.fillet_spin.valueChanged.connect(self._on_fillet_changed)

            self._load_existing_values()

        def _load_existing_values(self):
            try:
                bo = getattr(self.obj, "baseObject", None)
                if bo is not None and hasattr(bo, '__getitem__'):
                    obj_name = ""
                    face_name = ""
                    try:
                        obj_name = bo[0].Name
                    except Exception:
                        pass
                    try:
                        if len(bo) > 1 and bo[1]:
                            face_name = bo[1][0]
                    except Exception:
                        pass
                    if obj_name:
                        text = obj_name
                        if face_name:
                            text += ": " + str(face_name)
                        self.face_txt.setText(text)
            except Exception:
                pass
            try:
                sk = getattr(self.obj, "Sketch", None)
                if sk is not None:
                    self.sketch_txt.setText(sk.Name)
            except Exception:
                pass
            try:
                v = self.obj.RibWidth
                self.width_spin.setValue(getattr(v, "Value", float(v)))
            except Exception:
                self.width_spin.setValue(2.0)
            try:
                v = self.obj.FilletRadius
                self.fillet_spin.setValue(getattr(v, "Value", float(v)))
            except Exception:
                self.fillet_spin.setValue(0.0)
            try:
                rib = getattr(self.obj, "RibEdges", None)
                if rib is not None and hasattr(rib, '__getitem__'):
                    rib_obj = rib[0]
                    rib_names = rib[1]
                    if rib_obj and rib_names:
                        for name in rib_names:
                            item = QtGui.QTreeWidgetItem(self.rib_tree)
                            item.setText(0, rib_obj.Name)
                            item.setText(1, str(name))
            except Exception:
                pass

        def _start_pick(self, mode):
            if self._selection_mode == mode:
                self._end_pick()
                return
            if self._selection_mode is not None:
                self._end_pick()
            self._selection_mode = mode
            Gui.Selection.clearSelection()
            if mode in ('face', 'sketch'):
                Gui.Selection.setSelectionStyle(Gui.Selection.SelectionStyle.NormalSelection)
            elif mode == 'ribs':
                Gui.Selection.setSelectionStyle(Gui.Selection.SelectionStyle.GreedySelection)
            Gui.Selection.addObserver(self)
            if mode == 'face':
                self.face_btn.setText(translate("frameforgemod", "Done"))
                self.face_txt.setText(translate("frameforgemod", "Select a face..."))
            elif mode == 'sketch':
                self.sketch_btn.setText(translate("frameforgemod", "Done"))
                self.sketch_txt.setText(translate("frameforgemod", "Select a sketch..."))
                try:
                    if hasattr(self.obj, "baseObject") and self.obj.baseObject:
                        self.obj.baseObject[0].ViewObject.Visibility = False
                except Exception:
                    pass
            elif mode == 'ribs':
                self.rib_btn.setText(translate("frameforgemod", "Done (click to finish)"))
                rib = getattr(self.obj, "RibEdges", None)
                if rib is not None and hasattr(rib, '__getitem__') and rib[1]:
                    self._pending_rib_edges = list(rib[1])
                else:
                    self._pending_rib_edges = []
                try:
                    if hasattr(self.obj, "baseObject") and self.obj.baseObject:
                        self.obj.baseObject[0].ViewObject.Visibility = False
                    self.obj.ViewObject.Visibility = False
                    if hasattr(self.obj, "Sketch") and self.obj.Sketch:
                        self.obj.Sketch.ViewObject.Visibility = True
                except Exception:
                    pass

        def _end_pick(self):
            if self._selection_mode is not None:
                Gui.Selection.removeObserver(self)
                Gui.Selection.setSelectionStyle(Gui.Selection.SelectionStyle.NormalSelection)
                Gui.Selection.clearSelection()
                mode = self._selection_mode
                self._selection_mode = None
                if mode == 'face':
                    self.face_btn.setText(translate("frameforgemod", "Select Face"))
                elif mode == 'sketch':
                    self.sketch_btn.setText(translate("frameforgemod", "Select Sketch"))
                elif mode == 'ribs':
                    self.rib_btn.setText(translate("frameforgemod", "Select Ribs"))
                    if self._pending_rib_edges:
                        self._apply_rib_edges()
                    self._pending_rib_edges = []
                try:
                    if hasattr(self.obj, "baseObject") and self.obj.baseObject:
                        self.obj.baseObject[0].ViewObject.Visibility = True
                    self.obj.ViewObject.Visibility = True
                except Exception:
                    pass
                self.obj.Document.recompute()

        def addSelection(self, doc, obj, sub, pos):
            if self._selection_mode == 'face':
                sel = Gui.Selection.getSelectionEx()
                if sel and sel[0].SubElementNames:
                    so = sel[0].Object
                    sn = sel[0].SubElementNames[0]
                    self.obj.baseObject = (so, [sn])
                    self.face_txt.setText("{}: {}".format(so.Name, sn))
                    self.obj.Document.recompute()
                    self._end_pick()
            elif self._selection_mode == 'sketch':
                sel = Gui.Selection.getSelection()
                if sel and 'Sketcher' in sel[0].TypeId:
                    sketch = sel[0]
                    self.obj.Sketch = sketch
                    self.sketch_txt.setText(sketch.Name)
                    try:
                        self.obj.RibPositions = []
                    except Exception:
                        pass
                    self.obj.Document.recompute()
                    self._end_pick()
            elif self._selection_mode == 'ribs':
                sel = Gui.Selection.getSelectionEx()
                if sel:
                    for s in sel:
                        if s.HasSubObjects:
                            for i, sub_obj in enumerate(s.SubObjects):
                                if isinstance(sub_obj, Part.Edge):
                                    edge_name = s.SubElementNames[i]
                                    found = False
                                    for pe in self._pending_rib_edges:
                                        if pe[1] == edge_name:
                                            found = True
                                            break
                                    if not found:
                                        self._pending_rib_edges.append(edge_name)

        def _apply_rib_edges(self):
            if not self._pending_rib_edges:
                return
            sketch = self.obj.Sketch
            if sketch is None:
                return
            self.obj.RibEdges = (sketch, list(self._pending_rib_edges))
            self.rib_tree.clear()
            for ename in self._pending_rib_edges:
                item = QtGui.QTreeWidgetItem(self.rib_tree)
                item.setText(0, sketch.Name)
                item.setText(1, ename)
            try:
                resolved = _resolve_rib_edges(sketch, self._pending_rib_edges, None)
                positions = [e.CenterOfMass for e in resolved]
                self.obj.RibPositions = positions
            except Exception:
                pass
            self.obj.Document.recompute()

        def _clear_ribs(self):
            self.rib_tree.clear()
            self._pending_rib_edges = []
            self.obj.RibEdges = (self.obj.Sketch, [])
            self.obj.RibPositions = []
            self.obj.Document.recompute()

        def _on_width_changed(self, val):
            self.obj.RibWidth = val
            self.obj.Document.recompute()

        def _on_fillet_changed(self, val):
            self.obj.FilletRadius = val
            self.obj.Document.recompute()

        def isAllowedAlterSelection(self):
            return True

        def isAllowedAlterView(self):
            return True

        def accept(self):
            self._end_pick()
            try:
                if hasattr(self.obj, "baseObject") and self.obj.baseObject:
                    self.obj.baseObject[0].ViewObject.Visibility = False
                if hasattr(self.obj, "Sketch") and self.obj.Sketch:
                    self.obj.Sketch.ViewObject.Visibility = False
                self.obj.ViewObject.Visibility = True
            except Exception:
                pass
            App.ActiveDocument.commitTransaction()
            App.ActiveDocument.recompute()
            return True

        def reject(self):
            self._end_pick()
            try:
                if hasattr(self.obj, "baseObject") and self.obj.baseObject:
                    self.obj.baseObject[0].ViewObject.Visibility = True
                self.obj.ViewObject.Visibility = True
            except Exception:
                pass
            App.ActiveDocument.abortTransaction()
            App.ActiveDocument.recompute()
            return True

    class AddVentCommand:
        def GetResources(self):
            return {
                "Pixmap": TOOL_ICON,
                "MenuText": translate("frameforgemod", "Add Vent"),
                "Accel": "M, V",
                "ToolTip": translate(
                    "frameforgemod",
                    "Create a vent opening\n"
                    "1. Select a flat face on the object\n"
                    "2. Select a sketch with a closed boundary\n"
                    "3. Select sketch edges as ribs\n"
                    "4. Adjust Rib Width and Fillet in the property editor",
                ),
            }

        def Activated(self):
            sel = Gui.Selection.getSelectionEx()
            if len(sel) < 2:
                App.Console.PrintWarning("FF2: Select a face AND a sketch\n")
                return

            selobj = None
            selected_faces = []
            selected_sketch = None

            for s in sel:
                if s.Object.isDerivedFrom("Sketcher::SketchObject"):
                    selected_sketch = s.Object
                elif s.SubElementNames and any(n.startswith("Face") for n in s.SubElementNames):
                    selobj = s.Object
                    selected_faces = s.SubElementNames
                elif selobj is None:
                    selobj = s.Object
                    selected_faces = s.SubElementNames

            if selobj is None or selected_sketch is None:
                App.Console.PrintWarning("FF2: Select a face AND a sketch\n")
                return

            doc = App.ActiveDocument
            doc.openTransaction("Vent")

            body = _smFindBody(selobj)
            if body is not None:
                newObj = doc.addObject("PartDesign::FeaturePython", "Vent")
            else:
                newObj = doc.addObject("Part::FeaturePython", "Vent")
            VentFeature(newObj, selobj, selected_faces, selected_sketch)
            VentViewProvider(newObj.ViewObject)
            if body is not None:
                body.addObject(newObj)

            doc.recompute()
            newObj.ViewObject.Visibility = True

            panel = VentTaskPanel(newObj)
            Gui.Control.showDialog(panel)

        def IsActive(self):
            return len(Gui.Selection.getSelection()) >= 2

    Gui.addCommand("frameforgemod_AddVent", AddVentCommand())

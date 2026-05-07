import math
import os

import FreeCAD as App
import Part

if App.GuiUp:
    from PySide import QtCore, QtGui
    import FreeCADGui as Gui

from freecad.frameforge2.ff_tools import ICONPATH, translate
from freecad.frameforge2.frameforge_exceptions import FrameForge2Exception

TOOL_ICON = os.path.join(ICONPATH, "extruded-cutout.svg")
smEpsilon = App.Base.Precision.approximation()

PATTERN_TYPES = ["hexagon", "circle", "triangle", "oblong"]
GRID_MODES = ["staggered", "rectangular"]
PATTERN_LABELS = {
    "hexagon": "Hexagon 六边形",
    "circle": "Circle 圆形",
    "triangle": "Triangle 三角形",
    "oblong": "Oblong 长腰型",
}
GRID_LABELS = {
    "staggered": "Staggered 交错",
    "rectangular": "Rectangular 矩形",
}


def _make_hexagon_face(center, size):
    pts = []
    for i in range(6):
        angle = math.pi / 6 + i * math.pi / 3
        pts.append(App.Vector(center.x + size * math.cos(angle),
                              center.y + size * math.sin(angle), 0))
    wire = Part.makePolygon(pts + [pts[0]])
    return Part.Face(wire)


def _make_triangle_face(center, size, angle=0):
    """Equilateral triangle pointing up (angle=0) or rotated."""
    h = size * math.sqrt(3) / 2.0
    r = h * 2.0 / 3.0
    pts = []
    for i in range(3):
        a = angle + i * 2 * math.pi / 3
        pts.append(App.Vector(center.x + r * math.cos(a),
                              center.y + r * math.sin(a), 0))
    wire = Part.makePolygon(pts + [pts[0]])
    return Part.Face(wire)


def _make_circle_face(center, radius):
    c = Part.Circle()
    c.Center = center
    c.Radius = radius
    e = Part.Edge(c)
    w = Part.Wire([e])
    return Part.Face(w)


def _make_oblong_face(center, width, height, angle=0):
    """Capsule/stadium shape."""
    half_w = width / 2.0
    half_h = height / 2.0
    r = min(half_w, half_h)
    if width > height:
        d = half_w - r
        arc1_center = App.Vector(center.x + d, center.y, 0)
        arc2_center = App.Vector(center.x - d, center.y, 0)

        c1 = Part.Circle(arc1_center, App.Vector(0, 0, 1), r)
        c2 = Part.Circle(arc2_center, App.Vector(0, 0, 1), r)
        e1 = Part.Edge(c1)
        e2 = Part.Edge(c2)
        p1 = App.Vector(arc1_center.x, center.y + r, 0)
        p2 = App.Vector(arc2_center.x, center.y + r, 0)
        p3 = App.Vector(arc2_center.x, center.y - r, 0)
        p4 = App.Vector(arc1_center.x, center.y - r, 0)
        l1 = Part.makeLine(p1, p2)
        l2 = Part.makeLine(p3, p4)
        wire = Part.Wire([e1, l1, e2, l2])
    else:
        d = half_h - r
        arc1_center = App.Vector(center.x, center.y + d, 0)
        arc2_center = App.Vector(center.x, center.y - d, 0)
        c1 = Part.Circle(arc1_center, App.Vector(0, 0, 1), r)
        c2 = Part.Circle(arc2_center, App.Vector(0, 0, 1), r)
        e1 = Part.Edge(c1)
        e2 = Part.Edge(c2)
        p1 = App.Vector(center.x + r, arc1_center.y, 0)
        p2 = App.Vector(center.x + r, arc2_center.y, 0)
        p3 = App.Vector(center.x - r, arc2_center.y, 0)
        p4 = App.Vector(center.x - r, arc1_center.y, 0)
        l1 = Part.makeLine(p1, p2)
        l2 = Part.makeLine(p3, p4)
        wire = Part.Wire([e1, l1, e2, l2])
    return Part.Face(wire)


def _make_element(center, size, pattern_type, size_decrease, max_dist, bbox_center):
    actual_size = size
    if size_decrease > 0 and max_dist > 0:
        dist = (center - bbox_center).Length
        factor = 1.0 - size_decrease * (dist / max_dist)
        actual_size = max(size * factor, size * 0.1)
    if pattern_type == "hexagon":
        return _make_hexagon_face(center, actual_size)
    elif pattern_type == "circle":
        return _make_circle_face(center, actual_size)
    elif pattern_type == "triangle":
        return _make_triangle_face(center, actual_size)
    elif pattern_type == "oblong":
        w = actual_size * 2.0
        h = actual_size * 0.6
        return _make_oblong_face(center, w, h)
    return None


def _generate_pattern(boundary_face, boundary_wire, pattern_type, size, spacing,
                      grid_mode, size_decrease, z_plane):
    bb = boundary_face.BoundBox
    bbox_center = App.Vector(bb.Center.x, bb.Center.y, z_plane)
    max_dist = max(bb.XLength, bb.YLength) * 0.71

    elements = []
    if pattern_type == "hexagon":
        col_spacing = size * math.sqrt(3) + spacing
        row_spacing = size * 1.5 + spacing
        row = 0
        y = bb.YMin
        while y <= bb.YMax:
            offset_x = col_spacing / 2.0 if row % 2 == 1 else 0
            x = bb.XMin - size + offset_x
            while x <= bb.XMax + size:
                center = App.Vector(x, y, z_plane)
                test_face = _make_hexagon_face(center, size)
                common = test_face.common(boundary_face)
                if common and hasattr(common, 'Area') and common.Area > smEpsilon:
                    el = _make_element(center, size, pattern_type,
                                       size_decrease, max_dist, bbox_center)
                    if el:
                        elements.append(el)
                x += col_spacing
            y += row_spacing
            row += 1
    else:
        if pattern_type == "circle":
            el_spacing = size * 2 + spacing
        elif pattern_type == "triangle":
            el_spacing = size * math.sqrt(3) + spacing
        elif pattern_type == "oblong":
            el_spacing = size * 2.5 + spacing
        else:
            el_spacing = size * 2 + spacing

        row_spacing = el_spacing
        if grid_mode == "staggered":
            row_spacing = el_spacing * math.sqrt(3) / 2.0
        row = 0
        y = bb.YMin
        while y <= bb.YMax:
            offset_x = el_spacing / 2.0 if (grid_mode == "staggered" and row % 2 == 1) else 0
            x = bb.XMin - size + offset_x
            while x <= bb.XMax + size:
                center = App.Vector(x, y, z_plane)
                if pattern_type == "circle":
                    test_face = _make_circle_face(center, size)
                elif pattern_type == "triangle":
                    test_face = _make_triangle_face(center, size)
                else:
                    test_face = _make_oblong_face(center, size * 2, size * 0.6)
                common = test_face.common(boundary_face)
                if common and hasattr(common, 'Area') and common.Area > smEpsilon:
                    el = _make_element(center, size, pattern_type,
                                       size_decrease, max_dist, bbox_center)
                    if el:
                        elements.append(el)
                x += el_spacing
            y += row_spacing
            row += 1
    return elements


def _findBoundaryWire(sketch_shape):
    if not sketch_shape or sketch_shape.isNull():
        return None
    best = None
    best_area = 0
    for w in sketch_shape.Wires:
        try:
            f = Part.Face(w)
            if abs(f.Area) > best_area:
                best_area = abs(f.Area)
                best = w
        except Part.OCCError:
            continue
    if best:
        return best
    from freecad.frameforge2.create_vent_tool import _make_wire_from_edges
    return _make_wire_from_edges(sketch_shape.Edges)


class PatternFill:
    def __init__(self, obj, selobj, selected_faces, sketch):
        obj.addProperty("App::PropertyLinkSub", "baseObject",
                        "Parameters", "").baseObject = (selobj, selected_faces)
        obj.addProperty("App::PropertyLink", "Sketch",
                        "Parameters", "").Sketch = sketch
        obj.addProperty("App::PropertyEnumeration", "PatternType",
                        "Pattern", "")
        obj.PatternType = PATTERN_TYPES
        obj.PatternType = "hexagon"
        obj.addProperty("App::PropertyDistance", "ElementSize",
                        "Pattern", "").ElementSize = 5.0
        obj.addProperty("App::PropertyDistance", "Spacing",
                        "Pattern", "").Spacing = 2.0
        obj.addProperty("App::PropertyFloat", "SizeDecrease",
                        "Pattern", "").SizeDecrease = 0.0
        obj.addProperty("App::PropertyEnumeration", "GridMode",
                        "Pattern", "").GridMode = GRID_MODES
        obj.addProperty("App::PropertyDistance", "Thickness",
                        "Parameters", "").Thickness = 5.0
        obj.Proxy = self

    def execute(self, fp):
        base_obj = fp.baseObject[0]
        base = base_obj.Shape
        base_sub_names = fp.baseObject[1]
        sketch = fp.Sketch

        base_face = None
        normal = None

        def _resolve_face(names):
            from freecad.frameforge2.create_vent_tool import _getElementFromTNP
            for nm in names:
                try:
                    bf = base.getElement(_getElementFromTNP(nm))
                    if bf.ShapeType == 'Face':
                        return bf, bf.normalAt(0, 0)
                except Exception:
                    continue
            return None, None

        base_face, normal = _resolve_face(base_sub_names)

        if base_face is None:
            if hasattr(sketch, "Support") and sketch.Support is not None:
                s = sketch.Support
                if isinstance(s, tuple) and len(s) > 1:
                    sup = s[1]
                    sup_list = list(sup) if isinstance(sup, (list, tuple)) else [sup]
                    base_face, normal = _resolve_face(sup_list)

        if base_face is None:
            sk_pos = sketch.Placement.Base
            sk_rot = sketch.Placement.Rotation
            sk_normal = sk_rot.multVec(App.Vector(0, 0, 1))
            for i, f in enumerate(base.Faces):
                try:
                    f_normal = f.normalAt(0, 0)
                    if abs(f_normal.dot(sk_normal)) < 0.999:
                        continue
                    f_pos = f.CenterOfMass
                    if abs(f_pos.dot(f_normal) - sk_pos.dot(sk_normal)) < 0.5:
                        base_face = f
                        normal = f_normal
                        break
                except (Part.OCCError, AttributeError):
                    continue

        if base_face is None:
            raise FrameForge2Exception(
                "No face selected on base object.\n"
                "Please select a face or map the sketch to a face.")
        thk = fp.Thickness.Value

        sketch_shape = fp.Sketch.Shape
        boundary_wire = _findBoundaryWire(sketch_shape)
        if boundary_wire is None:
            raise FrameForge2Exception("Cannot find closed boundary in sketch.")
        boundary_face = Part.Face(boundary_wire)
        z_plane = boundary_face.CenterOfMass.z

        elements = _generate_pattern(
            boundary_face, boundary_wire,
            fp.PatternType,
            fp.ElementSize.Value,
            fp.Spacing.Value,
            fp.GridMode,
            fp.SizeDecrease,
            z_plane,
        )
        if not elements:
            fp.Shape = base
            return

        compound = Part.Compound(elements)

        extrude_dir = normal * -thk
        try:
            cut_solid = compound.extrude(extrude_dir)
            result = base.cut(cut_solid)
        except Part.OCCError as e:
            raise FrameForge2Exception("Pattern cut failed: " + str(e))

        try:
            result = result.removeSplitter()
        except Exception:
            pass
        fp.Shape = result


if App.GuiUp:

    class PatternFillVP:
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
            if state is not None and "ObjectName" in state:
                self.Object = App.ActiveDocument.getObject(state["ObjectName"])

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
            taskd = PatternFillTaskPanel(vobj.Object)
            App.ActiveDocument.openTransaction(self.Object.Name)
            Gui.Control.showDialog(taskd)
            return True

        def unsetEdit(self, _vobj, _mode):
            return False

    class PatternFillTaskPanel:
        def __init__(self, obj):
            self.obj = obj
            self.form = QtGui.QWidget()
            self.form.setWindowTitle("Pattern Fill 填充阵列")
            layout = QtGui.QVBoxLayout(self.form)

            t = QtGui.QHBoxLayout()
            t.addWidget(QtGui.QLabel("Pattern 图案:"))
            self.combo_pattern = QtGui.QComboBox()
            self.combo_pattern.addItems([PATTERN_LABELS[p] for p in PATTERN_TYPES])
            t.addWidget(self.combo_pattern)
            layout.addLayout(t)

            g = QtGui.QHBoxLayout()
            g.addWidget(QtGui.QLabel("Layout 排列:"))
            self.combo_grid = QtGui.QComboBox()
            self.combo_grid.addItems([GRID_LABELS[g] for g in GRID_MODES])
            g.addWidget(self.combo_grid)
            layout.addLayout(g)

            sz = QtGui.QHBoxLayout()
            sz.addWidget(QtGui.QLabel("Size 尺寸:"))
            self.spin_size = QtGui.QDoubleSpinBox()
            self.spin_size.setDecimals(2)
            self.spin_size.setSingleStep(1.0)
            self.spin_size.setMinimum(0.5)
            self.spin_size.setMaximum(200.0)
            sz.addWidget(self.spin_size)
            layout.addLayout(sz)

            sp = QtGui.QHBoxLayout()
            sp.addWidget(QtGui.QLabel("Spacing 间距:"))
            self.spin_spacing = QtGui.QDoubleSpinBox()
            self.spin_spacing.setDecimals(2)
            self.spin_spacing.setSingleStep(0.5)
            self.spin_spacing.setMinimum(0.0)
            self.spin_spacing.setMaximum(100.0)
            sp.addWidget(self.spin_spacing)
            layout.addLayout(sp)

            sd = QtGui.QHBoxLayout()
            sd.addWidget(QtGui.QLabel("Gradient 渐变:"))
            self.spin_gradient = QtGui.QDoubleSpinBox()
            self.spin_gradient.setDecimals(2)
            self.spin_gradient.setSingleStep(0.05)
            self.spin_gradient.setMinimum(0.0)
            self.spin_gradient.setMaximum(1.0)
            sd.addWidget(self.spin_gradient)
            layout.addLayout(sd)

            th = QtGui.QHBoxLayout()
            th.addWidget(QtGui.QLabel("Thickness 深度:"))
            self.spin_thk = QtGui.QDoubleSpinBox()
            self.spin_thk.setDecimals(2)
            self.spin_thk.setSingleStep(1.0)
            self.spin_thk.setMinimum(0.5)
            self.spin_thk.setMaximum(200.0)
            th.addWidget(self.spin_thk)
            layout.addLayout(th)

            layout.addStretch()

            self._load_values()

            self.combo_pattern.currentIndexChanged.connect(self._on_pattern_changed)
            self.combo_grid.currentIndexChanged.connect(self._on_grid_changed)
            self.spin_size.valueChanged.connect(self._on_size_changed)
            self.spin_spacing.valueChanged.connect(self._on_spacing_changed)
            self.spin_gradient.valueChanged.connect(self._on_gradient_changed)
            self.spin_thk.valueChanged.connect(self._on_thk_changed)

        def _load_values(self):
            try:
                pt = str(self.obj.PatternType)
                idx = PATTERN_TYPES.index(pt) if pt in PATTERN_TYPES else 0
                self.combo_pattern.setCurrentIndex(idx)
            except Exception:
                pass
            try:
                gm = str(self.obj.GridMode)
                idx = GRID_MODES.index(gm) if gm in GRID_MODES else 0
                self.combo_grid.setCurrentIndex(idx)
            except Exception:
                pass
            try:
                self.spin_size.setValue(self.obj.ElementSize.Value)
            except Exception:
                self.spin_size.setValue(5.0)
            try:
                self.spin_spacing.setValue(self.obj.Spacing.Value)
            except Exception:
                self.spin_spacing.setValue(2.0)
            try:
                self.spin_gradient.setValue(self.obj.SizeDecrease)
            except Exception:
                self.spin_gradient.setValue(0.0)
            try:
                self.spin_thk.setValue(self.obj.Thickness.Value)
            except Exception:
                self.spin_thk.setValue(5.0)

        def _update(self):
            try:
                self.obj.Document.recompute()
            except Exception:
                pass

        def _on_pattern_changed(self, idx):
            if 0 <= idx < len(PATTERN_TYPES):
                self.obj.PatternType = PATTERN_TYPES[idx]
            self._update()

        def _on_grid_changed(self, idx):
            if 0 <= idx < len(GRID_MODES):
                self.obj.GridMode = GRID_MODES[idx]
            self._update()

        def _on_size_changed(self, val):
            self.obj.ElementSize = val
            self._update()

        def _on_spacing_changed(self, val):
            self.obj.Spacing = val
            self._update()

        def _on_gradient_changed(self, val):
            self.obj.SizeDecrease = val
            self._update()

        def _on_thk_changed(self, val):
            self.obj.Thickness = val
            self._update()

        def accept(self):
            try:
                if hasattr(self.obj, "baseObject") and self.obj.baseObject:
                    self.obj.baseObject[0].ViewObject.Visibility = True
                self.obj.ViewObject.Visibility = True
            except Exception:
                pass
            App.ActiveDocument.commitTransaction()
            App.ActiveDocument.recompute()
            return True

        def reject(self):
            try:
                if hasattr(self.obj, "baseObject") and self.obj.baseObject:
                    self.obj.baseObject[0].ViewObject.Visibility = True
            except Exception:
                pass
            App.ActiveDocument.abortTransaction()
            App.ActiveDocument.recompute()
            return True

    class PatternFillCommand:
        def GetResources(self):
            return {
                "Pixmap": TOOL_ICON,
                "MenuText": "Pattern Fill 填充阵列",
                "ToolTip": "Fill sketch boundary with pattern\n填充阵列：选中面和边界草图后自动填充图案\n"
                           "Patterns: Hexagon/Circle/Triangle/Oblong\n"
                           "支持六边形、圆形、三角形、长腰型",
            }

        def Activated(self):
            doc = App.ActiveDocument
            sel = Gui.Selection.getSelectionEx()

            selobj = None
            selected_faces = []
            selected_sketch = None

            for s in sel:
                if s.Object.isDerivedFrom("Sketcher::SketchObject"):
                    selected_sketch = s.Object
                for sn in s.SubElementNames:
                    name = sn.rstrip('.')
                    obj = doc.getObject(name)
                    if obj and obj.isDerivedFrom("Sketcher::SketchObject"):
                        selected_sketch = obj
                    elif 'Face' in sn:
                        selobj = s.Object
                        selected_faces.append(sn)
                if selobj is None and s.HasSubObjects and not s.Object.isDerivedFrom("Sketcher::SketchObject"):
                    selobj = s.Object
                    if not selected_faces:
                        selected_faces = list(s.SubElementNames)

            if selobj is not None and selected_sketch is not None:
                pass
            else:
                App.Console.PrintWarning("FF2: Select face (3D) + sketch (tree, Ctrl+click)\n")
                return

            doc = App.ActiveDocument
            doc.openTransaction("PatternFill")
            from freecad.frameforge2.create_offset_plane_tool import find_body
            body = find_body(selobj)
            if body is not None:
                newObj = doc.addObject("PartDesign::FeaturePython", "PatternFill")
            else:
                newObj = doc.addObject("Part::FeaturePython", "PatternFill")
            PatternFill(newObj, selobj, selected_faces, selected_sketch)
            PatternFillVP(newObj.ViewObject)
            if body is not None:
                body.addObject(newObj)
            doc.recompute()
            newObj.ViewObject.Visibility = True
            panel = PatternFillTaskPanel(newObj)
            Gui.Control.showDialog(panel)

        def IsActive(self):
            return App.ActiveDocument is not None

    Gui.addCommand("FrameForge2_PatternFill", PatternFillCommand())

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

PATTERN_TYPES = ["hexagon", "circle", "triangle", "user sketch"]
GRID_MODES = ["staggered", "rectangular"]
PATTERN_LABELS = {
    "hexagon": "Hexagon 六边形",
    "circle": "Circle 圆形",
    "triangle": "Triangle 三角形",
    "user sketch": "User Sketch 自绘草图",
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
                              center.y + size * math.sin(angle), center.z))
    wire = Part.makePolygon(pts + [pts[0]])
    return Part.Face(wire)


def _make_triangle_face(center, size, angle=-math.pi/2):
    h = size * math.sqrt(3) / 2.0
    r = h * 2.0 / 3.0
    pts = []
    for i in range(3):
        a = angle + i * 2 * math.pi / 3
        pts.append(App.Vector(center.x + r * math.cos(a),
                              center.y + r * math.sin(a), center.z))
    wire = Part.makePolygon(pts + [pts[0]])
    return Part.Face(wire)


def _make_circle_face(center, radius):
    c = Part.Circle()
    c.Center = center
    c.Radius = radius
    e = Part.Edge(c)
    w = Part.Wire([e])
    return Part.Face(w)



def _make_element(center, size, pattern_type, size_decrease, max_dist, bbox_center, angle=None):
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
        return _make_triangle_face(center, actual_size, angle if angle is not None else -math.pi/2)
    return None


def _generate_pattern(boundary_face, boundary_wire, pattern_type, size, spacing_x,
                      spacing_y, grid_mode, size_decrease, face_axes):
    origin, x_axis, y_axis, normal = face_axes

    local_pts = [_project_pt(v.Point, origin, x_axis, y_axis) for v in boundary_face.Vertexes]
    min_x = min(p.x for p in local_pts)
    max_x = max(p.x for p in local_pts)
    min_y = min(p.y for p in local_pts)
    max_y = max(p.y for p in local_pts)

    face_centroid_3d = boundary_face.CenterOfMass
    bbox_center = _project_pt(face_centroid_3d, origin, x_axis, y_axis)
    max_dist = max(max_x - min_x, max_y - min_y) * 0.71

    def _is_inside_2d(x, y):
        center_3d = _unproject_pt(x, y, origin, x_axis, y_axis)
        try:
            return boundary_face.isInside(center_3d, size * 0.5, True)
        except Exception:
            return True

    elements = []
    if pattern_type == "hexagon":
        col_spacing = max(size * math.sqrt(3) + spacing_x, 0.001)
        row_spacing = max(size * 1.5 + spacing_y, 0.001)
        row = 0
        y = min_y
        while y <= max_y:
            offset_x = col_spacing / 2.0 if (grid_mode == "staggered" and row % 2 == 1) else 0
            x = min_x - size + offset_x
            while x <= max_x + size:
                if _is_inside_2d(x, y):
                    center = App.Vector(x, y, 0)
                    local_face = _make_element(center, size, pattern_type,
                                               size_decrease, max_dist, bbox_center)
                    if local_face:
                        world_face = _transform_face_to_world(local_face, origin, x_axis, y_axis, normal)
                        if world_face:
                            elements.append(world_face)
                x += col_spacing
            y += row_spacing
            row += 1
    elif pattern_type == "triangle":
        col_spacing = max(size + spacing_x, 0.001)
        row_spacing = max(size * math.sqrt(3) / 2 + spacing_y, 0.001)
        row = 0
        y = min_y
        while y <= max_y:
            do_stagger = (grid_mode == "staggered")
            offset_x = col_spacing / 2.0 if (do_stagger and row % 2 == 1) else 0
            x = min_x - size + offset_x
            while x <= max_x + size:
                if _is_inside_2d(x, y):
                    center = App.Vector(x, y, 0)
                    angle = (-math.pi/2 if row % 2 == 0 else math.pi/2) if do_stagger else -math.pi/2
                    local_face = _make_element(center, size, pattern_type,
                                               size_decrease, max_dist, bbox_center, angle)
                    if local_face:
                        world_face = _transform_face_to_world(local_face, origin, x_axis, y_axis, normal)
                        if world_face:
                            elements.append(world_face)
                x += col_spacing
            y += row_spacing
            row += 1
    else:
        el_spacing = max(size * 2 + spacing_x, 0.001)
        row_spacing = max(size * 2 + spacing_y, 0.001)
        if grid_mode == "staggered":
            row_spacing = min(row_spacing, el_spacing * math.sqrt(3) / 2.0)
        row = 0
        y = min_y
        while y <= max_y:
            offset_x = el_spacing / 2.0 if (grid_mode == "staggered" and row % 2 == 1) else 0
            x = min_x - size + offset_x
            while x <= max_x + size:
                if _is_inside_2d(x, y):
                    center = App.Vector(x, y, 0)
                    local_face = _make_element(center, size, pattern_type,
                                               size_decrease, max_dist, bbox_center)
                    if local_face:
                        world_face = _transform_face_to_world(local_face, origin, x_axis, y_axis, normal)
                        if world_face:
                            elements.append(world_face)
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


def _get_face_axes(face):
    normal = face.normalAt(0, 0)
    surf = face.Surface
    if hasattr(surf, 'Position'):
        origin = surf.Position
    else:
        origin = face.CenterOfMass
    if hasattr(surf, 'XAxis') and surf.XAxis.Length > 1e-10:
        x_axis = surf.XAxis.normalize()
    else:
        x_axis = App.Vector(1, 0, 0).cross(normal)
        if x_axis.Length < 1e-10:
            x_axis = App.Vector(0, 1, 0).cross(normal)
        x_axis.normalize()
    y_axis = normal.cross(x_axis).normalize()
    return origin, x_axis, y_axis, normal


def _project_pt(point_3d, origin, x_axis, y_axis):
    rel = point_3d - origin
    return App.Vector(rel.dot(x_axis), rel.dot(y_axis), 0)


def _unproject_pt(lx, ly, origin, x_axis, y_axis):
    return origin + x_axis * lx + y_axis * ly


def _transform_face_to_world(local_face, origin, x_axis, y_axis, normal):
    wire = local_face.OuterWire
    edges = wire.Edges

    if len(edges) == 1 and isinstance(edges[0].Curve, Part.Circle):
        circle = edges[0].Curve
        center_3d = origin + x_axis * circle.Center.x + y_axis * circle.Center.y
        c = Part.Circle()
        c.Center = center_3d
        c.Axis = normal
        c.Radius = circle.Radius
        try:
            return Part.Face(Part.Wire([Part.Edge(c)]))
        except Part.OCCError:
            pass

    try:
        pts_3d = [origin + x_axis * v.Point.x + y_axis * v.Point.y for v in wire.Vertexes]
        pts_3d.append(pts_3d[0])
        return Part.Face(Part.makePolygon(pts_3d))
    except Exception:
        return None


def _fill_with_element(boundary_face, element_face, spacing_x, spacing_y, grid_mode, face_axes):
    origin, x_axis, y_axis, normal = face_axes

    local_pts = [_project_pt(v.Point, origin, x_axis, y_axis) for v in boundary_face.Vertexes]
    min_x = min(p.x for p in local_pts)
    max_x = max(p.x for p in local_pts)
    min_y = min(p.y for p in local_pts)
    max_y = max(p.y for p in local_pts)

    try:
        wire = element_face.OuterWire
        verts = list(wire.Vertexes)
        if len(verts) >= 3 and len(verts) >= len(wire.Edges):
            base_pts_3d = [v.Point for v in verts]
            if base_pts_3d and base_pts_3d[0].distanceToPoint(base_pts_3d[-1]) < 1e-7:
                base_pts_3d.pop()
        else:
            base_pts_3d = wire.discretize(24)
    except Exception:
        base_pts_3d = element_face.discretize(24)
    base_pts_local = [_project_pt(p, origin, x_axis, y_axis) for p in base_pts_3d]

    el_min_x = min(p.x for p in base_pts_local)
    el_max_x = max(p.x for p in base_pts_local)
    el_min_y = min(p.y for p in base_pts_local)
    el_max_y = max(p.y for p in base_pts_local)
    el_w = el_max_x - el_min_x
    el_h = el_max_y - el_min_y
    el_cx = (el_min_x + el_max_x) / 2.0
    el_cy = (el_min_y + el_max_y) / 2.0
    el_radius = max(el_w, el_h) / 2.0

    el_spacing = max(el_w + spacing_x, 0.001)
    row_spacing = max(el_h + spacing_y, 0.001)
    if grid_mode == "staggered":
        row_spacing = min(row_spacing, (el_h + spacing_x) * math.sqrt(3) / 2.0)

    def _check_center(cx, cy):
        center_3d = _unproject_pt(cx, cy, origin, x_axis, y_axis)
        try:
            return boundary_face.isInside(center_3d, el_radius, True)
        except Exception:
            return True

    elements = []
    row = 0
    y0 = min_y - el_h
    while y0 <= max_y + el_h:
        ox = el_spacing / 2.0 if (grid_mode == "staggered" and row % 2 == 1) else 0
        x0 = min_x - el_w + ox
        for i in range(int((max_x + el_w - x0) / el_spacing) + 2):
            x = x0 + i * el_spacing
            if not _check_center(x, y0):
                continue
            pts_3d = []
            for p in base_pts_local:
                lx = p.x + x - el_cx
                ly = p.y + y0 - el_cy
                pts_3d.append(origin + x_axis * lx + y_axis * ly)
            pts_3d.append(pts_3d[0])
            try:
                wire = Part.makePolygon(pts_3d)
                world_face = Part.Face(wire)
                if world_face:
                    elements.append(world_face)
            except Part.OCCError:
                continue
        y0 += row_spacing
        row += 1
    return elements


class PatternFill:
    def __init__(self, obj, selobj, selected_faces, sketch, pattern_sketch=None):
        obj.addProperty("App::PropertyLinkSub", "baseObject",
                        "Parameters", "").baseObject = (selobj, selected_faces)
        obj.addProperty("App::PropertyLink", "Sketch",
                        "Parameters", "").Sketch = sketch
        obj.addProperty("App::PropertyLink", "PatternSketch",
                        "Pattern", "").PatternSketch = pattern_sketch
        obj.addProperty("App::PropertyEnumeration", "PatternType",
                        "Pattern", "")
        obj.PatternType = PATTERN_TYPES
        obj.PatternType = "user sketch" if pattern_sketch else "hexagon"
        obj.addProperty("App::PropertyDistance", "ElementSize",
                        "Pattern", "").ElementSize = 5.0
        obj.addProperty("App::PropertyDistance", "Spacing",
                        "Pattern", "").Spacing = 2.0
        obj.addProperty("App::PropertyDistance", "SpacingY",
                        "Pattern", "").SpacingY = 2.0
        obj.addProperty("App::PropertyBool", "LinkSpacing",
                        "Pattern", "").LinkSpacing = True
        obj.addProperty("App::PropertyFloat", "SizeDecrease",
                        "Pattern", "").SizeDecrease = 0.0
        obj.addProperty("App::PropertyEnumeration", "GridMode",
                        "Pattern", "").GridMode = GRID_MODES
        obj.addProperty("App::PropertyDistance", "Thickness",
                        "Parameters", "").Thickness = 10.0
        obj.Proxy = self

    def execute(self, fp):
        base_obj = fp.baseObject[0]
        base = base_obj.Shape
        base_sub_names = fp.baseObject[1]
        sketch = fp.Sketch

        from freecad.frameforge2.create_vent_tool import _getElementFromTNP
        face_found = False
        if base_sub_names:
            try:
                name = _getElementFromTNP(base_sub_names[0])
                if name:
                    bf = base.getElement(name)
                    if bf.ShapeType == 'Face':
                        face_found = True
            except Exception:
                pass
        if not face_found:
            base_sub_names = []
        if not base_sub_names:
            if hasattr(sketch, "Support") and sketch.Support is not None:
                s = sketch.Support
                if isinstance(s, tuple) and len(s) > 1:
                    base_sub_names = list(s[1]) if isinstance(s[1], (list, tuple)) else [s[1]]
            if not base_sub_names:
                try:
                    gp = sketch.getGlobalPlacement()
                    sk_pos = gp.Base
                    sk_norm = gp.Rotation.multVec(App.Vector(0, 0, 1))
                except Exception:
                    sk_pos = sketch.Placement.Base
                    sk_norm = sketch.Placement.Rotation.multVec(App.Vector(0, 0, 1))
                best_face = None
                for i, f in enumerate(base.Faces):
                    try:
                        f_normal = f.normalAt(0, 0)
                        if abs(f_normal.dot(sk_norm)) < 0.999:
                            continue
                        if best_face is None:
                            best_face = ("Face{}".format(i + 1), abs(f.CenterOfMass.dot(f_normal) - sk_pos.dot(sk_norm)))
                        dist = abs(f.CenterOfMass.dot(f_normal) - sk_pos.dot(sk_norm))
                        if dist < 1.0:
                            base_sub_names = ["Face{}".format(i + 1)]
                            break
                        if dist < best_face[1]:
                            best_face = ("Face{}".format(i + 1), dist)
                    except Exception:
                        continue
                if not base_sub_names and best_face:
                    base_sub_names = [best_face[0]]
                    App.Console.PrintMessage("Fill: using closest face {} (offset={:.1f}mm)\n".format(
                        best_face[0], best_face[1]))
        if not base_sub_names:
            raise FrameForge2Exception(
                "No face selected. Select a face on base or map sketch to a face.")

        base_face = base.getElement(_getElementFromTNP(base_sub_names[0]))
        normal = base_face.normalAt(0, 0)

        from freecad.frameforge2.create_vent_tool import _smGetThickness
        thk = _smGetThickness(base, base_face)
        if thk < smEpsilon:
            bb = base.BoundBox
            extent = abs((bb.Max - bb.Min).dot(normal))
            if extent > smEpsilon:
                thk = extent
                App.Console.PrintMessage("Fill: auto thickness={:.2f}\n".format(thk))
            else:
                thk = fp.Thickness.Value

        extrude_dir = normal * -thk

        sketch_shape = fp.Sketch.Shape
        boundary_wire = _findBoundaryWire(sketch_shape)
        if boundary_wire is None:
            raise FrameForge2Exception("Cannot find closed boundary in sketch.")

        boundary_face = Part.Face(boundary_wire)
        face_axes = _get_face_axes(boundary_face)

        sp_x = fp.Spacing.Value
        sp_y = fp.SpacingY.Value if not fp.LinkSpacing else sp_x

        elements = []
        if fp.PatternType == "user sketch":
            if fp.PatternSketch is None:
                raise FrameForge2Exception(
                    "User sketch pattern selected but no pattern sketch assigned.\n"
                    "请先选择一个图案草图。")
            sk = fp.PatternSketch
            if sk.isDerivedFrom("Sketcher::SketchObject"):
                element_face = None
                if sk.Shape.Faces:
                    element_face = max(sk.Shape.Faces, key=lambda f: abs(f.Area))
                if element_face is None:
                    for w in sk.Shape.Wires:
                        try:
                            f = Part.Face(w)
                            if element_face is None or abs(f.Area) > abs(element_face.Area):
                                element_face = f
                        except Part.OCCError:
                            pass
                if element_face is not None:
                    App.Console.PrintMessage("Fill: element face area={:.2f}\n".format(element_face.Area))
                    elements = _fill_with_element(
                        boundary_face, element_face,
                        sp_x, sp_y,
                        fp.GridMode,
                        face_axes,
                    )
                    App.Console.PrintMessage("Fill: generated {} elements\n".format(len(elements)))
        if not elements:
            elements = _generate_pattern(
                boundary_face, boundary_wire,
                fp.PatternType,
                fp.ElementSize.Value,
                sp_x, sp_y,
                fp.GridMode,
                fp.SizeDecrease,
                face_axes,
            )
        if not elements:
            fp.Shape = base
            return

        App.Console.PrintMessage("Fill: total {} elements\n".format(len(elements)))
        if len(elements) > 500:
            App.Console.PrintWarning(
                "Fill: {} elements may be slow, consider larger spacing\n".format(len(elements)))

        compound = Part.Compound(elements)

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

            self.sketch_widget = QtGui.QWidget()
            skg = QtGui.QHBoxLayout(self.sketch_widget)
            skg.setContentsMargins(0, 0, 0, 0)
            self.sketch_btn = QtGui.QPushButton("Sketch 图案")
            self.sketch_txt = QtGui.QLineEdit()
            self.sketch_txt.setReadOnly(True)
            skg.addWidget(self.sketch_btn)
            skg.addWidget(self.sketch_txt)
            layout.addWidget(self.sketch_widget)

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
            sp.addWidget(QtGui.QLabel("Spacing X 水平间距:"))
            self.spin_spacing = QtGui.QDoubleSpinBox()
            self.spin_spacing.setDecimals(2)
            self.spin_spacing.setSingleStep(0.5)
            self.spin_spacing.setMinimum(-50.0)
            self.spin_spacing.setMaximum(100.0)
            sp.addWidget(self.spin_spacing)
            layout.addLayout(sp)

            self.link_check = QtGui.QCheckBox("Unify XY 统一间距")
            self.link_check.setChecked(True)
            layout.addWidget(self.link_check)

            spy = QtGui.QHBoxLayout()
            spy.addWidget(QtGui.QLabel("Spacing Y 垂直间距:"))
            self.spin_spacing_y = QtGui.QDoubleSpinBox()
            self.spin_spacing_y.setDecimals(2)
            self.spin_spacing_y.setSingleStep(0.5)
            self.spin_spacing_y.setMinimum(-50.0)
            self.spin_spacing_y.setMaximum(100.0)
            spy.addWidget(self.spin_spacing_y)
            self.spin_spacing_y.setEnabled(False)
            layout.addLayout(spy)

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
            self.spin_spacing_y.valueChanged.connect(self._on_spacing_y_changed)
            self.link_check.toggled.connect(self._on_link_toggled)
            self.spin_gradient.valueChanged.connect(self._on_gradient_changed)
            self.spin_thk.valueChanged.connect(self._on_thk_changed)
            self.sketch_btn.clicked.connect(self._pick_pattern_sketch)

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
                self.spin_spacing_y.setValue(self.obj.SpacingY.Value)
            except Exception:
                self.spin_spacing_y.setValue(2.0)
            try:
                link = getattr(self.obj, "LinkSpacing", True)
                self.link_check.setChecked(link)
                self.spin_spacing_y.setEnabled(not link)
            except Exception:
                pass
            try:
                self.spin_gradient.setValue(self.obj.SizeDecrease)
            except Exception:
                self.spin_gradient.setValue(0.0)
            try:
                self.spin_thk.setValue(self.obj.Thickness.Value)
            except Exception:
                self.spin_thk.setValue(10.0)
            try:
                sk = getattr(self.obj, "PatternSketch", None)
                if sk:
                    self.sketch_txt.setText(sk.Name)
            except Exception:
                pass

        def _update(self):
            try:
                self.obj.Document.recompute()
            except Exception:
                pass

        def _on_pattern_changed(self, idx):
            if 0 <= idx < len(PATTERN_TYPES):
                self.obj.PatternType = PATTERN_TYPES[idx]
            self._update()

        def _pick_pattern_sketch(self):
            for s in Gui.Selection.getSelectionEx():
                if s.Object.isDerivedFrom("Sketcher::SketchObject"):
                    self._apply_sketch(s.Object)
                    return
                for sn in s.SubElementNames:
                    o = App.ActiveDocument.getObject(sn.rstrip('.'))
                    if o and o.isDerivedFrom("Sketcher::SketchObject"):
                        self._apply_sketch(o)
                        return

        def _apply_sketch(self, sk):
            self.obj.PatternSketch = sk
            self.obj.PatternType = "user sketch"
            from freecad.frameforge2.create_offset_plane_tool import find_body
            body = find_body(self.obj.baseObject[0]) if hasattr(self.obj, 'baseObject') and self.obj.baseObject else None
            if body and not find_body(sk):
                body.addObject(sk)
            self.sketch_txt.setText(sk.Name)
            self._update_combo()
            self.obj.Document.recompute()

        def _update_combo(self):
            try:
                pt = str(self.obj.PatternType)
                idx = PATTERN_TYPES.index(pt) if pt in PATTERN_TYPES else 0
                self.combo_pattern.setCurrentIndex(idx)
            except Exception:
                pass

        def _on_grid_changed(self, idx):
            if 0 <= idx < len(GRID_MODES):
                self.obj.GridMode = GRID_MODES[idx]
            self._update()

        def _on_size_changed(self, val):
            self.obj.ElementSize = val
            self._update()

        def _on_spacing_changed(self, val):
            self.obj.Spacing = val
            if self.link_check.isChecked():
                self.spin_spacing_y.setValue(val)
            self._update()

        def _on_spacing_y_changed(self, val):
            self.obj.SpacingY = val
            self._update()

        def _on_link_toggled(self, linked):
            self.spin_spacing_y.setEnabled(not linked)
            self.obj.LinkSpacing = linked
            if linked:
                self.spin_spacing_y.setValue(self.spin_spacing.value())
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
                           "Patterns: Hexagon/Circle/Triangle\n"
                           "支持六边形、圆形、三角形、长腰型",
            }

        def Activated(self):
            sel = Gui.Selection.getSelectionEx()
            doc = App.ActiveDocument
            selobj = None
            selected_faces = []
            selected_sketch = None
            pattern_sketch = None

            for s in sel:
                got_sketch = None
                if s.Object.isDerivedFrom("Sketcher::SketchObject"):
                    got_sketch = s.Object
                else:
                    for sn in s.SubElementNames:
                        o = doc.getObject(sn.rstrip('.'))
                        if o and o.isDerivedFrom("Sketcher::SketchObject"):
                            got_sketch = o
                            break
                if got_sketch:
                    if selected_sketch is None:
                        selected_sketch = got_sketch
                    else:
                        pattern_sketch = got_sketch
                elif selobj is None:
                    selobj = s.Object
                    if s.SubElementNames:
                        selected_faces = list(s.SubElementNames)

            if selobj is None or selected_sketch is None:
                App.Console.PrintWarning("FF2: Select face + sketch\n")
                return

            doc = App.ActiveDocument
            doc.openTransaction("PatternFill")
            from freecad.frameforge2.create_offset_plane_tool import find_body
            body = find_body(selobj)
            if body is None:
                body = find_body(selected_sketch)
            if body is not None:
                newObj = doc.addObject("PartDesign::FeaturePython", "PatternFill")
            else:
                newObj = doc.addObject("Part::FeaturePython", "PatternFill")
            PatternFill(newObj, selobj, selected_faces, selected_sketch, pattern_sketch)
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

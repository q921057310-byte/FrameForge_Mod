import FreeCAD as App
import FreeCADGui as Gui
import Part

from freecad.frameforgemod._utils import _register_profile_metadata, get_profile_from_trimmedbody, is_trimmedbody
from freecad.frameforgemod.ff_tools import ICONPATH, UIPATH, translate


# Connector specification table
CONNECTOR_SPECS = {
    "M6": {"shaft_dia": 7.0, "head_dia": 11.0, "head_len": 4.0, "slot_max": 8.0},
    "M8": {"shaft_dia": 9.0, "head_dia": 15.0, "head_len": 5.0, "slot_max": 10.0},
    "M10": {"shaft_dia": 11.0, "head_dia": 18.0, "head_len": 6.0, "slot_max": 12.0},
}

SERIES_TO_SIZE = {
    20: "M6",
    30: "M8",
    40: "M8",
    45: "M8",
    50: "M10",
}

# QY built-in connector drilling specs (Chinese standard 内置连接件)
# Used to auto-fill HoleDiameter / HoleDepth / HoleDistance when a profile is selected
QY_SPECS = {
    30: {"model": "QY16-8-30", "hole_dia": 15.0, "hole_depth": 13.0, "hole_distance": 20.0, "bolt": "M6"},
    40: {"model": "QY20-8-40", "hole_dia": 20.0, "hole_depth": 16.8, "hole_distance": 20.5, "bolt": "M8"},
    45: {"model": "QY20-10-45", "hole_dia": 20.0, "hole_depth": 16.8, "hole_distance": 20.5, "bolt": "M8"},
}

# T-Joint connector: detected hole diameter → screw specification matching
# (min_dia, max_dia, screw_label, {through_dia, csink_dia, csink_depth})
TJOINT_MATCH_TABLE = [
    (4.5, 5.5, "M6", {"through_dia": 6.5, "csink_dia": 11.0, "csink_depth": 6.0}),
    (6.0, 7.5, "M8", {"through_dia": 8.5, "csink_dia": 14.0, "csink_depth": 8.0}),
    (8.0, 9.5, "M10", {"through_dia": 10.5, "csink_dia": 18.0, "csink_depth": 10.0}),
]


def _detect_series_from_profile(profile_obj):
    try:
        if hasattr(profile_obj, "ProfileWidth") and hasattr(profile_obj, "ProfileHeight"):
            w = float(profile_obj.ProfileWidth)
            h = float(profile_obj.ProfileHeight)
        elif hasattr(profile_obj, "Shape") and not profile_obj.Shape.isNull():
            bb = profile_obj.Shape.BoundBox
            dims = sorted([bb.XLength, bb.YLength, bb.ZLength])
            w, h = dims[0], dims[1]  # smallest two = cross-section
        else:
            return None
        size = int(min(w, h))
        known = sorted(SERIES_TO_SIZE.keys())
        for s in known:
            if abs(size - s) <= 5:
                return s
        if size <= 25:
            return 20
        if size <= 35:
            return 30
        if size <= 42:
            return 40
        if size <= 48:
            return 45
        return 50
    except Exception:
        return None


def _get_recommended_size(profile_obj):
    series = _detect_series_from_profile(profile_obj)
    if series and series in SERIES_TO_SIZE:
        return SERIES_TO_SIZE[series]
    return "M8"


def _get_qy_specs(profile_obj):
    series = _detect_series_from_profile(profile_obj)
    if series and series in QY_SPECS:
        return QY_SPECS[series]
    return None


def _get_body_to_cut(obj_ref):
    if is_trimmedbody(obj_ref):
        return obj_ref
    return obj_ref


def _find_extrusion_dir(body_shape):
    """Extrusion direction = normal of the smallest-area face (end face)."""
    candidates = []
    for f in body_shape.Faces:
        try:
            candidates.append((f.Area, f.normalAt(0.5, 0.5), f))
        except Exception:
            pass
    candidates.sort(key=lambda x: x[0])
    if candidates:
        return candidates[0][1]
    return App.Vector(0, 0, 1)


# ── T-Joint helper functions ──────────────────────────────────


def _match_tjoint_spec(detected_hole_diameter):
    for min_d, max_d, screw, spec in TJOINT_MATCH_TABLE:
        if min_d <= detected_hole_diameter <= max_d:
            return (screw, spec)
    return None


def _detect_tjoint(doc, objs):
    if len(objs) < 2:
        raise ValueError("Need exactly 2 objects for T-joint detection")

    best_a = None
    best_b = None
    best_end_name = None
    best_side_name = None
    best_area_ratio = 0.0  # higher = clearer end-vs-side distinction

    for oa in objs:
        for ob in objs:
            if oa is ob:
                continue
            try:
                if oa.Shape.isNull() or ob.Shape.isNull():
                    continue

                s_a = oa.Shape
                s_b = ob.Shape
                max_area_a = max(f.Area for f in s_a.Faces)
                max_area_b = max(f.Area for f in s_b.Faces)

                for i_a, fa in enumerate(s_a.Faces):
                    if fa.Area > max_area_a * 0.5:
                        continue  # skip large faces (side faces of A)
                    try:
                        na = fa.normalAt(0.5, 0.5)
                    except Exception:
                        continue

                    for i_b, fb in enumerate(s_b.Faces):
                        if fb.Area < max_area_b * 0.25:
                            continue  # skip small faces (end faces of B)
                        try:
                            nb = fb.normalAt(0.5, 0.5)
                        except Exception:
                            continue

                        if abs(na.dot(nb)) < 0.99:
                            continue

                        try:
                            min_dist = min(fa.distToShape(fb)[0], fb.distToShape(fa)[0])
                        except Exception:
                            continue
                        if min_dist > 0.1:
                            continue

                        ratio = max(fb.Area / max(fa.Area, 0.01), 0.0)
                        if ratio > best_area_ratio:
                            best_area_ratio = ratio
                            best_a = oa  # A has smaller face (end face)
                            best_end_name = "Face%d" % (i_a + 1)
                            best_b = ob  # B has larger face (side face)
                            best_side_name = "Face%d" % (i_b + 1)
            except Exception:
                continue

    if best_a is None:
        raise ValueError("No T-joint detected: check that one profile end face touches the other's side face")

    return (best_a, best_end_name, best_b, best_side_name)


def _get_face_narrow_side_info(face):
    bb = face.BoundBox
    dims = [
        (bb.XLength, "x", bb.XMin, bb.XMax),
        (bb.YLength, "y", bb.YMin, bb.YMax),
        (bb.ZLength, "z", bb.ZMin, bb.ZMax),
    ]
    dims = [d for d in dims if d[0] > 0.001]
    if not dims:
        return (1.0, 1.0, App.Vector(0, 0, 0), App.Vector(1, 0, 0))
    dims.sort(key=lambda d: d[0])
    narrow_size = dims[0][0]
    wide_size = dims[1][0] if len(dims) > 1 else dims[0][0]
    narrow_dir = dims[0][1]
    narrow_min = dims[0][2]
    narrow_max = dims[0][3]
    narrow_center = (narrow_min + narrow_max) / 2.0

    if narrow_dir == "x":
        pt1 = App.Vector(narrow_center, bb.YMin, bb.ZMin)
        pt2 = App.Vector(narrow_center, bb.YMax, bb.ZMin)
    elif narrow_dir == "y":
        pt1 = App.Vector(bb.XMin, narrow_center, bb.ZMin)
        pt2 = App.Vector(bb.XMax, narrow_center, bb.ZMin)
    else:
        pt1 = App.Vector(bb.XMin, bb.YMin, narrow_center)
        pt2 = App.Vector(bb.XMax, bb.YMin, narrow_center)

    axis_dir = pt2 - pt1
    if axis_dir.Length < 0.001:
        axis_dir = App.Vector(1, 0, 0)
    axis_dir.normalize()

    return (narrow_size, wide_size, pt1, axis_dir)


def _point_to_axis_distance(point, axis_origin, axis_dir):
    v = point - axis_origin
    cross = v.cross(axis_dir)
    return cross.Length


def _detect_holes_from_face(face):
    if not face or not isinstance(face, Part.Face):
        return []

    outer_wire = face.OuterWire
    holes = []
    for w in face.Wires:
        if w.isSame(outer_wire):
            continue
        if len(w.Edges) != 1:
            continue
        if not isinstance(w.Edges[0].Curve, Part.Circle):
            continue
        c = w.Edges[0].Curve
        holes.append((c.Center, c.Radius * 2.0, w))

    return holes


def _detect_hole_diameter_from_face(face):
    holes = _detect_holes_from_face(face)
    if not holes:
        return None, "A 型材端面无孔，请先用哨子连接器打中心孔"

    narrow_size, wide_size, axis_pt, axis_dir = _get_face_narrow_side_info(face)

    outer_vertices = face.OuterWire.Vertexes

    candidates = []
    for center, dia, wire in holes:
        # filter corner holes
        min_corner_dist = min(center.distanceToPoint(v.Point) for v in outer_vertices)
        if min_corner_dist < narrow_size * 0.25:
            continue

        # filter by narrow side center axis
        axis_dist = _point_to_axis_distance(center, axis_pt, axis_dir)
        if axis_dist < narrow_size * 0.25:
            candidates.append((center, dia, wire))

    if not candidates:
        return None, "A 端面未检测到窄边中心孔（已过滤四角孔）"

    # pick the hole closest to the narrow edge
    face_normal = face.normalAt(0.5, 0.5)
    candidates.sort(key=lambda h: h[0].dot(face_normal))

    best_center, best_dia, _ = candidates[0]
    return best_dia, None


def _get_all_holes_info(face):
    holes = _detect_holes_from_face(face)
    if not holes:
        return None, "A 型材端面无孔"

    narrow_size, wide_size, axis_pt, axis_dir = _get_face_narrow_side_info(face)
    outer_vertices = face.OuterWire.Vertexes

    candidates = []
    for center, dia, wire in holes:
        min_corner_dist = min(center.distanceToPoint(v.Point) for v in outer_vertices)
        is_corner = min_corner_dist < narrow_size * 0.25
        axis_dist = _point_to_axis_distance(center, axis_pt, axis_dir)
        is_narrow = axis_dist < narrow_size * 0.25
        candidates.append({"center": center, "diameter": dia, "corner": is_corner, "narrow": is_narrow,
                           "wire": wire})

    return candidates, None


class WhistleConnector:
    def __init__(self, obj):
        self.Type = "WhistleConnector"
        _register_profile_metadata(obj)

        # Selection
        obj.addProperty(
            "App::PropertyLinkSub", "EndFace", "Connector",
            translate("App::Property", "The end face of the profile"),
        ).EndFace = None

        obj.addProperty(
            "App::PropertyLinkSub", "DrillFace", "Connector",
            translate("App::Property", "The groove face to drill through"),
        ).DrillFace = None



        # Hole parameters — these ARE the drilling dimensions (editable)
        obj.addProperty(
            "App::PropertyLength", "HoleDiameter", "Hole",
            translate("App::Property", "Diameter of the drill hole"),
        ).HoleDiameter = 15.0

        obj.addProperty(
            "App::PropertyLength", "HoleDepth", "Hole",
            translate("App::Property", "Depth of the drill hole"),
        ).HoleDepth = 13.0

        obj.addProperty(
            "App::PropertyLength", "HoleDistance", "Hole",
            translate("App::Property", "Distance from the end face to hole center"),
        ).HoleDistance = 20.0

        # Direction
        obj.addProperty(
            "App::PropertyBool", "Reverse", "Hole",
            translate("App::Property", "Reverse drilling direction"),
        ).Reverse = False

        # T-Joint connector type
        obj.addProperty(
            "App::PropertyString", "ConnectorType", "Hole",
            translate("App::Property", "Connector type (Single or TJoint)"),
        ).ConnectorType = "Single"
        obj.setEditorMode("ConnectorType", 1)

        obj.addProperty(
            "App::PropertyLength", "ThroughHoleDiameter", "T-Joint",
            translate("App::Property", "Through hole diameter for TJoint"),
        ).ThroughHoleDiameter = 6.5

        obj.addProperty(
            "App::PropertyLength", "CounterSinkDiameter", "T-Joint",
            translate("App::Property", "Counterbore diameter"),
        ).CounterSinkDiameter = 11.0

        obj.addProperty(
            "App::PropertyLength", "CounterSinkDepth", "T-Joint",
            translate("App::Property", "Counterbore depth"),
        ).CounterSinkDepth = 6.0

        obj.addProperty(
            "App::PropertyString", "MatchedScrewSize", "T-Joint",
            "Auto-detected screw size (M6/M8/M10)",
        ).MatchedScrewSize = ""
        obj.setEditorMode("MatchedScrewSize", 1)

        obj.addProperty(
            "App::PropertyFloat", "DetectedHoleDiameter", "T-Joint",
            "Detected center hole diameter on reference profile",
        )
        obj.setEditorMode("DetectedHoleDiameter", 1)

        obj.addProperty(
            "App::PropertyLink", "TJointReferenceA", "T-Joint",
            "Reference profile A (end face side)",
        )
        obj.setEditorMode("TJointReferenceA", 1)

        # QY model info (reference only)
        obj.addProperty(
            "App::PropertyString", "QYModel", "Hole",
            "QY connector model number",
        ).QYModel = ""
        obj.setEditorMode("QYModel", 1)

        obj.Proxy = self

    def dumps(self):
        return None

    def loads(self, state):
        return None

    def execute(self, fp):
        if fp.ConnectorType == "TJoint":
            if fp.EndFace is not None and fp.DrillFace is not None:
                self._execute_tjoint(fp)
            elif fp.DrillFace is not None:
                try:
                    fp.Shape = Part.Compound([])
                except Exception:
                    pass
            else:
                try:
                    fp.Shape = Part.Compound([])
                except Exception:
                    pass
            return

        if fp.DrillFace is None:
            App.Console.PrintMessage("WhistleConnector: no DrillFace\n")
            return
        if fp.DrillFace[0] is fp:
            App.Console.PrintMessage("WhistleConnector: face is on self\n")
            return

        drill_obj, drill_name = fp.DrillFace
        drill_face = drill_obj.getSubObject(drill_name[0])
        if drill_face is None:
            App.Console.PrintWarning(f"WhistleConnector: face '{drill_name[0]}' not found\n")
            return

        try:
            drill_normal = drill_face.normalAt(0.5, 0.5)
            drill_center = drill_face.CenterOfGravity
        except Exception as e:
            App.Console.PrintWarning(f"WhistleConnector: bad drill face: {e}\n")
            return

        body = _get_body_to_cut(drill_obj)
        body_shape = body.Shape
        if body_shape.isNull():
            App.Console.PrintWarning("WhistleConnector: body null\n")
            return

        # ── Compute hole position ──
        # Strategy: from drill face normal → which side of profile → groove center
        # at side midpoint using end face local axes. Works for shoulder/wall/undercut clicks.
        hole_center = drill_center
        App.Console.PrintMessage(
            f"WhistleConnector: drill_center=({drill_center.x:.2f},{drill_center.y:.2f},{drill_center.z:.2f}) "
            f"drill_normal=({drill_normal.x:.3f},{drill_normal.y:.3f},{drill_normal.z:.3f})\n")
        if fp.EndFace is not None:
            try:
                end_obj, end_name = fp.EndFace
                end_face = end_obj.getSubObject(end_name[0])
                if end_face is not None:
                    end_dir = end_face.normalAt(0.5, 0.5)
                    end_ref = end_face.CenterOfGravity
                    body_center = body_shape.BoundBox.Center
                    if end_dir.dot(body_center - end_ref) < 0:
                        end_dir = -end_dir
                    hole_dist = float(fp.HoleDistance)

                    # Get profile cross-section dimensions
                    profile_obj = get_profile_from_trimmedbody(drill_obj)
                    W = float(getattr(profile_obj, 'ProfileWidth', 40))
                    H = float(getattr(profile_obj, 'ProfileHeight', 40))

                    # Groove center: from BB side midpoint in end face plane
                    bb = body_shape.BoundBox
                    bb_center = bb.Center
                    # Find which BB axis drill_normal aligns with
                    dots = [(abs(drill_normal.x), "x", bb.XMin, bb.XMax),
                            (abs(drill_normal.y), "y", bb.YMin, bb.YMax),
                            (abs(drill_normal.z), "z", bb.ZMin, bb.ZMax)]
                    dots.sort(key=lambda x: -x[0])
                    ax_name, ax_min, ax_max = dots[0][1], dots[0][2], dots[0][3]
                    # Sign of drill_normal along this axis
                    vec = App.Vector(1 if ax_name=="x" else 0,
                                     1 if ax_name=="y" else 0,
                                     1 if ax_name=="z" else 0)
                    sign = 1.0 if drill_normal.dot(vec) > 0 else -1.0
                    half = (ax_max - ax_min) / 2.0
                    side_center = bb_center + vec * sign * half

                    # Groove center = side midpoint, projected to end face plane
                    # (removes extrusion component)
                    proj = side_center - end_dir * (side_center - end_ref).dot(end_dir)
                    hole_center = proj + end_dir * hole_dist
                    App.Console.PrintMessage(
                        f"WhistleConnector: side={ax_name} sign={'+' if sign>0 else '-'} "
                        f"proj=({proj.x:.1f},{proj.y:.1f},{proj.z:.1f}) "
                        f"+{hole_dist:.0f}mm → hole=({hole_center.x:.1f},{hole_center.y:.1f},{hole_center.z:.1f})\n")
            except Exception as e:
                App.Console.PrintWarning(f"WhistleConnector: position failed: {e}\n")

        # ── Drill parameters ──
        hole_r = float(fp.HoleDiameter) / 2.0
        hole_depth = float(fp.HoleDepth)
        extrude_len = hole_depth + 0.1

        orig_vol = body_shape.Volume
        # ── Direction: always drill perpendicular to drill face (into body) ──
        # Priority: -drill_normal > drill_normal > orthogonal (fallback)
        min_ok = 3.1416 * hole_r ** 2 * 1.0  # at least 1mm deep

        def _cut_test(direction, label):
            try:
                off = hole_center - direction * 0.1
                circ = Part.Circle(off, direction, hole_r)
                f = Part.Face(Part.Wire([Part.Edge(circ)]))
                if f.isNull() or not f.isValid():
                    return None
                ex = f.extrude(direction * extrude_len)
                if ex.isNull() or not ex.isValid():
                    return None
                r = body_shape.cut(ex)
                if r.isNull() or not r.isValid():
                    return None
                return r
            except Exception:
                return None

        # 1) Try -normal (into body) — this is the CORRECT direction
        result = _cut_test(-drill_normal, "-normal")
        if result is not None:
            removed = orig_vol - result.Volume
            if removed > min_ok:
                fp.Shape = result
                App.Console.PrintMessage(
                    f"WhistleConnector: perpendicular to drill face (-normal), "
                    f"removed {removed:.0f}mm³\n")
                self._update_structure_data(fp, get_profile_from_trimmedbody(drill_obj))
                return

        # 2) Try +normal (out of body) — only if -normal didn't work
        result = _cut_test(drill_normal, "+normal")
        if result is not None:
            removed = orig_vol - result.Volume
            if removed > min_ok:
                fp.Shape = result
                App.Console.PrintMessage(
                    f"WhistleConnector: +normal direction (reverse), "
                    f"removed {removed:.0f}mm³\n")
                self._update_structure_data(fp, get_profile_from_trimmedbody(drill_obj))
                return

        # 3) Orthogonal fallback
        for axis in [App.Vector(1, 0, 0), App.Vector(0, 1, 0), App.Vector(0, 0, 1)]:
            perp = drill_normal.cross(axis)
            if perp.Length < 0.01:
                continue
            perp.normalize()
            for d, lbl in [(perp, "+perp"), (-perp, "-perp")]:
                result = _cut_test(d, lbl)
                if result is not None:
                    removed = orig_vol - result.Volume
                    if removed > min_ok:
                        fp.Shape = result
                        App.Console.PrintMessage(
                            f"WhistleConnector: {lbl} (fallback), "
                            f"removed {removed:.0f}mm³\n")
                        self._update_structure_data(fp, get_profile_from_trimmedbody(drill_obj))
                        return

        App.Console.PrintWarning(
            f"WhistleConnector: all directions failed\n")

    def _execute_tjoint(self, fp):
        if fp.EndFace is None or fp.DrillFace is None:
            App.Console.PrintMessage("TJointConnector: missing face references\n")
            return

        end_obj, end_names = fp.EndFace
        end_face = end_obj.getSubObject(end_names[0])
        if end_face is None:
            App.Console.PrintWarning("TJointConnector: end face not found\n")
            return

        drill_obj, drill_names = fp.DrillFace
        drill_face = drill_obj.getSubObject(drill_names[0])
        if drill_face is None:
            App.Console.PrintWarning("TJointConnector: drill face not found\n")
            return
        if drill_obj is fp:
            App.Console.PrintMessage("TJointConnector: face is on self\n")
            return

        # ── Reference profiles: A = end face owner, B = drill face owner ──
        prof_a = get_profile_from_trimmedbody(end_obj)
        prof_b = get_profile_from_trimmedbody(drill_obj)

        # ── Hole center on A's end face ──
        holes = _detect_holes_from_face(end_face)
        if not holes:
            App.Console.PrintWarning("TJointConnector: no hole detected on reference end face\n")
            return

        # Always find the best hole center regardless of diameter override
        narrow_size, wide_size, axis_pt, axis_dir = _get_face_narrow_side_info(end_face)
        outer_vertices = end_face.OuterWire.Vertexes

        non_corner = []
        for center, dia, wire in holes:
            min_corner = min(center.distanceToPoint(v.Point) for v in outer_vertices)
            if min_corner >= narrow_size * 0.25:
                non_corner.append((center, dia, wire))

        if not non_corner:
            non_corner = holes

        non_corner.sort(key=lambda h: _point_to_axis_distance(h[0], axis_pt, axis_dir))
        hole_center_a, detected_dia, _ = non_corner[0]

        # Use the DetectedHoleDiameter override if set
        use_dia = float(fp.DetectedHoleDiameter) if float(fp.DetectedHoleDiameter) > 0 else detected_dia

        # ── Match screw spec ──
        match = _match_tjoint_spec(use_dia)
        if match is None:
            App.Console.PrintWarning(
                f"TJointConnector: detected hole {use_dia:.1f}mm outside matching range\n"
            )
            spec = {
                "through_dia": float(fp.ThroughHoleDiameter),
                "csink_dia": float(fp.CounterSinkDiameter),
                "csink_depth": float(fp.CounterSinkDepth),
            }
            screw = "Manual"
        else:
            screw, spec = match

        through_dia = float(fp.ThroughHoleDiameter) if fp.ThroughHoleDiameter > 0 else spec["through_dia"]
        csink_dia = float(fp.CounterSinkDiameter) if fp.CounterSinkDiameter > 0 else spec["csink_dia"]
        csink_depth = float(fp.CounterSinkDepth) if fp.CounterSinkDepth > 0 else spec["csink_depth"]

        fp.MatchedScrewSize = screw
        fp.DetectedHoleDiameter = use_dia

        # ── Compute hole position on B ──
        drill_normal = drill_face.normalAt(0.5, 0.5)
        drill_cog = drill_face.CenterOfGravity

        # Project A hole center onto B drill face plane
        proj = hole_center_a - drill_normal * (hole_center_a - drill_cog).dot(drill_normal)

        # Direction: drill into B body (opposite to drill_face normal)
        drill_dir = -drill_normal

        body_b_shape = _get_body_to_cut(drill_obj).Shape
        if body_b_shape.isNull():
            App.Console.PrintWarning("TJointConnector: B body is null\n")
            return

        orig_vol = body_b_shape.Volume
        extrude_through = csink_depth + 100.0  # deep enough to go through

        def _cut_cylinder(center, direction, diameter, length, body_shape):
            r = diameter / 2.0
            off = center - direction * 0.01
            try:
                circ = Part.Circle(off, direction, r)
                f = Part.Face(Part.Wire([Part.Edge(circ)]))
                if f.isNull() or not f.isValid():
                    return None
                ex = f.extrude(direction * length)
                if ex.isNull() or not ex.isValid():
                    return None
                return body_shape.cut(ex)
            except Exception:
                return None

        # Step 1: Counterbore (outer, shallow)
        step1 = _cut_cylinder(proj, drill_dir, csink_dia, csink_depth, body_b_shape)
        if step1 is None or step1.isNull():
            App.Console.PrintWarning("TJointConnector: countersink cut failed\n")
            fp.Shape = body_b_shape
            return

        # Step 2: Through hole (inner, deep) — cut from original surface deeper
        # offset start to avoid overlapping cut artifact
        through_start = proj + drill_dir * (csink_depth - 0.02)
        step2 = _cut_cylinder(through_start, drill_dir, through_dia, extrude_through, step1)
        if step2 is None or step2.isNull():
            fp.Shape = step1  # at least keep the counterbore
        else:
            fp.Shape = step2

        removed = orig_vol - fp.Shape.Volume
        App.Console.PrintMessage(
            f"TJointConnector: {screw} through⌀{through_dia:.1f} + csink⌀{csink_dia:.1f}x{csink_depth:.1f}, "
            f"removed {removed:.0f}mm³\n"
        )

        self._update_structure_data(fp, prof_b)
        fp.TJointReferenceA = prof_a

    def _update_structure_data(self, obj, prof=None):
        try:
            if prof is None:
                if obj.DrillFace and len(obj.DrillFace) > 0:
                    prof = get_profile_from_trimmedbody(obj.DrillFace[0])
                if prof is None and obj.DrillFace and len(obj.DrillFace) > 0:
                    obj_ref = obj.DrillFace[0]
                    if hasattr(obj_ref, "PID"):
                        prof = obj_ref
            if prof:
                obj.PID = prof.PID
                obj.SizeName = prof.SizeName
                obj.Family = prof.Family
                obj.Material = prof.Material
                obj.CustomProfile = prof.CustomProfile if hasattr(prof, "CustomProfile") else None
                obj.ApproxWeight = prof.ApproxWeight
                obj.Price = prof.Price
                obj.Length = float(obj.HoleDistance)
                obj.Width = prof.ProfileWidth if hasattr(prof, "ProfileWidth") else 0
                obj.Height = prof.ProfileHeight if hasattr(prof, "ProfileHeight") else 0
        except Exception:
            pass


class ViewProviderWhistleConnector:
    def __init__(self, vobj):
        vobj.Proxy = self
        self.ViewObject = vobj
        self.Object = vobj.Object
        vobj.ShapeColor = (0.6, 0.6, 0.6)
        vobj.Transparency = 0

    def attach(self, vobj):
        self.ViewObject = vobj
        self.Object = vobj.Object
        vobj.ShapeColor = (0.6, 0.6, 0.6)
        vobj.Transparency = 0

    def updateData(self, fp, prop):
        if prop in ("DrillFace", "EndFace", "Shape"):
            ref_face = None
            try:
                if fp.DrillFace and len(fp.DrillFace) > 0 and fp.DrillFace[0]:
                    ref_face = fp.DrillFace[0]
                elif fp.EndFace and len(fp.EndFace) > 0 and fp.EndFace[0]:
                    ref_face = fp.EndFace[0]
                if ref_face:
                    vp = ref_face.ViewObject
                    self.ViewObject.ShapeColor = vp.ShapeColor
                    self.ViewObject.Transparency = vp.Transparency
            except Exception:
                pass
        return

    def getDisplayModes(self, obj):
        return []

    def getDefaultDisplayMode(self):
        return "FlatLines"

    def setDisplayMode(self, mode):
        return mode

    def _get_parent(self):
        try:
            if self.Object.DrillFace and len(self.Object.DrillFace) > 0:
                return self.Object.DrillFace[0]
            if self.Object.EndFace and len(self.Object.EndFace) > 0:
                return self.Object.EndFace[0]
        except Exception:
            pass
        return None

    def _both_faces_set(self):
        try:
            return (self.Object.EndFace is not None
                    and self.Object.DrillFace is not None
                    and len(self.Object.EndFace) > 0
                    and len(self.Object.DrillFace) > 0)
        except Exception:
            return False

    def claimChildren(self):
        parent = self._get_parent()
        if parent:
            return [parent]
        return []

    def onChanged(self, vp, prop):
        if prop in ("EndFace", "DrillFace") and self._both_faces_set():
            parent = self._get_parent()
            if parent:
                try:
                    parent.ViewObject.Visibility = False
                except Exception:
                    pass

    def onDelete(self, vobj, sub):
        parent = self._get_parent()
        if parent:
            try:
                parent.ViewObject.Visibility = True
            except Exception:
                pass
        return True

    def setEdit(self, vobj, mode):
        if mode != 0:
            return None
        import freecad.frameforgemod.create_whistle_connector_tool as tools
        fp = self.Object
        if hasattr(fp, "ConnectorType") and fp.ConnectorType == "TJoint":
            taskd = tools.TJointConnectorTaskPanel(fp)
        else:
            taskd = tools.WhistleConnectorTaskPanel(fp)
        Gui.Control.showDialog(taskd)
        return True

    def unsetEdit(self, vobj, mode):
        if mode != 0:
            return None
        Gui.Control.closeDialog()
        return True

    def edit(self):
        Gui.ActiveDocument.setEdit(self.Object, 0)

    def getIcon(self):
        return """
        /* XPM */
            static char * whistle_connector_xpm[] = {
            "16 16 2 1",
            " 	c None",
            "@	c #729FCF",
            "                ",
            "     @@@@@@     ",
            "    @@@@@@@@    ",
            "    @@    @@    ",
            "    @@    @@    ",
            "    @@    @@    ",
            "    @@    @@    ",
            "    @@@@@@@@    ",
            "     @@@@@@     ",
            "      @  @      ",
            "     @@  @@     ",
            "    @@@  @@@    ",
            "   @@@@  @@@@   ",
            "  @@@@@  @@@@@  ",
            " @@@@@@  @@@@@@ ",
            "                "};
        """

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

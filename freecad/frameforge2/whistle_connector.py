import FreeCAD as App
import FreeCADGui as Gui
import Part

from freecad.frameforge2._utils import get_profile_from_trimmedbody, is_trimmedbody
from freecad.frameforge2.ff_tools import ICONPATH, UIPATH, translate
from freecad.frameforge2.version import __version__ as ff_version


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


class WhistleConnector:
    def __init__(self, obj):
        obj.addProperty(
            "App::PropertyString",
            "FrameforgeVersion",
            "Profile",
            "Frameforge Version used to create the profile",
        ).FrameforgeVersion = ff_version

        obj.addProperty("App::PropertyString", "PID", "Profile", "Profile ID").PID = ""
        obj.setEditorMode("PID", 1)

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

        # QY model info (reference only)
        obj.addProperty(
            "App::PropertyString", "QYModel", "Hole",
            "QY connector model number",
        ).QYModel = ""
        obj.setEditorMode("QYModel", 1)

        # Profile metadata (readonly)
        obj.addProperty("App::PropertyString", "Family", "Profile", "")
        obj.setEditorMode("Family", 1)
        obj.addProperty("App::PropertyString", "SizeName", "Profile", "")
        obj.setEditorMode("SizeName", 1)
        obj.addProperty("App::PropertyString", "Material", "Profile", "")
        obj.setEditorMode("Material", 1)
        obj.addProperty("App::PropertyFloat", "ApproxWeight", "Base", "Approximate weight in Kilogram")
        obj.setEditorMode("ApproxWeight", 1)
        obj.addProperty("App::PropertyFloat", "Price", "Base", "Profile Price")
        obj.setEditorMode("Price", 1)
        obj.addProperty("App::PropertyLink", "CustomProfile", "Profile", "Target profile").CustomProfile = None
        obj.setEditorMode("CustomProfile", 1)

        obj.addProperty("App::PropertyLength", "Width", "Structure", "Parameter for structure")
        obj.setEditorMode("Width", 1)
        obj.addProperty("App::PropertyLength", "Height", "Structure", "Parameter for structure")
        obj.setEditorMode("Height", 1)
        obj.addProperty("App::PropertyLength", "Length", "Structure", "Parameter for structure")
        obj.setEditorMode("Length", 1)
        obj.addProperty("App::PropertyBool", "Cutout", "Structure", "Has Cutout").Cutout = True
        obj.setEditorMode("Cutout", 1)
        obj.addProperty("App::PropertyString", "CuttingAngleA", "Structure", "Cutting Angle A")
        obj.setEditorMode("CuttingAngleA", 1)
        obj.addProperty("App::PropertyString", "CuttingAngleB", "Structure", "Cutting Angle B")
        obj.setEditorMode("CuttingAngleB", 1)

        obj.Proxy = self

    def onChanged(self, fp, prop):
        pass

    def execute(self, fp):
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
            # Only hide parent when BOTH faces are configured
            if self._both_faces_set():
                try:
                    parent.ViewObject.Visibility = False
                except Exception:
                    pass
            return [parent]
        return []

    def onChanged(self, vp, prop):
        # When both faces are set, hide parent
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
        import freecad.frameforge2.create_whistle_connector_tool
        taskd = freecad.frameforge2.create_whistle_connector_tool.WhistleConnectorTaskPanel(self.Object)
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

import FreeCAD as App
import FreeCADGui as Gui
import Part
import math

from freecad.frameforgemod.ff_tools import translate

BOLT_PRESETS = {
    "Custom":    {"hole_dia": 8.5, "csink_dia": 14.0, "csink_depth": 8.0, "depth": 20.0},
    "M3":        {"hole_dia": 3.2, "csink_dia": 6.0, "csink_depth": 3.0, "depth": 20.0},
    "M4":        {"hole_dia": 4.2, "csink_dia": 8.0, "csink_depth": 4.0, "depth": 20.0},
    "M5":        {"hole_dia": 5.2, "csink_dia": 9.0, "csink_depth": 4.5, "depth": 20.0},
    "M6":        {"hole_dia": 6.5, "csink_dia": 11.0, "csink_depth": 6.0, "depth": 20.0},
    "M8":        {"hole_dia": 8.5, "csink_dia": 14.0, "csink_depth": 8.0, "depth": 20.0},
    "M10":       {"hole_dia": 10.5, "csink_dia": 18.0, "csink_depth": 10.0, "depth": 20.0},
    "M12":       {"hole_dia": 12.5, "csink_dia": 20.0, "csink_depth": 12.0, "depth": 20.0},
    "Pin2.5":    {"hole_dia": 2.5, "csink_dia": 2.5, "csink_depth": 0, "depth": 10.0},
    "Pin3":      {"hole_dia": 3.0, "csink_dia": 3.0, "csink_depth": 0, "depth": 10.0},
    "Pin5":      {"hole_dia": 5.0, "csink_dia": 5.0, "csink_depth": 0, "depth": 10.0},
    "Pin6":      {"hole_dia": 6.0, "csink_dia": 6.0, "csink_depth": 0, "depth": 10.0},
    "Pin8":      {"hole_dia": 8.0, "csink_dia": 8.0, "csink_depth": 0, "depth": 10.0},
    "Pin10":     {"hole_dia": 10.0, "csink_dia": 10.0, "csink_depth": 0, "depth": 10.0},
}

_HOLE_TYPES = ["Through", "Blind", "Counterbore"]


class HoleFeature:
    def __init__(self, obj):
        self.Type = "HoleFeature"
        obj.Proxy = self

        obj.addProperty("App::PropertyLinkSub", "Base", "Hole",
                        translate("App::Property", "Profile face to drill into")).Base = None

        obj.addProperty("App::PropertyLinkSubList", "Positions", "Hole",
                        translate("App::Property", "Sketch vertices or circles for positioning")).Positions = []

        obj.addProperty("App::PropertyEnumeration", "HoleType", "Hole",
                        translate("App::Property", "Through / Blind / Counterbore")).HoleType = _HOLE_TYPES

        obj.addProperty("App::PropertyEnumeration", "BoltSpec", "Hole",
                        translate("App::Property", "Bolt size preset")).BoltSpec = list(BOLT_PRESETS.keys())

        obj.addProperty("App::PropertyLength", "HoleDiameter", "Hole",
                        translate("App::Property", "Hole diameter")).HoleDiameter = 8.5

        obj.addProperty("App::PropertyLength", "HoleDepth", "Hole",
                        translate("App::Property", "Blind hole depth (0 = auto through)")).HoleDepth = 20.0

        obj.addProperty("App::PropertyLength", "CounterSinkDiameter", "Hole",
                        translate("App::Property", "Counterbore diameter")).CounterSinkDiameter = 14.0

        obj.addProperty("App::PropertyLength", "CounterSinkDepth", "Hole",
                        translate("App::Property", "Counterbore depth")).CounterSinkDepth = 8.0

        obj.addProperty("App::PropertyBool", "Reverse", "Hole",
                        translate("App::Property", "Flip direction")).Reverse = False

        obj.addProperty("App::PropertyAngle", "RotX", "Direction",
                        translate("App::Property", "Rotate around X")).RotX = 0.0
        obj.addProperty("App::PropertyAngle", "RotY", "Direction",
                        translate("App::Property", "Rotate around Y")).RotY = 0.0
        obj.addProperty("App::PropertyAngle", "RotZ", "Direction",
                        translate("App::Property", "Rotate around Z")).RotZ = 0.0

        # CutResult removed to avoid cyclic dependency (DAG error)
        # obj.addProperty("App::PropertyLink", "CutResult", "Hole", "").CutResult = None
        # obj.setEditorMode("CutResult", 2)

        self._cached_key = None
        self._cached_shape = None

    def _hole_key(self, fp):
        try:
            key = [fp.HoleType, fp.BoltSpec, float(fp.HoleDiameter), float(fp.HoleDepth),
                   float(fp.CounterSinkDiameter), float(fp.CounterSinkDepth),
                   int(fp.Reverse), float(fp.RotX), float(fp.RotY), float(fp.RotZ)]
            if fp.Base and len(fp.Base) >= 2:
                obase = fp.Base[0]
                key.append(obase.Name)
                key.append(fp.Base[1][0])
            if fp.Positions:
                for tup in fp.Positions:
                    key.append(tup[0].Name)
                    key.extend(tup[1])
            return hash(tuple(key))
        except Exception:
            return None

    def onChanged(self, fp, prop):
        if prop in ("Base", "Positions", "HoleType", "BoltSpec", "HoleDiameter", "HoleDepth",
                     "CounterSinkDiameter", "CounterSinkDepth", "Reverse", "RotX", "RotY", "RotZ"):
            self._cached_key = None
            self._cached_shape = None

    def dumps(self):
        return None

    def loads(self, state):
        return None

    def execute(self, fp):
        App.Console.PrintMessage("HoleFeature.execute: start\n")
        try:
            cache_key = self._hole_key(fp)
            if cache_key is not None and getattr(self, "_cached_key", None) == cache_key and getattr(self, "_cached_shape", None) is not None:
                fp.Shape = self._cached_shape
                return
            result = self._execute(fp)
            if result is not None:
                fp.Shape = result
                self._cached_key = cache_key
                self._cached_shape = result
            self._sync_cut_label(fp)
        except Exception as e:
            App.Console.PrintWarning(f"HoleFeature.execute error: {e}\n")

    def _sync_cut_label(self, fp):
        if not hasattr(fp, "CutResult"):
            return
        cut = fp.CutResult
        if cut is None:
            return
        base = fp.Base[0] if fp.Base else None
        if base is None:
            return
        try:
            name = getattr(base, "SizeName", None)
            if not name:
                label = base.Label
                name = label.split("_Profile_")[0] if "_Profile_" in label else label
            cut.Label = f"{name}_Cut"
        except Exception:
            pass

    def _execute(self, fp):
        if fp.Base is None:
            return None

        base_obj, base_subs = fp.Base
        base_face = base_obj.getSubObject(base_subs[0])
        if base_face is None or not isinstance(base_face, Part.Face):
            return None

        positions = []
        for tup in fp.Positions:
            obj = tup[0]
            for sub_name in tup[1]:
                sub = obj.getSubObject(sub_name)
                if sub is None:
                    continue
                if isinstance(sub, Part.Vertex):
                    positions.append(sub.Point)
                elif isinstance(sub, Part.Edge):
                    try:
                        c = sub.Curve
                        if hasattr(c, "Center"):
                            positions.append(c.Center)
                        elif hasattr(sub, "Vertexes") and len(sub.Vertexes) >= 2:
                            positions.append(sub.Vertexes[0].Point)
                            positions.append(sub.Vertexes[-1].Point)
                    except Exception:
                        pass

        if not positions:
            positions = [base_face.CenterOfGravity]

        direction = base_face.normalAt(0.5, 0.5)
        body_center = base_obj.Shape.BoundBox.Center
        if direction.dot(body_center - base_face.CenterOfGravity) < 0:
            direction = -direction

        rx = float(fp.RotX)
        ry = float(fp.RotY)
        rz = float(fp.RotZ)
        rot = App.Rotation(App.Vector(1, 0, 0), math.radians(rx))
        rot = App.Rotation(App.Vector(0, 1, 0), math.radians(ry)).multiply(rot)
        rot = App.Rotation(App.Vector(0, 0, 1), math.radians(rz)).multiply(rot)
        direction = rot.multVec(direction)

        if fp.Reverse:
            direction = -direction

        App.Console.PrintMessage(
            f"HoleFeature: {len(positions)} pos, dir=({direction.x:.2f},{direction.y:.2f},{direction.z:.2f})\n")

        hole_type = str(fp.HoleType)
        hole_r = float(fp.HoleDiameter) / 2.0
        hole_depth = float(fp.HoleDepth)
        csink_r = float(fp.CounterSinkDiameter) / 2.0
        csink_depth = float(fp.CounterSinkDepth)

        diag = base_obj.Shape.BoundBox.DiagonalLength
        if hole_type in ("Through", "Counterbore"):
            cut_depth = diag * 2.0
        else:
            cut_depth = max(hole_depth, diag) if hole_depth <= 0 else hole_depth

        solids = []
        for pos in positions:
            cyl = self._make_cylinder(pos, direction, hole_r, cut_depth)
            if cyl:
                solids.append(cyl)
            if hole_type == "Counterbore" and csink_r > hole_r:
                cb = self._make_cylinder(pos, direction, csink_r, csink_depth)
                if cb:
                    solids.append(cb)

        if not solids:
            return None

        result = solids[0]
        for s in solids[1:]:
            result = result.fuse(s)

        return result

    def _make_cylinder(self, center, direction, radius, length):
        off = center - direction * 0.01
        try:
            circ = Part.Circle(off, direction, radius)
            face = Part.Face(Part.Wire([Part.Edge(circ)]))
            if face.isNull() or not face.isValid():
                return None
            cyl = face.extrude(direction * length)
            if cyl.isNull() or not cyl.isValid():
                return None
            return cyl
        except Exception:
            return None


class ViewProviderHoleFeature:
    def __init__(self, vobj):
        vobj.Proxy = self
        self.ViewObject = vobj
        self.Object = vobj.Object
        vobj.ShapeColor = (1.0, 0.3, 0.3)
        vobj.Transparency = 50

    def attach(self, vobj):
        self.ViewObject = vobj
        self.Object = vobj.Object
        vobj.ShapeColor = (1.0, 0.3, 0.3)
        vobj.Transparency = 50

    def updateData(self, fp, prop):
        pass

    def getDisplayModes(self, obj):
        return []

    def getDefaultDisplayMode(self):
        return "FlatLines"

    def setDisplayMode(self, mode):
        return mode

    def claimChildren(self):
        return []

    def onChanged(self, vp, prop):
        pass

    def onDelete(self, vobj, sub):
        return True

    def setEdit(self, vobj, mode):
        if mode != 0:
            return None
        try:
            vobj.Visibility = True
        except Exception:
            pass
        import freecad.frameforgemod.create_connector_hole_tool as tools
        fp = self.Object
        taskd = tools.HoleFeatureTaskPanel(fp)
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
            static char * hole_feature_xpm[] = {
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

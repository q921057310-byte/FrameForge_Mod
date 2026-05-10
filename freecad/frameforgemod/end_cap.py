import os

import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtCore, QtGui

from freecad.frameforgemod._utils import (
    _register_profile_metadata,
    get_profile_from_trimmedbody,
    get_readable_cutting_angles,
    get_trimmed_profile_all_cutting_angles,
    length_along_normal,
)
from freecad.frameforgemod.ff_tools import ICONPATH, PROFILEIMAGES_PATH, PROFILESPATH, UIPATH, translate

THREAD_SPECS = {
    "Custom": 0,
    "M3": 2.5,
    "M5": 4.2,
    "M6": 5.0,
    "M8": 6.8,
    "M10": 8.5,
    "M12": 10.2,
}


def _endcap_params():
    return App.ParamGet("User parameter:BaseApp/Preferences/Frameforge/EndCap")


def _load_endcap_defaults(obj):
    p = _endcap_params()
    obj.Thickness = p.GetFloat("Thickness", float(obj.Thickness))
    obj.Offset = p.GetFloat("Offset", float(obj.Offset))
    obj.Reverse = p.GetBool("Reverse", obj.Reverse)
    obj.CapType = p.GetInt("CapType", obj.CapType)
    obj.PlugOffset = p.GetFloat("PlugOffset", float(obj.PlugOffset))
    obj.ChamferEnabled = p.GetBool("ChamferEnabled", obj.ChamferEnabled)
    obj.ChamferSize = p.GetFloat("ChamferSize", float(obj.ChamferSize))
    obj.FilletEnabled = p.GetBool("FilletEnabled", obj.FilletEnabled)
    obj.FilletSize = p.GetFloat("FilletSize", float(obj.FilletSize))
    obj.HoleEnabled = p.GetBool("HoleEnabled", obj.HoleEnabled)
    obj.HoleThreaded = p.GetBool("HoleThreaded", obj.HoleThreaded)
    try:
        spec = p.GetString("HoleThreadSpec", str(obj.HoleThreadSpec))
        if spec in THREAD_SPECS:
            obj.HoleThreadSpec = spec
    except Exception:
        pass
    obj.HoleDiameter = p.GetFloat("HoleDiameter", float(obj.HoleDiameter))


def _save_endcap_defaults(obj):
    p = _endcap_params()
    p.SetFloat("Thickness", float(obj.Thickness))
    p.SetFloat("Offset", float(obj.Offset))
    p.SetBool("Reverse", bool(obj.Reverse))
    p.SetInt("CapType", int(obj.CapType))
    p.SetFloat("PlugOffset", float(obj.PlugOffset))
    p.SetBool("ChamferEnabled", bool(obj.ChamferEnabled))
    p.SetFloat("ChamferSize", float(obj.ChamferSize))
    p.SetBool("FilletEnabled", bool(obj.FilletEnabled))
    p.SetFloat("FilletSize", float(obj.FilletSize))
    p.SetBool("HoleEnabled", bool(obj.HoleEnabled))
    p.SetBool("HoleThreaded", bool(obj.HoleThreaded))
    p.SetString("HoleThreadSpec", str(obj.HoleThreadSpec))
    p.SetFloat("HoleDiameter", float(obj.HoleDiameter))


class EndCap:
    def __init__(self, obj, selected_face):
        _register_profile_metadata(obj)

        obj.addProperty("App::PropertyLinkSub", "BaseObject", "EndCap",
                        translate("App::Property", "Selected face for the end cap")).BaseObject = (
            selected_face
        )

        obj.addProperty(
            "App::PropertyLength",
            "Thickness",
            "EndCap",
            translate("App::Property", "Cap thickness"),
        ).Thickness = 5.0

        obj.addProperty(
            "App::PropertyLength",
            "Offset",
            "EndCap",
            translate("App::Property", "Gap (distance from face)"),
        ).Offset = 0.0

        obj.addProperty(
            "App::PropertyBool",
            "Reverse",
            "EndCap",
            translate("App::Property", "Reverse cap direction"),
        ).Reverse = False

        obj.addProperty(
            "App::PropertyInteger",
            "CapType",
            "EndCap",
            translate("App::Property", "Cap type: 0=Plate, 1=Plug"),
        ).CapType = 0

        obj.addProperty(
            "App::PropertyLength",
            "PlugOffset",
            "EndCap",
            translate("App::Property", "Plug clearance (shrinks plug relative to inner hole)"),
        ).PlugOffset = 0.5

        obj.addProperty(
            "App::PropertyBool",
            "ChamferEnabled",
            "EndCap",
            translate("App::Property", "Enable chamfer on edges"),
        ).ChamferEnabled = False

        obj.addProperty(
            "App::PropertyLength",
            "ChamferSize",
            "EndCap",
            translate("App::Property", "Chamfer size"),
        ).ChamferSize = 2.0

        obj.addProperty(
            "App::PropertyBool",
            "FilletEnabled",
            "EndCap",
            translate("App::Property", "Enable fillet on edges"),
        ).FilletEnabled = False

        obj.addProperty(
            "App::PropertyLength",
            "FilletSize",
            "EndCap",
            translate("App::Property", "Fillet radius"),
        ).FilletSize = 2.0

        obj.addProperty(
            "App::PropertyBool",
            "HoleEnabled",
            "EndCap",
            translate("App::Property", "Enable center hole"),
        ).HoleEnabled = False

        obj.addProperty(
            "App::PropertyBool",
            "HoleThreaded",
            "EndCap",
            translate("App::Property", "Threaded hole"),
        ).HoleThreaded = False

        obj.addProperty(
            "App::PropertyEnumeration",
            "HoleThreadSpec",
            "EndCap",
            translate("App::Property", "Thread spec (auto-fills diameter)"),
        ).HoleThreadSpec = list(THREAD_SPECS.keys())

        obj.addProperty(
            "App::PropertyLength",
            "HoleDiameter",
            "EndCap",
            translate("App::Property", "Hole diameter"),
        ).HoleDiameter = 6.0

        _load_endcap_defaults(obj)

        obj.Proxy = self
        self._cached_key = None
        self._cached_shape = None

    def dumps(self):
        return None

    def loads(self, state):
        self._cached_key = None
        self._cached_shape = None

    def _endcap_key(self, fp):
        try:
            key_parts = [fp.CapType, fp.Reverse, fp.Thickness, fp.Offset, fp.PlugOffset,
                         fp.HoleEnabled, fp.HoleDiameter, fp.HoleThreaded, fp.HoleThreadSpec,
                         fp.ChamferEnabled, fp.ChamferSize, fp.FilletEnabled, fp.FilletSize]
            if fp.BaseObject and len(fp.BaseObject) >= 2:
                try:
                    obj, name = fp.BaseObject
                    face_shape = obj.getSubObject(name[0])
                    if face_shape and not face_shape.isNull():
                        bb = face_shape.BoundBox
                        key_parts.append(hash((bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax)))
                except Exception:
                    pass
            return hash(tuple(key_parts))
        except Exception:
            return None

    def onChanged(self, fp, prop):
        if prop == "HoleThreadSpec":
            spec = str(fp.HoleThreadSpec)
            if spec in THREAD_SPECS and THREAD_SPECS[spec] > 0:
                fp.HoleDiameter = THREAD_SPECS[spec]

    def execute(self, fp):
        if fp.BaseObject is None:
            return

        obj_ref, face_name = fp.BaseObject
        face = obj_ref.getSubObject(face_name[0])
        if face is None:
            return

        try:
            n = face.normalAt(0.5, 0.5)
        except Exception:
            return

        cache_key = self._endcap_key(fp)
        if cache_key is not None and getattr(self, "_cached_key", None) == cache_key and getattr(self, "_cached_shape", None) is not None:
            fp.Shape = self._cached_shape
            self._update_structure_data(fp)
            return

        if fp.Reverse:
            n = n.negative()

        # Convert to float (PropertyLength returns Quantity)
        t = float(fp.Thickness)
        gap = float(fp.Offset)

        if t <= 0:
            return

        # Build cap based on type
        try:
            if fp.CapType == 0:  # Plate: outer wire, extrude outward
                base_wire = face.OuterWire
                extrude_dir = n
            else:  # Plug: inner hole wire, extrude into profile
                plug_off = float(fp.PlugOffset)
                inner = None
                for w in face.Wires:
                    if not w.isSame(face.OuterWire):
                        inner = w
                        break
                if inner is not None:
                    base_wire = inner
                else:
                    base_wire = face.OuterWire
                if plug_off > 0:
                    try:
                        offset_result = base_wire.makeOffset2D(-plug_off)
                        if offset_result and not offset_result.isNull() and offset_result.Wires:
                            base_wire = offset_result.Wires[0]
                    except Exception as e:
                        App.Console.PrintWarning(f"EndCap: plug offset failed: {e}\n")
                extrude_dir = -n

            cap_face = Part.Face(base_wire)
            if cap_face.isNull() or not cap_face.isValid():
                return
        except Exception as e:
            App.Console.PrintWarning(f"EndCap: cap construction failed: {e}\n")
            return

        thick_vec = extrude_dir * t
        gap_vec = extrude_dir * gap
        cap = cap_face.translated(gap_vec).extrude(thick_vec)
        if cap.isNull() or not cap.isValid():
            cap = cap_face.extrude(thick_vec)
            if cap.isNull() or not cap.isValid():
                return

        # Center hole (bolt hole)
        if fp.HoleEnabled and fp.HoleDiameter > 0:
            try:
                hdia = float(fp.HoleDiameter)
                center = face.CenterOfGravity
                hole_len = t + 10
                if fp.HoleThreaded:
                    csink_r = hdia * 0.65
                    cone_h = csink_r - hdia / 2.0
                    cone = Part.makeCone(csink_r, hdia / 2.0, cone_h, center, extrude_dir)
                    cyl = Part.makeCylinder(hdia / 2.0, hole_len, center, n)
                    hole = cyl.fuse(cone)
                    hole.translate(n * (-5))
                else:
                    circle = Part.makeCircle(hdia / 2.0, center, n)
                    hole_face = Part.Face(Part.Wire(circle))
                    hole = hole_face.extrude(n * hole_len)
                    hole.translate(n * (-5))
                if not hole.isNull() and hole.isValid():
                    cap = cap.cut(hole)
            except Exception:
                pass

        # Apply chamfer or fillet to vertical edges
        try:
            min_len = max(float(fp.ChamferSize), float(fp.FilletSize)) * 2.0
            if min_len <= 0:
                min_len = 0.1
            candidates = []
            for e in cap.Edges:
                d = e.Vertexes[-1].Point - e.Vertexes[0].Point
                dl = d.Length
                if dl > min_len and abs(d.dot(extrude_dir)) / dl > 0.9:
                    candidates.append(e)
            if candidates:
                ch = float(fp.ChamferSize) if fp.ChamferEnabled and fp.ChamferSize > 0 else 0
                fi = float(fp.FilletSize) if fp.FilletEnabled and fp.FilletSize > 0 else 0
                for e in candidates:
                    try:
                        if ch > 0:
                            r = cap.makeChamfer(ch, [e])
                            if r and not r.isNull() and r.isValid():
                                cap = r
                        elif fi > 0:
                            r = cap.makeFillet(fi, [e])
                            if r and not r.isNull() and r.isValid():
                                cap = r
                    except Exception:
                        pass
        except Exception as e:
            App.Console.PrintWarning(f"EndCap: chamfer/fillet error: {e}\n")

        fp.Shape = cap
        self._cached_key = cache_key
        self._cached_shape = cap
        self._update_structure_data(fp)


    def _update_structure_data(self, obj):
        try:
            prof = get_profile_from_trimmedbody(obj.BaseObject[0])
        except Exception:
            return
        if not hasattr(prof, "PID"):
            return

        obj.PID = prof.PID
        obj.Width = prof.ProfileWidth if hasattr(prof, "ProfileWidth") else 0
        obj.Height = prof.ProfileHeight if hasattr(prof, "ProfileHeight") else 0
        obj.Family = prof.Family
        obj.CustomProfile = getattr(prof, "CustomProfile", None)
        obj.SizeName = prof.SizeName
        obj.Material = prof.Material
        obj.ApproxWeight = prof.ApproxWeight
        obj.Price = prof.Price

        obj.Length = obj.Thickness + obj.Offset


class ViewProviderEndCap:
    def __init__(self, vobj):
        vobj.Proxy = self
        self.ViewObject = vobj
        self.Object = vobj.Object

    def attach(self, vobj):
        self.ViewObject = vobj
        self.Object = vobj.Object
        vobj.ShapeColor = (0.6, 0.6, 0.6)
        vobj.Transparency = 0

    def getDisplayModes(self, obj):
        modes = []
        return modes

    def getDefaultDisplayMode(self):
        return "FlatLines"

    def setDisplayMode(self, mode):
        return mode

    def claimChildren(self):
        if self.Object.BaseObject:
            return [self.Object.BaseObject[0]]
        return []

    def onChanged(self, vp, prop):
        pass

    def onDelete(self, vobj, sub):
        try:
            if vobj.Object and vobj.Object.BaseObject:
                vobj.Object.BaseObject[0].ViewObject.Visibility = True
        except Exception:
            pass
        return True

    def getIcon(self):
        return """
        /* XPM */
            static char * end_cap_xpm[] = {
            "16 16 2 1",
            " 	c None",
            "@	c #729FCF",
            "@@@@@@@@@@@@@@@@",
            "@              @",
            "@              @",
            "@  @@@@@@@@@@  @",
            "@  @@@@@@@@@@  @",
            "@  @@@@@@@@@@  @",
            "@  @@@@@@@@@@  @",
            "@  @@@@@@@@@@  @",
            "@  @@@@@@@@@@  @",
            "@  @@@@@@@@@@  @",
            "@  @@@@@@@@@@  @",
            "@  @@@@@@@@@@  @",
            "@              @",
            "@              @",
            "@              @",
            "@@@@@@@@@@@@@@@@"};
        """

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def setEdit(self, vobj, mode):
        if mode != 0:
            return None

        import freecad.frameforgemod.create_end_cap_tool

        taskd = freecad.frameforgemod.create_end_cap_tool.CreateEndCapTaskPanel(self.Object)
        Gui.Control.showDialog(taskd)
        return True

    def unsetEdit(self, vobj, mode):
        if mode != 0:
            return None

        Gui.Control.closeDialog()
        return True

    def edit(self):
        FreeCADGui.ActiveDocument.setEdit(self.Object, 0)

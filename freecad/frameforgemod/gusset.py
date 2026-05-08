import math
import os

import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtCore, QtGui

from freecad.frameforgemod._utils import (
    _register_profile_metadata,
    get_profile_from_trimmedbody,
    length_along_normal,
)
from freecad.frameforgemod.ff_tools import ICONPATH, PROFILEIMAGES_PATH, PROFILESPATH, UIPATH, translate


class Gusset:
    def __init__(self, obj):
        _register_profile_metadata(obj)

        obj.addProperty(
            "App::PropertyLinkSubList",
            "Face1",
            "Gusset",
            translate("App::Property", "First face"),
        ).Face1 = None

        obj.addProperty(
            "App::PropertyLinkSubList",
            "Face2",
            "Gusset",
            translate("App::Property", "Second face"),
        ).Face2 = None

        obj.addProperty(
            "App::PropertyLength",
            "Thickness",
            "Gusset",
            translate("App::Property", "Plate thickness"),
        ).Thickness = 6.0

        obj.addProperty(
            "App::PropertyLength",
            "LegLength1",
            "Gusset",
            translate("App::Property", "Length along first face"),
        ).LegLength1 = 50.0

        obj.addProperty(
            "App::PropertyLength",
            "LegLength2",
            "Gusset",
            translate("App::Property", "Length along second face"),
        ).LegLength2 = 50.0

        obj.addProperty(
            "App::PropertyLength",
            "Offset",
            "Gusset",
            translate("App::Property", "Offset from the corner"),
        ).Offset = 0.0

        obj.addProperty(
            "App::PropertyInteger",
            "ThicknessAlign",
            "Gusset",
            translate("App::Property", "Thickness: 0=forward, 1=center, 2=reverse"),
        ).ThicknessAlign = 1

        obj.addProperty(
            "App::PropertyInteger",
            "PositionAlign",
            "Gusset",
            translate("App::Property", "Position: 0=left, 1=center, 2=right"),
        ).PositionAlign = 1

        obj.addProperty(
            "App::PropertyLength",
            "PositionOffset",
            "Gusset",
            translate("App::Property", "Position offset along the intersection line"),
        ).PositionOffset = 0.0

        obj.addProperty(
            "App::PropertyBool",
            "HoleEnabled",
            "Gusset",
            translate("App::Property", "Enable center hole"),
        ).HoleEnabled = False

        obj.addProperty(
            "App::PropertyLength",
            "HoleDiameter",
            "Gusset",
            translate("App::Property", "Hole diameter"),
        ).HoleDiameter = 8.0

        obj.Proxy = self
        self._cached_key = None
        self._cached_shape = None

    def _gusset_key(self, fp):
        try:
            key_parts = [
                float(fp.Thickness),
                float(fp.HoleDiameter) if fp.HoleEnabled else 0.0,
                float(fp.LegLength1),
                float(fp.LegLength2),
                float(fp.Offset),
                int(fp.ThicknessAlign),
                int(fp.PositionAlign),
                float(fp.PositionOffset),
                int(fp.HoleEnabled),
            ]
            for face_prop in (fp.Face1, fp.Face2):
                if face_prop and len(face_prop) > 0 and len(face_prop[0]) >= 2:
                    try:
                        face_shape = face_prop[0][0].getSubObject(face_prop[0][1][0])
                        if face_shape and not face_shape.isNull():
                            bb = face_shape.BoundBox
                            key_parts.append(hash((bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax)))
                    except Exception:
                        pass
            return hash(tuple(key_parts))
        except Exception:
            return None

    def onChanged(self, fp, prop):
        if prop in ("Face1", "Face2", "Thickness", "LegLength1", "LegLength2",
                     "Offset", "ThicknessAlign", "PositionAlign", "PositionOffset",
                     "HoleEnabled", "HoleDiameter"):
            self._cached_key = None
            self._cached_shape = None
            fp.recompute()

    def execute(self, fp):
        if fp.Face1 is None or fp.Face2 is None:
            fp.Shape = Part.Shape()
            return
        if len(fp.Face1) == 0 or len(fp.Face2) == 0:
            fp.Shape = Part.Shape()
            return
        if len(fp.Face1[0]) < 2 or len(fp.Face2[0]) < 2:
            fp.Shape = Part.Shape()
            return

        obj1, subs1 = fp.Face1[0]
        obj2, subs2 = fp.Face2[0]
        face1 = obj1.getSubObject(subs1[0])
        face2 = obj2.getSubObject(subs2[0])

        if face1 is None or face2 is None:
            return
        if not isinstance(face1.Surface, Part.Plane) or not isinstance(face2.Surface, Part.Plane):
            return

        cache_key = self._gusset_key(fp)
        if self._cached_key == cache_key and self._cached_shape is not None:
            fp.Shape = self._cached_shape
            self._update_structure_data(fp)
            return

        s1 = face1.Surface
        s2 = face2.Surface
        n1 = s1.Axis
        n2 = s2.Axis

        # Intersection line of the two planes
        line_dir = n1.cross(n2)
        if line_dir.Length < 1e-7:
            App.Console.PrintMessage("Gusset: faces are parallel, cannot create gusset\n")
            return
        line_dir.normalize()

        # Find point on intersection line by solving plane equations
        d1_f = s1.Position.dot(n1)
        d2_f = s2.Position.dot(n2)
        n1n2 = n1.dot(n2)
        det = 1.0 - n1n2 * n1n2
        if abs(det) < 1e-7:
            return
        a = (d1_f - n1n2 * d2_f) / det
        b = (d2_f - n1n2 * d1_f) / det
        p0 = n1 * a + n2 * b

        # Directions along each face, perpendicular to the intersection line
        dir1 = n1.cross(line_dir).normalize()
        dir2 = n2.cross(line_dir).normalize()

        # Point directions toward the face centers
        c1 = face1.CenterOfGravity
        c2 = face2.CenterOfGravity
        if (c1 - p0).dot(dir1) < 0:
            dir1 = -dir1
        if (c2 - p0).dot(dir2) < 0:
            dir2 = -dir2

        # Convert all dimension properties to float (PropertyLength returns Quantity)
        t = float(fp.Thickness)
        leg1 = float(fp.LegLength1)
        leg2 = float(fp.LegLength2)
        off = float(fp.Offset)
        pos_off = float(fp.PositionOffset)

        # Triangle vertices with offset
        offset_vec = dir1 * off + dir2 * off
        v0 = p0 + offset_vec
        v1 = p0 + dir1 * leg1 + offset_vec
        v2 = p0 + dir2 * leg2 + offset_vec

        # Compute position along the intersection line
        # Collect all face vertices to find the extent of the intersection
        all_pts = []
        for face in [face1, face2]:
            for v in face.Vertexes:
                all_pts.append(v.Point)

        dots = [p.dot(line_dir) for p in all_pts]
        line_min = min(dots)
        line_max = max(dots)

        # Determine which end is "outside" vs "inside"
        # Average of all face vertices is interior; farthest end from it is "outside"
        avg_pt = App.Vector(0, 0, 0)
        for pt in all_pts:
            avg_pt += pt
        avg_pt /= len(all_pts)
        ref_dot = avg_pt.dot(line_dir)

        if abs(line_min - ref_dot) > abs(line_max - ref_dot):
            outside_val, inside_val = line_min, line_max
        else:
            outside_val, inside_val = line_max, line_min

        # Compute target based on alignment mode
        # 0=外侧, 1=居中, 2=内侧
        line_ref = p0.dot(line_dir)
        if fp.PositionAlign == 0:  # 外侧
            target = outside_val
        elif fp.PositionAlign == 1:  # 居中
            target = (line_min + line_max) / 2.0
        else:  # 内侧
            target = inside_val

        shift = target - line_ref + pos_off
        if shift != 0:
            pos_vec = line_dir * shift
            v0 = v0 + pos_vec
            v1 = v1 + pos_vec
            v2 = v2 + pos_vec

        # Normal of the triangle (perpendicular to the plate)
        tri_normal = (v1 - v0).cross(v2 - v0).normalize()

        # For centered mode, shift triangle face back by half thickness
        # so extrude gives equal thickness on both sides
        if fp.ThicknessAlign == 1:  # 居中
            shift_vec = tri_normal * (-t / 2.0)
            v0 = v0 + shift_vec
            v1 = v1 + shift_vec
            v2 = v2 + shift_vec

        # Re-create triangle face with possibly shifted vertices
        try:
            wire = Part.makePolygon([v0, v1, v2, v0])
            tri_face = Part.Face(wire)
        except Exception as e:
            App.Console.PrintWarning(f"Gusset: face construction failed: {e}\n")
            return

        if tri_face.isNull() or not tri_face.isValid():
            return

        # Extrude to create solid (thickness direction depends on alignment mode)
        extrude_dir = tri_normal if fp.ThicknessAlign != 2 else -tri_normal
        gusset = tri_face.extrude(extrude_dir * t)
        if gusset.isNull() or not gusset.isValid():
            return

        # Hole - use long bidirectional hole to always penetrate
        if fp.HoleEnabled and fp.HoleDiameter > 0:
            try:
                hdia = float(fp.HoleDiameter)
                center = (v0 + v1 + v2) / 3.0
                circle = Part.makeCircle(hdia / 2.0, center, tri_normal)
                hole_face = Part.Face(Part.Wire(circle))
                hole = hole_face.extrude(tri_normal * (t * 4))
                if not hole.isNull() and hole.isValid():
                    hole.translate(tri_normal * (-t * 2))
                    gusset = gusset.cut(hole)
            except Exception:
                pass

        fp.Shape = gusset
        self._cached_key = cache_key
        self._cached_shape = gusset
        self._update_structure_data(fp)

    def _update_structure_data(self, obj):
        try:
            base_obj = None
            if obj.Face1 and len(obj.Face1) > 0:
                base_obj = obj.Face1[0]
            if base_obj is None and obj.Face2 and len(obj.Face2) > 0:
                base_obj = obj.Face2[0]
            if base_obj:
                prof = get_profile_from_trimmedbody(base_obj)
                if prof:
                    obj.PID = prof.PID
                    obj.SizeName = prof.SizeName
                    obj.Family = prof.Family
                    obj.Material = prof.Material
                    obj.CustomProfile = prof.CustomProfile if hasattr(prof, "CustomProfile") else None
                    obj.ApproxWeight = prof.ApproxWeight
                    obj.Price = prof.Price
                    obj.Length = float(obj.Thickness)
        except Exception:
            pass


class ViewProviderGusset:
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
        if prop in ("Face1", "Face2", "Shape"):
            try:
                if fp.Face1 and len(fp.Face1) > 0 and fp.Face1[0]:
                    vp = fp.Face1[0].ViewObject
                    self.ViewObject.ShapeColor = vp.ShapeColor
                    self.ViewObject.Transparency = vp.Transparency
                    return
            except Exception:
                pass
            try:
                if fp.Face2 and len(fp.Face2) > 0 and fp.Face2[0]:
                    vp = fp.Face2[0].ViewObject
                    self.ViewObject.ShapeColor = vp.ShapeColor
                    self.ViewObject.Transparency = vp.Transparency
            except Exception:
                pass
        return

    def getDisplayModes(self, obj):
        modes = []
        return modes

    def getDefaultDisplayMode(self):
        return "FlatLines"

    def setDisplayMode(self, mode):
        return mode

    def claimChildren(self):
        children = []
        try:
            if self.Object.Face1 and len(self.Object.Face1) > 0:
                children.append(self.Object.Face1[0])
        except Exception:
            pass
        try:
            if self.Object.Face2 and len(self.Object.Face2) > 0:
                children.append(self.Object.Face2[0])
        except Exception:
            pass
        return children

    def onChanged(self, vp, prop):
        pass

    def onDelete(self, fp, sub):
        return True

    def setEdit(self, vobj, mode):
        if mode != 0:
            return None

        import freecad.frameforgemod.create_gusset_tool

        taskd = freecad.frameforgemod.create_gusset_tool.CreateGussetTaskPanel(self.Object)
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
            static char * gusset_xpm[] = {
            "16 16 2 1",
            " 	c None",
            "@	c #729FCF",
            "@@@@@@@@@@@@@@@@",
            "@@            @@",
            "@@@          @@@",
            "@@@@        @@@@",
            "@@@@@      @@@@@",
            "@@@@@@    @@@@@@",
            "@@@@@@@  @@@@@@@",
            "@@@@@@@@@@@@@@@@",
            "@@@@@@@  @@@@@@@",
            "@@@@@@    @@@@@@",
            "@@@@@      @@@@@",
            "@@@@        @@@@",
            "@@@          @@@",
            "@@            @@",
            "@              @",
            "@@@@@@@@@@@@@@@@"};
        """

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

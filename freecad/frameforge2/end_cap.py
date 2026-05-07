import os

import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtCore, QtGui

from freecad.frameforge2._utils import (
    get_profile_from_trimmedbody,
    get_readable_cutting_angles,
    get_trimmed_profile_all_cutting_angles,
    length_along_normal,
)
from freecad.frameforge2.ff_tools import ICONPATH, PROFILEIMAGES_PATH, PROFILESPATH, UIPATH, translate
from freecad.frameforge2.version import __version__ as ff_version


class EndCap:
    def __init__(self, obj, selected_face):
        obj.addProperty(
            "App::PropertyString",
            "FrameforgeVersion",
            "Profile",
            "Frameforge Version used to create the profile",
        ).FrameforgeVersion = ff_version

        obj.addProperty(
            "App::PropertyString",
            "PID",
            "Profile",
            "Profile ID",
        ).PID = ""
        obj.setEditorMode("PID", 1)

        obj.addProperty("App::PropertyLinkSub", "BaseObject", "EndCap", "Selected face for the end cap").BaseObject = (
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
            translate("App::Property", "Offset from the face"),
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
            "App::PropertyLength",
            "HoleDiameter",
            "EndCap",
            translate("App::Property", "Hole diameter"),
        ).HoleDiameter = 6.0

        # related to Profile (readonly)
        obj.addProperty("App::PropertyString", "Family", "Profile", "")
        obj.setEditorMode("Family", 1)

        obj.addProperty("App::PropertyLink", "CustomProfile", "Profile", "Target profile").CustomProfile = None
        obj.setEditorMode("CustomProfile", 1)

        obj.addProperty("App::PropertyString", "SizeName", "Profile", "")
        obj.setEditorMode("SizeName", 1)

        obj.addProperty("App::PropertyString", "Material", "Profile", "")
        obj.setEditorMode("Material", 1)

        obj.addProperty("App::PropertyFloat", "ApproxWeight", "Base", "Approximate weight in Kilogram")
        obj.setEditorMode("ApproxWeight", 1)

        obj.addProperty("App::PropertyFloat", "Price", "Base", "Profile Price")
        obj.setEditorMode("Price", 1)

        # structure
        obj.addProperty("App::PropertyLength", "Width", "Structure", "Parameter for structure")
        obj.addProperty("App::PropertyLength", "Height", "Structure", "Parameter for structure")
        obj.addProperty("App::PropertyLength", "Length", "Structure", "Parameter for structure")
        obj.addProperty("App::PropertyBool", "Cutout", "Structure", "Has Cutout").Cutout = False
        obj.setEditorMode("Width", 1)
        obj.setEditorMode("Height", 1)
        obj.setEditorMode("Length", 1)
        obj.setEditorMode("Cutout", 1)

        obj.addProperty(
            "App::PropertyString",
            "CuttingAngleA",
            "Structure",
            "Cutting Angle A",
        )
        obj.setEditorMode("CuttingAngleA", 1)
        obj.addProperty(
            "App::PropertyString",
            "CuttingAngleB",
            "Structure",
            "Cutting Angle B",
        )
        obj.setEditorMode("CuttingAngleB", 1)

        obj.Proxy = self

    def onChanged(self, fp, prop):
        pass

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

        if fp.Reverse:
            n = n.negative()

        # Convert to float (PropertyLength returns Quantity)
        t = float(fp.Thickness)
        off = float(fp.Offset)

        # Build cap based on type
        try:
            if fp.CapType == 0:  # Plate: outer wire, extrude outward
                base_wire = face.OuterWire
                extrude_dir = n
            else:  # Plug: inner hole wire, extrude into profile
                plug_off = float(fp.PlugOffset)
                # Find inner wire (cavity) if available
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
                        base_wire = base_wire.offset2D(-plug_off, 0.01, fill=False)
                    except Exception:
                        pass
                extrude_dir = -n

            cap_face = Part.Face(base_wire)
            if cap_face.isNull() or not cap_face.isValid():
                return
        except Exception as e:
            App.Console.PrintWarning(f"EndCap: cap construction failed: {e}\n")
            return

        thick_vec = extrude_dir * t
        offset_vec = extrude_dir * off
        cap = cap_face.extrude(offset_vec + thick_vec)
        if cap.isNull() or not cap.isValid():
            cap = cap_face.extrude(thick_vec)
            if cap.isNull() or not cap.isValid():
                return

        # Center hole (bolt hole)
        if fp.HoleEnabled and fp.HoleDiameter > 0:
            try:
                hdia = float(fp.HoleDiameter)
                center = face.CenterOfGravity
                if fp.HoleThreaded:
                    # Threaded hole: add cosmetic countersink for visual distinction
                    csink_r = hdia * 0.65
                    cone_h = csink_r - hdia / 2.0
                    cone = Part.makeCone(csink_r, hdia / 2.0, cone_h, center, extrude_dir)
                    cyl = Part.makeCylinder(hdia / 2.0, t + off + 10, center, n)
                    hole = cyl.fuse(cone)
                    hole.translate(n * (-5))
                else:
                    circle = Part.makeCircle(hdia / 2.0, center, n)
                    hole_face = Part.Face(Part.Wire(circle))
                    hole = hole_face.extrude(n * (t + off + 10))
                    hole.translate(n * (-5))
                if not hole.isNull() and hole.isValid():
                    cap = cap.cut(hole)
            except Exception:
                pass

        # Apply chamfer or fillet to end edges
        try:
            # Find face(s) furthest along extrude_dir (the end face)
            end_faces = []
            max_dot = None
            for f in cap.Faces:
                fc = f.CenterOfGravity.dot(extrude_dir)
                if max_dot is None or fc > max_dot + 0.01:
                    max_dot = fc
                    end_faces = [f]
                elif abs(fc - max_dot) < 0.01:
                    end_faces.append(f)
            # Collect unique edges from end faces
            end_edges = []
            seen_hashes = set()
            for f in end_faces:
                for e in f.Edges:
                    h = e.hashCode()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        end_edges.append(e)
            if end_edges:
                if fp.ChamferEnabled and fp.ChamferSize > 0:
                    cap = cap.makeChamfer(fp.ChamferSize, end_edges)
                elif fp.FilletEnabled and fp.FilletSize > 0:
                    cap = cap.fillet(fp.FilletSize, end_edges)
        except Exception:
            pass

        fp.Shape = cap
        self._update_structure_data(fp)

    def _update_structure_data(self, obj):
        try:
            prof = get_profile_from_trimmedbody(obj.BaseObject[0])
        except Exception:
            return

        obj.PID = prof.PID
        obj.Width = prof.ProfileWidth if hasattr(prof, "ProfileWidth") else 0
        obj.Height = prof.ProfileHeight if hasattr(prof, "ProfileHeight") else 0
        obj.Family = prof.Family
        obj.CustomProfile = prof.CustomProfile
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
        vobj.ShapeColor = (0.6, 0.6, 0.6)
        vobj.Transparency = 0

    def attach(self, vobj):
        self.ViewObject = vobj
        self.Object = vobj.Object
        vobj.ShapeColor = (0.6, 0.6, 0.6)
        vobj.Transparency = 0

    def updateData(self, fp, prop):
        if prop in ("BaseObject", "Shape"):
            if fp.BaseObject and fp.BaseObject[0]:
                try:
                    vp = fp.BaseObject[0].ViewObject
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

        import freecad.frameforge2.create_end_cap_tool

        taskd = freecad.frameforge2.create_end_cap_tool.CreateEndCapTaskPanel(self.Object)
        Gui.Control.showDialog(taskd)
        return True

    def unsetEdit(self, vobj, mode):
        if mode != 0:
            return None

        Gui.Control.closeDialog()
        return True

    def edit(self):
        FreeCADGui.ActiveDocument.setEdit(self.Object, 0)

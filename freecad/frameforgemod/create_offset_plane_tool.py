import os

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtGui

from freecad.frameforgemod.ff_tools import ICONPATH, translate

TOOL_ICON = os.path.join(ICONPATH, "offset_plane.svg")


def find_body(obj):
    if obj.TypeId == 'PartDesign::Body':
        return obj
    if hasattr(obj, 'getParentGroup'):
        p = obj.getParentGroup()
        if p and p.TypeId == 'PartDesign::Body':
            return p
    doc = obj.Document if hasattr(obj, 'Document') else None
    if doc:
        for o in doc.Objects:
            if o.TypeId == 'PartDesign::Body' and hasattr(o, 'Group') and obj in o.Group:
                return o
    return None


class CreateOffsetPlaneCommand:
    def GetResources(self):
        return {
            "Pixmap": TOOL_ICON,
            "MenuText": translate("frameforgemod", "Offset Datum Plane"),
            "ToolTip": translate(
                "frameforgemod",
                "Create a datum plane offset from a selected face"),
        }

    def IsActive(self):
        if App.ActiveDocument is None:
            return False
        sel = Gui.Selection.getSelectionEx()
        return len(sel) > 0 and len(sel[0].SubElementNames) > 0

    def Activated(self):
        doc = App.ActiveDocument
        sel = Gui.Selection.getSelectionEx()
        if not sel or not sel[0].SubElementNames:
            App.Console.PrintWarning("FF2: Select a face first\n")
            return
        obj = sel[0].Object
        face = sel[0].SubElementNames[0]
        distance, ok = QtGui.QInputDialog.getDouble(
            None, translate("frameforgemod", "Offset Datum Plane"),
            translate("frameforgemod", "Offset distance (mm, negative = opposite):"),
            10.0, -10000, 10000, 1)
        if not ok:
            return
        body = find_body(obj)
        if body:
            plane = body.newObject('PartDesign::Plane', 'OffsetPlane')
        else:
            plane = doc.addObject('PartDesign::Plane', 'OffsetPlane')
        try:
            plane.Support = (obj, face)
        except AttributeError:
            plane.AttachmentSupport = [(obj, face)]
        plane.MapMode = 'FlatFace'
        try:
            from FreeCAD import Placement, Vector, Rotation
            plane.AttachmentOffset = Placement(Vector(0, 0, distance), Rotation())
        except AttributeError:
            plane.Offset = distance
        doc.recompute()


Gui.addCommand("frameforgemod_OffsetPlane", CreateOffsetPlaneCommand())

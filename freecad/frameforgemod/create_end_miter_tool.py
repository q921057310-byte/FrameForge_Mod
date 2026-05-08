"""Independent miter tool for profile frames.

Select two intersecting/adjacent profiles (one edge each) to create
miter cuts on both at their shared corner.
"""
import os

import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtCore, QtGui

from freecad.frameforgemod.ff_tools import ICONPATH, translate
from freecad.frameforgemod.trimmed_profile import TrimmedProfile, ViewProviderTrimmedProfile


class CreateEndMiterCommand:
    def GetResources(self):
        return {
            "Pixmap": os.path.join(ICONPATH, "corner-end-miter.svg"),
            "MenuText": translate("frameforgemod", "Miter Ends"),
            "Accel": "M, C",
            "ToolTip": translate(
                "frameforgemod",
                "Select two intersecting/adjacent profiles (one edge each) to miter.",
            ),
        }

    def IsActive(self):
        if App.ActiveDocument:
            sel = Gui.Selection.getSelectionEx()
            if len(sel) == 2:
                for s in sel:
                    if len(s.SubElementNames) != 1:
                        return False
                return True
        return False

    def Activated(self):
        sel = Gui.Selection.getSelectionEx()
        App.ActiveDocument.openTransaction("Make End Miter Profile")

        if len(sel) == 2:
            self.make_end_miter_profile(sel[0].Object, [(sel[1].Object, sel[1].SubElementNames)])
            self.make_end_miter_profile(sel[1].Object, [(sel[0].Object, sel[0].SubElementNames)])

        App.ActiveDocument.commitTransaction()
        App.ActiveDocument.recompute()

    def make_end_miter_profile(self, trimmedBody=None, trimmingBoundary=None):
        doc = App.ActiveDocument

        name = "TrimmedProfile" if trimmedBody is None else f"{trimmedBody.Name}_Mt"
        trimmed_profile = doc.addObject("Part::FeaturePython", name)

        if trimmedBody is not None and len(trimmedBody.Parents) > 0:
            trimmedBody.Parents[-1][0].addObject(trimmed_profile)

        TrimmedProfile(trimmed_profile)

        ViewProviderTrimmedProfile(trimmed_profile.ViewObject)
        trimmed_profile.TrimmedBody = trimmedBody
        trimmed_profile.TrimmingBoundary = trimmingBoundary

        trimmed_profile.TrimmedProfileType = "End Miter"

        return trimmed_profile


Gui.addCommand("frameforgemod_EndMiter", CreateEndMiterCommand())

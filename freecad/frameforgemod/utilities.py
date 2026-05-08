import os
from collections import Counter

import FreeCAD
import FreeCADGui
import TechDrawGui
from PySide import QtCore, QtGui
try:
    from PySide import QtWidgets
except ImportError:
    QtWidgets = QtGui

import freecad.frameforgemod._utils as ffu
from freecad.frameforgemod.ff_tools import ICONPATH, PROFILEIMAGES_PATH, PROFILESPATH, UIPATH, translate

# TechDraw PDF Gen


class ExportTechDrawCommand:
    def GetResources(self):
        return {
            "Pixmap": os.path.join(ICONPATH, "gen_techdraw.svg"),
            "MenuText": translate("frameforgemod", "Export TechDraw to PDF"),
            "Accel": "M, E",
            "ToolTip": translate(
                "frameforgemod",
                "Export all TechDraw pages in the document to PDF files.",
            ),
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        doc = FreeCAD.ActiveDocument

        if doc is None:
            raise RuntimeError("No active document")

        # Output directory
        if doc.FileName:
            out_dir = QtWidgets.QFileDialog.getExistingDirectory(None, "Export folder", os.path.dirname(doc.FileName))
        else:
            out_dir = FreeCAD.getUserAppDataDir()

        for obj in doc.Objects:
            if obj.TypeId == "TechDraw::DrawPage":
                pdf_name = "".join(c for c in obj.Label if c.isalnum() or c in (" ", ".", "_")).rstrip()
                pdf_path = os.path.join(out_dir, f"{pdf_name}.pdf")

                TechDrawGui.exportPageAsPdf(obj, pdf_path)

                FreeCAD.Console.PrintMessage(f"Exported: {pdf_path}\n")

        FreeCAD.Console.PrintMessage("All TechDraw pages exported.\n")


FreeCADGui.addCommand("frameforgemod_ExportTechDraw", ExportTechDrawCommand())


class RecomputeFrameForgeObjectsCommand:
    def GetResources(self):
        return {
            "Pixmap": os.path.join(ICONPATH, "recompute.svg"),
            "MenuText": translate("frameforgemod", "Recursive Recompute"),
            "Accel": "M, Shift+R",
            "ToolTip": translate(
                "frameforgemod",
                "Recursively recompute all FrameForge objects and their dependencies.",
            ),
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        stats = []

        def recursive_recompute(objs):
            for obj in objs:
                if ffu.is_profile(obj) or ffu.is_trimmedbody(obj) or ffu.is_extrudedcutout(obj):
                    recursive_recompute(obj.OutList)

                    FreeCAD.Console.PrintMessage(f"{obj.Label} ...")

                    obj.recompute()

                    stats.append(obj.Label)
                    FreeCAD.Console.PrintMessage("ok\n")

        recursive_recompute(FreeCAD.ActiveDocument.Objects)

        cs = Counter(stats)
        for k in cs:
            FreeCAD.Console.PrintMessage(f"{k} = {cs[k]}\n")
        # FreeCAD.ActiveDocument.recompute()


FreeCADGui.addCommand("frameforgemod_RecomputeFrameForgeObjects", RecomputeFrameForgeObjectsCommand())

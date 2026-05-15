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


class ColorProfilesCommand:
    def GetResources(self):
        return {
            "Pixmap": os.path.join(ICONPATH, "profile.svg"),
            "MenuText": "Color Profiles / 型材着色",
            "ToolTip": "Color identical profiles (same Family + Size + Length + CutAngles).\n相同型材（同系列+同尺寸+同长度+同切角）分配同色。",
        }

    def IsActive(self):
        return True

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        if not doc:
            return
        sel = FreeCADGui.Selection.getSelection()
        objs = sel if sel else doc.Objects

        def get_profile(obj):
            """Get (Family, SizeName, Length, CutA, CutB) from profile or trimmed."""
            if hasattr(obj, "ProfileWidth") and hasattr(obj, "ProfileHeight"):
                return (getattr(obj, "Family", ""),
                        getattr(obj, "SizeName", ""),
                        round(float(getattr(obj, "Length", 0)), 1),
                        getattr(obj, "CuttingAngleA", ""),
                        getattr(obj, "CuttingAngleB", ""))
            if hasattr(obj, "TrimmedBody") and obj.TrimmedBody:
                p = obj.TrimmedBody
                return (getattr(p, "Family", ""),
                        getattr(p, "SizeName", ""),
                        round(float(getattr(obj, "Length", 0)), 1),
                        getattr(obj, "CuttingAngleA", ""),
                        getattr(obj, "CuttingAngleB", ""))
            return None

        groups = {}
        for o in objs:
            key = get_profile(o)
            if key:
                groups.setdefault(key, []).append(o)

        if not groups:
            FreeCAD.Console.PrintMessage("No profiles or trimmed profiles found.\n")
            return

        colors = [(0.85, 0.60, 0.10), (0.10, 0.50, 0.85), (0.85, 0.20, 0.20),
                  (0.10, 0.75, 0.40), (0.70, 0.30, 0.80), (0.20, 0.70, 0.70),
                  (0.90, 0.50, 0.10), (0.50, 0.50, 0.50), (0.10, 0.40, 0.60),
                  (0.80, 0.40, 0.40), (0.40, 0.70, 0.30), (0.50, 0.30, 0.60)]

        for i, (key, objs) in enumerate(groups.items()):
            color = colors[i % len(colors)]
            for o in objs:
                try:
                    o.ViewObject.ShapeColor = color
                except Exception:
                    pass
            FreeCAD.Console.PrintMessage(f"{objs[0].Family} {objs[0].SizeName} → color #{i+1}\n")

        doc.recompute()


FreeCADGui.addCommand("frameforgemod_ColorProfiles", ColorProfilesCommand())

# -*- coding: utf-8 -*-
"""Weld annotation - fillet weld along edge between two faces."""

import os
import math
import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtCore, QtGui
from freecad.frameforgemod.ff_tools import ICONPATH, translate


class WeldTaskPanel:
    def __init__(self, edge, edge_obj_name):
        self.edge = edge
        self.obj_name = edge_obj_name
        self.form = QtGui.QWidget()
        layout = QtGui.QVBoxLayout(self.form)

        info = QtGui.QLabel(
            "Create a fillet weld along this edge.\n"
            "Automatically detected adjacent faces.\n"
            "沿此边创建角焊缝，自动检测相邻面。")
        info.setWordWrap(True)
        layout.addWidget(info)

        grp = QtGui.QGroupBox("Weld / 焊缝")
        grp_lay = QtGui.QFormLayout(grp)
        self.spin_size = QtGui.QDoubleSpinBox()
        self.spin_size.setRange(1, 50)
        self.spin_size.setValue(4.0)
        self.spin_size.setSuffix(" mm")
        grp_lay.addRow("Size / 尺寸:", self.spin_size)
        layout.addWidget(grp)

        btn = QtGui.QPushButton("Create Weld / 创建焊缝")
        btn.clicked.connect(self._create)
        layout.addWidget(btn)
        layout.addStretch()

    def _create(self):
        size = self.spin_size.value()
        doc = App.ActiveDocument
        if not doc:
            return
        try:
            v0 = self.edge.Vertexes[0].Point
            v1 = self.edge.Vertexes[-1].Point
            e_dir = (v1 - v0).normalize()
            length = (v1 - v0).Length
            if length < 0.1:
                return

            # Find adjacent faces and their normals
            norms = []
            obj = doc.getObject(self.obj_name) if self.obj_name else None
            if obj and hasattr(obj, "Shape"):
                for f in obj.Shape.Faces:
                    for e in f.Edges:
                        if e.isSame(self.edge):
                            try:
                                n = f.normalAt(0.5, 0.5).normalize()
                                if abs(n.dot(e_dir)) < 0.1:
                                    norms.append(n)
                            except Exception:
                                pass
                            break

            if len(norms) >= 2:
                n1, n2 = norms[0], norms[1]
            else:
                # Fallback: guess perpendicular directions
                up = App.Vector(0, 0, 1)
                if abs(e_dir.z) > 0.99:
                    up = App.Vector(1, 0, 0)
                n1 = e_dir.cross(up).normalize()
                n2 = n1.cross(e_dir).normalize()

            # Build fillet cross-section: quarter-circle arc
            n1.normalize(); n2.normalize()
            segments = 8
            pts = [v0]
            for i in range(segments + 1):
                a = math.radians(90.0 * i / segments)
                pt = v0 + n1 * (size * math.cos(a)) + n2 * (size * math.sin(a))
                pts.append(pt)
            pts.append(v0)
            wire = Part.makePolygon(pts)
            face = Part.Face(wire)
            if face.isNull():
                return

            bead = face.extrude(e_dir * length)
            if bead.isNull() or not bead.isValid():
                return

            name = f"Weld_{size}mm"
            feat = doc.addObject("Part::Feature", name)
            feat.Shape = bead
            try:
                feat.ViewObject.ShapeColor = (0.90, 0.70, 0.10)
                feat.ViewObject.Transparency = 25
            except Exception:
                pass
            doc.recompute()
            Gui.Control.closeDialog()
        except Exception as e:
            App.Console.PrintError(f"Weld failed: {e}\n")


class WeldCommand:
    def GetResources(self):
        return {
            "Pixmap": os.path.join(ICONPATH, "line.svg"),
            "MenuText": "Weld / 焊缝",
            "ToolTip": "Fillet weld along edge. Select an edge between two faces.\n选择两个型材的交线创建角焊缝。",
        }

    def IsActive(self):
        return bool(App.ActiveDocument)

    def Activated(self):
        sel = Gui.Selection.getSelectionEx()
        edge = None
        obj_name = None
        for s in sel:
            for n in s.SubElementNames:
                if n.startswith("Edge"):
                    e = s.Object.getSubObject(n)
                    if e and hasattr(e, 'Vertexes') and len(e.Vertexes) >= 2:
                        edge = e
                        obj_name = s.Object.Name
                        break
            if edge:
                break
        if edge is None:
            QtGui.QMessageBox.warning(None, "No Edge", "Select an edge first.\n先选一条边线。")
            return
        Gui.Control.showDialog(WeldTaskPanel(edge, obj_name))


Gui.addCommand("frameforgemod_Weld", WeldCommand())

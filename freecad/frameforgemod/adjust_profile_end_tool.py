# -*- coding: utf-8 -*-

import os
import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtCore, QtGui
from freecad.frameforgemod.ff_tools import ICONPATH, translate


class _SelObserver:
    def __init__(self, panel):
        self.panel = panel

    def addSelection(self, doc, obj, sub, pnt):
        self.panel._on_selection(doc, obj, sub)


class AdjustEndTaskPanel:
    def __init__(self, obj):
        self.obj = obj
        self._selected = None
        self.form = QtGui.QWidget()
        layout = QtGui.QVBoxLayout(self.form)

        info = QtGui.QLabel("Click a FACE on another profile to auto-detect A/B,\nor click A/B box below and enter value:")
        info.setWordWrap(True)
        layout.addWidget(info)

        # A side indicator
        self.group_a = QtGui.QGroupBox("A side (start)")
        self.group_a.setCheckable(True)
        self.group_a.setChecked(False)
        self.group_a.clicked.connect(lambda: self._select("A"))
        a_layout = QtGui.QVBoxLayout(self.group_a)
        self.sb_a = QtGui.QDoubleSpinBox()
        self.sb_a.setRange(-10000, 10000)
        self.sb_a.setDecimals(1)
        self.sb_a.setSuffix(" mm")
        self.sb_a.setValue(float(getattr(obj, "OffsetA", 0)))
        self.sb_a.valueChanged.connect(lambda v: self._set_and_update("A", v))
        a_layout.addWidget(self.sb_a)
        self.label_a = QtGui.QLabel("Click face to detect or enter value")
        self.label_a.setStyleSheet("color: #888; font-size: 10px;")
        a_layout.addWidget(self.label_a)
        layout.addWidget(self.group_a)

        # B side indicator
        self.group_b = QtGui.QGroupBox("B side (end)")
        self.group_b.setCheckable(True)
        self.group_b.setChecked(False)
        self.group_b.clicked.connect(lambda: self._select("B"))
        b_layout = QtGui.QVBoxLayout(self.group_b)
        self.sb_b = QtGui.QDoubleSpinBox()
        self.sb_b.setRange(-10000, 10000)
        self.sb_b.setDecimals(1)
        self.sb_b.setSuffix(" mm")
        self.sb_b.setValue(float(getattr(obj, "OffsetB", 0)))
        self.sb_b.valueChanged.connect(lambda v: self._set_and_update("B", v))
        b_layout.addWidget(self.sb_b)
        self.label_b = QtGui.QLabel("Click face to detect or enter value")
        self.label_b.setStyleSheet("color: #888; font-size: 10px;")
        b_layout.addWidget(self.label_b)
        layout.addWidget(self.group_b)

        layout.addStretch()

        self.obs = _SelObserver(self)
        Gui.Selection.addObserver(self.obs)

    def _select(self, side):
        if side == "A":
            self._selected = "A"
            self.group_a.setStyleSheet("QGroupBox { color: #060; font-weight: bold; }")
            self.group_b.setStyleSheet("")
            self.group_b.setChecked(False)
        else:
            self._selected = "B"
            self.group_a.setStyleSheet("")
            self.group_b.setStyleSheet("QGroupBox { color: #060; font-weight: bold; }")
            self.group_a.setChecked(False)

    def _set_and_update(self, side, val):
        if side == "A":
            self.obj.OffsetA = val
        else:
            self.obj.OffsetB = val
        self.obj.recompute()

    def _on_selection(self, doc, obj_name, sub):
        """Calculate offset to extend this profile to the selected face."""
        try:
            sel_obj = App.ActiveDocument.getObject(obj_name)
            if sel_obj is None or sel_obj is self.obj:
                return
            if not sub or not sub.startswith("Face"):
                return
            face = sel_obj.getSubObject(sub)
            if not isinstance(face, Part.Face):
                return

            if not hasattr(self.obj, "Target") or not self.obj.Target:
                return
            edge_obj = self.obj.Target[0].getSubObject(self.obj.Target[1][0])
            if not edge_obj:
                return
            a_pt = edge_obj.Vertexes[1].Point
            b_pt = edge_obj.Vertexes[0].Point
            edge_dir = (b_pt - a_pt).normalize()
            edge_len = (b_pt - a_pt).Length

            face_center = face.CenterOfMass
            t = (face_center - a_pt).dot(edge_dir)

            # Reset both indicators
            self.group_a.setStyleSheet("")
            self.group_b.setStyleSheet("")

            if t < 0:
                offset_val = -t
                side = "A"
                self.group_a.setStyleSheet("QGroupBox { color: #060; font-weight: bold; }")
                self.label_a.setText(f"Detected: OffsetA = {offset_val:.1f} mm")
                self.label_a.setStyleSheet("color: #060;")
                self.label_b.setText("")
            elif t > edge_len:
                offset_val = t - edge_len
                side = "B"
                self.group_b.setStyleSheet("QGroupBox { color: #060; font-weight: bold; }")
                self.label_b.setText(f"Detected: OffsetB = {offset_val:.1f} mm")
                self.label_b.setStyleSheet("color: #060;")
                self.label_a.setText("")
            else:
                dist_a = t
                dist_b = edge_len - t
                if dist_a <= dist_b:
                    offset_val = -dist_a
                    side = "A"
                    self.group_a.setStyleSheet("QGroupBox { color: #060; font-weight: bold; }")
                    self.label_a.setText(f"Detected: OffsetA = {offset_val:.1f} mm")
                    self.label_a.setStyleSheet("color: #060;")
                    self.label_b.setText("")
                else:
                    offset_val = -dist_b
                    side = "B"
                    self.group_b.setStyleSheet("QGroupBox { color: #060; font-weight: bold; }")
                    self.label_b.setText(f"Detected: OffsetB = {offset_val:.1f} mm")
                    self.label_b.setStyleSheet("color: #060;")
                    self.label_a.setText("")

            if side == "A":
                self.sb_a.blockSignals(True)
                self.sb_a.setValue(offset_val)
                self.sb_a.blockSignals(False)
                self.obj.OffsetA = offset_val
            else:
                self.sb_b.blockSignals(True)
                self.sb_b.setValue(offset_val)
                self.sb_b.blockSignals(False)
                self.obj.OffsetB = offset_val
            self.obj.recompute()
            self.face_label.setStyleSheet("color: #060;")
        except Exception as e:
            self.label_a.setText(f"Error: {e}")
            self.label_a.setStyleSheet("color: #800;")

    def open(self):
        App.ActiveDocument.openTransaction("Adjust End Offsets")

    def reject(self):
        if self.obs:
            Gui.Selection.removeObserver(self.obs)
            self.obs = None
        App.ActiveDocument.abortTransaction()
        return True

    def accept(self):
        if self.obs:
            Gui.Selection.removeObserver(self.obs)
        self.obj.OffsetA = self.sb_a.value()
        self.obj.OffsetB = self.sb_b.value()
        App.ActiveDocument.commitTransaction()
        App.ActiveDocument.recompute()
        return True


class AdjustEndCommand:
    def GetResources(self):
        return {
            "Pixmap": os.path.join(ICONPATH, "end-extend.svg"),
            "MenuText": "Adjust Ends",
            "ToolTip": "Click a face on another profile to auto-extend to it, or set OffsetA/B manually",
        }

    def IsActive(self):
        if App.ActiveDocument:
            sel = Gui.Selection.getSelection()
            return len(sel) == 1 and hasattr(sel[0], "OffsetA")
        return False

    def Activated(self):
        obj = Gui.Selection.getSelection()[0]
        Gui.Control.showDialog(AdjustEndTaskPanel(obj))


Gui.addCommand("frameforgemod_AdjustEnds", AdjustEndCommand())

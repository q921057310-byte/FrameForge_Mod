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
    def __init__(self, objs):
        self.objs = objs
        self.target_faces = []
        self._sbs = {}
        self._manual = set()  # (obj.Name, side) tracked as manually edited

        self.form = QtGui.QWidget()
        layout = QtGui.QVBoxLayout(self.form)

        info = QtGui.QLabel(translate(
            "AdjustEnds",
            "Click target faces to extend/shorten selected profiles.\n"
            "Each profile uses the nearest target face.\n"
            "Re-click a face to remove it from targets.\n"
            "Values entered manually are NOT overwritten by detection."))
        info.setWordWrap(True)
        layout.addWidget(info)

        self.target_label = QtGui.QLabel(translate("AdjustEnds", "未选择目标面。"))
        self.target_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(self.target_label)

        # A group
        self.group_a = QtGui.QGroupBox(translate("AdjustEnds", "A 端（起点）"))
        self.group_a.setCheckable(True)
        self.group_a.setChecked(True)
        self.a_layout = QtGui.QVBoxLayout(self.group_a)
        self.a_layout.setContentsMargins(4, 4, 4, 4)
        self.a_placeholder = QtGui.QLabel(translate("AdjustEnds", "None"))
        self.a_placeholder.setStyleSheet("color: #888; font-size: 10px;")
        self.a_layout.addWidget(self.a_placeholder)
        layout.addWidget(self.group_a)

        # B group
        self.group_b = QtGui.QGroupBox(translate("AdjustEnds", "B 端（终点）"))
        self.group_b.setCheckable(True)
        self.group_b.setChecked(True)
        self.b_layout = QtGui.QVBoxLayout(self.group_b)
        self.b_layout.setContentsMargins(4, 4, 4, 4)
        self.b_placeholder = QtGui.QLabel(translate("AdjustEnds", "None"))
        self.b_placeholder.setStyleSheet("color: #888; font-size: 10px;")
        self.b_layout.addWidget(self.b_placeholder)
        layout.addWidget(self.group_b)

        # Reverse checkbox
        self.reverse_cb = QtGui.QCheckBox(translate("AdjustEnds", "交换 A ↔ B（反向）"))
        self.reverse_cb.toggled.connect(self._on_reverse_toggled)
        layout.addWidget(self.reverse_cb)

        layout.addStretch()

        self._build_initial_rows()
        self.obs = _SelObserver(self)
        Gui.Selection.addObserver(self.obs)

    def _build_initial_rows(self):
        self._clear_groups()
        for obj in self.objs:
            val_a = float(getattr(obj, "OffsetA", 0))
            val_b = float(getattr(obj, "OffsetB", 0))
            self._add_row(self.a_layout, obj, "A", val_a)
            self._add_row(self.b_layout, obj, "B", val_b)
        self.a_placeholder.setVisible(len(self.objs) == 0)
        self.b_placeholder.setVisible(len(self.objs) == 0)

    def _add_row(self, layout_, obj, side, value):
        row = QtGui.QWidget()
        h = QtGui.QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)

        name = QtGui.QLabel(obj.Label)
        name.setMinimumWidth(80)
        name.setStyleSheet("font-weight: bold;")
        h.addWidget(name)

        sb = QtGui.QDoubleSpinBox()
        sb.setRange(-10000, 10000)
        sb.setDecimals(1)
        sb.setSuffix(" mm")
        sb.setValue(value)
        h.addWidget(sb, 1)

        layout_.addWidget(row)

        def handler(v, o=obj, s=side):
            self._manual.add((o.Name, s))
            setattr(o, "OffsetA" if s == "A" else "OffsetB", v)
            o.recompute()

        sb.valueChanged.connect(handler)
        self._sbs.setdefault(obj.Name, {})[side] = sb

    def _clear_groups(self):
        for layout_ in [self.a_layout, self.b_layout]:
            while layout_.count():
                item = layout_.takeAt(0)
                w = item.widget()
                if w and w is not self.a_placeholder and w is not self.b_placeholder:
                    w.setParent(None)
        self._sbs.clear()
        self._manual.clear()

    def _on_reverse_toggled(self, checked):
        if not checked:
            return
        for obj in self.objs:
            if hasattr(obj, "OffsetA") and hasattr(obj, "OffsetB"):
                a = float(obj.OffsetA)
                b = float(obj.OffsetB)
                obj.OffsetA = b
                obj.OffsetB = a
                obj.recompute()
        App.ActiveDocument.recompute()
        # Rebuild rows with new values
        self._build_initial_rows()
        # Reset checkbox (fire-and-forget action)
        self.reverse_cb.setChecked(False)

    def _get_edge_data(self, obj):
        if not hasattr(obj, "Target") or not obj.Target:
            return None
        edge = obj.Target[0].getSubObject(obj.Target[1][0])
        if not edge:
            return None

        pl = obj.Placement
        z_dir = pl.Rotation.multVec(App.Vector(0, 0, 1))
        base = pl.Base

        # Determine which vertex is the A end (lower local-Z)
        v0 = edge.Vertexes[0].Point
        v1 = edge.Vertexes[1].Point
        v0_local_z = (v0 - base).dot(z_dir)
        v1_local_z = (v1 - base).dot(z_dir)

        if v0_local_z <= v1_local_z:
            a_pt, b_pt = v0, v1
        else:
            a_pt, b_pt = v1, v0

        edge_dir = (b_pt - a_pt).normalize()
        edge_len = (b_pt - a_pt).Length
        return (a_pt, b_pt, edge_dir, edge_len)

    def _nearest_face_to_point(self, pt):
        nearest = None
        nearest_dist = float("inf")
        for tup in self.target_faces:
            d = (tup[2].CenterOfMass - pt).Length
            if d < nearest_dist:
                nearest_dist = d
                nearest = tup
        return nearest

    def _calc_offset(self, t, edge_len):
        if t <= 0:
            return "A", -t
        elif t >= edge_len:
            return "B", t - edge_len
        else:
            d_a, d_b = t, edge_len - t
            if d_a <= d_b:
                return "A", -d_a
            else:
                return "B", -d_b

    def _rebuild_from_faces(self):
        detected_a = False
        detected_b = False

        for obj in self.objs:
            ed = self._get_edge_data(obj)
            if ed is None:
                continue
            a_pt, b_pt, edge_dir, edge_len = ed
            sbs = self._sbs.get(obj.Name, {})

            face_for_a = self._nearest_face_to_point(a_pt)
            if face_for_a and (obj.Name, "A") not in self._manual:
                t = (face_for_a[2].CenterOfMass - a_pt).dot(edge_dir)
                side, val = self._calc_offset(t, edge_len)
                self._set_spinbox(obj, sbs, side, val)
                if side == "A":
                    detected_a = True
                else:
                    detected_b = True

            face_for_b = self._nearest_face_to_point(b_pt)
            if face_for_b and (obj.Name, "B") not in self._manual:
                t = (face_for_b[2].CenterOfMass - a_pt).dot(edge_dir)
                side, val = self._calc_offset(t, edge_len)
                self._set_spinbox(obj, sbs, side, val)
                if side == "A":
                    detected_a = True
                else:
                    detected_b = True

        # Update group titles with detection indicator
        if detected_a:
            self.group_a.setTitle(translate("AdjustEnds", "A 端（起点）") + " ← detected")
            self.group_a.setStyleSheet("QGroupBox { color: #c00; font-weight: bold; }")
        else:
            self.group_a.setTitle(translate("AdjustEnds", "A 端（起点）"))
            self.group_a.setStyleSheet("")
        if detected_b:
            self.group_b.setTitle(translate("AdjustEnds", "B 端（终点）") + " ← detected")
            self.group_b.setStyleSheet("QGroupBox { color: #c00; font-weight: bold; }")
        else:
            self.group_b.setTitle(translate("AdjustEnds", "B 端（终点）"))
            self.group_b.setStyleSheet("")

        self._update_target_label()

    def _set_spinbox(self, obj, sbs, side, val):
        if side in sbs:
            sb = sbs[side]
            sb.blockSignals(True)
            sb.setValue(val)
            sb.blockSignals(False)
            setattr(obj, "OffsetA" if side == "A" else "OffsetB", val)
            obj.recompute()

    def _update_target_label(self):
        if not self.target_faces:
            self.target_label.setText(translate("AdjustEnds", "未选择目标面。"))
            self.target_label.setStyleSheet("color: #888; font-size: 10px;")
            return
        lines = [f"{t[0]}.{t[1]}" for t in self.target_faces]
        self.target_label.setText(f"{len(lines)} target(s): " + ", ".join(lines))
        self.target_label.setStyleSheet("color: #060; font-size: 10px; font-weight: bold;")

    def _on_selection(self, doc, obj_name, sub):
        try:
            if not sub or not sub.startswith("Face"):
                return
            sel_obj = App.ActiveDocument.getObject(obj_name)
            if sel_obj is None:
                return
            face = sel_obj.getSubObject(sub)
            if not isinstance(face, Part.Face):
                return

            # Toggle off if already in targets
            for i, tup in enumerate(self.target_faces):
                if tup[0] == obj_name and tup[1] == sub:
                    self.target_faces.pop(i)
                    # Also clear manual flags for this obj so detection can re-run
                    keys_to_clear = [(k, s) for k, s in list(self._manual) if k == obj_name]
                    for k in keys_to_clear:
                        self._manual.discard(k)
                    self._rebuild_from_faces()
                    return

            self.target_faces.append((obj_name, sub, face))
            self._rebuild_from_faces()
        except Exception as e:
            self.target_label.setText(f"Error: {e}")
            self.target_label.setStyleSheet("color: #800; font-size: 10px;")

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
            self.obs = None
        App.ActiveDocument.commitTransaction()
        App.ActiveDocument.recompute()
        return True


class AdjustEndCommand:
    def GetResources(self):
        return {
            "Pixmap": os.path.join(ICONPATH, "end-extend.svg"),
            "MenuText": translate("AdjustEnds", "调整端头"),
            "ToolTip": translate("AdjustEnds",
                "Click target faces to extend/shorten selected profiles."),
        }

    def IsActive(self):
        if App.ActiveDocument:
            sel = Gui.Selection.getSelection()
            return len(sel) >= 1 and all(hasattr(o, "OffsetA") for o in sel)
        return False

    def Activated(self):
        objs = Gui.Selection.getSelection()
        Gui.Control.showDialog(AdjustEndTaskPanel(objs))


Gui.addCommand("frameforgemod_AdjustEnds", AdjustEndCommand())

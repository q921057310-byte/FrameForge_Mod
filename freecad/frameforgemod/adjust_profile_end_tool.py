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
        self.target_faces = []  # list of (obj_name, sub_name, face)
        self._sbs = {}  # obj.Name -> {side: sb}

        self.form = QtGui.QWidget()
        layout = QtGui.QVBoxLayout(self.form)

        info = QtGui.QLabel(translate(
            "AdjustEnds",
            "Click target faces to extend/shorten selected profiles.\n"
            "Each profile uses the nearest target face.\n"
            "Re-click a face to remove it from targets."))
        info.setWordWrap(True)
        layout.addWidget(info)

        # Target faces display
        self.target_label = QtGui.QLabel(translate("AdjustEnds", "No target faces selected."))
        self.target_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(self.target_label)

        # A group
        self.group_a = QtGui.QGroupBox(translate("AdjustEnds", "A end (start)"))
        self.group_a.setCheckable(True)
        self.group_a.setChecked(True)
        self.a_layout = QtGui.QVBoxLayout(self.group_a)
        self.a_layout.setContentsMargins(4, 4, 4, 4)
        self.a_placeholder = QtGui.QLabel(translate("AdjustEnds", "None"))
        self.a_placeholder.setStyleSheet("color: #888; font-size: 10px;")
        self.a_layout.addWidget(self.a_placeholder)
        layout.addWidget(self.group_a)

        # B group
        self.group_b = QtGui.QGroupBox(translate("AdjustEnds", "B end (end)"))
        self.group_b.setCheckable(True)
        self.group_b.setChecked(True)
        self.b_layout = QtGui.QVBoxLayout(self.group_b)
        self.b_layout.setContentsMargins(4, 4, 4, 4)
        self.b_placeholder = QtGui.QLabel(translate("AdjustEnds", "None"))
        self.b_placeholder.setStyleSheet("color: #888; font-size: 10px;")
        self.b_layout.addWidget(self.b_placeholder)
        layout.addWidget(self.group_b)

        layout.addStretch()

        self._build_initial_rows()
        self.obs = _SelObserver(self)
        Gui.Selection.addObserver(self.obs)

    def _build_initial_rows(self):
        """Show one row per profile with A/B spinboxes pre-filled from properties."""
        self._clear_groups()

        has_a = False
        has_b = False

        for obj in self.objs:
            val_a = float(getattr(obj, "OffsetA", 0))
            val_b = float(getattr(obj, "OffsetB", 0))

            # A side row
            if True:  # always show, user can adjust
                self._add_row(self.a_layout, obj, "A", val_a, "")
                has_a = True

            # B side row
            if True:
                self._add_row(self.b_layout, obj, "B", val_b, "")
                has_b = True

        self.a_placeholder.setVisible(not has_a)
        self.b_placeholder.setVisible(not has_b)

    def _add_row(self, layout_, obj, side, value, ref_label):
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

        if ref_label:
            ref = QtGui.QLabel(ref_label)
            ref.setStyleSheet("color: #666; font-size: 9px;")
            h.addWidget(ref)

        layout_.addWidget(row)

        def handler(v, o=obj, s=side):
            setattr(o, "OffsetA" if s == "A" else "OffsetB", v)
            o.recompute()

        sb.valueChanged.connect(handler)
        self._sbs.setdefault(obj.Name, {})[side] = sb

    def _clear_groups(self):
        for layout_, in [
            (self.a_layout,),
            (self.b_layout,),
        ]:
            while layout_.count():
                item = layout_.takeAt(0)
                if item.widget() and item.widget() is not self.a_placeholder and item.widget() is not self.b_placeholder:
                    item.widget().setParent(None)
        self._sbs.clear()

    def _find_nearest_face(self, obj):
        """Return (face, face_label) nearest to profile's midpoint, or (None, '')"""
        if not hasattr(obj, "Target") or not obj.Target:
            return None, "no path"
        edge = obj.Target[0].getSubObject(obj.Target[1][0])
        if not edge:
            return None, "no edge"

        mid_pt = (edge.Vertexes[0].Point + edge.Vertexes[1].Point) * 0.5
        nearest = None
        nearest_dist = float("inf")
        for tup in self.target_faces:
            d = (tup[2].CenterOfMass - mid_pt).Length
            if d < nearest_dist:
                nearest_dist = d
                nearest = tup
        return nearest, ""

    def _rebuild_from_faces(self):
        """Auto-fill spinbox values from target faces."""
        # Build lookup: obj.Name -> (face, label)
        assignments = {}
        unmatched = []
        for obj in self.objs:
            best, note = self._find_nearest_face(obj)
            if best is None:
                unmatched.append((obj.Label, note))
            else:
                assignments[obj.Name] = (obj, best)

        # Update spinbox values
        for obj in self.objs:
            if obj.Name not in self._sbs:
                continue
            if obj.Name not in assignments:
                # No match - set to 0
                for side_sb in self._sbs[obj.Name].values():
                    side_sb.blockSignals(True)
                    side_sb.setValue(0)
                    side_sb.blockSignals(False)
                continue

            obj_, (tup) = assignments[obj.Name]
            if len(tup) != 3:
                continue
            face = tup[2]
            label = f"{tup[0]}.{tup[1]}"

            edge = obj.Target[0].getSubObject(obj.Target[1][0])
            a_pt = edge.Vertexes[1].Point
            b_pt = edge.Vertexes[0].Point
            edge_dir = (b_pt - a_pt).normalize()
            edge_len = (b_pt - a_pt).Length
            t = (face.CenterOfMass - a_pt).dot(edge_dir)

            if t <= 0:
                side, val = "A", -t
            elif t >= edge_len:
                side, val = "B", t - edge_len
            else:
                d_a, d_b = t, edge_len - t
                if d_a <= d_b:
                    side, val = "A", -d_a
                else:
                    side, val = "B", -d_b

            # Set the calculated side's spinbox
            sbs = self._sbs[obj.Name]
            for s, sb in sbs.items():
                sb.blockSignals(True)
                sb.setValue(val if s == side else 0)
                sb.blockSignals(False)
                obj.OffsetA = val if s == "A" else 0
                obj.OffsetB = val if s == "B" else 0
                obj.recompute()

			self._update_target_label()

    def _update_target_label(self):
        if not self.target_faces:
            self.target_label.setText(translate("AdjustEnds", "No target faces selected."))
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

            # Toggle: clicking same face again removes it
            for i, tup in enumerate(self.target_faces):
                if tup[0] == obj_name and tup[1] == sub:
                    self.target_faces.pop(i)
                    self._rebuild_from_faces()
                    return

            # New target face
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
        # All changes already applied via spinbox handlers in real time
        App.ActiveDocument.commitTransaction()
        App.ActiveDocument.recompute()
        return True


class AdjustEndCommand:
    def GetResources(self):
        return {
            "Pixmap": os.path.join(ICONPATH, "end-extend.svg"),
            "MenuText": translate("AdjustEnds", "Adjust Ends"),
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

import os

import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtCore, QtGui
try:
    from PySide import QtWidgets
except ImportError:
    QtWidgets = QtGui

from freecad.frameforgemod.ff_tools import ICONPATH, UIPATH, translate
from freecad.frameforgemod.gusset import Gusset, ViewProviderGusset


class CreateGussetTaskPanel:
    def __init__(self, obj):
        self.obj = obj
        self.dump = obj.dumpContent()

        self.form = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self.form)

        # Top-right Apply button
        _top_row = QtWidgets.QHBoxLayout()
        _top_row.addStretch()
        _apply_btn = QtWidgets.QPushButton(translate("frameforgemod", "Apply"))
        _apply_btn.setFixedWidth(60)
        _apply_btn.setFixedHeight(22)
        _apply_btn.clicked.connect(self.apply)
        _top_row.addWidget(_apply_btn)
        layout.addLayout(_top_row)

        # Selection group
        sel_group = QtWidgets.QGroupBox(translate("frameforgemod", "Selection"))
        sel_layout = QtWidgets.QVBoxLayout(sel_group)

        btn1_layout = QtWidgets.QHBoxLayout()
        self.select1_btn = QtWidgets.QPushButton(translate("frameforgemod", "Select Face 1"))
        self.select1_btn.setIcon(QtGui.QIcon(os.path.join(ICONPATH, "list-add.svg")))
        self.select1_btn.clicked.connect(lambda: self.select_face(1))
        btn1_layout.addWidget(self.select1_btn)
        self.face1_label = QtWidgets.QLabel(translate("frameforgemod", "Not selected"))
        btn1_layout.addWidget(self.face1_label)
        sel_layout.addLayout(btn1_layout)

        btn2_layout = QtWidgets.QHBoxLayout()
        self.select2_btn = QtWidgets.QPushButton(translate("frameforgemod", "Select Face 2"))
        self.select2_btn.setIcon(QtGui.QIcon(os.path.join(ICONPATH, "list-add.svg")))
        self.select2_btn.clicked.connect(lambda: self.select_face(2))
        btn2_layout.addWidget(self.select2_btn)
        self.face2_label = QtWidgets.QLabel(translate("frameforgemod", "Not selected"))
        btn2_layout.addWidget(self.face2_label)
        sel_layout.addLayout(btn2_layout)

        layout.addWidget(sel_group)

        # Geometry group
        geo_group = QtWidgets.QGroupBox(translate("frameforgemod", "Geometry"))
        geo_layout = QtWidgets.QFormLayout(geo_group)

        self.spin_leg1 = QtWidgets.QDoubleSpinBox()
        self.spin_leg1.setRange(1.0, 10000.0)
        self.spin_leg1.setDecimals(1)
        self.spin_leg1.setValue(float(obj.LegLength1))
        self.spin_leg1.setSuffix(" mm")
        self.spin_leg1.valueChanged.connect(self.on_leg1_changed)
        geo_layout.addRow(translate("frameforgemod", "Leg length 1"), self.spin_leg1)

        self.spin_leg2 = QtWidgets.QDoubleSpinBox()
        self.spin_leg2.setRange(1.0, 10000.0)
        self.spin_leg2.setDecimals(1)
        self.spin_leg2.setValue(float(obj.LegLength2))
        self.spin_leg2.setSuffix(" mm")
        self.spin_leg2.valueChanged.connect(self.on_leg2_changed)
        geo_layout.addRow(translate("frameforgemod", "Leg length 2"), self.spin_leg2)

        self.spin_offset = QtWidgets.QDoubleSpinBox()
        self.spin_offset.setRange(0.0, 10000.0)
        self.spin_offset.setDecimals(1)
        self.spin_offset.setValue(float(obj.Offset))
        self.spin_offset.setSuffix(" mm")
        self.spin_offset.valueChanged.connect(self.on_offset_changed)
        geo_layout.addRow(translate("frameforgemod", "Offset from corner"), self.spin_offset)

        self.spin_thick = QtWidgets.QDoubleSpinBox()
        self.spin_thick.setRange(0.1, 1000.0)
        self.spin_thick.setDecimals(1)
        self.spin_thick.setValue(float(obj.Thickness))
        self.spin_thick.setSuffix(" mm")
        self.spin_thick.valueChanged.connect(self.on_thickness_changed)
        geo_layout.addRow(translate("frameforgemod", "Thickness"), self.spin_thick)

        layout.addWidget(geo_group)

        # Options group
        opt_group = QtWidgets.QGroupBox(translate("frameforgemod", "Options"))
        opt_layout = QtWidgets.QFormLayout(opt_group)

        self.combo_thick_align = QtWidgets.QComboBox()
        self.combo_thick_align.addItems(["正向", "居中", "反向"])
        self.combo_thick_align.setCurrentIndex(obj.ThicknessAlign)
        self.combo_thick_align.currentIndexChanged.connect(self.on_thick_align_changed)
        opt_layout.addRow(translate("frameforgemod", "Thickness"), self.combo_thick_align)

        self.combo_pos_align = QtWidgets.QComboBox()
        self.combo_pos_align.addItems(["左端", "居中", "右端"])
        self.combo_pos_align.setCurrentIndex(obj.PositionAlign)
        self.combo_pos_align.currentIndexChanged.connect(self.on_pos_align_changed)
        opt_layout.addRow(translate("frameforgemod", "Position"), self.combo_pos_align)

        self.spin_pos_offset = QtWidgets.QDoubleSpinBox()
        self.spin_pos_offset.setRange(-10000.0, 10000.0)
        self.spin_pos_offset.setDecimals(1)
        self.spin_pos_offset.setValue(float(obj.PositionOffset))
        self.spin_pos_offset.setSuffix(" mm")
        self.spin_pos_offset.valueChanged.connect(self.on_pos_offset_changed)
        opt_layout.addRow(translate("frameforgemod", "Position offset"), self.spin_pos_offset)

        # Hole options below the form layout
        self.cb_hole = QtWidgets.QCheckBox(translate("frameforgemod", "Center hole"))
        self.cb_hole.setChecked(obj.HoleEnabled)
        self.cb_hole.toggled.connect(self.on_hole_toggled)
        opt_layout.addRow(self.cb_hole)

        self.spin_hole_dia = QtWidgets.QDoubleSpinBox()
        self.spin_hole_dia.setRange(1.0, 1000.0)
        self.spin_hole_dia.setDecimals(1)
        self.spin_hole_dia.setValue(float(obj.HoleDiameter))
        self.spin_hole_dia.setSuffix(" mm")
        self.spin_hole_dia.setEnabled(obj.HoleEnabled)
        self.spin_hole_dia.valueChanged.connect(self.on_hole_dia_changed)
        opt_layout.addRow(translate("frameforgemod", "Hole diameter"), self.spin_hole_dia)

        # Chamfer options
        self.cb_chamfer_ra = QtWidgets.QCheckBox(translate("frameforgemod", "Right angle edges"))
        self.cb_chamfer_ra.setChecked(obj.ChamferRightAngle)
        self.cb_chamfer_ra.toggled.connect(self.on_chamfer_ra_toggled)
        opt_layout.addRow(self.cb_chamfer_ra)

        self.spin_chamfer_ra = QtWidgets.QDoubleSpinBox()
        self.spin_chamfer_ra.setRange(0.1, 100.0)
        self.spin_chamfer_ra.setDecimals(1)
        self.spin_chamfer_ra.setValue(float(obj.ChamferRightAngleSize))
        self.spin_chamfer_ra.setSuffix(" mm")
        self.spin_chamfer_ra.setEnabled(obj.ChamferRightAngle)
        self.spin_chamfer_ra.valueChanged.connect(self.on_chamfer_ra_size_changed)
        opt_layout.addRow(translate("frameforgemod", "RA chamfer size"), self.spin_chamfer_ra)

        self.cb_chamfer_ac = QtWidgets.QCheckBox(translate("frameforgemod", "Acute edge"))
        self.cb_chamfer_ac.setChecked(obj.ChamferAcute)
        self.cb_chamfer_ac.toggled.connect(self.on_chamfer_ac_toggled)
        opt_layout.addRow(self.cb_chamfer_ac)

        self.spin_chamfer_ac = QtWidgets.QDoubleSpinBox()
        self.spin_chamfer_ac.setRange(0.1, 100.0)
        self.spin_chamfer_ac.setDecimals(1)
        self.spin_chamfer_ac.setValue(float(obj.ChamferAcuteSize))
        self.spin_chamfer_ac.setSuffix(" mm")
        self.spin_chamfer_ac.setEnabled(obj.ChamferAcute)
        self.spin_chamfer_ac.valueChanged.connect(self.on_chamfer_ac_size_changed)
        opt_layout.addRow(translate("frameforgemod", "AC chamfer size"), self.spin_chamfer_ac)

        layout.addWidget(opt_group)

        layout.addStretch()

        self.update_ui()

    def select_face(self, num):
        """Read the current selection and use the first face found."""
        sel = Gui.Selection.getSelectionEx()
        if len(sel) == 0:
            App.Console.PrintMessage(translate("frameforgemod", "Select a face in the 3D view first, then click this button\n"))
            return
        if len(sel) > 1:
            App.Console.PrintMessage(translate("frameforgemod", "Select only one face\n"))
            return
        if len(sel[0].SubElementNames) != 1:
            App.Console.PrintMessage(translate("frameforgemod", "Click a single face (not the whole object)\n"))
            return
        obj = sel[0].Object
        sub = sel[0].SubElementNames[0]
        face = obj.getSubObject(sub)
        if not isinstance(face, Part.Face):
            App.Console.PrintMessage(translate("frameforgemod", "That is not a face\n"))
            return

        if num == 1:
            self.obj.Face1 = [(obj, (sub,))]
            self.face1_label.setText(f"{obj.Label} ({sub})")
        else:
            # Check different from Face1
            try:
                if self.obj.Face1 and len(self.obj.Face1) > 0:
                    existing_obj, existing_subs = self.obj.Face1[0]
                    if existing_obj is obj and existing_subs == (sub,):
                        App.Console.PrintMessage(translate("frameforgemod", "Select a different face\n"))
                        return
            except Exception:
                pass
            self.obj.Face2 = [(obj, (sub,))]
            self.face2_label.setText(f"{obj.Label} ({sub})")

        self.obj.recompute()

    def on_leg1_changed(self, val):
        self.obj.LegLength1 = val
        self.obj.recompute()

    def on_leg2_changed(self, val):
        self.obj.LegLength2 = val
        self.obj.recompute()

    def on_offset_changed(self, val):
        self.obj.Offset = val
        self.obj.recompute()

    def on_thickness_changed(self, val):
        self.obj.Thickness = val
        self.obj.recompute()

    def on_thick_align_changed(self, idx):
        self.obj.ThicknessAlign = idx
        self.obj.recompute()

    def on_pos_align_changed(self, idx):
        self.obj.PositionAlign = idx
        self.obj.recompute()

    def on_pos_offset_changed(self, val):
        self.obj.PositionOffset = val
        self.obj.recompute()

    def on_hole_toggled(self, checked):
        self.obj.HoleEnabled = checked
        self.spin_hole_dia.setEnabled(checked)
        self.obj.recompute()

    def on_hole_dia_changed(self, val):
        self.obj.HoleDiameter = val
        self.obj.recompute()

    def on_chamfer_ra_toggled(self, checked):
        self.obj.ChamferRightAngle = checked
        self.spin_chamfer_ra.setEnabled(checked)
        self.obj.recompute()

    def on_chamfer_ra_size_changed(self, val):
        self.obj.ChamferRightAngleSize = val
        self.obj.recompute()

    def on_chamfer_ac_toggled(self, checked):
        self.obj.ChamferAcute = checked
        self.spin_chamfer_ac.setEnabled(checked)
        self.obj.recompute()

    def on_chamfer_ac_size_changed(self, val):
        self.obj.ChamferAcuteSize = val
        self.obj.recompute()

    def update_ui(self):
        try:
            if self.obj.Face1 and len(self.obj.Face1) > 0:
                o, subs = self.obj.Face1[0]
                self.face1_label.setText(f"{o.Label} ({subs[0]})")
        except Exception:
            pass
        try:
            if self.obj.Face2 and len(self.obj.Face2) > 0:
                o, subs = self.obj.Face2[0]
                self.face2_label.setText(f"{o.Label} ({subs[0]})")
        except Exception:
            pass

    def open(self):
        App.Console.PrintMessage(translate("frameforgemod", "Opening Create Gusset\n"))
        App.ActiveDocument.openTransaction("Create Gusset")

    def reject(self):
        App.Console.PrintMessage(translate("frameforgemod", "Rejecting Create Gusset\n"))
        App.ActiveDocument.abortTransaction()
        try:
            App.ActiveDocument.removeObject(self.obj.Name)
        except Exception:
            pass
        Gui.ActiveDocument.resetEdit()
        return True

    def apply(self):
        App.Console.PrintMessage(translate("frameforgemod", "Applying...\n"))
        self.obj.Face1 = None
        self.obj.Face2 = None
        self.face1_label.setText(translate("frameforgemod", "Not selected"))
        self.face2_label.setText(translate("frameforgemod", "Not selected"))
        App.ActiveDocument.commitTransaction()
        try:
            self.obj.recompute()
        except Exception:
            pass
        App.ActiveDocument.recompute()
        try:
            Gui.updateGui()
        except Exception:
            pass
        if hasattr(self, 'dump') and hasattr(self.obj, 'dumpContent'):
            self.dump = self.obj.dumpContent()
        App.ActiveDocument.openTransaction("Continue editing")
        App.Console.PrintMessage(translate("frameforgemod", "Ready.\n"))

    def accept(self):
        App.Console.PrintMessage(translate("frameforgemod", "Accepting Create Gusset\n"))
        App.ActiveDocument.commitTransaction()
        App.ActiveDocument.recompute()
        Gui.ActiveDocument.resetEdit()
        return True


class GussetCommand:
    def GetResources(self):
        return {
            "Pixmap": os.path.join(ICONPATH, "gusset.svg"),
            "MenuText": translate("frameforgemod", "Gusset"),
            "Accel": "M, G",
            "ToolTip": translate(
                "frameforgemod",
                "<html><head/><body><p><b>Gusset plate</b> \
                    <br><br> \
                    Select two adjacent faces of profiles to add a gusset plate. \
                    </p></body></html>",
            ),
        }

    def IsActive(self):
        if App.ActiveDocument:
            if len(Gui.Selection.getSelection()) > 0:
                for sel in Gui.Selection.getSelectionEx():
                    if len(sel.SubElementNames) != 1:
                        return False
                    o = sel.Object
                    if not isinstance(o.getSubObject(sel.SubElementNames[0]), Part.Face):
                        return False
                return True
            else:
                return True
        return False

    def Activated(self):
        sel = Gui.Selection.getSelectionEx()
        App.ActiveDocument.openTransaction("Make Gusset")

        doc = App.ActiveDocument
        obj = doc.addObject("Part::FeaturePython", "Gusset")
        Gusset(obj)
        ViewProviderGusset(obj.ViewObject)

        if len(sel) >= 1 and len(sel[0].SubElementNames) > 0:
            obj.Face1 = [(sel[0].Object, (sel[0].SubElementNames[0],))]
            if len(sel[0].Object.Parents) > 0:
                sel[0].Object.Parents[-1][0].addObject(obj)
        if len(sel) >= 2 and len(sel[1].SubElementNames) > 0:
            obj.Face2 = [(sel[1].Object, (sel[1].SubElementNames[0],))]

        App.ActiveDocument.commitTransaction()

        panel = CreateGussetTaskPanel(obj)
        Gui.Control.showDialog(panel)


Gui.addCommand("frameforgemod_Gusset", GussetCommand())

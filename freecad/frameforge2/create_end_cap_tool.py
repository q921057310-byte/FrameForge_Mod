import os

import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtCore, QtGui
try:
    from PySide import QtWidgets
except ImportError:
    QtWidgets = QtGui

from freecad.frameforge2.end_cap import EndCap, ViewProviderEndCap
from freecad.frameforge2.ff_tools import ICONPATH, UIPATH, translate


class CreateEndCapTaskPanel:
    def __init__(self, obj):
        self.obj = obj
        self.dump = obj.dumpContent()

        self.form = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self.form)

        # Top-right Apply button
        _top_row = QtWidgets.QHBoxLayout()
        _top_row.addStretch()
        _apply_btn = QtWidgets.QPushButton(translate("FrameForge2", "Apply"))
        _apply_btn.setFixedWidth(60)
        _apply_btn.setFixedHeight(22)
        _apply_btn.clicked.connect(self.apply)
        _top_row.addWidget(_apply_btn)
        layout.addLayout(_top_row)

        # Selection group
        sel_group = QtWidgets.QGroupBox(translate("FrameForge2", "Selection"))
        sel_layout = QtWidgets.QVBoxLayout(sel_group)

        btn_layout = QtWidgets.QHBoxLayout()
        self.select_btn = QtWidgets.QPushButton(translate("FrameForge2", "Select Face"))
        self.select_btn.setIcon(QtGui.QIcon(os.path.join(ICONPATH, "list-add.svg")))
        self.select_btn.clicked.connect(self.select_face)
        btn_layout.addWidget(self.select_btn)

        self.face_label = QtWidgets.QLabel(translate("FrameForge2", "No face selected"))
        btn_layout.addWidget(self.face_label)
        sel_layout.addLayout(btn_layout)
        layout.addWidget(sel_group)

        # Parameters group
        param_group = QtWidgets.QGroupBox(translate("FrameForge2", "Parameters"))
        param_layout = QtWidgets.QFormLayout(param_group)

        self.spin_thickness = QtWidgets.QDoubleSpinBox()
        self.spin_thickness.setRange(0.1, 1000.0)
        self.spin_thickness.setDecimals(1)
        self.spin_thickness.setValue(float(obj.Thickness))
        self.spin_thickness.setSuffix(" mm")
        self.spin_thickness.valueChanged.connect(self.on_thickness_changed)
        param_layout.addRow(translate("FrameForge2", "Thickness"), self.spin_thickness)

        self.spin_offset = QtWidgets.QDoubleSpinBox()
        self.spin_offset.setRange(-1000.0, 1000.0)
        self.spin_offset.setDecimals(1)
        self.spin_offset.setValue(float(obj.Offset))
        self.spin_offset.setSuffix(" mm")
        self.spin_offset.valueChanged.connect(self.on_offset_changed)
        param_layout.addRow(translate("FrameForge2", "Offset"), self.spin_offset)

        self.combo_cap_type = QtWidgets.QComboBox()
        self.combo_cap_type.addItems(["Plate", "Plug"])
        self.combo_cap_type.setCurrentIndex(obj.CapType)
        self.combo_cap_type.currentIndexChanged.connect(self.on_cap_type_changed)
        param_layout.addRow(translate("FrameForge2", "Type"), self.combo_cap_type)

        self.spin_plug_offset = QtWidgets.QDoubleSpinBox()
        self.spin_plug_offset.setRange(0.0, 100.0)
        self.spin_plug_offset.setDecimals(1)
        self.spin_plug_offset.setValue(float(obj.PlugOffset))
        self.spin_plug_offset.setSuffix(" mm")
        self.spin_plug_offset.setEnabled(obj.CapType == 1)
        self.spin_plug_offset.valueChanged.connect(self.on_plug_offset_changed)
        param_layout.addRow(translate("FrameForge2", "Plug offset"), self.spin_plug_offset)

        self.cb_reverse = QtWidgets.QCheckBox(translate("FrameForge2", "Reverse direction"))
        self.cb_reverse.setChecked(obj.Reverse)
        self.cb_reverse.toggled.connect(self.on_reverse_toggled)
        param_layout.addRow(self.cb_reverse)

        layout.addWidget(param_group)

        # Edge treatment group
        edge_group = QtWidgets.QGroupBox(translate("FrameForge2", "Edge Treatment"))
        edge_layout = QtWidgets.QFormLayout(edge_group)

        self.cb_chamfer = QtWidgets.QCheckBox(translate("FrameForge2", "Chamfer"))
        self.cb_chamfer.setChecked(obj.ChamferEnabled)
        self.cb_chamfer.toggled.connect(self.on_chamfer_toggled)
        edge_layout.addRow(self.cb_chamfer)

        self.spin_chamfer = QtWidgets.QDoubleSpinBox()
        self.spin_chamfer.setRange(0.1, 100.0)
        self.spin_chamfer.setDecimals(1)
        self.spin_chamfer.setValue(float(obj.ChamferSize))
        self.spin_chamfer.setSuffix(" mm")
        self.spin_chamfer.setEnabled(obj.ChamferEnabled)
        self.spin_chamfer.valueChanged.connect(self.on_chamfer_size_changed)
        edge_layout.addRow(translate("FrameForge2", "Chamfer size"), self.spin_chamfer)

        self.cb_fillet = QtWidgets.QCheckBox(translate("FrameForge2", "Fillet"))
        self.cb_fillet.setChecked(obj.FilletEnabled)
        self.cb_fillet.toggled.connect(self.on_fillet_toggled)
        edge_layout.addRow(self.cb_fillet)

        self.spin_fillet = QtWidgets.QDoubleSpinBox()
        self.spin_fillet.setRange(0.1, 100.0)
        self.spin_fillet.setDecimals(1)
        self.spin_fillet.setValue(float(obj.FilletSize))
        self.spin_fillet.setSuffix(" mm")
        self.spin_fillet.setEnabled(obj.FilletEnabled)
        self.spin_fillet.valueChanged.connect(self.on_fillet_size_changed)
        edge_layout.addRow(translate("FrameForge2", "Fillet radius"), self.spin_fillet)

        layout.addWidget(edge_group)

        # Hole group
        hole_group = QtWidgets.QGroupBox(translate("FrameForge2", "Bolt Hole"))
        hole_layout = QtWidgets.QFormLayout(hole_group)

        self.cb_hole = QtWidgets.QCheckBox(translate("FrameForge2", "Center hole"))
        self.cb_hole.setChecked(obj.HoleEnabled)
        self.cb_hole.toggled.connect(self.on_hole_toggled)
        hole_layout.addRow(self.cb_hole)

        self.cb_hole_threaded = QtWidgets.QCheckBox(translate("FrameForge2", "Threaded"))
        self.cb_hole_threaded.setChecked(obj.HoleThreaded)
        self.cb_hole_threaded.setEnabled(obj.HoleEnabled)
        self.cb_hole_threaded.toggled.connect(self.on_hole_threaded_toggled)
        hole_layout.addRow(self.cb_hole_threaded)

        self.spin_hole_dia = QtWidgets.QDoubleSpinBox()
        self.spin_hole_dia.setRange(1.0, 100.0)
        self.spin_hole_dia.setDecimals(1)
        self.spin_hole_dia.setValue(float(obj.HoleDiameter))
        self.spin_hole_dia.setSuffix(" mm")
        self.spin_hole_dia.setEnabled(obj.HoleEnabled)
        self.spin_hole_dia.valueChanged.connect(self.on_hole_dia_changed)
        hole_layout.addRow(translate("FrameForge2", "Diameter"), self.spin_hole_dia)

        layout.addWidget(hole_group)

        layout.addStretch()

        self.update_ui()

    def select_face(self):
        """Read the current selection and use the first face found."""
        sel = Gui.Selection.getSelectionEx()
        if len(sel) == 0:
            App.Console.PrintMessage(translate("FrameForge2", "Select a face in the 3D view first, then click this button\n"))
            return
        if len(sel) > 1:
            App.Console.PrintMessage(translate("FrameForge2", "Select only one face\n"))
            return
        if len(sel[0].SubElementNames) != 1:
            App.Console.PrintMessage(translate("FrameForge2", "Click a single face (not the whole object)\n"))
            return
        obj = sel[0].Object
        sub = sel[0].SubElementNames[0]
        face = obj.getSubObject(sub)
        if not isinstance(face, Part.Face):
            App.Console.PrintMessage(translate("FrameForge2", "That is not a face\n"))
            return

        self.obj.BaseObject = (obj, (sub,))
        self.face_label.setText(f"{obj.Label} ({sub})")
        self.obj.recompute()

    def on_thickness_changed(self, val):
        self.obj.Thickness = val
        self.obj.recompute()

    def on_offset_changed(self, val):
        self.obj.Offset = val
        self.obj.recompute()

    def on_reverse_toggled(self, checked):
        self.obj.Reverse = checked
        self.obj.recompute()

    def on_cap_type_changed(self, idx):
        self.obj.CapType = idx
        self.spin_plug_offset.setEnabled(idx == 1)
        self.obj.recompute()

    def on_plug_offset_changed(self, val):
        self.obj.PlugOffset = val
        self.obj.recompute()

    def on_chamfer_toggled(self, checked):
        self.obj.ChamferEnabled = checked
        self.spin_chamfer.setEnabled(checked)
        if checked and self.cb_fillet.isChecked():
            self.cb_fillet.setChecked(False)
        self.obj.recompute()

    def on_chamfer_size_changed(self, val):
        self.obj.ChamferSize = val
        self.obj.recompute()

    def on_fillet_toggled(self, checked):
        self.obj.FilletEnabled = checked
        self.spin_fillet.setEnabled(checked)
        if checked and self.cb_chamfer.isChecked():
            self.cb_chamfer.setChecked(False)
        self.obj.recompute()

    def on_fillet_size_changed(self, val):
        self.obj.FilletSize = val
        self.obj.recompute()

    def on_hole_toggled(self, checked):
        self.obj.HoleEnabled = checked
        self.spin_hole_dia.setEnabled(checked)
        self.cb_hole_threaded.setEnabled(checked)
        self.obj.recompute()

    def on_hole_threaded_toggled(self, checked):
        self.obj.HoleThreaded = checked
        self.obj.recompute()

    def on_hole_dia_changed(self, val):
        self.obj.HoleDiameter = val
        self.obj.recompute()

    def update_ui(self):
        self.spin_plug_offset.setEnabled(self.obj.CapType == 1)
        if self.obj.BaseObject:
            try:
                o, subs = self.obj.BaseObject
                self.face_label.setText(f"{o.Label} ({subs[0]})")
            except Exception:
                self.face_label.setText(translate("FrameForge2", "No face selected"))

    def open(self):
        App.Console.PrintMessage(translate("FrameForge2", "Opening Create End Cap\n"))
        App.ActiveDocument.openTransaction("Create End Cap")

    def reject(self):
        App.Console.PrintMessage(translate("FrameForge2", "Rejecting Create End Cap\n"))
        self.obj.restoreContent(self.dump)
        App.ActiveDocument.abortTransaction()
        Gui.ActiveDocument.resetEdit()
        return True

    def apply(self):
        App.Console.PrintMessage(translate("FrameForge2", "Applying...\n"))
        # Clear face selection so user can immediately select next
        self.obj.BaseObject = None
        self.face_label.setText(translate("FrameForge2", "No face selected"))
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
        App.Console.PrintMessage("Ready.\n")

    def accept(self):
        App.Console.PrintMessage(translate("FrameForge2", "Accepting Create End Cap\n"))
        App.ActiveDocument.commitTransaction()
        App.ActiveDocument.recompute()
        Gui.ActiveDocument.resetEdit()
        return True


class EndCapCommand:
    def GetResources(self):
        return {
            "Pixmap": os.path.join(ICONPATH, "end-cap.svg"),
            "MenuText": translate("FrameForge2", "End Cap"),
            "Accel": "M, C",
            "ToolTip": translate(
                "FrameForge2",
                "<html><head/><body><p><b>End Cap</b> \
                    <br><br> \
                    Select an open face of a profile to add an end cap. \
                    </p></body></html>",
            ),
        }

    def IsActive(self):
        if App.ActiveDocument:
            if len(Gui.Selection.getSelection()) > 0:
                for sel in Gui.Selection.getSelectionEx():
                    o = sel.Object
                    if len(sel.SubElementNames) != 1:
                        return False
                    if not isinstance(o.getSubObject(sel.SubElementNames[0]), Part.Face):
                        return False
                return True
            else:
                return True
        return False

    def Activated(self):
        sel = Gui.Selection.getSelectionEx()
        App.ActiveDocument.openTransaction("Make End Cap")

        selected_face = None
        if len(sel) >= 1 and len(sel[0].SubElementNames) > 0:
            selected_face = (sel[0].Object, sel[0].SubElementNames[0])

        doc = App.ActiveDocument
        name = "EndCap"
        obj = doc.addObject("Part::FeaturePython", name)

        end_cap = EndCap(obj, selected_face)
        ViewProviderEndCap(obj.ViewObject)

        if selected_face is not None and len(sel[0].Object.Parents) > 0:
            sel[0].Object.Parents[-1][0].addObject(obj)

        App.ActiveDocument.commitTransaction()

        panel = CreateEndCapTaskPanel(obj)
        Gui.Control.showDialog(panel)


Gui.addCommand("FrameForge2_EndCap", EndCapCommand())

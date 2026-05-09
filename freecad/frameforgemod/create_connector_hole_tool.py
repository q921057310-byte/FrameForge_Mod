import os

import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtCore, QtGui
try:
    from PySide import QtWidgets
except ImportError:
    QtWidgets = QtGui

from freecad.frameforgemod.connector_hole import HoleFeature, ViewProviderHoleFeature, BOLT_PRESETS, _HOLE_TYPES
from freecad.frameforgemod.ff_tools import ICONPATH, translate


class _SelObserver:
    def __init__(self, panel):
        self.panel = panel

    def addSelection(self, doc, obj_name, sub, pnt):
        self.panel._on_selection(doc, obj_name, sub)


class HoleFeatureTaskPanel:
    def __init__(self, obj):
        self.obj = obj
        self._obs = None

        self.form = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self.form)

        top_bar = QtWidgets.QHBoxLayout()
        top_bar.addStretch()
        ok_btn = QtWidgets.QPushButton(translate("frameforgemod", "OK"))
        ok_btn.setFixedWidth(60)
        ok_btn.setFixedHeight(22)
        ok_btn.clicked.connect(self.accept)
        top_bar.addWidget(ok_btn)
        apply_btn = QtWidgets.QPushButton(translate("frameforgemod", "Apply"))
        apply_btn.setFixedWidth(60)
        apply_btn.setFixedHeight(22)
        apply_btn.clicked.connect(self.apply)
        top_bar.addWidget(apply_btn)
        cancel_btn = QtWidgets.QPushButton(translate("frameforgemod", "Cancel"))
        cancel_btn.setFixedWidth(60)
        cancel_btn.setFixedHeight(22)
        cancel_btn.clicked.connect(self.reject)
        top_bar.addWidget(cancel_btn)
        layout.addLayout(top_bar)

        info = QtWidgets.QLabel(translate("frameforgemod",
            "<b>Hole</b><br>"
            "1. Click PROFILE face<br>"
            "2. Click SKETCH: points / circles(center) / lines(both ends)<br>"
            "   (click again to remove)"
        ))
        info.setWordWrap(True)
        layout.addWidget(info)

        self.base_label = QtWidgets.QLabel(translate("frameforgemod", "Base: not set"))
        layout.addWidget(self.base_label)
        self.pos_label = QtWidgets.QLabel(translate("frameforgemod", "Positions: 0"))
        layout.addWidget(self.pos_label)

        param_group = QtWidgets.QGroupBox(translate("frameforgemod", "Hole Parameters"))
        param_layout = QtWidgets.QFormLayout(param_group)

        self.hole_type = QtWidgets.QComboBox()
        self.hole_type.addItems(_HOLE_TYPES)
        current_type = str(obj.HoleType)
        self.hole_type.setCurrentText(current_type)
        self.hole_type.currentTextChanged.connect(self._on_type_changed)
        param_layout.addRow(translate("frameforgemod", "Type"), self.hole_type)

        self.bolt_spec = QtWidgets.QComboBox()
        self.bolt_spec.addItems(list(BOLT_PRESETS.keys()))
        current_spec = str(obj.BoltSpec)
        self.bolt_spec.setCurrentText(current_spec)
        self.bolt_spec.currentTextChanged.connect(self._on_bolt_changed)
        param_layout.addRow(translate("frameforgemod", "Bolt"), self.bolt_spec)

        self.spin_dia = QtWidgets.QDoubleSpinBox()
        self.spin_dia.setRange(1.0, 100.0)
        self.spin_dia.setDecimals(1)
        self.spin_dia.setSuffix(" mm")
        self.spin_dia.setValue(float(obj.HoleDiameter))
        self.spin_dia.valueChanged.connect(
            lambda v: self._set_and_recompute("HoleDiameter", v))
        param_layout.addRow(translate("frameforgemod", "Diameter"), self.spin_dia)

        self.spin_depth = QtWidgets.QDoubleSpinBox()
        self.spin_depth.setRange(0.0, 500.0)
        self.spin_depth.setDecimals(1)
        self.spin_depth.setSuffix(" mm")
        self.spin_depth.setValue(float(obj.HoleDepth))
        self.spin_depth.valueChanged.connect(
            lambda v: self._set_and_recompute("HoleDepth", v))
        param_layout.addRow(translate("frameforgemod", "Depth"), self.spin_depth)

        self.spin_csink_dia = QtWidgets.QDoubleSpinBox()
        self.spin_csink_dia.setRange(1.0, 100.0)
        self.spin_csink_dia.setDecimals(1)
        self.spin_csink_dia.setSuffix(" mm")
        self.spin_csink_dia.setValue(float(obj.CounterSinkDiameter))
        self.spin_csink_dia.valueChanged.connect(
            lambda v: self._set_and_recompute("CounterSinkDiameter", v))
        param_layout.addRow(translate("frameforgemod", "CSink Dia"), self.spin_csink_dia)

        self.spin_csink_depth = QtWidgets.QDoubleSpinBox()
        self.spin_csink_depth.setRange(0.5, 100.0)
        self.spin_csink_depth.setDecimals(1)
        self.spin_csink_depth.setSuffix(" mm")
        self.spin_csink_depth.setValue(float(obj.CounterSinkDepth))
        self.spin_csink_depth.valueChanged.connect(
            lambda v: self._set_and_recompute("CounterSinkDepth", v))
        param_layout.addRow(translate("frameforgemod", "CSink Depth"), self.spin_csink_depth)

        self.reverse_cb = QtWidgets.QCheckBox(translate("frameforgemod", "Reverse"))
        self.reverse_cb.setChecked(obj.Reverse)
        self.reverse_cb.toggled.connect(
            lambda v: self._set_and_recompute("Reverse", v))
        param_layout.addRow(self.reverse_cb)

        rot_group = QtWidgets.QGroupBox(translate("frameforgemod", "Direction Rotation"))
        rot_layout = QtWidgets.QHBoxLayout(rot_group)
        rot_layout.addWidget(QtWidgets.QLabel(translate("frameforgemod", "X:")))
        self.combo_rotx = QtWidgets.QComboBox()
        self.combo_rotx.addItems(["-90", "0", "90", "180"])
        self.combo_rotx.setCurrentText(str(int(float(obj.RotX))))
        self.combo_rotx.currentTextChanged.connect(
            lambda v: self._set_and_recompute("RotX", float(v)))
        rot_layout.addWidget(self.combo_rotx)
        rot_layout.addWidget(QtWidgets.QLabel(translate("frameforgemod", " Y:")))
        self.combo_roty = QtWidgets.QComboBox()
        self.combo_roty.addItems(["-90", "0", "90", "180"])
        self.combo_roty.setCurrentText(str(int(float(obj.RotY))))
        self.combo_roty.currentTextChanged.connect(
            lambda v: self._set_and_recompute("RotY", float(v)))
        rot_layout.addWidget(self.combo_roty)
        rot_layout.addWidget(QtWidgets.QLabel(translate("frameforgemod", " Z:")))
        self.combo_rotz = QtWidgets.QComboBox()
        self.combo_rotz.addItems(["-90", "0", "90", "180"])
        self.combo_rotz.setCurrentText(str(int(float(obj.RotZ))))
        self.combo_rotz.currentTextChanged.connect(
            lambda v: self._set_and_recompute("RotZ", float(v)))
        rot_layout.addWidget(self.combo_rotz)
        param_layout.addRow(rot_group)

        layout.addWidget(param_group)
        layout.addStretch()

        self._update_visibility(current_type)
        self._refresh_labels()

        self._obs = _SelObserver(self)
        Gui.Selection.addObserver(self._obs)
        App.Console.PrintMessage("HoleFeature: observer registered\n")

    def _set_and_recompute(self, prop, value):
        setattr(self.obj, prop, value)
        self.obj.touch()
        self.obj.recompute()
        App.ActiveDocument.recompute()
        App.Console.PrintMessage(f"HoleFeature: {prop} = {value}\n")

    def _on_type_changed(self, hole_type):
        self.obj.HoleType = hole_type
        self._update_visibility(hole_type)
        self.obj.touch()
        self.obj.recompute()
        App.ActiveDocument.recompute()

    def _on_bolt_changed(self, spec):
        self.obj.BoltSpec = spec
        if spec in BOLT_PRESETS and spec != "Custom":
            preset = BOLT_PRESETS[spec]
            self.obj.HoleDiameter = preset["hole_dia"]
            self.obj.HoleDepth = preset["depth"]
            self.obj.CounterSinkDiameter = preset["csink_dia"]
            self.obj.CounterSinkDepth = preset["csink_depth"]
            self.spin_dia.setValue(preset["hole_dia"])
            self.spin_depth.setValue(preset["depth"])
            self.spin_csink_dia.setValue(preset["csink_dia"])
            self.spin_csink_depth.setValue(preset["csink_depth"])

            is_pin = spec.startswith("Pin")
            if is_pin:
                self.hole_type.setCurrentText("Blind")
                self.obj.HoleType = "Blind"
                self._update_visibility("Blind")

        self.obj.touch()
        self.obj.recompute()
        App.ActiveDocument.recompute()
        App.Console.PrintMessage(f"HoleFeature: BoltSpec = {spec}\n")

    def _update_visibility(self, hole_type):
        is_blind = hole_type == "Blind"
        is_cbore = hole_type == "Counterbore"
        self.spin_depth.setVisible(is_blind)
        self.spin_csink_dia.setVisible(is_cbore)
        self.spin_csink_depth.setVisible(is_cbore)

    def _refresh_labels(self):
        base = self.obj.Base
        if base and base[0]:
            self.base_label.setText(f"Base: {base[0].Label} ({base[1][0]})")
        else:
            self.base_label.setText("Base: not set")
        count = 0
        for _, subs in (self.obj.Positions or []):
            count += len(subs)
        self.pos_label.setText(f"Positions: {count}")

    def _on_selection(self, doc_name, obj_name, sub):
        App.Console.PrintMessage(f"HoleFeature select: doc={doc_name} obj={obj_name} sub={sub}\n")

        if not sub:
            return
        if self.obj is None:
            return
        if obj_name == self.obj.Name:
            return

        doc = App.getDocument(doc_name)
        sel_obj = doc.getObject(obj_name)
        if sel_obj is None:
            return

        if self.obj.Base is None and sub.startswith("Face"):
            self.obj.Base = (sel_obj, (sub,))
            self.obj.touch()
            self._refresh_labels()
            self.obj.recompute()
            App.ActiveDocument.recompute()
            App.Console.PrintMessage(f"HoleFeature: Base = {sel_obj.Label}.{sub}\n")
            return

        if not sub.startswith(("Vertex", "Edge")):
            return

        positions = list(self.obj.Positions) if self.obj.Positions else []
        removed = False
        for i, (pobj, subs) in enumerate(positions):
            if pobj is sel_obj and sub in subs:
                subs_list = list(subs)
                subs_list.remove(sub)
                if subs_list:
                    positions[i] = (pobj, tuple(subs_list))
                else:
                    positions.pop(i)
                removed = True
                App.Console.PrintMessage(f"HoleFeature: removed {sel_obj.Label}.{sub}\n")
                break

        if not removed:
            found = False
            for i, (pobj, subs) in enumerate(positions):
                if pobj is sel_obj:
                    positions[i] = (pobj, tuple(list(subs) + [sub]))
                    found = True
                    break
            if not found:
                positions.append((sel_obj, (sub,)))
            App.Console.PrintMessage(f"HoleFeature: added {sel_obj.Label}.{sub}\n")

        self.obj.Positions = positions
        self.obj.touch()
        self._refresh_labels()
        self.obj.recompute()
        App.ActiveDocument.recompute()

    def open(self):
        App.Console.PrintMessage("HoleFeature: open\n")

    def reject(self):
        App.Console.PrintMessage("HoleFeature: reject\n")
        if self._obs:
            Gui.Selection.removeObserver(self._obs)
            self._obs = None
        try:
            App.ActiveDocument.removeObject(self.obj.Name)
        except Exception:
            pass
        Gui.ActiveDocument.resetEdit()
        return True

    def apply(self):
        App.Console.PrintMessage("HoleFeature: apply\n")
        self._do_cut()
        self.obj.Base = None
        self.obj.Positions = []
        self._refresh_labels()
        App.ActiveDocument.recompute()
        try:
            Gui.updateGui()
        except Exception:
            pass

    def _do_cut(self):
        base_obj = self.obj.Base[0] if self.obj.Base else None
        if base_obj is None:
            return
        try:
            from BOPTools import BOPFeatures
            bp = BOPFeatures.BOPFeatures(App.activeDocument())
            cut_obj = bp.make_cut([base_obj.Name, self.obj.Name])
            if cut_obj:
                name = getattr(base_obj, "SizeName", None)
                if not name:
                    label = base_obj.Label
                    name = label.split("_Profile_")[0] if "_Profile_" in label else label
                cut_obj.Label = f"{name}_Cut"
                self.obj.CutResult = cut_obj
                base_obj.ViewObject.Visibility = False
                self.obj.ViewObject.Visibility = False
                App.Console.PrintMessage(f"HoleFeature: Cut = {cut_obj.Label}\n")
        except Exception as e:
            App.Console.PrintWarning(f"HoleFeature: cut failed: {e}\n")

    def accept(self):
        App.Console.PrintMessage("HoleFeature: accept\n")
        if self._obs:
            Gui.Selection.removeObserver(self._obs)
            self._obs = None
        self.obj.recompute()
        App.ActiveDocument.recompute()
        self._do_cut()

        App.ActiveDocument.recompute()
        Gui.updateGui()
        Gui.ActiveDocument.resetEdit()
        return True


class HoleFeatureCommand:
    def GetResources(self):
        return {
            "Pixmap": os.path.join(ICONPATH, "whistle-connector.svg"),
            "MenuText": translate("frameforgemod", "Hole"),
            "ToolTip": translate("frameforgemod",
                "Drill holes on profiles. Select profile face, then sketch points/circles."),
        }

    def IsActive(self):
        return bool(App.ActiveDocument)

    def Activated(self):
        App.Console.PrintMessage("HoleFeature: activated\n")
        doc = App.ActiveDocument
        obj = doc.addObject("Part::FeaturePython", "Hole")
        HoleFeature(obj)
        ViewProviderHoleFeature(obj.ViewObject)

        sel = Gui.Selection.getSelectionEx()
        for sx in sel:
            for sub in sx.SubElementNames:
                if sub.startswith("Face"):
                    if obj.Base is None:
                        obj.Base = (sx.Object, (sub,))
                        obj.touch()
                        App.Console.PrintMessage(f"HoleFeature: pre Base={sx.Object.Label}.{sub}\n")
                        break
            if obj.Base:
                continue
            for sub in sx.SubElementNames:
                if sub.startswith(("Vertex", "Edge")):
                    geo = sx.Object.getSubObject(sub)
                    if isinstance(geo, (Part.Vertex, Part.Edge)):
                        positions = list(obj.Positions) if obj.Positions else []
                        found = False
                        for i, (pobj, subs) in enumerate(positions):
                            if pobj is sx.Object:
                                positions[i] = (pobj, tuple(list(subs) + [sub]))
                                found = True
                                break
                        if not found:
                            positions.append((sx.Object, (sub,)))
                        obj.Positions = positions
                        obj.touch()
                        App.Console.PrintMessage(f"HoleFeature: pre pos={sx.Object.Label}.{sub}\n")

        if sel:
            try:
                p = sel[0].Object
                if hasattr(p, "Parents") and p.Parents:
                    p.Parents[-1][0].addObject(obj)
            except Exception:
                pass

        App.ActiveDocument.recompute()
        panel = HoleFeatureTaskPanel(obj)
        Gui.Control.showDialog(panel)


Gui.addCommand("frameforgemod_HoleFeature", HoleFeatureCommand())

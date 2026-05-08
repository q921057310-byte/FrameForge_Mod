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
from freecad.frameforgemod.whistle_connector import (
    WhistleConnector,
    ViewProviderWhistleConnector,
    _get_qy_specs,
    _detect_hole_diameter_from_face,
    _match_tjoint_spec,
    _get_all_holes_info,
)


class _SelObserver:
    """Auto-capture face selections while the task panel is open."""

    def __init__(self, panel):
        self.panel = panel

    def addSelection(self, doc, obj_name, sub, pnt):
        self.panel._on_selection(doc, obj_name, sub)


class WhistleConnectorTaskPanel:
    def __init__(self, obj):
        self.obj = obj
        self.dump = obj.dumpContent()
        self._obs = None

        self.form = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self.form)

        # Top bar with Apply button (top-right, small)
        top_bar = QtWidgets.QHBoxLayout()
        top_bar.addStretch()
        apply_btn = QtWidgets.QPushButton(translate("frameforgemod", "Apply"))
        apply_btn.setFixedWidth(60)
        apply_btn.setFixedHeight(22)
        apply_btn.clicked.connect(self.apply)
        top_bar.addWidget(apply_btn)
        layout.addLayout(top_bar)

        # Status labels (auto-updated by selection observer)
        self.end_label = QtWidgets.QLabel(translate("frameforgemod", "Waiting for end face..."))
        self.drill_label = QtWidgets.QLabel(translate("frameforgemod", "Waiting for drill face..."))

        info = QtWidgets.QLabel(
            "<b>" + translate("frameforgemod", "Click faces in order:") + "</b><br>"
            "1. " + translate("frameforgemod", "Click the GROOVE FACE (side)") + "<br>"
            "2. " + translate("frameforgemod", "Click the END FACE (cross-section)"))
        info.setWordWrap(True)

        layout.addWidget(info)
        layout.addWidget(self.end_label)
        layout.addWidget(self.drill_label)

        # Hole parameters
        hole_group = QtWidgets.QGroupBox(translate("frameforgemod", "Hole Dimensions"))
        hole_layout = QtWidgets.QFormLayout(hole_group)

        self.spin_dia = QtWidgets.QDoubleSpinBox()
        self.spin_dia.setRange(1.0, 100.0)
        self.spin_dia.setDecimals(1)
        self.spin_dia.setSuffix(" mm")
        self.spin_dia.setValue(float(obj.HoleDiameter))
        self.spin_dia.valueChanged.connect(lambda v: [setattr(obj, "HoleDiameter", v), obj.recompute()])
        hole_layout.addRow(translate("frameforgemod", "Diameter"), self.spin_dia)

        self.spin_depth = QtWidgets.QDoubleSpinBox()
        self.spin_depth.setRange(1.0, 500.0)
        self.spin_depth.setDecimals(1)
        self.spin_depth.setSuffix(" mm")
        self.spin_depth.setValue(float(obj.HoleDepth))
        self.spin_depth.valueChanged.connect(lambda v: [setattr(obj, "HoleDepth", v), obj.recompute()])
        hole_layout.addRow(translate("frameforgemod", "Depth"), self.spin_depth)

        self.spin_dist = QtWidgets.QDoubleSpinBox()
        self.spin_dist.setRange(0.0, 1000.0)
        self.spin_dist.setDecimals(1)
        self.spin_dist.setSuffix(" mm")
        self.spin_dist.setValue(float(obj.HoleDistance))
        self.spin_dist.valueChanged.connect(lambda v: [setattr(obj, "HoleDistance", v), obj.recompute()])
        hole_layout.addRow(translate("frameforgemod", "Dist. from End"), self.spin_dist)

        self.reverse_cb = QtWidgets.QCheckBox(translate("frameforgemod", "Reverse"))
        self.reverse_cb.setChecked(obj.Reverse)
        self.reverse_cb.toggled.connect(lambda v: [setattr(obj, "Reverse", v), obj.recompute()])
        hole_layout.addRow(self.reverse_cb)

        layout.addWidget(hole_group)

        # QY info
        self.qy_label = QtWidgets.QLabel("")
        layout.addWidget(self.qy_label)
        self._update_qy()

        layout.addStretch()

    # ── Selection observer ──────────────────────────────────

    def open(self):
        App.Console.PrintMessage("Whistle Connector: click GROOVE FACE first, then END FACE\n")
        self._obs = _SelObserver(self)
        Gui.Selection.addObserver(self._obs)
        App.ActiveDocument.openTransaction("Whistle Connector")

    def reject(self):
        if self._obs:
            Gui.Selection.removeObserver(self._obs)
        App.ActiveDocument.abortTransaction()
        try:
            App.ActiveDocument.removeObject(self.obj.Name)
        except Exception:
            pass
        Gui.ActiveDocument.resetEdit()
        return True

    def apply(self):
        App.Console.PrintMessage(translate("frameforgemod", "Applying...\n"))
        self.obj.EndFace = None
        self.obj.DrillFace = None
        self.end_label.setText(translate("frameforgemod", "Waiting for end face..."))
        self.drill_label.setText(translate("frameforgemod", "Waiting for drill face..."))
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
        if self._obs:
            Gui.Selection.removeObserver(self._obs)
        App.ActiveDocument.commitTransaction()
        App.ActiveDocument.recompute()
        Gui.ActiveDocument.resetEdit()
        return True

    # ── Selection handler ──────────────────────────────────

    def _on_selection(self, doc_name, obj_name, sub):
        if not sub or not sub.startswith("Face"):
            return
        if self.obj is None or obj_name == self.obj.Name:
            return

        doc = App.getDocument(doc_name)
        obj = doc.getObject(obj_name)
        if obj is None:
            return

        face = obj.getSubObject(sub)
        if not isinstance(face, Part.Face):
            return

        # Toggle: clicking same face again clears it
        for slot, label in [("DrillFace", self.drill_label), ("EndFace", self.end_label)]:
            stored = getattr(self.obj, slot)
            if stored and len(stored) > 0 and stored[0] is obj and stored[1] == (sub,):
                setattr(self.obj, slot, None)
                label.setText(translate("frameforgemod", "Not set"))
                App.Console.PrintMessage(f"Cleared {slot}\n")
                self.obj.recompute()
                return

        # Ordered: click drill face first, then end face
        if self.obj.DrillFace is None:
            self.obj.DrillFace = (obj, (sub,))
            self.drill_label.setText(f"{translate('frameforgemod', 'Drill face')}: {obj.Label} ({sub})")
            self._update_qy()
            App.Console.PrintMessage(f"Drill face set: {obj.Label} {sub}\n")
            App.Console.PrintMessage("Now click END FACE (cross-section) of the profile.\n")
        else:
            self.obj.EndFace = (obj, (sub,))
            self.end_label.setText(f"{translate('frameforgemod', 'End face')}: {obj.Label} ({sub})")
            App.Console.PrintMessage(f"End face set: {obj.Label} {sub}\n")
            self.obj.recompute()
            App.Console.PrintMessage("Both faces set. OK to finish.\n")

    def _update_qy(self):
        try:
            if self.obj.DrillFace:
                from freecad.frameforgemod._utils import get_profile_from_trimmedbody
                prof = get_profile_from_trimmedbody(self.obj.DrillFace[0])
                qy = _get_qy_specs(prof)
                if qy:
                    self.obj.QYModel = qy["model"]
                    self.obj.HoleDiameter = qy["hole_dia"]
                    self.obj.HoleDepth = qy["hole_depth"]
                    self.obj.HoleDistance = qy["hole_distance"]
                    self.spin_dia.setValue(qy["hole_dia"])
                    self.spin_depth.setValue(qy["hole_depth"])
                    self.spin_dist.setValue(qy["hole_distance"])
                    self.qy_label.setText(
                        f"QY: {qy['model']} {qy['hole_dia']}×{qy['hole_depth']}@{qy['hole_distance']}mm")
                    self.obj.recompute()
                    App.Console.PrintMessage(f"QY auto-set: {qy['model']}\n")
                    return
                else:
                    App.Console.PrintMessage("QY: no matching series (try manual input)\n")
        except Exception as e:
            App.Console.PrintWarning(f"QY detection failed: {e}\n")
        self.qy_label.setText("QY: not detected")


class WhistleConnectorCommand:
    def GetResources(self):
        return {
            "Pixmap": os.path.join(ICONPATH, "whistle-connector.svg"),
            "MenuText": translate("frameforgemod", "Whistle Connector"),
            "Accel": "M, W",
            "ToolTip": translate(
                "frameforgemod",
                "Click the end face, then the groove face. Hole is drilled centered on the groove.",
            ),
        }

    def IsActive(self):
        return bool(App.ActiveDocument)

    def Activated(self):
        App.ActiveDocument.openTransaction("Make Whistle Connector")
        doc = App.ActiveDocument
        obj = doc.addObject("Part::FeaturePython", "WhistleConnector")
        WhistleConnector(obj)
        ViewProviderWhistleConnector(obj.ViewObject)

        # Assign pre-selected faces if available
        sel = Gui.Selection.getSelectionEx()
        for sx in sel:
            for sub in sx.SubElementNames:
                if not sub.startswith("Face"):
                    continue
                f = sx.Object.getSubObject(sub)
                if not isinstance(f, Part.Face):
                    continue
                is_end = False
                try:
                    sh = sx.Object.Shape
                    if not sh.isNull() and sh.Faces:
                        max_a = max(ff.Area for ff in sh.Faces)
                        is_end = f.Area < max_a * 0.25
                except Exception:
                    pass
                if is_end:
                    if obj.EndFace is None:
                        obj.EndFace = (sx.Object, (sub,))
                else:
                    if obj.DrillFace is None:
                        obj.DrillFace = (sx.Object, (sub,))

        # Add to parent group
        if sel:
            try:
                p = sel[0].Object
                if hasattr(p, "Parents") and p.Parents:
                    p.Parents[-1][0].addObject(obj)
            except Exception:
                pass

        App.ActiveDocument.commitTransaction()
        panel = WhistleConnectorTaskPanel(obj)
        Gui.Control.showDialog(panel)


Gui.addCommand("frameforgemod_WhistleConnector", WhistleConnectorCommand())


class TJointConnectorTaskPanel:
    def __init__(self, obj):
        self.obj = obj
        self.dump = obj.dumpContent()
        self._obs = None
        self._b_obj = None  # B profile object for hiding

        self.form = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self.form)

        top_bar = QtWidgets.QHBoxLayout()
        top_bar.addStretch()
        apply_btn = QtWidgets.QPushButton(translate("frameforgemod", "Apply"))
        apply_btn.setFixedWidth(60)
        apply_btn.setFixedHeight(22)
        apply_btn.clicked.connect(self.apply)
        top_bar.addWidget(apply_btn)
        layout.addLayout(top_bar)

        info = QtWidgets.QLabel(
            "<b>" + translate("frameforgemod", "T-Joint Connector") + "</b><br>"
            + translate("frameforgemod", "1. Click B side face (B hides)<br>2. Click A end face (with hole)")
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.b_label = QtWidgets.QLabel(translate("frameforgemod", "Waiting for B side face..."))
        self.a_label = QtWidgets.QLabel(translate("frameforgemod", "Waiting for A end face..."))
        layout.addWidget(self.b_label)
        layout.addWidget(self.a_label)

        self.detected_label = QtWidgets.QLabel(translate("frameforgemod", "Detected hole: not yet"))
        layout.addWidget(self.detected_label)

        self.match_label = QtWidgets.QLabel(translate("frameforgemod", "Matched spec: --"))
        layout.addWidget(self.match_label)

        param_group = QtWidgets.QGroupBox(translate("frameforgemod", "T-Joint Parameters"))
        param_layout = QtWidgets.QFormLayout(param_group)

        self.spin_through = QtWidgets.QDoubleSpinBox()
        self.spin_through.setRange(1.0, 50.0)
        self.spin_through.setDecimals(1)
        self.spin_through.setSuffix(" mm")
        self.spin_through.setValue(float(obj.ThroughHoleDiameter))
        self.spin_through.valueChanged.connect(
            lambda v: [setattr(obj, "ThroughHoleDiameter", v), obj.recompute()])
        param_layout.addRow(translate("frameforgemod", "Through Hole Dia"), self.spin_through)

        self.spin_csink_dia = QtWidgets.QDoubleSpinBox()
        self.spin_csink_dia.setRange(1.0, 50.0)
        self.spin_csink_dia.setDecimals(1)
        self.spin_csink_dia.setSuffix(" mm")
        self.spin_csink_dia.setValue(float(obj.CounterSinkDiameter))
        self.spin_csink_dia.valueChanged.connect(
            lambda v: [setattr(obj, "CounterSinkDiameter", v), obj.recompute()])
        param_layout.addRow(translate("frameforgemod", "Counterbore Dia"), self.spin_csink_dia)

        self.spin_csink_depth = QtWidgets.QDoubleSpinBox()
        self.spin_csink_depth.setRange(0.5, 50.0)
        self.spin_csink_depth.setDecimals(1)
        self.spin_csink_depth.setSuffix(" mm")
        self.spin_csink_depth.setValue(float(obj.CounterSinkDepth))
        self.spin_csink_depth.valueChanged.connect(
            lambda v: [setattr(obj, "CounterSinkDepth", v), obj.recompute()])
        param_layout.addRow(translate("frameforgemod", "Counterbore Depth"), self.spin_csink_depth)

        self.spin_detected_dia = QtWidgets.QDoubleSpinBox()
        self.spin_detected_dia.setRange(1.0, 50.0)
        self.spin_detected_dia.setDecimals(2)
        self.spin_detected_dia.setSuffix(" mm")
        self.spin_detected_dia.setValue(0.0)
        self.spin_detected_dia.valueChanged.connect(
            lambda v: [setattr(obj, "DetectedHoleDiameter", v), self._rematch_spec(), obj.recompute()])
        param_layout.addRow(translate("frameforgemod", "Detected Hole Dia"), self.spin_detected_dia)

        layout.addWidget(param_group)
        layout.addStretch()

    def open(self):
        App.Console.PrintMessage("T-Joint Connector: click B side face first, then A end face\n")
        self._obs = _SelObserver(self)
        Gui.Selection.addObserver(self._obs)
        App.ActiveDocument.openTransaction("T-Joint Connector")
        self.obj.ConnectorType = "TJoint"

    def reject(self):
        self._restore_b()
        if self._obs:
            Gui.Selection.removeObserver(self._obs)
        App.ActiveDocument.abortTransaction()
        try:
            App.ActiveDocument.removeObject(self.obj.Name)
        except Exception:
            pass
        Gui.ActiveDocument.resetEdit()
        return True

    def apply(self):
        self._restore_b()
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
        App.Console.PrintMessage("T-Joint applied.\n")

    def accept(self):
        self._restore_b()
        if self._obs:
            Gui.Selection.removeObserver(self._obs)
        App.ActiveDocument.commitTransaction()
        App.ActiveDocument.recompute()
        Gui.ActiveDocument.resetEdit()
        return True

    def _restore_b(self):
        if self._b_obj:
            try:
                self._b_obj.ViewObject.Visibility = True
            except Exception:
                pass
        self._b_obj = None

    def _on_selection(self, doc_name, obj_name, sub):
        if not sub or not sub.startswith("Face"):
            return
        if self.obj is None or obj_name == self.obj.Name:
            return

        doc = App.getDocument(doc_name)
        sel_obj = doc.getObject(obj_name)
        if sel_obj is None:
            return

        face = sel_obj.getSubObject(sub)
        if not isinstance(face, Part.Face):
            return

        # Step 1: click B side face (DrillFace) → hide B
        if self.obj.DrillFace is None:
            self.obj.DrillFace = (sel_obj, (sub,))
            self.b_label.setText(
                f"{translate('frameforgemod', 'B side face')}: {sel_obj.Label} ({sub})")
            self._b_obj = sel_obj
            try:
                self._b_obj.ViewObject.Visibility = False
            except Exception:
                pass
            self.obj.recompute()
            App.Console.PrintMessage(
                f"B side face set: {sel_obj.Label} {sub}. "
                f"Now click A END FACE with the hole.\n")
            return

        # Step 2: click A end face (EndFace) → detect hole, match
        from freecad.frameforgemod._utils import get_profile_from_trimmedbody
        self.obj.EndFace = (sel_obj, (sub,))
        self.obj.TJointReferenceA = get_profile_from_trimmedbody(sel_obj)
        self.a_label.setText(
            f"{translate('frameforgemod', 'A end face')}: {sel_obj.Label} ({sub})")
        App.Console.PrintMessage(f"A end face set: {sel_obj.Label} {sub}\n")

        self._detect_and_match(face)
        self.obj.recompute()
        App.Console.PrintMessage("Ready. Press Apply or OK.\n")

    def _detect_and_match(self, face):
        dia, err = _detect_hole_diameter_from_face(face)
        if dia is not None:
            self.spin_detected_dia.setValue(dia)
            self.obj.DetectedHoleDiameter = dia
            self.detected_label.setText(
                f"{translate('frameforgemod', 'Detected hole')}: {dia:.1f} mm")
            self._rematch_spec()
        else:
            all_holes, _ = _get_all_holes_info(face)
            if all_holes:
                non_corner = [h for h in all_holes if not h.get("corner")]
                if non_corner:
                    dia = non_corner[0]["diameter"]
                    self.spin_detected_dia.setValue(dia)
                    self.obj.DetectedHoleDiameter = dia
                    self.detected_label.setText(
                        f"{translate('frameforgemod', 'Detected hole')}: {dia:.2f} mm " +
                        translate('frameforgemod', '(fallback, no narrow-center hole)'))
                    self._rematch_spec()
                else:
                    self.detected_label.setText(translate("frameforgemod", err or "No valid hole detected"))
            else:
                self.detected_label.setText(translate("frameforgemod", err or "No hole detected on face"))

    def _rematch_spec(self):
        dia = float(self.spin_detected_dia.value())
        if dia <= 0:
            return
        match = _match_tjoint_spec(dia)
        if match:
            screw, spec = match
            self.obj.MatchedScrewSize = screw
            self.obj.ThroughHoleDiameter = spec["through_dia"]
            self.obj.CounterSinkDiameter = spec["csink_dia"]
            self.obj.CounterSinkDepth = spec["csink_depth"]
            self.spin_through.setValue(spec["through_dia"])
            self.spin_csink_dia.setValue(spec["csink_dia"])
            self.spin_csink_depth.setValue(spec["csink_depth"])
            self.match_label.setText(
                f"{translate('frameforgemod', 'Matched')}: {screw}  "
                f"Thru⌀{spec['through_dia']:.1f} + Cbore⌀{spec['csink_dia']:.1f}x{spec['csink_depth']:.1f} mm")
            App.Console.PrintMessage(
                f"T-Joint: matched {screw} for {dia:.1f}mm hole\n")
        else:
            self.obj.MatchedScrewSize = "Manual"
            self.match_label.setText(
                f"{translate('frameforgemod', 'Diameter {:.1f} out of range, manual adjust needed').format(dia)}")
            App.Console.PrintWarning(
                f"T-Joint: no match for {dia:.1f}mm, manual adjust required\n")


class TJointConnectorCommand:
    def GetResources(self):
        return {
            "Pixmap": os.path.join(ICONPATH, "whistle-connector.svg"),
            "MenuText": translate("frameforgemod", "T-Joint Connector"),
            "Accel": "M, T",
            "ToolTip": translate(
                "frameforgemod",
                "Select two profiles in T-joint. Auto-detects A/B, hides B, drills countersunk through hole.",
            ),
        }

    def IsActive(self):
        return bool(App.ActiveDocument)

    def Activated(self):
        doc = App.ActiveDocument

        App.ActiveDocument.openTransaction("Make T-Joint Connector")

        obj = doc.addObject("Part::FeaturePython", "TJointConnector")
        WhistleConnector(obj)
        ViewProviderWhistleConnector(obj.ViewObject)

        obj.ConnectorType = "TJoint"

        App.ActiveDocument.commitTransaction()

        panel = TJointConnectorTaskPanel(obj)
        Gui.Control.showDialog(panel)


Gui.addCommand("frameforgemod_TJointConnector", TJointConnectorCommand())


class ConnectorToolGroup:
    def GetCommands(self):
        return ("frameforgemod_WhistleConnector", "frameforgemod_TJointConnector")

    def GetDefaultCommand(self):
        return 0

    def GetResources(self):
        return {
            "Pixmap": os.path.join(ICONPATH, "whistle-connector.svg"),
            "MenuText": translate("frameforgemod", "Connector"),
            "ToolTip": translate(
                "frameforgemod",
                "Whistle connector or T-Joint connector",
            ),
        }


Gui.addCommand("frameforgemod_ConnectorGroup", ConnectorToolGroup())

import os

import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtCore, QtGui
try:
    from PySide import QtWidgets
except ImportError:
    QtWidgets = QtGui

from freecad.frameforge2.ff_tools import ICONPATH, UIPATH, translate
from freecad.frameforge2.whistle_connector import (
    WhistleConnector,
    ViewProviderWhistleConnector,
    _get_qy_specs,
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
        apply_btn = QtWidgets.QPushButton(translate("FrameForge2", "Apply"))
        apply_btn.setFixedWidth(60)
        apply_btn.setFixedHeight(22)
        apply_btn.clicked.connect(self.apply)
        top_bar.addWidget(apply_btn)
        layout.addLayout(top_bar)

        # Status labels (auto-updated by selection observer)
        self.end_label = QtWidgets.QLabel(translate("FrameForge2", "Waiting for end face..."))
        self.drill_label = QtWidgets.QLabel(translate("FrameForge2", "Waiting for drill face..."))

        info = QtWidgets.QLabel(
            "<b>" + translate("FrameForge2", "Click faces in order:") + "</b><br>"
            "1. " + translate("FrameForge2", "Click the GROOVE FACE (side)") + "<br>"
            "2. " + translate("FrameForge2", "Click the END FACE (cross-section)"))
        info.setWordWrap(True)

        layout.addWidget(info)
        layout.addWidget(self.end_label)
        layout.addWidget(self.drill_label)

        # Hole parameters
        hole_group = QtWidgets.QGroupBox(translate("FrameForge2", "Hole Dimensions"))
        hole_layout = QtWidgets.QFormLayout(hole_group)

        self.spin_dia = QtWidgets.QDoubleSpinBox()
        self.spin_dia.setRange(1.0, 100.0)
        self.spin_dia.setDecimals(1)
        self.spin_dia.setSuffix(" mm")
        self.spin_dia.setValue(float(obj.HoleDiameter))
        self.spin_dia.valueChanged.connect(lambda v: [setattr(obj, "HoleDiameter", v), obj.recompute()])
        hole_layout.addRow(translate("FrameForge2", "Diameter"), self.spin_dia)

        self.spin_depth = QtWidgets.QDoubleSpinBox()
        self.spin_depth.setRange(1.0, 500.0)
        self.spin_depth.setDecimals(1)
        self.spin_depth.setSuffix(" mm")
        self.spin_depth.setValue(float(obj.HoleDepth))
        self.spin_depth.valueChanged.connect(lambda v: [setattr(obj, "HoleDepth", v), obj.recompute()])
        hole_layout.addRow(translate("FrameForge2", "Depth"), self.spin_depth)

        self.spin_dist = QtWidgets.QDoubleSpinBox()
        self.spin_dist.setRange(0.0, 1000.0)
        self.spin_dist.setDecimals(1)
        self.spin_dist.setSuffix(" mm")
        self.spin_dist.setValue(float(obj.HoleDistance))
        self.spin_dist.valueChanged.connect(lambda v: [setattr(obj, "HoleDistance", v), obj.recompute()])
        hole_layout.addRow(translate("FrameForge2", "Dist. from End"), self.spin_dist)

        self.reverse_cb = QtWidgets.QCheckBox(translate("FrameForge2", "Reverse"))
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
        self.obj.restoreContent(self.dump)
        App.ActiveDocument.abortTransaction()
        Gui.ActiveDocument.resetEdit()
        return True

    def apply(self):
        App.Console.PrintMessage(translate("FrameForge2", "Applying...\n"))
        self.obj.EndFace = None
        self.obj.DrillFace = None
        self.end_label.setText(translate("FrameForge2", "Waiting for end face..."))
        self.drill_label.setText(translate("FrameForge2", "Waiting for drill face..."))
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
                label.setText(translate("FrameForge2", "Not set"))
                App.Console.PrintMessage(f"Cleared {slot}\n")
                self.obj.recompute()
                return

        # Ordered: click drill face first, then end face
        if self.obj.DrillFace is None:
            self.obj.DrillFace = (obj, (sub,))
            self.drill_label.setText(f"{translate('FrameForge2', 'Drill face')}: {obj.Label} ({sub})")
            self._update_qy()
            App.Console.PrintMessage(f"Drill face set: {obj.Label} {sub}\n")
            App.Console.PrintMessage("Now click END FACE (cross-section) of the profile.\n")
        else:
            self.obj.EndFace = (obj, (sub,))
            self.end_label.setText(f"{translate('FrameForge2', 'End face')}: {obj.Label} ({sub})")
            App.Console.PrintMessage(f"End face set: {obj.Label} {sub}\n")
            self.obj.recompute()
            App.Console.PrintMessage("Both faces set. OK to finish.\n")

    def _update_qy(self):
        try:
            if self.obj.DrillFace:
                from freecad.frameforge2._utils import get_profile_from_trimmedbody
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
            "MenuText": translate("FrameForge2", "Whistle Connector"),
            "Accel": "M, W",
            "ToolTip": translate(
                "FrameForge2",
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


Gui.addCommand("FrameForge2_WhistleConnector", WhistleConnectorCommand())

import glob
import json
import os

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui
try:
    from PySide import QtWidgets
except ImportError:
    QtWidgets = QtGui

from freecad.frameforge2.extruded_cutout import ExtrudedCutout, ViewProviderExtrudedCutout
from freecad.frameforge2.ff_tools import ICONPATH, PROFILEIMAGES_PATH, PROFILESPATH, UIPATH, FormProxy, translate
from freecad.frameforge2.frameforge_exceptions import FrameForge2Exception


class CreateExtrudedCutoutTaskPanel:
    """TaskPanel pour FrameForge ExtrudedCutout (corrigé pour CutType)."""

    def __init__(self, obj):
        self.obj = obj

        self.cut_types = [
            "Through All",
            "Distance",
        ]

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

        layout.addWidget(QtWidgets.QLabel("Cut type"))
        self.comboCutType = QtWidgets.QComboBox()
        self.comboCutType.addItems(self.cut_types)
        try:
            current = str(self.obj.CutType)
            idx = self.cut_types.index(current)
        except Exception:
            idx = 0
        self.comboCutType.setCurrentIndex(idx)
        layout.addWidget(self.comboCutType)

        self.spinA = QtWidgets.QDoubleSpinBox()
        self.spinA.setRange(-1e6, 1e6)
        self.spinA.setDecimals(4)
        try:
            self.spinA.setValue(float(self.obj.ExtrusionLength1.Value))
        except Exception:
            try:
                self.spinA.setValue(float(self.obj.ExtrusionLength1))
            except Exception:
                self.spinA.setValue(500.0)

        layout.addWidget(QtWidgets.QLabel("Extrusion Length"))
        layout.addWidget(self.spinA)

        self.comboCutType.currentIndexChanged.connect(self.onCutTypeChanged)
        self.spinA.valueChanged.connect(self.onLengthAChanged)

        self.updateWidgetsVisibility()

    def onCutTypeChanged(self, idx):
        if 0 <= idx < len(self.cut_types):
            self.obj.CutType = self.cut_types[idx]
        else:
            self.obj.CutType = self.cut_types[0]
        self.updateWidgetsVisibility()

        self.obj.recompute()

    def onLengthAChanged(self, val):
        self.obj.ExtrusionLength = val
        self.obj.recompute()

    def updateWidgetsVisibility(self):
        """Afficher/masquer les widgets de longueur selon CutType selectionné."""
        ct = getattr(self.obj, "CutType", self.cut_types[0])
        self.spinA.setVisible(ct in ["Distance"])

    def open(self):
        App.Console.PrintMessage(translate("FrameForge2", "Opening Create Extrude Cutout\n"))

        App.ActiveDocument.openTransaction("Create Cutout")

    def apply(self):
        App.Console.PrintMessage(translate("FrameForge2", "Applying...\n"))
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
        App.ActiveDocument.openTransaction("Continue editing")
        App.Console.PrintMessage("Ready.\n")

    def accept(self):
        App.Console.PrintMessage(translate("FrameForge2", "Accepting Create Extrude Cutout\n"))
        try:
            if hasattr(self.obj, "Sketch") and self.obj.Sketch:
                try:
                    self.obj.Sketch.ViewObject.hide()
                except Exception:
                    pass
        except Exception:
            pass

        App.ActiveDocument.commitTransaction()
        App.ActiveDocument.recompute()

        return True

    def reject(self):
        App.Console.PrintMessage(translate("FrameForge2", "Rejecting Create Extrude Cutout\n"))
        App.ActiveDocument.abortTransaction()

        return True


class AddExtrudedCutoutCommandClass:
    """Add Extruded Cutout command."""

    def GetResources(self):
        return {
            # 资源中可用的 svg 文件名。
            "Pixmap": os.path.join(ICONPATH, "extruded-cutout.svg"),
            "MenuText": translate("FrameForge2", "Extruded Cutout"),
            "Accel": "E, C",
            "ToolTip": translate(
                "FrameForge2",
                "Create an extruded cutout from a sketch:\n"
                "1. Select a face of a part (not a thickness face).\n"
                "2. Select a closed sketch for the cutout.\n"
                "3. Adjust parameters in the Property editor.",
            ),
        }

    def Activated(self):
        """Create an Extruded Cutout object from user selections."""
        # Get the selected object and face.
        selection = Gui.Selection.getSelectionEx()[0]
        # When user select first the sketch
        if selection.Object.isDerivedFrom("Sketcher::SketchObject"):
            # Get selected sketch
            cutSketch = selection.Object
            # Check if we have any sub-objects (faces) selected.
            selection = Gui.Selection.getSelectionEx()[1]
            if len(selection.SubObjects) == 0:
                raise FrameForge2Exception("No face selected. Please select a face.")
            # Get selected object.
            selected_object = selection.Object
            # Get the selected face.
            selected_face = [selected_object, selection.SubElementNames[0]]
        # When user select first the object face.
        else:
            # Check if we have any sub-objects (faces) selected.
            if len(selection.SubObjects) == 0:
                raise FrameForge2Exception("No face selected. Please select a face.")
            # Get selected object.
            selected_object = selection.Object
            # Get the selected face.
            selected_face = [selected_object, selection.SubElementNames[0]]
            # Get selected sketch.
            selection = Gui.Selection.getSelectionEx()[1]
            cutSketch = selection.Object

        if cutSketch is None or not selected_object.Shape:
            raise FrameForge2Exception("Both a valid sketch and an object with a shape must be selected.")

        App.ActiveDocument.openTransaction("Create Cutout")

        name = "ExtrudedCutout" if selected_object is None else f"{selected_object.Name}_Ex"

        obj = App.ActiveDocument.addObject("Part::FeaturePython", name)
        obj.addExtension("Part::AttachExtensionPython")

        if len(selected_object.Parents) > 0:
            part = selected_object.Parents[-1][0]
            part.addObject(obj)

            part.addObject(cutSketch)

        extruded_cutout = ExtrudedCutout(obj, cutSketch, selected_face)
        ViewProviderExtrudedCutout(obj.ViewObject)
        App.ActiveDocument.commitTransaction()

        obj.recompute()

        panel = CreateExtrudedCutoutTaskPanel(obj)
        Gui.Control.showDialog(panel)

    def IsActive(self):
        return len(Gui.Selection.getSelection()) == 2


Gui.addCommand("FrameForge2_AddExtrudeCutout", AddExtrudedCutoutCommandClass())

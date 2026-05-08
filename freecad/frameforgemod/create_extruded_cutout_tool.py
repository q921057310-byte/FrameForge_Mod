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

from freecad.frameforgemod.extruded_cutout import ExtrudedCutout, ViewProviderExtrudedCutout
from freecad.frameforgemod.ff_tools import ICONPATH, PROFILEIMAGES_PATH, PROFILESPATH, UIPATH, FormProxy, translate
from freecad.frameforgemod.frameforgemod_exceptions import FrameForgemodException


class CreateExtrudedCutoutTaskPanel:
    """TaskPanel pour FrameForge ExtrudedCutout (corrigé pour CutType)."""

    def __init__(self, obj, cut_sketch=None, original_sketch_parents=None):
        self.obj = obj
        self.cut_sketch = cut_sketch
        self.original_sketch_parents = original_sketch_parents or []
        self.dump = obj.dumpContent()

        self.cut_types = [
            "Through All",
            "Distance",
        ]

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
        App.Console.PrintMessage(translate("frameforgemod", "Opening Create Extrude Cutout\n"))

        App.ActiveDocument.openTransaction("Create Cutout")

    def apply(self):
        App.Console.PrintMessage(translate("frameforgemod", "Applying...\n"))
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
        App.Console.PrintMessage(translate("frameforgemod", "Accepting Create Extrude Cutout\n"))
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
        App.Console.PrintMessage(translate("frameforgemod", "Rejecting Create Extrude Cutout\n"))
        App.ActiveDocument.abortTransaction()
        try:
            App.ActiveDocument.removeObject(self.obj.Name)
        except Exception:
            pass
        if self.cut_sketch:
            for p in list(self.cut_sketch.InList):
                try:
                    p.removeObject(self.cut_sketch)
                except Exception:
                    pass
            for p in self.original_sketch_parents:
                try:
                    p.addObject(self.cut_sketch)
                except Exception:
                    pass
        Gui.ActiveDocument.resetEdit()
        return True


class AddExtrudedCutoutCommandClass:
    """Add Extruded Cutout command."""

    def GetResources(self):
        return {
            # 资源中可用的 svg 文件名。
            "Pixmap": os.path.join(ICONPATH, "extruded-cutout.svg"),
            "MenuText": translate("frameforgemod", "Extruded Cutout"),
            "Accel": "E, C",
            "ToolTip": translate(
                "frameforgemod",
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
                raise FrameForgemodException("No face selected. Please select a face.")
            # Get selected object.
            selected_object = selection.Object
            # Get the selected face.
            selected_face = [selected_object, selection.SubElementNames[0]]
            selected_face_shape = selection.SubObjects[0]
        # When user select first the object face.
        else:
            # Check if we have any sub-objects (faces) selected.
            if len(selection.SubObjects) == 0:
                raise FrameForgemodException("No face selected. Please select a face.")
            # Get selected object.
            selected_object = selection.Object
            # Get the selected face.
            selected_face = [selected_object, selection.SubElementNames[0]]
            selected_face_shape = selection.SubObjects[0]
            # Get selected sketch.
            selection = Gui.Selection.getSelectionEx()[1]
            cutSketch = selection.Object

        if cutSketch is None or not selected_object.Shape:
            raise FrameForgemodException("Both a valid sketch and an object with a shape must be selected.")

        # If user selected a TJoint/WhistleConnector face, resolve to the underlying profile
        if hasattr(selected_object, 'DrillFace') and selected_object.DrillFace:
            root = selected_object.DrillFace[0]
        elif hasattr(selected_object, 'baseObject') and selected_object.baseObject:
            root = selected_object.baseObject[0]
        else:
            root = None

        if root is not None and root is not selected_object:
            try:
                root.ViewObject.Visibility = True
            except Exception:
                pass
            # Map selected face to root profile by normal matching
            try:
                sel_normal = selected_face_shape.normalAt(0.5, 0.5)
                best = None
                best_dot = -2.0
                for i, f in enumerate(root.Shape.Faces):
                    n = f.normalAt(0.5, 0.5)
                    d = sel_normal.dot(n)
                    if d > best_dot:
                        best_dot = d
                        best = f"Face{i + 1}"
                if best is not None and best_dot > 0.99:
                    selected_object = root
                    selected_face = [root, best]
            except Exception:
                pass

        App.ActiveDocument.openTransaction("Create Cutout")

        name = "ExtrudedCutout" if selected_object is None else f"{selected_object.Name}_Ex"

        obj = App.ActiveDocument.addObject("Part::FeaturePython", name)
        obj.addExtension("Part::AttachExtensionPython")

        if len(selected_object.Parents) > 0:
            part = selected_object.Parents[-1][0]
            part.addObject(obj)

            original_sketch_parents = list(cutSketch.InList)
            part.addObject(cutSketch)
        else:
            original_sketch_parents = list(cutSketch.InList)

        extruded_cutout = ExtrudedCutout(obj, cutSketch, selected_face)
        ViewProviderExtrudedCutout(obj.ViewObject)
        App.ActiveDocument.commitTransaction()

        obj.recompute()

        panel = CreateExtrudedCutoutTaskPanel(obj, cut_sketch=cutSketch, original_sketch_parents=original_sketch_parents)
        Gui.Control.showDialog(panel)

    def IsActive(self):
        return len(Gui.Selection.getSelection()) == 2


Gui.addCommand("frameforgemod_AddExtrudeCutout", AddExtrudedCutoutCommandClass())

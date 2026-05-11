import glob
import json
import os

import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtCore, QtGui
try:
    from PySide import QtWidgets
except ImportError:
    QtWidgets = QtGui

# Optional imports for compatibility with FreeCAD 1.0+
try:
    import ArchCommands  # noqa: F401
except ImportError:
    ArchCommands = None
try:
    import BOPTools.SplitAPI  # noqa: F401
except ImportError:
    BOPTools = None

from freecad.frameforgemod.ff_tools import ICONPATH, PROFILEIMAGES_PATH, PROFILESPATH, UIPATH, translate
from freecad.frameforgemod.trimmed_profile import TrimmedProfile, ViewProviderTrimmedProfile


class CreateTrimmedProfileTaskPanel:
    def __init__(self, fp, mode):
        ui_file = os.path.join(UIPATH, "create_trimmed_profiles.ui")
        self.form = Gui.PySideUic.loadUi(ui_file)

        # Top-right Apply button
        _top_row = QtWidgets.QHBoxLayout()
        _top_row.addStretch()
        self.form.layout().insertLayout(0, _top_row)

        self.fp = fp
        self.dump = fp.dumpContent()
        self.mode = mode
        self.trimmed_bodies = []
        self._extra_objects = []

        self.initialize_ui()

    def initialize_ui(self):
        add_icon = QtGui.QIcon(os.path.join(ICONPATH, "list-add.svg"))
        remove_icon = QtGui.QIcon(os.path.join(ICONPATH, "list-remove.svg"))
        coped_type_icon = QtGui.QIcon(os.path.join(ICONPATH, "corner-coped-type.svg"))
        simple_type_icon = QtGui.QIcon(os.path.join(ICONPATH, "corner-simple-type.svg"))

        QSize = QtCore.QSize(32, 32)

        self.form.rb_perfectfit.setIcon(coped_type_icon)
        self.form.rb_perfectfit.setIconSize(QSize)
        self.form.rb_perfectfit.toggled.connect(lambda: self.update_cuttype("Perfect fit"))

        self.form.rb_simplefit.setIcon(simple_type_icon)
        self.form.rb_simplefit.setIconSize(QSize)
        self.form.rb_simplefit.toggled.connect(lambda: self.update_cuttype("Simple fit"))

        param = App.ParamGet("User parameter:BaseApp/Preferences/Frameforge_mod")
        if param.GetString("Default Cut Type") == "Perfect fit":
            self.form.rb_perfectfit.toggle()
        elif param.GetString("Default Cut Type") == "Simple fit":
            self.form.rb_simplefit.toggle()

        self.form.add_trimmed_object_button.setIcon(add_icon)
        self.form.add_boundary_button.setIcon(add_icon)
        self.form.remove_boundary_button.setIcon(remove_icon)
        self.form.remove_body_button.setIcon(remove_icon)

        self.form.add_trimmed_object_button.clicked.connect(self.add_trimmed_body)
        self.form.add_boundary_button.clicked.connect(self.add_trimming_bodies)
        self.form.remove_boundary_button.clicked.connect(self.remove_trimming_bodies)
        self.form.remove_body_button.clicked.connect(self.remove_trimmed_body)

    def update_cuttype(self, cuttype):
        self.fp.CutType = cuttype

        self.update_view_and_model()

    def add_trimmed_body(self):
        sel = Gui.Selection.getSelectionEx()
        if not sel or all(len(s.SubElementNames) == 0 for s in sel):
            App.Console.PrintMessage(translate("frameforgemod", "Select at least one face for TrimmedBody\n"))
            return

        added = 0
        for selObject in sel:
            obj = selObject.Object
            if not any(isinstance(obj.getSubObject(sub), Part.Face) for sub in selObject.SubElementNames):
                continue
            if any(existing is obj for existing, _ in self.trimmed_bodies):
                App.Console.PrintMessage(translate("frameforgemod", "Already added: {}").format(obj.Name) + "\n")
                continue
            self.trimmed_bodies.append((obj, ""))
            added += 1

        if added > 0:
            App.Console.PrintMessage(translate("frameforgemod", "Added {} trimmed body(ies)").format(added) + "\n")

        self.update_view_and_model()

    def remove_trimmed_body(self):
        selected = self.form.bodies_list_widget.selectedItems()
        if not selected:
            return
        for item in selected:
            entry = item.data(1)
            if entry in self.trimmed_bodies:
                self.trimmed_bodies.remove(entry)
        self.update_view_and_model()

    def add_trimming_bodies(self):
        App.Console.PrintMessage(translate("frameforgemod", "Add Trimming bodies...\n"))

        # It looks like the TrimmingBoundary list must be rebuilt, not working if trying to only append data..
        trimming_boundaries = [e for e in self.fp.TrimmingBoundary]

        for selObject in Gui.Selection.getSelectionEx():
            valid_subs = tuple(
                sub for sub in selObject.SubElementNames
                if isinstance(selObject.Object.getSubObject(sub), Part.Face)
            )
            if not valid_subs:
                App.Console.PrintMessage(translate("frameforgemod", "Select faces only") + "\n")
                return

            entry = (selObject.Object, valid_subs)
            if all([tb != entry for tb in trimming_boundaries]):
                trimming_boundaries.append(entry)

                App.Console.PrintMessage(
                    translate("frameforgemod", "\tadd trimming body: {} {}").format(selObject.ObjectName, valid_subs) + "\n"
                )

            else:
                App.Console.PrintMessage(translate("frameforgemod", "Already a trimming boundarie for this TrimmedBody\n"))

        self.fp.TrimmingBoundary = trimming_boundaries

        self.update_view_and_model()

    def remove_trimming_bodies(self):
        App.Console.PrintMessage(translate("frameforgemod", "Remove Trimming body\n"))

        selected_tb = [item.data(1) for item in self.form.boundaries_list_widget.selectedItems()]
        self.fp.TrimmingBoundary = [tb for tb in self.fp.TrimmingBoundary if tb not in selected_tb]

        self.update_view_and_model()

    def update_view_and_model(self):
        self.form.bodies_list_widget.clear()
        # Show bodies from the panel list (creation multi-select) or from fp (pre-created / edition)
        shown = set()
        for obj, sub in self.trimmed_bodies:
            label = f"{obj.Label} ({obj.Name} {sub})" if sub else f"{obj.Label} ({obj.Name})"
            item = QtWidgets.QListWidgetItem()
            item.setText(label)
            item.setData(1, (obj, sub))
            self.form.bodies_list_widget.addItem(item)
            shown.add(id(obj))
        if self.fp.TrimmedBody is not None and id(self.fp.TrimmedBody) not in shown:
            item = QtWidgets.QListWidgetItem()
            item.setText(f"{self.fp.TrimmedBody.Label} ({self.fp.TrimmedBody.Name})")
            item.setData(1, (self.fp.TrimmedBody, ""))
            self.form.bodies_list_widget.addItem(item)

        self.form.boundaries_list_widget.clear()
        for bound in self.fp.TrimmingBoundary:
            item = QtWidgets.QListWidgetItem()
            item.setText("{} ({} {})".format(bound[0].Label, bound[0].Name, ", ".join(bound[1])))
            item.setData(1, bound)
            self.form.boundaries_list_widget.addItem(item)

        # self.fp.recompute()  # skip: App.ActiveDocument.recompute() handles all
        App.ActiveDocument.recompute()

    def open(self):
        App.Console.PrintMessage(translate("frameforgemod", "Opening Create Trimmed Profile\n"))
        App.ActiveDocument.openTransaction("Update Trim")
        self.update_view_and_model()

    def reject(self):
        App.Console.PrintMessage(translate("frameforgemod", "Rejecting CreateProfile {}").format(self.mode) + "\n")

        if self.mode == "edition":
            self.fp.restoreContent(self.dump)

        elif self.mode == "creation":
            trimmedBody = self.fp.TrimmedBody

            App.ActiveDocument.removeObject(self.fp.Name)

            for tp in self._extra_objects:
                try:
                    App.ActiveDocument.removeObject(tp.Name)
                except Exception:
                    pass

            if trimmedBody:
                trimmedBody.ViewObject.Visibility = True

        App.ActiveDocument.commitTransaction()

        App.ActiveDocument.recompute()
        Gui.ActiveDocument.resetEdit()

        return True

    def apply(self):
        App.Console.PrintMessage(translate("frameforgemod", "Applying...\n"))
        # Same logic as accept() — process trimmed bodies so it actually works
        if self.mode == "creation" and len(self.trimmed_bodies) >= 1:
            boundaries = [b for b in self.fp.TrimmingBoundary]
            for i, (obj, sub) in enumerate(self.trimmed_bodies):
                if i == 0:
                    self.fp.TrimmedBody = obj
                else:
                    tp = make_trimmed_profile(trimmedBody=obj, trimmingBoundary=boundaries)
                    self._extra_objects.append(tp)
            if not self.fp.TrimmedBody:
                App.ActiveDocument.removeObject(self.fp.Name)
        App.ActiveDocument.commitTransaction()
        # self.fp.recompute()  # skip: App.ActiveDocument.recompute() handles all
        App.ActiveDocument.recompute()
        try:
            Gui.updateGui()
        except Exception:
            pass
        if hasattr(self, 'dump') and hasattr(self.fp, 'dumpContent'):
            self.dump = self.fp.dumpContent()
        App.ActiveDocument.openTransaction("Continue editing")
        self.trimmed_bodies = []
        self.form.bodies_list_widget.clear()
        self.form.boundaries_list_widget.clear()
        App.Console.PrintMessage(translate("frameforgemod", "Ready. Continue adding trims or click OK.\n"))

    def accept(self):
        App.Console.PrintMessage(translate("frameforgemod", "Accepting Create Trimmed Profile\n"))

        param = App.ParamGet("User parameter:BaseApp/Preferences/Frameforge_mod")
        param.SetString("Default Cut Type", self.fp.CutType)

        if self.mode == "creation" and len(self.trimmed_bodies) >= 1:
            boundaries = [b for b in self.fp.TrimmingBoundary]
            for i, (obj, sub) in enumerate(self.trimmed_bodies):
                if i == 0:
                    self.fp.TrimmedBody = obj
                else:
                    make_trimmed_profile(trimmedBody=obj, trimmingBoundary=boundaries)
            # Remove the empty template if it still has no body
            if not self.fp.TrimmedBody:
                App.ActiveDocument.removeObject(self.fp.Name)

        App.ActiveDocument.commitTransaction()
        App.ActiveDocument.recompute()
        Gui.ActiveDocument.resetEdit()

        return True


class TrimProfileCommand:
    def GetResources(self):
        return {
            "Pixmap": os.path.join(ICONPATH, "corner-end-trim.svg"),
            "MenuText": translate("frameforgemod", "Trim Profile"),
            "Accel": "M, T",
            "ToolTip": translate(
                "frameforgemod",
                "<html><head/><body><p><b>Trim a profile</b> \
                    <br><br> \
                    Select a profile to trim, then a face as the cutting boundary. \
                    </p></body></html>",
            ),
        }

    def IsActive(self):
        if App.ActiveDocument:
            if len(Gui.Selection.getSelection()) > 0:
                for sel in Gui.Selection.getSelectionEx():
                    if len(sel.SubElementNames) != 1:
                        return False
                    if not isinstance(sel.Object.getSubObject(sel.SubElementNames[0]), Part.Face):
                        return False
                return True
            else:
                return True
        return False

    def Activated(self):
        sel = Gui.Selection.getSelectionEx()
        App.ActiveDocument.openTransaction("Make Trimmed Profile")
        if len(sel) == 0:
            trimmed_profile = make_trimmed_profile()
            App.ActiveDocument.commitTransaction()
            panel = CreateTrimmedProfileTaskPanel(trimmed_profile, mode="creation")
            Gui.Control.showDialog(panel)
            return

        trimming_boundary = []
        for selectionObject in sel[1:]:
            bound = (selectionObject.Object, selectionObject.SubElementNames)
            trimming_boundary.append(bound)
        trimmed_profile = make_trimmed_profile(
            trimmedBody=sel[0].Object, trimmingBoundary=trimming_boundary
        )
        App.ActiveDocument.commitTransaction()
        App.ActiveDocument.recompute()


def make_trimmed_profile(trimmedBody=None, trimmingBoundary=None):
    doc = App.ActiveDocument

    if trimmedBody is None:
        name = "TrimmedProfile"
    else:
        n = getattr(trimmedBody, "SizeName", None)
        if not n:
            label = trimmedBody.Label
            n = label.split("_Profile_")[0] if "_Profile_" in label else label
        name = f"{n}_Tr"
    trimmed_profile = doc.addObject("Part::FeaturePython", name)

    if trimmedBody is not None and len(trimmedBody.Parents) > 0:
        trimmedBody.Parents[-1][0].addObject(trimmed_profile)

    TrimmedProfile(trimmed_profile)

    ViewProviderTrimmedProfile(trimmed_profile.ViewObject)
    trimmed_profile.TrimmedBody = trimmedBody
    trimmed_profile.TrimmingBoundary = trimmingBoundary

    trimmed_profile.TrimmedProfileType = "End Trim"
    trimmed_profile.CutType = "Simple fit"

    if trimmedBody is not None:
        try:
            trimmedBody.ViewObject.Visibility = False
        except Exception:
            pass

    return trimmed_profile


class TrimToolGroup:
    """Group: adjust ends + trim profile."""
    def GetCommands(self):
        return ("frameforgemod_AdjustEnds", "frameforgemod_TrimProfile")

    def GetDefaultCommand(self):
        return 0

    def GetResources(self):
        return {
            "Pixmap": os.path.join(ICONPATH, "end-extend.svg"),
            "MenuText": translate("frameforgemod", "Adjust Ends"),
            "ToolTip": translate("frameforgemod",
                                "Adjust profile end offsets or trim ends"),
        }

    def IsActive(self):
        return App.ActiveDocument is not None


Gui.addCommand("frameforgemod_TrimProfiles", TrimToolGroup())
Gui.addCommand("frameforgemod_TrimProfile", TrimProfileCommand())

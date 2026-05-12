import os

import FreeCAD as App
import FreeCADGui as Gui

from freecad.frameforgemod.ff_tools import ICONPATH, translate


ISOLATE_SKIP_DEFAULT = "Constraint,Joint,Revolute,Slider,Cylindrical,GroundedJoint,Plane,Origin"


def _get_skip_keywords():
    raw = App.ParamGet("User parameter:BaseApp/Preferences/Frameforge_mod/Isolate").GetString("SkipKeywords", ISOLATE_SKIP_DEFAULT)
    return tuple(k.strip() for k in raw.split(",") if k.strip())


class IsolateCommand:
    _isolated = False

    def GetResources(self):
        if IsolateCommand._isolated:
            return {
                "Pixmap": os.path.join(ICONPATH, "exit-isolate.svg"),
                "MenuText": translate("frameforgemod", "Exit Isolate"),
                "Accel": "M, I",
                "ToolTip": translate(
                    "frameforgemod",
                    "Restore visibility of all FrameForge objects",
                ),
            }
        else:
            return {
                "Pixmap": os.path.join(ICONPATH, "isolate.svg"),
                "MenuText": translate("frameforgemod", "Isolate Selected"),
                "Accel": "M, I",
                "ToolTip": translate(
                    "frameforgemod",
                    "Show only selected FrameForge objects, hide others",
                ),
            }

    def IsActive(self):
        if IsolateCommand._isolated:
            return bool(App.ActiveDocument)
        return bool(App.ActiveDocument) and bool(Gui.Selection.getSelection())

    def Activated(self):
        if IsolateCommand._isolated:
            self._exit_isolate()
        else:
            self._enter_isolate()

    def _iter_all(self):
        for doc in App.listDocuments().values():
            for obj in doc.Objects:
                yield obj

    def _enter_isolate(self):
        selected = Gui.Selection.getSelection()
        if not selected:
            return

        selected_names = {o.Name for o in selected}
        for sel_obj in selected:
            for p in sel_obj.Parents:
                selected_names.add(p[0].Name)

        for obj in self._iter_all():
            try:
                obj.ViewObject.Visibility = obj.Name in selected_names
            except AttributeError:
                pass

        IsolateCommand._isolated = True
        Gui.updateGui()

    def _exit_isolate(self):
        skip = _get_skip_keywords()
        for obj in self._iter_all():
            try:
                tid = getattr(obj, 'TypeId', '')
                label = getattr(obj, 'Label', '') or ''
                name = getattr(obj, 'Name', '') or ''
                if any(k in tid or k in label or k in name for k in skip):
                    continue
                obj.ViewObject.Visibility = True
            except Exception:
                pass

        IsolateCommand._isolated = False
        Gui.updateGui()


class IsolateSettingsCommand:
    def GetResources(self):
        return {
            "MenuText": translate("frameforgemod", "Isolate Settings"),
            "ToolTip": translate("frameforgemod", "Configure which object types to skip when exiting isolate"),
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        from PySide import QtGui

        dlg = QtGui.QDialog()
        dlg.setWindowTitle(translate("frameforgemod", "Isolate Skip Keywords"))
        layout = QtGui.QVBoxLayout(dlg)

        lbl = QtGui.QLabel(translate("frameforgemod",
            "Comma-separated keywords.\n"
            "Objects matching these (by TypeId, Label, or Name) are NOT shown\n"
            "when exiting isolate. Changes take effect immediately."))
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        edit = QtGui.QLineEdit()
        raw = App.ParamGet("User parameter:BaseApp/Preferences/Frameforge_mod/Isolate").GetString("SkipKeywords", ISOLATE_SKIP_DEFAULT)
        edit.setText(raw)
        layout.addWidget(edit)

        btn_box = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dlg.accept)
        btn_box.rejected.connect(dlg.reject)
        layout.addWidget(btn_box)

        if dlg.exec_() == QtGui.QDialog.Accepted:
            App.ParamGet("User parameter:BaseApp/Preferences/Frameforge_mod/Isolate").SetString("SkipKeywords", edit.text())


Gui.addCommand("frameforgemod_Isolate", IsolateCommand())
Gui.addCommand("frameforgemod_IsolateSettings", IsolateSettingsCommand())

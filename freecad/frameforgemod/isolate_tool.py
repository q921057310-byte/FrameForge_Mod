import os

import FreeCAD as App
import FreeCADGui as Gui

from freecad.frameforgemod._utils import (
    is_cut,
    is_endcap,
    is_extrudedcutout,
    is_fusion,
    is_group,
    is_gusset,
    is_holefeature,
    is_link,
    is_part,
    is_profile,
    is_tjointconnector,
    is_trimmedbody,
    is_whistleconnector,
)
from freecad.frameforgemod.ff_tools import ICONPATH, translate
from freecad.frameforgemod.preferences import get_isolate_skip_keywords


def _is_container(obj):
    return (
        is_fusion(obj)
        or is_cut(obj)
        or obj.TypeId == "App::Part"
        or obj.TypeId == "App::DocumentObjectGroup"
    )


def _is_frameforge_leaf(obj):
    return (
        is_profile(obj)
        or is_trimmedbody(obj)
        or is_extrudedcutout(obj)
        or is_endcap(obj)
        or is_gusset(obj)
        or is_whistleconnector(obj)
        or is_holefeature(obj)
        or is_tjointconnector(obj)
        or is_link(obj)
    )


def _is_frameforge_object(obj):
    return _is_container(obj) or _is_frameforge_leaf(obj)


def _build_parent_map(doc):
    parent_map = {}
    for obj in doc.Objects:
        if obj.TypeId == "Part::MultiFuse" and hasattr(obj, "Shapes"):
            for child in obj.Shapes:
                parent_map[child.Name] = obj.Name
        elif is_cut(obj) and hasattr(obj, "Base") and obj.Base is not None:
            parent_map[obj.Base.Name] = obj.Name
        elif obj.TypeId in ("App::Part", "App::DocumentObjectGroup") and hasattr(obj, "Group"):
            for child in obj.Group:
                parent_map[child.Name] = obj.Name
    return parent_map


def _walk_up_to_root(obj_name, parent_map, max_depth=20):
    chain = []
    current = obj_name
    depth = 0
    visited = set()
    while current in parent_map and depth < max_depth:
        if current in visited:
            break
        visited.add(current)
        parent = parent_map[current]
        chain.append(parent)
        current = parent
        depth += 1
    return chain


def _find_nearest_fusion(obj_name, parent_map):
    current = obj_name
    visited = set()
    while current in parent_map:
        if current in visited:
            break
        visited.add(current)
        parent = parent_map[current]
        if parent is not None:
            parent_obj = App.ActiveDocument.getObject(parent)
            if parent_obj is not None and (parent_obj.TypeId in ("Part::MultiFuse", "Part::Cut")):
                return parent
        current = parent
    return None


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

    def _enter_isolate(self):
        selected = Gui.Selection.getSelection()
        if not selected:
            return

        selected_names = {o.Name for o in selected}

        # Also show parent containers and linked objects
        for sel_obj in selected:
            for p in sel_obj.Parents:
                selected_names.add(p[0].Name)
            link_from = getattr(sel_obj, "LinkedObject", None)
            if link_from:
                selected_names.add(link_from.Name)
                for p in link_from.Parents:
                    selected_names.add(p[0].Name)

        # Hide everything not selected (across all documents)
        for doc in App.listDocuments().values():
            for obj in doc.Objects:
                try:
                    obj.ViewObject.Visibility = obj.Name in selected_names
                except AttributeError:
                    pass

        IsolateCommand._isolated = True
        Gui.updateGui()

    def _exit_isolate(self):
        _skip_keywords = get_isolate_skip_keywords()
        for doc in App.listDocuments().values():
            for obj in doc.Objects:
                try:
                    tid = getattr(obj, 'TypeId', '')
                    label = getattr(obj, 'Label', '') or ''
                    name = getattr(obj, 'Name', '') or ''
                    if any(k in tid or k in label or k in name for k in _skip_keywords):
                        continue
                    obj.ViewObject.Visibility = True
                except Exception:
                    pass

        IsolateCommand._isolated = False
        Gui.updateGui()


Gui.addCommand("frameforgemod_Isolate", IsolateCommand())


class IsolateSettingsCommand:
    def GetResources(self):
        return {
            "MenuText": "Isolate Settings",
            "ToolTip": "Configure which object types to skip when exiting isolate",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        from PySide import QtGui
        from freecad.frameforgemod.preferences import ISOLATE_SKIP_DEFAULT

        dlg = QtGui.QDialog()
        dlg.setWindowTitle("Isolate Skip Keywords")
        layout = QtGui.QVBoxLayout(dlg)

        lbl = QtGui.QLabel(
            "Comma-separated keywords.\n"
            "Objects matching these (by TypeId, Label, or Name) are NOT shown\n"
            "when exiting isolate. Changes take effect immediately."
        )
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


Gui.addCommand("frameforgemod_IsolateSettings", IsolateSettingsCommand())

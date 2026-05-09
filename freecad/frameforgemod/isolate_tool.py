import os

import FreeCAD as App
import FreeCADGui as Gui

from freecad.frameforgemod._utils import (
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


def _is_container(obj):
    return (
        obj.TypeId == "Part::MultiFuse"
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
            if parent_obj is not None and parent_obj.TypeId == "Part::MultiFuse":
                return parent
        current = parent
    return None


class IsolateCommand:
    _isolated = False
    _saved_state = {}

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
        doc = App.ActiveDocument
        selected = Gui.Selection.getSelection()
        if not selected:
            return

        all_ff = [o for o in doc.Objects if _is_frameforge_object(o)]
        parent_map = _build_parent_map(doc)

        for obj in all_ff:
            try:
                IsolateCommand._saved_state[obj.Name] = obj.ViewObject.Visibility
            except AttributeError:
                IsolateCommand._saved_state[obj.Name] = True

        keep_visible = set()
        for sel_obj in selected:
            fusion = _find_nearest_fusion(sel_obj.Name, parent_map)
            if fusion:
                keep_visible.add(fusion)
                for ancestor in _walk_up_to_root(fusion, parent_map):
                    keep_visible.add(ancestor)
            else:
                keep_visible.add(sel_obj.Name)
                for ancestor in _walk_up_to_root(sel_obj.Name, parent_map):
                    keep_visible.add(ancestor)

            if _is_container(sel_obj):
                for obj in all_ff:
                    ancestors = _walk_up_to_root(obj.Name, parent_map)
                    if sel_obj.Name in ancestors:
                        descendant_fusion = _find_nearest_fusion(obj.Name, parent_map)
                        if descendant_fusion:
                            keep_visible.add(descendant_fusion)
                        else:
                            keep_visible.add(obj.Name)

        for obj in all_ff:
            try:
                obj.ViewObject.Visibility = (obj.Name in keep_visible)
            except AttributeError:
                pass

        IsolateCommand._isolated = True
        Gui.updateGui()

    def _exit_isolate(self):
        doc = App.ActiveDocument
        for name, was_visible in IsolateCommand._saved_state.items():
            obj = doc.getObject(name)
            if obj is not None:
                try:
                    obj.ViewObject.Visibility = was_visible
                except AttributeError:
                    pass

        IsolateCommand._isolated = False
        IsolateCommand._saved_state = {}
        Gui.updateGui()


Gui.addCommand("frameforgemod_Isolate", IsolateCommand())

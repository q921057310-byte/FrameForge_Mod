# -*- coding: utf-8 -*-

import FreeCAD as App

_migrated = False


def _h(grp, key):
    """Safe Has() - works across FreeCAD versions."""
    try:
        return grp.Has(key)
    except Exception:
        return False


def _migrate_once():
    global _migrated
    if _migrated:
        return
    _migrated = True

    # Root-level parameters
    old_r = App.ParamGet("User parameter:BaseApp/Preferences/Frameforge")
    new_r = App.ParamGet("User parameter:BaseApp/Preferences/Frameforge_mod")
    for key, typ, dfl in [
        ("Allow Duplicating IDs", "bool", False),
        ("Group IDs", "bool", False),
        ("Include Count", "bool", False),
        ("Reset Numbering IDs", "bool", False),
        ("IDs numbering type", "int", 0),
        ("IDs numbering scheme", "int", 0),
        ("First Number ID", "int", 0),
        ("First Letter ID", "string", "A"),
        ("Full Parent Path", "bool", False),
        ("Include Links in BOM", "bool", False),
        ("Group BOM Items by Material/Size/Family", "bool", False),
        ("Generate Cut List", "bool", False),
        ("Stock Length", "float", 6000.0),
        ("Kerf", "float", 1.0),
    ]:
        if _h(new_r, key):
            continue
        v = None
        if typ == "bool":
            v = old_r.GetBool(key, dfl)
        elif typ == "int":
            v = old_r.GetInt(key, dfl)
        elif typ == "float":
            v = old_r.GetFloat(key, dfl)
        elif typ == "string":
            v = old_r.GetString(key, dfl)
        if v is not None and v != dfl:
            if typ == "bool":
                new_r.SetBool(key, v)
            elif typ == "int":
                new_r.SetInt(key, v)
            elif typ == "float":
                new_r.SetFloat(key, v)
            elif typ == "string":
                new_r.SetString(key, v)

    # Display sub-group
    old_d = App.ParamGet("User parameter:BaseApp/Preferences/Frameforge/Display")
    new_d = App.ParamGet("User parameter:BaseApp/Preferences/Frameforge_mod/Display")
    for key, typ, dfl in [
        ("LineWidth", "int", 2),
        ("PointSize", "float", 3.0),
        ("SphereScale", "float", 1.0),
        ("ShowHelpers", "bool", True),
        ("ShowEndpoints", "bool", True),
        ("ShowGuideLines", "bool", True),
        ("ShowLabels", "bool", True),
    ]:
        if _h(new_d, key):
            continue
        v = None
        if typ == "bool":
            v = old_d.GetBool(key, dfl)
        elif typ == "int":
            v = old_d.GetInt(key, dfl)
        elif typ == "float":
            v = old_d.GetFloat(key, dfl)
        if v is not None and v != dfl:
            if typ == "bool":
                new_d.SetBool(key, v)
            elif typ == "int":
                new_d.SetInt(key, v)
            elif typ == "float":
                new_d.SetFloat(key, v)

    # EndCap sub-group
    old_e = App.ParamGet("User parameter:BaseApp/Preferences/Frameforge/EndCap")
    new_e = App.ParamGet("User parameter:BaseApp/Preferences/Frameforge_mod/EndCap")
    for key, typ, dfl in [
        ("Thickness", "float", -1), ("Offset", "float", -1),
        ("PlugOffset", "float", -1), ("ChamferSize", "float", -1),
        ("FilletSize", "float", -1), ("HoleDiameter", "float", -1),
        ("HoleDepth", "float", -1),
        ("Reverse", "bool", False), ("ChamferEnabled", "bool", False),
        ("FilletEnabled", "bool", False), ("HoleEnabled", "bool", False),
        ("HoleThreaded", "bool", False),
        ("CapType", "int", -1),
        ("HoleThreadSpec", "string", ""),
    ]:
        if _h(new_e, key):
            continue
        if typ == "float":
            v = old_e.GetFloat(key, dfl)
            if v != dfl:
                new_e.SetFloat(key, v)
        elif typ == "bool":
            v = old_e.GetBool(key, dfl)
            if v != dfl:
                new_e.SetBool(key, v)
        elif typ == "int":
            v = old_e.GetInt(key, dfl)
            if v != dfl:
                new_e.SetInt(key, v)
        elif typ == "string":
            v = old_e.GetString(key, dfl)
            if v != dfl:
                new_e.SetString(key, v)


_migrate_once()


def get_line_width():
    return App.ParamGet("User parameter:BaseApp/Preferences/Frameforge_mod/Display").GetInt("LineWidth", 2)

def get_point_size():
    return App.ParamGet("User parameter:BaseApp/Preferences/Frameforge_mod/Display").GetFloat("PointSize", 3.0)

def get_sphere_scale():
    return App.ParamGet("User parameter:BaseApp/Preferences/Frameforge_mod/Display").GetFloat("SphereScale", 1.0)

def get_show_helpers():
    return App.ParamGet("User parameter:BaseApp/Preferences/Frameforge_mod/Display").GetBool("ShowHelpers", True)

def get_show_endpoints():
    return App.ParamGet("User parameter:BaseApp/Preferences/Frameforge_mod/Display").GetBool("ShowEndpoints", True)

def get_show_guides():
    return App.ParamGet("User parameter:BaseApp/Preferences/Frameforge_mod/Display").GetBool("ShowGuideLines", True)

def get_show_labels():
    return App.ParamGet("User parameter:BaseApp/Preferences/Frameforge_mod/Display").GetBool("ShowLabels", True)


profile_line_width = get_line_width
profile_point_size = get_point_size
profile_sphere_scale = get_sphere_scale
profile_show_helpers = get_show_helpers
profile_show_endpoints = get_show_endpoints
profile_show_guide_lines = get_show_guides
profile_show_labels = get_show_labels

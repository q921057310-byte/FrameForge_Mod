import sys

import freecad.frameforgemod as _ffm

sys.modules["freecad.frameforge2"] = _ffm

_submodules = [
    "_utils",
    "best_fit",
    "create_aluminum_profile",
    "create_bom",
    "create_bom_tool",
    "create_custom_profiles_tool",
    "create_edit_balloons_tool",
    "create_end_cap_tool",
    "create_end_miter_tool",
    "create_extruded_cutout_tool",
    "create_gusset_tool",
    "create_link",
    "create_offset_plane_tool",
    "create_pattern_fill_tool",
    "create_profiles_tool",
    "create_trimmed_profiles_tool",
    "create_vent_tool",
    "create_connector_hole_tool",
    "create_whistle_connector_tool",
    "edit_profile_tool",
    "end_cap",
    "extruded_cutout",
    "extrusions",
    "ff_tools",
    "frameforgemod_exceptions",
    "gusset",
    "parametric_line",
    "populate_ids",
    "populate_ids_tool",
    "profile",
    "trimmed_profile",
    "utilities",
    "version",
    "connector_hole",
    "preferences",
    "whistle_connector",
]

for sub in _submodules:
    try:
        mod = __import__(f"freecad.frameforgemod.{sub}", fromlist=[sub])
        sys.modules[f"freecad.frameforge2.{sub}"] = mod
    except ImportError:
        pass

try:
    import freecad.frameforgemod.frameforgemod_exceptions as _ffe
    sys.modules["freecad.frameforge2.frameforge_exceptions"] = _ffe
except ImportError:
    pass

try:
    import freecad.frameforgemod.dynamicdata as _dd
    sys.modules["freecad.frameforge2.dynamicdata"] = _dd
    import freecad.frameforgemod.dynamicdata.DynamicDataCmd as _ddc
    sys.modules["freecad.frameforge2.dynamicdata.DynamicDataCmd"] = _ddc
    import freecad.frameforgemod.dynamicdata.PropertyTableEditor as _ddp
    sys.modules["freecad.frameforge2.dynamicdata.PropertyTableEditor"] = _ddp
except ImportError:
    pass

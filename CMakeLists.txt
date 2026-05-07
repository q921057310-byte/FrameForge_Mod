set(Namespace_SRCS
        freecad/frameforge2/resources/icons/corner.svg
        freecad/frameforge2/resources/icons/splitcurve.svg
        freecad/frameforge2/resources/icons/warehouse_profiles.svg
        freecad/frameforge2/resources/icons/warehouse_custom_profiles.svg
        freecad/frameforge2/resources/icons/trim_extend.svg
        freecad/frameforge2/resources/icons/metalwb.svg
        freecad/frameforge2/resources/icons/line.svg
        freecad/frameforge2/resources/icons/corner-end-miter.svg
        freecad/frameforge2/resources/icons/discretize.svg
        freecad/frameforge2/resources/icons/joincurve.svg
        freecad/frameforge2/resources/icons/overlap.svg
        freecad/frameforge2/resources/icons/box.svg
        freecad/frameforge2/resources/icons/bom.svg
        freecad/frameforge2/resources/icons/parts_list.svg
        freecad/frameforge2/resources/icons/corner-coped-type.svg
        freecad/frameforge2/resources/icons/corner-simple-type.svg
        freecad/frameforge2/resources/icons/corner-end-trim.svg
        freecad/frameforge2/resources/icons/list-remove.svg
        freecad/frameforge2/resources/icons/extendcurve.svg
        freecad/frameforge2/resources/icons/list-add.svg
        freecad/frameforge2/resources/icons/extrude-cutout.svg

        freecad/frameforge2/resources/images/profiles/Metal/HEB_Fillet.png
        freecad/frameforge2/resources/images/profiles/Metal/Square_Hollow.png
        freecad/frameforge2/resources/images/profiles/Metal/HEM_Fillet.png
        freecad/frameforge2/resources/images/profiles/Metal/UPN_Fillet.png
        freecad/frameforge2/resources/images/profiles/Metal/Round_Bar.png
        freecad/frameforge2/resources/images/profiles/Metal/UPE.png
        freecad/frameforge2/resources/images/profiles/Metal/HEA.png
        freecad/frameforge2/resources/images/profiles/Metal/HEA_Fillet.png
        freecad/frameforge2/resources/images/profiles/Metal/HEB.png
        freecad/frameforge2/resources/images/profiles/Metal/IPN_Fillet.png
        freecad/frameforge2/resources/images/profiles/Metal/IPN.png
        freecad/frameforge2/resources/images/profiles/Metal/UPN.png
        freecad/frameforge2/resources/images/profiles/Metal/Square_Fillet.png
        freecad/frameforge2/resources/images/profiles/Metal/Unequal_Leg_Angles.png
        freecad/frameforge2/resources/images/profiles/Metal/Flat_Sections.png
        freecad/frameforge2/resources/images/profiles/Metal/IPE.png
        freecad/frameforge2/resources/images/profiles/Metal/UPE_Fillet.png
        freecad/frameforge2/resources/images/profiles/Metal/Unequal_Leg_Angles_Fillet.png
        freecad/frameforge2/resources/images/profiles/Metal/Rectangular_Hollow_Fillet.png
        freecad/frameforge2/resources/images/profiles/Metal/HEM.png
        freecad/frameforge2/resources/images/profiles/Metal/Square_Hollow_Fillet.png
        freecad/frameforge2/resources/images/profiles/Metal/Equal_Leg_Angles_Fillet.png
        freecad/frameforge2/resources/images/profiles/Metal/Equal_Leg_Angles.png
        freecad/frameforge2/resources/images/profiles/Metal/Rectangular_Hollow.png
        freecad/frameforge2/resources/images/profiles/Metal/IPE_Fillet.png
        freecad/frameforge2/resources/images/profiles/Metal/Pipe.png
        freecad/frameforge2/resources/images/profiles/Metal/Square.png
        freecad/frameforge2/resources/images/profiles/Warehouse.png

        freecad/frameforge2/resources/ui/create_trimmed_profiles.ui
        freecad/frameforge2/resources/ui/create_profiles.ui
        freecad/frameforge2/resources/ui/create_custom_profiles.ui

        freecad/frameforge2/resources/profiles/metal.json

        freecad/frameforge2/version.py
        freecad/frameforge2/ff_tools.py
        freecad/frameforge2/profile.py
        freecad/frameforge2/_utils.py
        freecad/frameforge2/parametric_line.py
        freecad/frameforge2/trimmed_profile.py
        freecad/frameforge2/utilities.py
        freecad/frameforge2/extrusions.py
        freecad/frameforge2/frameforge_exceptions.py
        freecad/frameforge2/init_gui.py
        freecad/frameforge2/end_cap.py
        freecad/frameforge2/gusset.py
        freecad/frameforge2/whistle_connector.py
        freecad/frameforge2/create_profiles_tool.py
        freecad/frameforge2/create_custom_profiles_tool.py
        freecad/frameforge2/create_trimmed_profiles_tool.py
        freecad/frameforge2/create_end_miter_tool.py
        freecad/frameforge2/create_end_cap_tool.py
        freecad/frameforge2/create_gusset_tool.py
        freecad/frameforge2/create_whistle_connector_tool.py
        freecad/frameforge2/edit_profile_tool.py
        freecad/frameforge2/extruded_cutout.py
        freecad/frameforge2/create_extruded_cutout_tool.py
        freecad/frameforge2/create_link.py
        freecad/frameforge2/create_bom.py
        freecad/frameforge2/create_bom_tool.py
        freecad/frameforge2/best_fit.py
        freecad/frameforge2/populate_ids.py
        freecad/frameforge2/populate_ids_tool.py
        freecad/frameforge2/create_edit_balloons_tool.py
        freecad/frameforge2/colorize.py
)

SOURCE_GROUP("" FILES ${Namespace_SRCS})

ADD_CUSTOM_TARGET(SEARCHBAR ALL
        SOURCES ${Namespace_SRCS}
)

fc_copy_sources(SEARCHBAR "${CMAKE_BINARY_DIR}/Mod/FrameForge2" ${Namespace_SRCS})

INSTALL(
    FILES
        ${Namespace_SRCS}
    DESTINATION
        Mod/SearchBar
)

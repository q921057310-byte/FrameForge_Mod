import os

import FreeCAD as App
import FreeCADGui as Gui

import freecad.frameforgemod._bridge

from freecad.frameforgemod.ff_tools import TRANSLATIONSPATH, translate

# Add translations path
Gui.addLanguagePath(TRANSLATIONSPATH)
Gui.updateLocale()


class FrameForgemod(Gui.Workbench):
    """
    class which gets initiated at startup of the gui
    """

    MenuText = "frameforgemod"
    ToolTip = "Create Profiles, Miters, Cuts from Sketchs and Edges"
    Icon = """
        /* XPM */
        static char * metalwb_xpm[] = {
        "16 16 139 2",
        "  	c None",
        ". 	c #FFF306",
        "+ 	c #FFF309",
        "@ 	c #FFF40C",
        "# 	c #FFF40F",
        "$ 	c #FFF40E",
        "% 	c #FFF40B",
        "& 	c #FFF411",
        "* 	c #FFF415",
        "= 	c #FFF518",
        "- 	c #FFF417",
        "; 	c #FFF413",
        "> 	c #FFF308",
        ", 	c #FFF30A",
        "' 	c #FFF520",
        ") 	c #FDF32C",
        "! 	c #FFF531",
        "~ 	c #FFF526",
        "{ 	c #FFF51B",
        "] 	c #F9EF14",
        "^ 	c #F4E90D",
        "/ 	c #E6DB05",
        "( 	c #FFF522",
        "_ 	c #FAF145",
        ": 	c #D7D151",
        "< 	c #E4DD5D",
        "[ 	c #D3CC41",
        "} 	c #CCC638",
        "| 	c #4C6686",
        "1 	c #46668D",
        "2 	c #44648D",
        "3 	c #416189",
        "4 	c #FFF51A",
        "5 	c #FFF639",
        "6 	c #C5BF4F",
        "7 	c #BBB936",
        "8 	c #D0CF11",
        "9 	c #918D32",
        "0 	c #435D78",
        "a 	c #4A76AC",
        "b 	c #4974A9",
        "c 	c #3F5B7C",
        "d 	c #3E4B55",
        "e 	c #6C7468",
        "f 	c #8B8E60",
        "g 	c #A4A35C",
        "h 	c #ABAA5E",
        "i 	c #A19E49",
        "j 	c #E6E600",
        "k 	c #FFFF00",
        "l 	c #C2C223",
        "m 	c #4770A0",
        "n 	c #4975A9",
        "o 	c #3E5A7B",
        "p 	c #436EA2",
        "q 	c #3C526D",
        "r 	c #4973A6",
        "s 	c #466892",
        "t 	c #B6B505",
        "u 	c #E7E700",
        "v 	c #8D9255",
        "w 	c #436389",
        "x 	c #3E597A",
        "y 	c #40699E",
        "z 	c #436EA6",
        "A 	c #37434C",
        "B 	c #416187",
        "C 	c #42638A",
        "D 	c #426288",
        "E 	c #3A4C5F",
        "F 	c #466385",
        "G 	c #556B7F",
        "H 	c #486280",
        "I 	c #4975AA",
        "J 	c #3E5979",
        "K 	c #3C659B",
        "L 	c #3E69A2",
        "M 	c #436FA6",
        "N 	c #4773AA",
        "O 	c #4773A9",
        "P 	c #4672A9",
        "Q 	c #4571A8",
        "R 	c #4570A6",
        "S 	c #3F5C7E",
        "T 	c #4871A3",
        "U 	c #4A75AA",
        "V 	c #3E5978",
        "W 	c #396197",
        "X 	c #39649D",
        "Y 	c #416593",
        "Z 	c #3F5F87",
        "` 	c #406BA3",
        " .	c #3F6BA3",
        "..	c #3E6AA2",
        "+.	c #3E69A1",
        "@.	c #374C65",
        "#.	c #3F5A78",
        "$.	c #416083",
        "%.	c #3D5775",
        "&.	c #365D93",
        "*.	c #355F99",
        "=.	c #3E6495",
        "-.	c #353E45",
        ";.	c #3D5D85",
        ">.	c #38639C",
        ",.	c #37629B",
        "'.	c #36619B",
        ").	c #3F5F84",
        "!.	c #4874AA",
        "~.	c #4672A8",
        "{.	c #3B5C88",
        "].	c #305A95",
        "^.	c #3C6396",
        "/.	c #36434E",
        "(.	c #3B5A83",
        "_.	c #315C96",
        ":.	c #305B95",
        "<.	c #2F5994",
        "[.	c #3D5D82",
        "}.	c #416CA4",
        "|.	c #386096",
        "1.	c #374658",
        "2.	c #374962",
        "3.	c #3D597D",
        "4.	c #3E5B7F",
        "5.	c #3A659E",
        "6.	c #345D94",
        "7.	c #37495E",
        "8.	c #3C5A80",
        "9.	c #325C97",
        "0.	c #315B96",
        "a.	c #2F5A95",
        "b.	c #3D5E88",
        "c.	c #374C66",
        "d.	c #394F6A",
        "e.	c #3A5A85",
        "f.	c #395984",
        "g.	c #3B5B86",
        "h.	c #36434F",
        "                . . .           ",
        "            + @ # # $ % .       ",
        "          % & * = = - ; $ >     ",
        "        , & = ' ) ! ~ { ] ^ /   ",
        "      . $ - ( _ : < [ } | 1 2 3 ",
        "      > & 4 5 6 7 8 9 0 a a b c ",
        "    d e f g h i j k l m a n o p ",
        "  q r a a a a s t u v w n x y z ",
        "A B C C C C D E F G H I J K L M ",
        "3 N O P Q R S T r U n V W X L Y ",
        "Z `  ...+.@.#.$.$.$.%.&.*.X =.-.",
        ";.>.>.,.'.).!.O ~.P {.].*.^./.  ",
        "(._.:.].<.[.}. ...` {.].|.1.    ",
        "2.3.3.3.3.4.X >.,.5.{.6.7.      ",
        "          8.9.0.a.*.b.c.        ",
        "          d.e.f.f.g.h.          "};
    """

    toolbox_drawing = ["Sketcher_NewSketch", "Part_Box", "frameforgemod_ParametricLine", "PartDesign_SubShapeBinder"]

    toolbox_frameforge = [
        "frameforgemod_AluminumProfileLibrary",
        "frameforgemod_TrimProfiles",
        "frameforgemod_AdjustEnds",
        "frameforgemod_EndMiter",
        "frameforgemod_AddExtrudeCutout",
        "frameforgemod_EndCap",
        "frameforgemod_Gusset",
        "frameforgemod_ConnectorGroup",
        "frameforgemod_HoleFeature",
    ]

    toolbox_group = ["Std_Group", "Std_Part"]

    toolbox_part = ["frameforgemod_Link", "Part_Fuse", "Part_Cut", "PartDesign_Body"]

    toolbox_output = [
        "frameforgemod_PopulateIDs",
        "frameforgemod_ResetIDs",
        "frameforgemod_CreateBalloons",
        "frameforgemod_RefreshBalloons",
        "frameforgemod_CreateBOM",
    ]

    toolbox_dynamicdata = [
        "DynamicData2CreateObject",
        "DynamicData2AddProperty",
        "DynamicData2CopyProperty",
        "DynamicData2CreateConfiguration",
    ]

    toolbox_other = ["frameforgemod_AddVent", "frameforgemod_PatternFill", "frameforgemod_OffsetPlane"]

    toolbox_utilities = [
        "frameforgemod_RecomputeFrameForgeObjects",
        "frameforgemod_ExportTechDraw",
        "frameforgemod_Isolate",
    ]

    def GetClassName(self):
        return "Gui::PythonWorkbench"

    def Initialize(self):
        """
        This function is called at the first activation of the workbench.
        here is the place to import all the commands
        """
        try:
            import SketcherGui
        except Exception:
            pass
        try:
            import PartDesignGui
        except Exception:
            pass

        from freecad.frameforgemod.ff_tools import translate

        import importlib
        for _m in [
            "freecad.frameforgemod.create_aluminum_profile",
            "freecad.frameforgemod.create_bom_tool",
            "freecad.frameforgemod.create_custom_profiles_tool",
            "freecad.frameforgemod.create_edit_balloons_tool",
            "freecad.frameforgemod.create_end_cap_tool",
            "freecad.frameforgemod.create_end_miter_tool",
            "freecad.frameforgemod.create_extruded_cutout_tool",
            "freecad.frameforgemod.create_gusset_tool",
            "freecad.frameforgemod.create_link",
            "freecad.frameforgemod.create_offset_plane_tool",
            "freecad.frameforgemod.create_pattern_fill_tool",
            "freecad.frameforgemod.create_profiles_tool",
            "freecad.frameforgemod.create_trimmed_profiles_tool",
            "freecad.frameforgemod.create_vent_tool",
            "freecad.frameforgemod.create_connector_hole_tool",
            "freecad.frameforgemod.create_whistle_connector_tool",
            "freecad.frameforgemod.edit_profile_tool",
            "freecad.frameforgemod.isolate_tool",
            "freecad.frameforgemod.parametric_line",
            "freecad.frameforgemod.populate_ids_tool",
            "freecad.frameforgemod.utilities",
            "freecad.frameforgemod.adjust_profile_end_tool",
        ]:
            importlib.import_module(_m)
        importlib.import_module("freecad.frameforgemod.dynamicdata.DynamicDataCmd")

        App.Console.PrintMessage(translate("frameforgemod", "Switching to frameforge") + "\n")

        self.appendToolbar(translate("frameforgemod", "Drawing Primitives"), self.toolbox_drawing)
        self.appendMenu(translate("frameforgemod", "Drawing Primitives"), self.toolbox_drawing)

        self.appendToolbar(translate("frameforgemod", "Frameforge"), self.toolbox_frameforge)
        self.appendMenu(translate("frameforgemod", "Frameforge"), self.toolbox_frameforge)

        self.appendToolbar(translate("frameforgemod", "Profiles Group"), self.toolbox_group)
        self.appendMenu(translate("frameforgemod", "Profiles Group"), self.toolbox_group)

        self.appendToolbar(translate("frameforgemod", "Part Primitives"), self.toolbox_part)
        self.appendMenu(translate("frameforgemod", "Part Primitives"), self.toolbox_part)

        self.appendToolbar(translate("frameforgemod", "Frameforge output"), self.toolbox_output)
        self.appendMenu(translate("frameforgemod", "Frameforge output"), self.toolbox_output)

        self.appendToolbar(translate("frameforgemod", "Dynamic Data"), self.toolbox_dynamicdata)
        self.appendMenu(translate("frameforgemod", "Dynamic Data"), self.toolbox_dynamicdata)

        self.appendToolbar(translate("frameforgemod", "Frameforge utilities"), self.toolbox_utilities)
        self.appendMenu(translate("frameforgemod", "Frameforge utilities"), self.toolbox_utilities)

        self.appendToolbar(translate("frameforgemod", "Other Tools"), self.toolbox_other)
        self.appendMenu(translate("frameforgemod", "Other Tools"), self.toolbox_other)

    def Activated(self):
        """
        code which should be computed when a user switch to this workbench
        """
        from freecad.frameforgemod.ff_tools import translate

        App.Console.PrintMessage(translate("frameforgemod", "Workbench frameforge activated.") + "\n")

    def Deactivated(self):
        """
        code which should be computed when this workbench is deactivated
        """
        from freecad.frameforgemod.ff_tools import translate

        App.Console.PrintMessage(translate("frameforgemod", "Workbench frameforge de-activated.") + "\n")


Gui.addWorkbench(FrameForgemod())

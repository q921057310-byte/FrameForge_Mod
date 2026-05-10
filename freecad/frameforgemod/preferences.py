# -*- coding: utf-8 -*-

import os
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

from freecad.frameforgemod.ff_tools import UIPATH, translate


def _params():
    return App.ParamGet("User parameter:BaseApp/Preferences/Frameforge/Display")


def get_line_width():
    return _params().GetInt("LineWidth", 2)

def get_point_size():
    return _params().GetFloat("PointSize", 3.0)

def get_sphere_scale():
    return _params().GetFloat("SphereScale", 1.0)

def get_show_helpers():
    return _params().GetBool("ShowHelpers", True)

def get_show_endpoints():
    return _params().GetBool("ShowEndpoints", True)

def get_show_guides():
    return _params().GetBool("ShowGuideLines", True)

def get_show_labels():
    return _params().GetBool("ShowLabels", True)


# Keep old names for backward compat in profile.py
profile_line_width = get_line_width
profile_point_size = get_point_size
profile_sphere_scale = get_sphere_scale
profile_show_helpers = get_show_helpers
profile_show_endpoints = get_show_endpoints
profile_show_guide_lines = get_show_guides
profile_show_labels = get_show_labels

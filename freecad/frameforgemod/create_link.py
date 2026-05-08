import os

import AttachmentEditor.TaskAttachmentEditor as TaskAttachmentEditor
import FreeCAD as App
import FreeCADGui as Gui

from freecad.frameforgemod._utils import getRootObject
from freecad.frameforgemod.ff_tools import ICONPATH, translate
from freecad.frameforgemod.version import __version__ as ff_version


def makeLink(source):
    doc = App.ActiveDocument

    link = doc.addObject("App::Link", source.Label + "_Link")
    link.LinkedObject = source

    link.addExtension("Part::AttachExtensionPython")
    link.MapMode = "Deactivated"

    link.addProperty(
        "App::PropertyString",
        "FrameforgeVersion",
        "Frameforge",
        "Frameforge Version used to create the profile",
    ).FrameforgeVersion = ff_version

    link.addProperty(
        "App::PropertyString",
        "PID",
        "Frameforge",
        "Profile ID",
    ).PID = ""

    doc.recompute()
    return link


class LinkCommand:
    def GetResources(self):
        return {
            "Pixmap": os.path.join(ICONPATH, "link.svg"),
            "MenuText": translate("frameforgemod", "Attached Link"),
            "ToolTip": translate("frameforgemod", "Create a link with Attachment"),
        }
    
    def IsActive(self):
        return bool(App.ActiveDocument) and bool(Gui.Selection.getSelection())

    def Activated(self):
        sel = Gui.Selection.getSelection()
        if not sel:
            return

        App.ActiveDocument.openTransaction("Create Links")
        roots = set()
        for obj in sel:
            roots.add(getRootObject(obj))

        for root in roots:
            link = makeLink(root)
            Gui.Control.showDialog(TaskAttachmentEditor.AttachmentEditorTaskPanel(link))
        App.ActiveDocument.commitTransaction()


Gui.addCommand("frameforgemod_Link", LinkCommand())

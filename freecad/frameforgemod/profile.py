import math

import FreeCAD as App
import FreeCADGui as Gui
import Part
from pivy import coin

from freecad.frameforgemod._utils import (
    get_readable_cutting_angles,
    length_along_normal,
    normalize_anchor,
)
from freecad.frameforgemod.extrusions import (
    make_tslot_face,
    make_vslot_face,
    make_profile_face,
    make_yiheda_vslot,
    make_aoh_vslot,
    make_40series_vslot,
    tslot20x20,
    tslot20x20_one_slot,
    tslot20x20_three_slot,
    tslot20x20_two_slot,
    tslot20x20_two_slot_opp,
    vslot20x20,
    vslot20x40,
    vslot20x60,
    vslot20x80,
)
from freecad.frameforgemod.frameforgemod_exceptions import FrameForgemodException
from freecad.frameforgemod.version import __version__ as ff_version

# Anchor enumerations for path alignment (PropertyEnumeration; index 0,1,2 used in formulas)
ANCHOR_X = ("Left", "Center", "Right")
ANCHOR_Y = ("Bottom", "Center", "Top")

FLANGE_ANGLES = {
    "UPE": 4.57,
    "UPN": 4.57,
    "IPE": 8,
    "HEA": 8,
    "HEB": 8,
    "HEM": 8,
    "IPN": 8,
}

MAX_BEVEL_ANGLE = 60

# Global variable for a 3D float vector (used in Profile class)
vec = App.Base.Vector


class Profile:
    def __init__(
        self,
        obj,
        init_w,
        init_h,
        init_mt,
        init_ft,
        init_r1,
        init_r2,
        init_len,
        init_wg,
        init_unit_price,
        init_mf,
        init_anchor_x,
        init_anchor_y,
        material,
        fam,
        size_name,
        bevels_combined,
        link_sub=None,
        custom_profile=None,
        init_mirror_h=False,
        init_mirror_v=False,
        init_rotation=0.0,
        init_offset_a=0.0,
        init_offset_b=0.0,
    ):
        """
        Constructor. Add properties to FreeCAD Profile object. Profile object have 11 nominal properties associated
        with initialization value 'init_w' to 'init_anchor_y' : ProfileHeight, ProfileWidth, [...] AnchorY (0,1,2). Depending
        on 'bevels_combined' parameters, there is 4 others properties for bevels : BevelACutY, etc. Depending on
        'fam' parameter, there is properties specific to profile family.
        """

        self.Type = "Profile"

        obj.addProperty(
            "App::PropertyString",
            "PID",
            "Profile",
            "Profile ID",
        ).PID = ""

        obj.addProperty(
            "App::PropertyString",
            "FrameforgeVersion",
            "Profile",
            "Frameforge Version used to create the profile",
        ).FrameforgeVersion = ff_version

        obj.addProperty(
            "App::PropertyString",
            "Material",
            "Profile",
            "",
        ).Material = material
        obj.addProperty(
            "App::PropertyString",
            "Family",
            "Profile",
            "",
        ).Family = fam

        obj.addProperty("App::PropertyLink", "CustomProfile", "Profile", "Target profile").CustomProfile = None

        obj.addProperty(
            "App::PropertyString",
            "SizeName",
            "Profile",
            "",
        ).SizeName = size_name

        obj.addProperty(
            "App::PropertyFloat",
            "ProfileHeight",
            "Profile",
            "",
        ).ProfileHeight = init_h
        obj.addProperty("App::PropertyFloat", "ProfileWidth", "Profile", "").ProfileWidth = init_w
        obj.addProperty("App::PropertyFloat", "ProfileLength", "Profile", "").ProfileLength = init_len  # should it be ?

        obj.addProperty(
            "App::PropertyFloat", "Thickness", "Profile", "Thickness of all the profile or the web"
        ).Thickness = init_mt
        obj.addProperty(
            "App::PropertyFloat", "ThicknessFlange", "Profile", "Thickness of the flanges"
        ).ThicknessFlange = init_ft

        obj.addProperty("App::PropertyFloat", "RadiusLarge", "Profile", "Large radius").RadiusLarge = init_r1
        obj.addProperty("App::PropertyFloat", "RadiusSmall", "Profile", "Small radius").RadiusSmall = init_r2
        obj.addProperty(
            "App::PropertyBool", "MakeFillet", "Profile", "Whether to draw the fillets or not"
        ).MakeFillet = init_mf

        if not bevels_combined:
            obj.addProperty(
                "App::PropertyFloat", "BevelACutY", "Profile", "Bevel on First axle at the start of the profile"
            ).BevelACutY = 0
            obj.addProperty(
                "App::PropertyFloat",
                "BevelACutX",
                "Profile",
                "Rotate the cut on Second axle at the start of the profile",
            ).BevelACutX = 0
            obj.addProperty(
                "App::PropertyFloat", "BevelBCutY", "Profile", "Bevel on First axle at the end of the profile"
            ).BevelBCutY = 0
            obj.addProperty(
                "App::PropertyFloat",
                "BevelBCutX",
                "Profile",
                "Rotate the cut on Second axle at the end of the profile",
            ).BevelBCutX = 0
        if bevels_combined:
            # TODO NOT USED
            obj.addProperty(
                "App::PropertyFloat", "BevelStartCut", "Profile", "Bevel at the start of the profile"
            ).BevelStartCut = 0
            obj.addProperty(
                "App::PropertyFloat", "BevelStartRotate", "Profile", "Rotate the second cut on Profile axle"
            ).BevelStartRotate = 0
            obj.addProperty(
                "App::PropertyFloat", "BevelEndCut", "Profile", "Bevel on First axle at the end of the profile"
            ).BevelEndCut = 0
            obj.addProperty(
                "App::PropertyFloat", "BevelEndRotate", "Profile", "Rotate the second cut on Profile axle"
            ).BevelEndRotate = 0

        obj.addProperty("App::PropertyFloat", "OffsetA", "Base", "Parameter for structure").OffsetA = init_offset_a

        obj.addProperty("App::PropertyFloat", "OffsetB", "Base", "Parameter for structure").OffsetB = init_offset_b

        # Overlap corner config (hidden, used by Aluminum Profile Library for dynamic updates)
        obj.addProperty("App::PropertyFloat", "OverlapASign", "Overlap", "Overlap sign at A-end: -1 cut, +1 extend, 0 off").OverlapASign = 0.0
        obj.setEditorMode("OverlapASign", 2)
        obj.addProperty("App::PropertyVector", "OverlapADir", "Overlap", "Direction to neighbor at A-end").OverlapADir = App.Vector(0, 0, 0)
        obj.setEditorMode("OverlapADir", 2)
        obj.addProperty("App::PropertyFloat", "OverlapAGap", "Overlap", "Gap at A-end").OverlapAGap = 0.0
        obj.setEditorMode("OverlapAGap", 2)
        obj.addProperty("App::PropertyFloat", "OverlapBSign", "Overlap", "Overlap sign at B-end: -1 cut, +1 extend, 0 off").OverlapBSign = 0.0
        obj.setEditorMode("OverlapBSign", 2)
        obj.addProperty("App::PropertyVector", "OverlapBDir", "Overlap", "Direction to neighbor at B-end").OverlapBDir = App.Vector(0, 0, 0)
        obj.setEditorMode("OverlapBDir", 2)
        obj.addProperty("App::PropertyFloat", "OverlapBGap", "Overlap", "Gap at B-end").OverlapBGap = 0.0
        obj.setEditorMode("OverlapBGap", 2)

        obj.addProperty("App::PropertyBool", "PreExtend", "Base", "Extend profile at both ends by max(width, height)").PreExtend = bool(init_offset_a > 0.0 or init_offset_b > 0.0)

        obj.addProperty("App::PropertyFloat", "LinearWeight", "Base", "Linear weight in kg/m").LinearWeight = init_wg
        obj.addProperty("App::PropertyFloat", "ApproxWeight", "Base", "Approximate weight in Kilogram").ApproxWeight = (
            obj.LinearWeight * init_len / 1000
        )
        obj.setEditorMode("ApproxWeight", 1)  # user doesn't change !

        obj.addProperty("App::PropertyFloat", "UnitPrice", "Base", "Approximate linear price").UnitPrice = (
            init_unit_price
        )
        obj.addProperty("App::PropertyFloat", "Price", "Base", "Profile Price").Price = (
            init_unit_price * init_len / 1000
        )
        obj.setEditorMode("Price", 1)  # user doesn't change !

        obj.addProperty("App::PropertyEnumeration", "AnchorX", "Profile", "Path alignment (horizontal)").AnchorX = (
            ANCHOR_X
        )
        obj.AnchorX = ANCHOR_X[normalize_anchor(init_anchor_x)]
        obj.addProperty("App::PropertyEnumeration", "AnchorY", "Profile", "Path alignment (vertical)").AnchorY = (
            ANCHOR_Y
        )
        obj.AnchorY = ANCHOR_Y[normalize_anchor(init_anchor_y)]
        if hasattr(obj, "CenteredOnWidth") or hasattr(obj, "CenteredOnHeight"):
            obj.AnchorX = "Center" if getattr(obj, "CenteredOnWidth", False) else "Left"
            obj.AnchorY = "Center" if getattr(obj, "CenteredOnHeight", False) else "Bottom"

        obj.addProperty(
            "App::PropertyBool", "MirrorH", "Profile", "Mirror cross-section horizontally (flip X)"
        ).MirrorH = bool(init_mirror_h)
        obj.addProperty(
            "App::PropertyBool", "MirrorV", "Profile", "Mirror cross-section vertically (flip Y)"
        ).MirrorV = bool(init_mirror_v)

        obj.addProperty(
            "App::PropertyFloat", "RotationAngle", "Profile", "Rotation of cross-section around path axis (degrees)"
        ).RotationAngle = float(init_rotation)
        # Apply rotation via AttachmentOffset (Angle in degrees)
        obj.setExpression(".AttachmentOffset.Rotation.Angle", "RotationAngle")

        if link_sub:
            obj.addProperty("App::PropertyLinkSub", "Target", "Base", "Target face").Target = link_sub

        if custom_profile:
            obj.CustomProfile = custom_profile
            obj.Family = "Custom Profile"

            obj.ProfileWidth = custom_profile.Shape.BoundBox.XLength
            obj.ProfileHeight = custom_profile.Shape.BoundBox.YLength

        # structure
        obj.addProperty("App::PropertyLength", "Width", "Structure", "Parameter for structure").Width = obj.ProfileWidth
        obj.addProperty("App::PropertyLength", "Height", "Structure", "Parameter for structure").Height = (
            obj.ProfileHeight
        )
        obj.addProperty(
            "App::PropertyLength",
            "Length",
            "Structure",
            "Parameter for structure",
        ).Length = obj.ProfileLength
        obj.addProperty("App::PropertyBool", "Cutout", "Structure", "Has Cutout").Cutout = False

        obj.setEditorMode("Width", 1)  # user doesn't change !
        obj.setEditorMode("Height", 1)
        obj.setEditorMode("Length", 1)
        obj.setEditorMode("Cutout", 1)

        obj.addProperty(
            "App::PropertyString",
            "CuttingAngleA",
            "Structure",
            "Cutting Angle A",
        )
        obj.setEditorMode("CuttingAngleA", 1)
        obj.addProperty(
            "App::PropertyString",
            "CuttingAngleB",
            "Structure",
            "Cutting Angle B",
        )
        obj.setEditorMode("CuttingAngleB", 1)

        self.bevels_combined = bevels_combined
        obj.Proxy = self

    def set_properties(
        self,
        obj,
        init_w,
        init_h,
        init_mt,
        init_ft,
        init_r1,
        init_r2,
        init_len,
        init_wg,
        init_unit_price,
        init_mf,
        init_anchor_x,
        init_anchor_y,
        material,
        fam,
        size_name,
        init_mirror_h=False,
        init_mirror_v=False,
        init_rotation=0.0,
    ):
        self.run_compatibility_migrations(obj)

        obj.Material = material
        obj.Family = fam
        obj.SizeName = size_name

        obj.ProfileHeight = init_h
        obj.ProfileWidth = init_w
        obj.ProfileLength = init_len  # should it be ?

        obj.Thickness = init_mt
        obj.ThicknessFlange = init_ft

        obj.RadiusLarge = init_r1
        obj.RadiusSmall = init_r2
        obj.MakeFillet = init_mf

        obj.LinearWeight = init_wg
        obj.UnitPrice = init_unit_price

        obj.AnchorX = ANCHOR_X[normalize_anchor(init_anchor_x)]
        obj.AnchorY = ANCHOR_Y[normalize_anchor(init_anchor_y)]
        obj.MirrorH = bool(init_mirror_h)
        obj.MirrorV = bool(init_mirror_v)
        obj.RotationAngle = float(init_rotation)

        # obj.OffsetA = .0  # Property for structure
        # obj.OffsetB = .0  # Property for structure

        self._cached_key = None
        self._cached_face = None

    def __getstate__(self):
        # Save only picklable data, NOT the cached TopoShape or Coin3D objects
        return {"Type": self.Type, "bevels_combined": self.bevels_combined}

    def __setstate__(self, state):
        self.Type = state.get("Type", "Profile")
        self.bevels_combined = state.get("bevels_combined", False)
        self._cached_key = None
        self._cached_face = None

    def _section_key(self, obj):
        """Cache key for cross-section face.
        Only includes parameters that affect the face shape + anchor + mirror.
        Length/bevel/offset changes reuse the cached face.
        """
        return (
            obj.Family,
            obj.ProfileWidth, obj.ProfileHeight,
            obj.Thickness, getattr(obj, 'ThicknessFlange', 0.0),
            getattr(obj, 'RadiusLarge', 0.0), getattr(obj, 'RadiusSmall', 0.0),
            obj.MakeFillet,
            obj.AnchorX, obj.AnchorY,
            obj.MirrorH, obj.MirrorV,
            obj.CustomProfile.Name if obj.CustomProfile else None,
            self.bevels_combined,
        )

    def onChanged(self, obj, p):
        if getattr(obj, "Restoring", False):
            return

        if getattr(self, "_guard_offsets", False):
            return

        if p == "PreExtend":
            self._guard_offsets = True
            try:
                if obj.PreExtend:
                    ext = max(obj.ProfileWidth, obj.ProfileHeight)
                    obj.OffsetA = ext
                    obj.OffsetB = ext
                else:
                    obj.OffsetA = 0.0
                    obj.OffsetB = 0.0
            finally:
                self._guard_offsets = False

        if (
            p == "PreExtend"
            or p == "ProfileWidth"
            or p == "ProfileHeight"
            or p == "Thickness"
            or p == "ThicknessFlange"
            or p == "RadiusLarge"
            or p == "RadiusSmall"
            or p == "MakeFillet"
            or p == "Length"
            or p == "BevelACutY"
            or p == "BevelBCutY"
            or p == "BevelACutX"
            or p == "BevelBCutX"
            or p == "BevelStartCut"
            or p == "BevelEndCut"
            or p == "BevelStartRotate"
            or p == "BevelEndRotate"
            or p == "OffsetA"
            or p == "OffsetB"
            or p == "AnchorX"
            or p == "AnchorY"
            or p == "MirrorH"
            or p == "MirrorV"
            or p == "RotationAngle"
            or p == "CustomProfile"
            or p == "Target"
        ):
            obj.recompute()


    def execute(self, obj):
        self.run_compatibility_migrations(obj)

        if not getattr(self, "_guard_overlap", False):
            self._guard_overlap = True
            try:
                self._recalc_overlap_offsets(obj)
            finally:
                self._guard_overlap = False

        try:
            L = obj.Target[0].getSubObject(obj.Target[1][0]).Length
            L += obj.OffsetA + obj.OffsetB
            obj.ProfileLength = L
        except Exception:
            App.Console.PrintLog(f"Profile: fallback length for {obj.Label}\n")
            L = obj.ProfileLength + obj.OffsetA + obj.OffsetB

        obj.ApproxWeight = obj.LinearWeight * L / 1000
        obj.Price = obj.UnitPrice * L / 1000

        W = getattr(obj, 'ProfileWidth', 0.0)
        H = getattr(obj, 'ProfileHeight', 0.0)
        pl = getattr(obj, 'Placement', App.Placement())
        TW = getattr(obj, 'Thickness', 0.0)
        TF = getattr(obj, 'ThicknessFlange', 0.0)

        R = getattr(obj, 'RadiusLarge', 0.0)
        r = getattr(obj, 'RadiusSmall', 0.0)
        d = vec(0, 0, 1)

        w = h = 0

        if self.bevels_combined == False:
            obj.BevelACutY = max(min(obj.BevelACutY, MAX_BEVEL_ANGLE), -MAX_BEVEL_ANGLE)
            obj.BevelACutX = max(min(obj.BevelACutX, MAX_BEVEL_ANGLE), -MAX_BEVEL_ANGLE)
            obj.BevelBCutY = max(min(obj.BevelBCutY, MAX_BEVEL_ANGLE), -MAX_BEVEL_ANGLE)
            obj.BevelBCutX = max(min(obj.BevelBCutX, MAX_BEVEL_ANGLE), -MAX_BEVEL_ANGLE)

            B1Y = obj.BevelACutY
            B2Y = -obj.BevelBCutY
            B1X = -obj.BevelACutX
            B2X = obj.BevelBCutX
            B1Z = 0
            B2Z = 0

        if self.bevels_combined == True:
            obj.BevelStartCut = max(min(obj.BevelStartCut, MAX_BEVEL_ANGLE), -MAX_BEVEL_ANGLE)
            obj.BevelStartRotate = max(min(obj.BevelStartRotate, MAX_BEVEL_ANGLE), -MAX_BEVEL_ANGLE)
            obj.BevelEndCut = max(min(obj.BevelEndCut, MAX_BEVEL_ANGLE), -MAX_BEVEL_ANGLE)
            obj.BevelEndRotate = max(min(obj.BevelEndRotate, MAX_BEVEL_ANGLE), -MAX_BEVEL_ANGLE)

            B1Y = obj.BevelStartCut
            B1Z = -obj.BevelStartRotate
            B2Y = -obj.BevelEndCut
            B2Z = -obj.BevelEndRotate
            B1X = 0
            B2X = 0

        ax = ANCHOR_X.index(obj.AnchorX) if obj.AnchorX in ANCHOR_X else 1
        ay = ANCHOR_Y.index(obj.AnchorY) if obj.AnchorY in ANCHOR_Y else 1
        w = -W * ax / 2
        h = -H * ay / 2

        # === FACE GENERATION ===
        cache_key = self._section_key(obj)
        if getattr(self, '_cached_key', None) == cache_key and getattr(self, '_cached_face', None) is not None:
            p = self._cached_face
        elif obj.Family in ('Equal Leg Angles', 'Unequal Leg Angles'):
            if not obj.MakeFillet:
                p1 = vec(0 + w, 0 + h, 0)
                p2 = vec(0 + w, H + h, 0)
                p3 = vec(TW + w, H + h, 0)
                p4 = vec(TW + w, TW + h, 0)
                p5 = vec(W + w, TW + h, 0)
                p6 = vec(W + w, 0 + h, 0)
                L1 = Part.makeLine(p1, p2)
                L2 = Part.makeLine(p2, p3)
                L3 = Part.makeLine(p3, p4)
                L4 = Part.makeLine(p4, p5)
                L5 = Part.makeLine(p5, p6)
                L6 = Part.makeLine(p6, p1)
                wire1 = Part.Wire([L1, L2, L3, L4, L5, L6])
            else:
                p1 = vec(0 + w, 0 + h, 0)
                p2 = vec(0 + w, H + h, 0)
                p3 = vec(TW - r + w, H + h, 0)
                p4 = vec(TW + w, H - r + h, 0)
                p5 = vec(TW + w, TW + R + h, 0)
                p6 = vec(TW + R + w, TW + h, 0)
                p7 = vec(W - r + w, TW + h, 0)
                p8 = vec(W + w, TW - r + h, 0)
                p9 = vec(W + w, 0 + h, 0)
                c1 = vec(TW - r + w, H - r + h, 0)
                c2 = vec(TW + R + w, TW + R + h, 0)
                c3 = vec(W - r + w, TW - r + h, 0)
                L1 = Part.makeLine(p1, p2)
                L2 = Part.makeLine(p2, p3)
                L3 = Part.makeLine(p4, p5)
                L4 = Part.makeLine(p6, p7)
                L5 = Part.makeLine(p8, p9)
                L6 = Part.makeLine(p9, p1)
                A1 = Part.makeCircle(r, c1, d, 0, 90)
                A2 = Part.makeCircle(R, c2, d, 180, 270)
                A3 = Part.makeCircle(r, c3, d, 0, 90)
                wire1 = Part.Wire([L1, L2, A1, L3, A2, L4, A3, L5, L6])
            p = Part.Face(wire1)

        elif obj.Family in ('Flat Sections', 'Square', 'Square Hollow', 'Rectangular Hollow'):
            wire1 = 0
            wire2 = 0

            if obj.Family in ('Square', 'Flat Sections'):
                p1 = vec(0 + w, 0 + h, 0)
                p2 = vec(0 + w, H + h, 0)
                p3 = vec(W + w, H + h, 0)
                p4 = vec(W + w, 0 + h, 0)
                L1 = Part.makeLine(p1, p2)
                L2 = Part.makeLine(p2, p3)
                L3 = Part.makeLine(p3, p4)
                L4 = Part.makeLine(p4, p1)
                wire1 = Part.Wire([L1, L2, L3, L4])

            if obj.Family in ('Square Hollow', 'Rectangular Hollow'):
                if not obj.MakeFillet:
                    p1 = vec(0 + w, 0 + h, 0)
                    p2 = vec(0 + w, H + h, 0)
                    p3 = vec(W + w, H + h, 0)
                    p4 = vec(W + w, 0 + h, 0)
                    p5 = vec(TW + w, TW + h, 0)
                    p6 = vec(TW + w, H + h - TW, 0)
                    p7 = vec(W + w - TW, H + h - TW, 0)
                    p8 = vec(W + w - TW, TW + h, 0)
                    L1 = Part.makeLine(p1, p2)
                    L2 = Part.makeLine(p2, p3)
                    L3 = Part.makeLine(p3, p4)
                    L4 = Part.makeLine(p4, p1)
                    L5 = Part.makeLine(p5, p6)
                    L6 = Part.makeLine(p6, p7)
                    L7 = Part.makeLine(p7, p8)
                    L8 = Part.makeLine(p8, p5)
                    wire1 = Part.Wire([L1, L2, L3, L4])
                    wire2 = Part.Wire([L5, L6, L7, L8])
                else:
                    p1 = vec(0 + w, 0 + R + h, 0)
                    p2 = vec(0 + w, H - R + h, 0)
                    p3 = vec(R + w, H + h, 0)
                    p4 = vec(W - R + w, H + h, 0)
                    p5 = vec(W + w, H - R + h, 0)
                    p6 = vec(W + w, R + h, 0)
                    p7 = vec(W - R + w, 0 + h, 0)
                    p8 = vec(R + w, 0 + h, 0)
                    c1 = vec(R + w, R + h, 0)
                    c2 = vec(R + w, H - R + h, 0)
                    c3 = vec(W - R + w, H - R + h, 0)
                    c4 = vec(W - R + w, R + h, 0)
                    L1 = Part.makeLine(p1, p2)
                    L2 = Part.makeLine(p3, p4)
                    L3 = Part.makeLine(p5, p6)
                    L4 = Part.makeLine(p7, p8)
                    A1 = Part.makeCircle(R, c1, d, 180, 270)
                    A2 = Part.makeCircle(R, c2, d, 90, 180)
                    A3 = Part.makeCircle(R, c3, d, 0, 90)
                    A4 = Part.makeCircle(R, c4, d, 270, 0)
                    wire1 = Part.Wire([L1, A2, L2, A3, L3, A4, L4, A1])

                    p1 = vec(TW + w, TW + r + h, 0)
                    p2 = vec(TW + w, H - TW - r + h, 0)
                    p3 = vec(TW + r + w, H - TW + h, 0)
                    p4 = vec(W - TW - r + w, H - TW + h, 0)
                    p5 = vec(W - TW + w, H - TW - r + h, 0)
                    p6 = vec(W - TW + w, TW + r + h, 0)
                    p7 = vec(W - TW - r + w, TW + h, 0)
                    p8 = vec(TW + r + w, TW + h, 0)
                    c1 = vec(TW + r + w, TW + r + h, 0)
                    c2 = vec(TW + r + w, H - TW - r + h, 0)
                    c3 = vec(W - TW - r + w, H - TW - r + h, 0)
                    c4 = vec(W - TW - r + w, TW + r + h, 0)
                    L1 = Part.makeLine(p1, p2)
                    L2 = Part.makeLine(p3, p4)
                    L3 = Part.makeLine(p5, p6)
                    L4 = Part.makeLine(p7, p8)
                    A1 = Part.makeCircle(r, c1, d, 180, 270)
                    A2 = Part.makeCircle(r, c2, d, 90, 180)
                    A3 = Part.makeCircle(r, c3, d, 0, 90)
                    A4 = Part.makeCircle(r, c4, d, 270, 0)
                    wire2 = Part.Wire([L1, A2, L2, A3, L3, A4, L4, A1])

            if wire2:
                p1 = Part.Face(wire1)
                p2 = Part.Face(wire2)
                p = p1.cut(p2)
            else:
                p = Part.Face(wire1)

        elif obj.Family in ('UPE', 'UPN'):
            if not obj.MakeFillet:
                Yd = 0
                if obj.Family == 'UPN':
                    Yd = W / 4 * math.tan(math.pi * FLANGE_ANGLES['UPN'] / 180)
                p1 = vec(w, h, 0)
                p2 = vec(w, H + h, 0)
                p3 = vec(w + W, H + h, 0)
                p4 = vec(W + w, h, 0)
                p5 = vec(W + w + Yd - TF, h, 0)
                p6 = vec(W + w - Yd - TF, H + h - TW, 0)
                p7 = vec(w + TF + Yd, H + h - TW, 0)
                p8 = vec(w + TF - Yd, h, 0)
                L1 = Part.makeLine(p1, p2)
                L2 = Part.makeLine(p2, p3)
                L3 = Part.makeLine(p3, p4)
                L4 = Part.makeLine(p4, p5)
                L5 = Part.makeLine(p5, p6)
                L6 = Part.makeLine(p6, p7)
                L7 = Part.makeLine(p7, p8)
                L8 = Part.makeLine(p8, p1)
                wire1 = Part.Wire([L1, L2, L3, L4, L5, L6, L7, L8])
                p = Part.Face(wire1)
            else:
                if obj.Family == 'UPE':
                    p1 = vec(w, h, 0)
                    p2 = vec(w, H + h, 0)
                    p3 = vec(w + W, H + h, 0)
                    p4 = vec(W + w, h, 0)
                    p5 = vec(W + w - TF + r, h, 0)
                    p6 = vec(W + w - TF, h + r, 0)
                    p7 = vec(W + w - TF, H + h - TW - R, 0)
                    p8 = vec(W + w - TF - R, H + h - TW, 0)
                    p9 = vec(w + TF + R, H + h - TW, 0)
                    p10 = vec(w + TF, H + h - TW - R, 0)
                    p11 = vec(w + TF, h + r, 0)
                    p12 = vec(w + TF - r, h, 0)
                    C1 = vec(w + TF - r, h + r, 0)
                    C2 = vec(w + TF + R, H + h - TW - R, 0)
                    C3 = vec(W + w - TF - R, H + h - TW - R, 0)
                    C4 = vec(W + w - TF + r, r + h, 0)
                    L1 = Part.makeLine(p1, p2)
                    L2 = Part.makeLine(p2, p3)
                    L3 = Part.makeLine(p3, p4)
                    L4 = Part.makeLine(p4, p5)
                    L5 = Part.makeLine(p6, p7)
                    L6 = Part.makeLine(p8, p9)
                    L7 = Part.makeLine(p10, p11)
                    L8 = Part.makeLine(p12, p1)
                    A1 = Part.makeCircle(r, C1, d, 270, 0)
                    A2 = Part.makeCircle(R, C2, d, 90, 180)
                    A3 = Part.makeCircle(R, C3, d, 0, 90)
                    A4 = Part.makeCircle(r, C4, d, 180, 270)
                    wire1 = Part.Wire([L1, L2, L3, L4, A4, L5, A3, L6, A2, L7, A1, L8])
                else:  # UPN
                    angarc = FLANGE_ANGLES['UPN']
                    angrad = math.pi * angarc / 180
                    sina = math.sin(angrad)
                    cosa = math.cos(angrad)
                    tana = math.tan(angrad)
                    cot1 = r * sina
                    y11 = r - cot1
                    cot2 = H / 2 - r * tana
                    cot3 = cot1 * tana
                    x11 = TF - cot2 - cot3
                    xc1 = TF - cot2 - cot3 - r * cosa
                    yc1 = r
                    cot8 = H / 2 - R - TW + R * sina * tana
                    x10 = TF + cot8
                    y10 = H - TW - R + R * sina
                    xc2 = cot8 + R * cosa + TF
                    yc2 = H - TW - R
                    x12 = TF - cot2 - cot3 - r * cosa
                    y12 = 0
                    x9 = cot8 + R * cosa + TF
                    y9 = H - TW
                    xc3 = W - xc2
                    yc3 = yc2
                    xc4 = W - xc1
                    yc4 = yc1
                    x1 = 0
                    y1 = 0
                    x2 = 0
                    y2 = H
                    x3 = W
                    y3 = H
                    x4 = W
                    y4 = 0
                    x5 = W - x12
                    y5 = 0
                    x6 = W - x11
                    y6 = y11
                    x7 = W - x10
                    y7 = y10
                    x8 = W - x9
                    y8 = y9
                    c1 = vec(xc1 + w, yc1 + h, 0)
                    c2 = vec(xc2 + w, yc2 + h, 0)
                    c3 = vec(xc3 + w, yc3 + h, 0)
                    c4 = vec(xc4 + w, yc4 + h, 0)
                    p1 = vec(x1 + w, y1 + h, 0)
                    p2 = vec(x2 + w, y2 + h, 0)
                    p3 = vec(x3 + w, y3 + h, 0)
                    p4 = vec(x4 + w, y4 + h, 0)
                    p5 = vec(x5 + w, y5 + h, 0)
                    p6 = vec(x6 + w, y6 + h, 0)
                    p7 = vec(x7 + w, y7 + h, 0)
                    p8 = vec(x8 + w, y8 + h, 0)
                    p9 = vec(x9 + w, y9 + h, 0)
                    p10 = vec(x10 + w, y10 + h, 0)
                    p11 = vec(x11 + w, y11 + h, 0)
                    p12 = vec(x12 + w, y12 + h, 0)
                    A1 = Part.makeCircle(r, c1, d, 270, 0 - angarc)
                    A2 = Part.makeCircle(R, c2, d, 90, 180 - angarc)
                    A3 = Part.makeCircle(R, c3, d, 0 + angarc, 90)
                    A4 = Part.makeCircle(r, c4, d, 180 + angarc, 270)
                    L1 = Part.makeLine(p1, p2)
                    L2 = Part.makeLine(p2, p3)
                    L3 = Part.makeLine(p3, p4)
                    L4 = Part.makeLine(p4, p5)
                    L5 = Part.makeLine(p6, p7)
                    L6 = Part.makeLine(p8, p9)
                    L7 = Part.makeLine(p10, p11)
                    L8 = Part.makeLine(p12, p1)
                    wire1 = Part.Wire([L1, L2, L3, L4, A4, L5, A3, L6, A2, L7, A1, L8])
                p = Part.Face(wire1)

        elif obj.Family in ('IPE', 'IPN', 'HEA', 'HEB', 'HEM'):
            XA1 = W / 2 - TW / 2
            XA2 = W / 2 + TW / 2

            if not obj.MakeFillet:
                Yd = 0
                if obj.Family == 'IPN':
                    Yd = W / 4 * math.tan(math.pi * FLANGE_ANGLES[obj.Family] / 180)
                p1 = vec(0 + w, 0 + h, 0)
                p2 = vec(0 + w, TF + h - Yd, 0)
                p3 = vec(XA1 + w, TF + h + Yd, 0)
                p4 = vec(XA1 + w, H - TF + h - Yd, 0)
                p5 = vec(0 + w, H - TF + h + Yd, 0)
                p6 = vec(0 + w, H + h, 0)
                p7 = vec(W + w, H + h, 0)
                p8 = vec(W + w, H - TF + h + Yd, 0)
                p9 = vec(XA2 + w, H - TF + h - Yd, 0)
                p10 = vec(XA2 + w, TF + h + Yd, 0)
                p11 = vec(W + w, TF + h - Yd, 0)
                p12 = vec(W + w, 0 + h, 0)
                L1 = Part.makeLine(p1, p2)
                L2 = Part.makeLine(p2, p3)
                L3 = Part.makeLine(p3, p4)
                L4 = Part.makeLine(p4, p5)
                L5 = Part.makeLine(p5, p6)
                L6 = Part.makeLine(p6, p7)
                L7 = Part.makeLine(p7, p8)
                L8 = Part.makeLine(p8, p9)
                L9 = Part.makeLine(p9, p10)
                L10 = Part.makeLine(p10, p11)
                L11 = Part.makeLine(p11, p12)
                L12 = Part.makeLine(p12, p1)
                wire1 = Part.Wire([L1, L2, L3, L4, L5, L6, L7, L8, L9, L10, L11, L12])
                p = Part.Face(wire1)
            else:
                if obj.Family == 'IPE':
                    p1 = vec(0 + w, 0 + h, 0)
                    p2 = vec(0 + w, TF + h, 0)
                    p3 = vec(XA1 - R + w, TF + h, 0)
                    p4 = vec(XA1 + w, TF + R + h, 0)
                    p5 = vec(XA1 + w, H - TF - R + h, 0)
                    p6 = vec(XA1 - R + w, H - TF + h, 0)
                    p7 = vec(0 + w, H - TF + h, 0)
                    p8 = vec(0 + w, H + h, 0)
                    p9 = vec(W + w, H + h, 0)
                    p10 = vec(W + w, H - TF + h, 0)
                    p11 = vec(XA2 + R + w, H - TF + h, 0)
                    p12 = vec(XA2 + w, H - TF - R + h, 0)
                    p13 = vec(XA2 + w, TF + R + h, 0)
                    p14 = vec(XA2 + R + w, TF + h, 0)
                    p15 = vec(W + w, TF + h, 0)
                    p16 = vec(W + w, 0 + h, 0)
                    c1 = vec(XA1 - R + w, TF + R + h, 0)
                    c2 = vec(XA1 - R + w, H - TF - R + h, 0)
                    c3 = vec(XA2 + R + w, H - TF - R + h, 0)
                    c4 = vec(XA2 + R + w, TF + R + h, 0)
                    L1 = Part.makeLine(p1, p2)
                    L2 = Part.makeLine(p2, p3)
                    L3 = Part.makeLine(p4, p5)
                    L4 = Part.makeLine(p6, p7)
                    L5 = Part.makeLine(p7, p8)
                    L6 = Part.makeLine(p8, p9)
                    L7 = Part.makeLine(p9, p10)
                    L8 = Part.makeLine(p10, p11)
                    L9 = Part.makeLine(p12, p13)
                    L10 = Part.makeLine(p14, p15)
                    L11 = Part.makeLine(p15, p16)
                    L12 = Part.makeLine(p16, p1)
                    A1 = Part.makeCircle(R, c1, d, 270, 0)
                    A2 = Part.makeCircle(R, c2, d, 0, 90)
                    A3 = Part.makeCircle(R, c3, d, 90, 180)
                    A4 = Part.makeCircle(R, c4, d, 180, 270)
                    wire1 = Part.Wire([L1, L2, A1, L3, A2, L4, L5, L6, L7, L8, A3, L9, A4, L10, L11, L12])
                else:  # IPN/HEA/HEB/HEM with fillet
                    angarc = FLANGE_ANGLES['IPN']
                    angrad = math.pi * angarc / 180
                    sina = math.sin(angrad)
                    cosa = math.cos(angrad)
                    tana = math.tan(angrad)
                    cot1 = W / 4 * tana
                    cot2 = TF - cot1
                    cot3 = r * cosa
                    cot4 = r - cot3 * tana
                    cot5 = cot4 * tana
                    cot5 = cot2 + cot5
                    cot6 = R * sina
                    cot7 = W / 4 - R - TW / 2
                    cot8 = cot6 + cot7
                    cot9 = cot7 * tana
                    cot10 = R * cosa
                    xc1 = r
                    yc1 = cot5 - cot3
                    c1 = vec(xc1 + w, yc1 + h, 0)
                    xc2 = W / 2 - TW / 2 - R
                    yc2 = cot9 + TF + cot10
                    c2 = vec(xc2 + w, yc2 + h, 0)
                    xc3 = xc2
                    yc3 = H - yc2
                    c3 = vec(xc3 + w, yc3 + h, 0)
                    xc4 = xc1
                    yc4 = H - yc1
                    c4 = vec(xc4 + w, yc4 + h, 0)
                    xc5 = W - xc1
                    yc5 = yc4
                    c5 = vec(xc5 + w, yc5 + h, 0)
                    xc6 = W - xc2
                    yc6 = yc3
                    c6 = vec(xc6 + w, yc6 + h, 0)
                    xc7 = xc6
                    yc7 = yc2
                    c7 = vec(xc7 + w, yc7 + h, 0)
                    xc8 = xc5
                    yc8 = yc1
                    c8 = vec(xc8 + w, yc8 + h, 0)
                    A1 = Part.makeCircle(r, c1, d, 90 + angarc, 180)
                    A2 = Part.makeCircle(R, c2, d, 270 + angarc, 0)
                    A3 = Part.makeCircle(R, c3, d, 0, 90 - angarc)
                    A4 = Part.makeCircle(r, c4, d, 180, 270 - angarc)
                    A5 = Part.makeCircle(r, c5, d, 270 + angarc, 0)
                    A6 = Part.makeCircle(R, c6, d, 90 + angarc, 180)
                    A7 = Part.makeCircle(R, c7, d, 180, 270 - angarc)
                    A8 = Part.makeCircle(r, c8, d, 0, 90 - angarc)
                    xp1 = 0
                    yp1 = 0
                    p1 = vec(xp1 + w, yp1 + h, 0)
                    xp2 = 0
                    yp2 = cot5 - cot3
                    p2 = vec(xp2 + w, yp2 + h, 0)
                    xp3 = cot4
                    yp3 = cot5
                    p3 = vec(xp3 + w, yp3 + h, 0)
                    xp4 = W / 4 + cot8
                    yp4 = TF + cot9
                    p4 = vec(xp4 + w, yp4 + h, 0)
                    xp5 = W / 2 - TW / 2
                    yp5 = yc2
                    p5 = vec(xp5 + w, yp5 + h, 0)
                    xp6 = xp5
                    yp6 = H - yp5
                    p6 = vec(xp6 + w, yp6 + h, 0)
                    xp7 = xp4
                    yp7 = H - yp4
                    p7 = vec(xp7 + w, yp7 + h, 0)
                    xp8 = xp3
                    yp8 = H - yp3
                    p8 = vec(xp8 + w, yp8 + h, 0)
                    xp9 = xp2
                    yp9 = H - yp2
                    p9 = vec(xp9 + w, yp9 + h, 0)
                    xp10 = xp1
                    yp10 = H
                    p10 = vec(xp10 + w, yp10 + h, 0)
                    xp11 = W
                    yp11 = H
                    p11 = vec(xp11 + w, yp11 + h, 0)
                    xp12 = xp11
                    yp12 = yp9
                    p12 = vec(xp12 + w, yp12 + h, 0)
                    xp13 = W - xp8
                    yp13 = yp8
                    p13 = vec(xp13 + w, yp13 + h, 0)
                    xp14 = W - xp7
                    yp14 = yp7
                    p14 = vec(xp14 + w, yp14 + h, 0)
                    xp15 = W - xp6
                    yp15 = yp6
                    p15 = vec(xp15 + w, yp15 + h, 0)
                    xp16 = W - xp5
                    yp16 = yp5
                    p16 = vec(xp16 + w, yp16 + h, 0)
                    xp17 = W - xp4
                    yp17 = yp4
                    p17 = vec(xp17 + w, yp17 + h, 0)
                    xp18 = W - xp3
                    yp18 = yp3
                    p18 = vec(xp18 + w, yp18 + h, 0)
                    xp19 = W - xp2
                    yp19 = yp2
                    p19 = vec(xp19 + w, yp19 + h, 0)
                    xp20 = W
                    yp20 = 0
                    p20 = vec(xp20 + w, yp20 + h, 0)
                    L1 = Part.makeLine(p1, p2)
                    L2 = Part.makeLine(p3, p4)
                    L3 = Part.makeLine(p5, p6)
                    L4 = Part.makeLine(p7, p8)
                    L5 = Part.makeLine(p9, p10)
                    L6 = Part.makeLine(p10, p11)
                    L7 = Part.makeLine(p11, p12)
                    L8 = Part.makeLine(p13, p14)
                    L9 = Part.makeLine(p15, p16)
                    L10 = Part.makeLine(p17, p18)
                    L11 = Part.makeLine(p19, p20)
                    L12 = Part.makeLine(p20, p1)
                    wire1 = Part.Wire([L1, A1, L2, A2, L3, A3, L4, A4, L5, L6, L7, A5, L8, A6, L9, A7, L10, A8, L11, L12])
                p = Part.Face(wire1)

        elif obj.Family == 'Round Bar':
            c = vec(H / 2 + h, H / 2 + h, 0)
            A1 = Part.makeCircle(H / 2, c, d, 0, 360)
            wire1 = Part.Wire([A1])
            p = Part.Face(wire1)

        elif obj.Family == 'Pipe':
            c = vec(H / 2 + h, H / 2 + h, 0)
            A1 = Part.makeCircle(H / 2, c, d, 0, 360)
            A2 = Part.makeCircle(H / 2 - TW, c, d, 0, 360)
            wire1 = Part.Wire([A1])
            wire2 = Part.Wire([A2])
            p1 = Part.Face(wire1)
            p2 = Part.Face(wire2)
            p = p1.cut(p2)

        elif obj.Family == 'Custom Profile':
            # Try linked shape object first (current session)
            custom_prof = obj.CustomProfile
            sk_shape = None
            if custom_prof is not None and custom_prof.Shape is not None and not custom_prof.Shape.isNull():
                sk_shape = custom_prof.Shape
            else:
                try:
                    custom_prof.recompute()
                except Exception:
                    pass
                if custom_prof is not None and custom_prof.Shape is not None and not custom_prof.Shape.isNull():
                    sk_shape = custom_prof.Shape
            # Fall back to embedded BREP data
            if sk_shape is None:
                brep = getattr(obj, 'CrossSectionBrep', "")
                if brep:
                    try:
                        import tempfile, os
                        brep_bytes = brep.encode("latin-1") if isinstance(brep, str) else brep
                        tmp = tempfile.NamedTemporaryFile(
                            suffix=".brp", delete=False, mode="wb")
                        try:
                            tmp.write(brep_bytes)
                            tmp.close()
                            sk_shape = Part.read(tmp.name)
                        finally:
                            os.unlink(tmp.name)
                    except Exception:
                        sk_shape = None
            # Last resort: try reading from source library file
            if sk_shape is None:
                try:
                    src = getattr(custom_prof, 'SourceFile', '') if custom_prof else ''
                    if not src:
                        src = getattr(obj, 'SourceFile', '')
                    if src and os.path.isfile(src):
                        import zipfile
                        with zipfile.ZipFile(src, 'r') as zf:
                            brp_entries = [n for n in zf.namelist()
                                          if n.endswith('.Shape.brp') and zf.getinfo(n).file_size > 0]
                            tmp2 = tempfile.mkdtemp()
                            try:
                                for entry in brp_entries:
                                    zf.extract(entry, tmp2)
                                    brp_path = os.path.join(tmp2, entry)
                                    try:
                                        shape = Part.read(brp_path)
                                        if shape is not None and not shape.isNull():
                                            if shape.ShapeType in ("Face", "Wire", "Compound"):
                                                sk_shape = shape.copy()
                                                break
                                    except Exception:
                                        pass
                            finally:
                                import shutil
                                shutil.rmtree(tmp2, ignore_errors=True)
                except Exception:
                    pass
            if sk_shape is None:
                App.Console.PrintLog(f"Profile '{obj.Label}': custom shape not available (re-select section to fix).\n")
                try:
                    obj.Shape = Part.Compound([])
                except Exception:
                    obj.Shape = Part.Shape()
                obj.purgeTouched()
                return
            if isinstance(sk_shape, Part.Wire):
                p = Part.Face(sk_shape)
            elif isinstance(sk_shape, Part.Face):
                p = sk_shape
            elif isinstance(sk_shape, Part.Compound):
                # Sketcher returns Compound when there are multiple wires
                wires = sk_shape.Wires
                if not wires:
                    raise FrameForgemodException("CustomProfile Compound has no wires.")
                # Sort by size: biggest wire = outer boundary
                wires = sorted(wires, key=lambda w: w.BoundBox.DiagonalLength, reverse=True)
                p = Part.Face(wires[0])
                for inner_w in wires[1:]:
                    p = p.cut(Part.Face(inner_w))
            else:
                raise FrameForgemodException(f"Unsupported shape type: {sk_shape.TypeId}")
            H = p.BoundBox.YLength
            W = p.BoundBox.XLength

        elif obj.Family == 'V-Slot':
            if H == 20.0 and W == 20.0:
                p = vslot20x20()
            elif H == 20.0 and W == 40.0:
                p = vslot20x40()
            elif H == 20.0 and W == 60.0:
                p = vslot20x60()
            elif H == 20.0 and W == 80.0:
                p = vslot20x80()
            else:
                p = make_vslot_face(W, H)

        elif obj.Family == 'T-Slot':
            p = make_tslot_face(W, H)

        elif obj.Family == 'T-Slot 3-Slots':
            if H == 20.0 and W == 20.0:
                p = tslot20x20_three_slot()
            else:
                p = make_tslot_face(W, H)

        elif obj.Family == 'T-Slot 2-Slots':
            if H == 20.0 and W == 20.0:
                p = tslot20x20_two_slot()
            else:
                p = make_tslot_face(W, H)

        elif obj.Family == 'T-Slot 2-Slots Opp':
            if H == 20.0 and W == 20.0:
                p = tslot20x20_two_slot_opp()
            else:
                p = make_tslot_face(W, H)

        elif obj.Family == 'T-Slot 1-Slot':
            if H == 20.0 and W == 20.0:
                p = tslot20x20_one_slot()
            else:
                p = make_tslot_face(W, H)

        elif obj.Family.startswith('欧标'):
            import re
            m = re.search(r'\(([\d.]+)\)', obj.Family)
            sw = float(m.group(1)) if m else None
            if '40系列' in obj.Family:
                p = make_40series_vslot(W, H)
            elif '30系列' in obj.Family:
                p = make_aoh_vslot(W, H)
            else:
                p = make_yiheda_vslot(W, H, sw=sw)

        elif obj.Family.startswith('国标'):
            import re
            m = re.search(r'\(([\d.]+)\)', obj.Family)
            sw = float(m.group(1)) if m else 6.0
            p = make_profile_face(W, H, sw, 1.6, 10.3, 4.62)

        # Cache the raw face (mirror/anchor applied below)
        if not (getattr(self, '_cached_key', None) == cache_key and getattr(self, '_cached_face', None) is not None):
            App.Console.PrintLog(f"  [cache MISS] {obj.Family} {obj.SizeName}\n")
            self._cached_key = cache_key
            self._cached_face = p
        else:
            App.Console.PrintLog(f"  [cache HIT]  {obj.Family} {obj.SizeName}\n")

        # === MIRROR ===
        mirror_h = getattr(obj, 'MirrorH', False)
        mirror_v = getattr(obj, 'MirrorV', False)
        center_pt = vec(W / 2 + w, H / 2 + h, 0)
        if mirror_h:
            p = p.mirror(center_pt, vec(1, 0, 0))
        if mirror_v:
            p = p.mirror(center_pt, vec(0, 1, 0))

        # === EXTRUSION ===
        if L:
            p = p.copy()
            p.translate(vec(0, 0, -obj.OffsetA))
            hc = 4 * max(H, W)
            pre_extend = getattr(obj, "PreExtend", True)
            extrude_len = L + (max(H, W) if pre_extend else 0)
            ProfileFull = p.extrude(vec(0, 0, extrude_len))

            if B1Y or B2Y or B1X or B2X or B1Z or B2Z:  # make the bevels:

                # "B" side
                if B2Y or B2X or B2Z:
                    box = Part.makeBox(hc, hc, hc)
                    box.translate(vec(-hc / 2 + w, -hc / 2 + h, L - obj.OffsetA))
                    pr = vec(0, 0, L - obj.OffsetA)
                    box.rotate(pr, vec(0, 1, 0), B2Y)
                    if self.bevels_combined == True:
                        box.rotate(pr, vec(0, 0, 1), B2Z)
                    else:
                        box.rotate(pr, vec(1, 0, 0), B2X)
                    ProfileFull = ProfileFull.cut(box)

                # "A" side
                if B1Y or B1X or B1Z:
                    box = Part.makeBox(hc, hc, hc)
                    box.translate(vec(-hc / 2 + w, -hc / 2 + h, -hc - obj.OffsetA))
                    pr = vec(0, 0, -obj.OffsetA)
                    box.rotate(pr, vec(0, 1, 0), B1Y)
                    if self.bevels_combined == True:
                        box.rotate(pr, vec(0, 0, 1), B1Z)
                    else:
                        box.rotate(pr, vec(1, 0, 0), B1X)
                    ProfileFull = ProfileFull.cut(box)

                ProfileFull = ProfileFull.removeSplitter()

            obj.Shape = ProfileFull

        else:
            obj.Shape = p

        self._update_structure_data(obj)

        obj.Placement = pl
        if getattr(obj, "MapMode", None) != "Deactivated":
            try:
                obj.positionBySupport()
            except Exception:
                App.Console.PrintLog(f"Profile: positionBySupport failed for {obj.Label}\n")
                self._placement_from_target(obj)
        elif hasattr(obj, "Target") and obj.Target is not None:
            self._placement_from_target(obj)

    def _placement_from_target(self, obj):
        """Place profile using Target edge vertices as fallback when positionBySupport is unavailable/failed."""
        try:
            target = obj.Target
            subname = target[1]
            if isinstance(subname, (list, tuple)):
                subname = subname[0]
            from freecad.frameforgemod._utils import get_profile_from_trimmedbody
            root = get_profile_from_trimmedbody(obj)
            if root is None:
                root = obj
            tgt = root.Target if hasattr(root, "Target") and root.Target is not None else target
            sn = tgt[1]
            if isinstance(sn, (list, tuple)):
                sn = sn[0]
            sketch_obj = App.ActiveDocument.getObject(tgt[0].Name)
            if sketch_obj:
                edge = sketch_obj.getSubObject(str(sn))
                if edge and hasattr(edge, "Vertexes") and len(edge.Vertexes) >= 2:
                    v1 = edge.Vertexes[0].Point
                    v2 = edge.Vertexes[-1].Point
                    direction = v2 - v1
                    if direction.Length > 0:
                        direction.normalize()
                        rot = App.Rotation(App.Vector(0, 0, 1), direction)
                        if hasattr(root, "RotationAngle") and root.RotationAngle:
                            rot_z = App.Rotation(App.Vector(0, 0, 1), root.RotationAngle)
                            rot = rot.multiply(rot_z)
                        obj.Placement = App.Placement(v1, rot)
        except Exception:
            App.Console.PrintLog(f"Profile: placement recovery failed for {obj.Label}\n")

    def _update_structure_data(self, obj):
        if obj.Family == "Custom Profile":
            obj.ProfileWidth = obj.CustomProfile.Shape.BoundBox.XLength
            obj.ProfileHeight = obj.CustomProfile.Shape.BoundBox.YLength

        obj.Width = obj.ProfileWidth
        obj.Height = obj.ProfileHeight

        obj.Length = length_along_normal(obj)
        cut_angles = get_readable_cutting_angles(
            getattr(obj, "BevelACutY", "N/A"),
            getattr(obj, "BevelACutX", "N/A"),
            getattr(obj, "BevelBCutY", "N/A"),
            getattr(obj, "BevelBCutX", "N/A"),
        )

        obj.CuttingAngleA = cut_angles[0]
        obj.CuttingAngleB = cut_angles[1]

    def _recalc_overlap_offsets(self, obj):
        """Recalculate overlap offsets when rotation or profile dimensions change."""
        for end, sign_prop, dir_prop, gap_prop in [
            ("A", "OverlapASign", "OverlapADir", "OverlapAGap"),
            ("B", "OverlapBSign", "OverlapBDir", "OverlapBGap")
        ]:
            sign = getattr(obj, sign_prop, 0.0)
            if sign == 0.0:
                continue
            dir_vec = getattr(obj, dir_prop, App.Vector(0, 0, 0))
            if dir_vec.Length < 0.001:
                continue
            try:
                target = obj.Target
                if target is None:
                    continue
                subname = target[1]
                if isinstance(subname, (list, tuple)):
                    subname = subname[0]
                edge = target[0].getSubObject(str(subname))
                if edge is None or not hasattr(edge, 'Vertexes') or len(edge.Vertexes) < 2:
                    continue
                z_dir = (edge.Vertexes[-1].Point - edge.Vertexes[0].Point).normalize()
            except Exception:
                continue
            world_up = App.Vector(0, 0, 1)
            if abs(z_dir.dot(world_up)) > 0.99:
                world_up = App.Vector(0, 1, 0)
            local_x = z_dir.cross(world_up).normalize()
            local_y = z_dir.cross(local_x).normalize()
            rot_angle = float(getattr(obj, "RotationAngle", 0))
            if rot_angle:
                rad = math.radians(rot_angle)
                cos_a = math.cos(rad)
                sin_a = math.sin(rad)
                local_x = local_x * cos_a + local_y * sin_a
                local_y = z_dir.cross(local_x).normalize()
            dir_in_xy = dir_vec - dir_vec.dot(z_dir) * z_dir
            if dir_in_xy.Length < 0.001:
                facing_dim = max(obj.ProfileWidth, obj.ProfileHeight) * 0.5
            else:
                dir_in_xy.normalize()
                if abs(dir_in_xy.dot(local_x)) >= abs(dir_in_xy.dot(local_y)):
                    facing_dim = obj.ProfileWidth * 0.5
                else:
                    facing_dim = obj.ProfileHeight * 0.5
            gap = float(getattr(obj, gap_prop, 0.0))
            if sign < 0:  # cut: increase cut by gap/2
                offset = sign * (facing_dim + gap / 2.0)
            else:  # extend: reduce extend by gap/2
                offset = max(0.0, facing_dim - gap / 2.0)
            if end == "A":
                obj.OffsetA = offset
            else:
                obj.OffsetB = offset

    def run_compatibility_migrations(self, obj):
        if not hasattr(obj, "FrameforgeVersion"):  # previous that 0.1.7
            if not hasattr(obj, "PID"):
                obj.addProperty(
                    "App::PropertyString",
                    "PID",
                    "Profile",
                    "Profile ID",
                ).PID = ""

            # add Family atttribute
            if not hasattr(obj, "Family"):
                App.Console.PrintMessage(f"Frameforge::object migration : adding Family to {obj.Label}\n")
                obj.addProperty(
                    "App::PropertyString",
                    "Family",
                    "Profile",
                    "",
                ).Family = self.fam

            if not hasattr(obj, "SizeName"):
                obj.addProperty(
                    "App::PropertyString",
                    "SizeName",
                    "Profile",
                    "",
                ).SizeName = "?"

            if not hasattr(obj, "Material"):
                obj.addProperty(
                    "App::PropertyString",
                    "Material",
                    "Profile",
                    "",
                ).Material = ""

            # add CustomProfile atttribute
            if not hasattr(obj, "CustomProfile"):
                obj.addProperty("App::PropertyLink", "CustomProfile", "Profile", "Target profile").CustomProfile = None

            if not hasattr(obj, "CrossSectionBrep"):
                obj.addProperty("App::PropertyString", "CrossSectionBrep", "Profile",
                                "Serialized cross-section shape BREP data").CrossSectionBrep = ""

            # add LinearWeight attribute (<= 0.1.7)
            if not hasattr(obj, "LinearWeight"):
                App.Console.PrintMessage(
                    f"Frameforge::object migration : adding LinearWeight ({self.WM}) to {obj.Label}\n"
                )
                obj.addProperty("App::PropertyFloat", "LinearWeight", "Base", "Linear weight in kg/m").LinearWeight = (
                    self.WM
                )
                obj.setEditorMode("ApproxWeight", 1)

            obj.addProperty("App::PropertyBool", "Cutout", "Structure", "Has Cutout").Cutout = False
            obj.setEditorMode("Cutout", 1)

            # update properties (bevels and offset)
            bsc1 = obj.BevelStartCut1
            bsc2 = obj.BevelStartCut2
            bec1 = obj.BevelEndCut1
            bec2 = obj.BevelEndCut2
            obj.addProperty(
                "App::PropertyFloat", "BevelACutY", "Profile", "Bevel on First axle at the start of the profile"
            ).BevelACutY = bsc1
            obj.addProperty(
                "App::PropertyFloat",
                "BevelACutX",
                "Profile",
                "Rotate the cut on Second axle at the start of the profile",
            ).BevelACutX = bsc2
            obj.addProperty(
                "App::PropertyFloat", "BevelBCutY", "Profile", "Bevel on First axle at the end of the profile"
            ).BevelBCutY = bec1
            obj.addProperty(
                "App::PropertyFloat",
                "BevelBCutX",
                "Profile",
                "Rotate the cut on Second axle at the end of the profile",
            ).BevelBCutX = bec2

            obj.removeProperty("BevelStartCut1")
            obj.removeProperty("BevelStartCut2")
            obj.removeProperty("BevelEndCut1")
            obj.removeProperty("BevelEndCut2")

            off_a = obj.OffsetA
            off_b = obj.OffsetB

            obj.removeProperty("OffsetA")
            obj.removeProperty("OffsetB")

            obj.addProperty("App::PropertyFloat", "OffsetA", "Base", "Parameter for structure").OffsetA = off_a

            obj.addProperty("App::PropertyFloat", "OffsetB", "Base", "Parameter for structure").OffsetB = off_b

            obj.setExpression(".AttachmentOffset.Base.z", None)
            obj.AttachmentOffset.Base.z = 0.0

            obj.addProperty(
                "App::PropertyString",
                "CuttingAngleA",
                "Structure",
                "Cutting Angle A",
            )
            obj.setEditorMode("CuttingAngleA", 1)
            obj.addProperty(
                "App::PropertyString",
                "CuttingAngleB",
                "Structure",
                "Cutting Angle B",
            )
            obj.setEditorMode("CuttingAngleB", 1)

            # Anchor: CenteredOn* -> AnchorX/AnchorY (enum)
            if not hasattr(obj, "AnchorX") or not hasattr(obj, "AnchorY"):
                obj.addProperty(
                    "App::PropertyEnumeration", "AnchorX", "Profile", "Path alignment (horizontal)"
                ).AnchorX = ANCHOR_X
                obj.AnchorX = "Center" if getattr(obj, "CenteredOnWidth", False) else "Left"
                obj.addProperty(
                    "App::PropertyEnumeration", "AnchorY", "Profile", "Path alignment (vertical)"
                ).AnchorY = ANCHOR_Y
                obj.AnchorY = "Center" if getattr(obj, "CenteredOnHeight", False) else "Bottom"
                if hasattr(obj, "CenteredOnWidth"):
                    obj.removeProperty("CenteredOnWidth")
                if hasattr(obj, "CenteredOnHeight"):
                    obj.removeProperty("CenteredOnHeight")

            # RotationAngle: add if missing (driven by AttachmentOffset expression)
            if not hasattr(obj, "RotationAngle"):
                obj.addProperty(
                    "App::PropertyFloat",
                    "RotationAngle",
                    "Profile",
                    "Rotation of cross-section around path axis (degrees)",
                ).RotationAngle = math.degrees(obj.AttachmentOffset.Rotation.Angle)
                obj.setExpression(".AttachmentOffset.Rotation.Angle", "RotationAngle")

            # MirrorH / MirrorV: add if missing
            if not hasattr(obj, "MirrorH"):
                obj.addProperty(
                    "App::PropertyBool", "MirrorH", "Profile", "Mirror cross-section horizontally (flip X)"
                ).MirrorH = False
            if not hasattr(obj, "MirrorV"):
                obj.addProperty(
                    "App::PropertyBool", "MirrorV", "Profile", "Mirror cross-section vertically (flip Y)"
                ).MirrorV = False

            if obj.MapReversed:
                # MirrorH/MirrorV are more flexible than "Reverse attachment"
                obj.MirrorH = not obj.MirrorH
                obj.MapReversed = False
                obj.MapPathParameter = 1.0 - obj.MapPathParameter

            # PreExtend: add if missing
            if not hasattr(obj, "PreExtend"):
                obj.addProperty(
                    "App::PropertyBool", "PreExtend", "Base",
                    "Extend profile at both ends by max(width, height)"
                ).PreExtend = bool(obj.OffsetA > 0 or obj.OffsetB > 0)

            # cleaning UPN/IPN related properties
            if hasattr(obj, "UPN"):
                obj.removeProperty("UPN")
            if hasattr(obj, "IPN"):
                obj.removeProperty("IPN")
            if hasattr(obj, "FlangeAngle"):
                obj.removeProperty("FlangeAngle")

            # add version
            obj.addProperty(
                "App::PropertyString",
                "FrameforgeVersion",
                "Profile",
                "Frameforge Version used to create the profile",
            ).FrameforgeVersion = ff_version

        else:
            if obj.FrameforgeVersion == "0.2.0":
                # exemple: perform migration. Something like that ?
                # if ff_version == "0.2.1":
                #       obj.AProperty = ...
                #       obj.FrameforgeVersion = ff_version # don't forget to update the version !
                pass

            # should help migrate projects create with the dev version between 0.1.7 and 0.2.0,
            if obj.FrameforgeVersion == "0.1.8":
                # Anchor: CenteredOn* -> AnchorX/AnchorY (enum)
                if not hasattr(obj, "AnchorX") or not hasattr(obj, "AnchorY"):
                    obj.addProperty(
                        "App::PropertyEnumeration", "AnchorX", "Profile", "Path alignment (horizontal)"
                    ).AnchorX = ANCHOR_X
                    obj.AnchorX = "Center" if getattr(obj, "CenteredOnWidth", False) else "Left"
                    obj.addProperty(
                        "App::PropertyEnumeration", "AnchorY", "Profile", "Path alignment (vertical)"
                    ).AnchorY = ANCHOR_Y
                    obj.AnchorY = "Center" if getattr(obj, "CenteredOnHeight", False) else "Bottom"
                    if hasattr(obj, "CenteredOnWidth"):
                        obj.removeProperty("CenteredOnWidth")
                    if hasattr(obj, "CenteredOnHeight"):
                        obj.removeProperty("CenteredOnHeight")

                # RotationAngle: add if missing (driven by AttachmentOffset expression)
                if not hasattr(obj, "RotationAngle"):
                    obj.addProperty(
                        "App::PropertyFloat",
                        "RotationAngle",
                        "Profile",
                        "Rotation of cross-section around path axis (degrees)",
                    ).RotationAngle = math.degrees(obj.AttachmentOffset.Rotation.Angle)
                    obj.setExpression(".AttachmentOffset.Rotation.Angle", "RotationAngle")

                # MirrorH / MirrorV: add if missing
                if not hasattr(obj, "MirrorH"):
                    obj.addProperty(
                        "App::PropertyBool", "MirrorH", "Profile", "Mirror cross-section horizontally (flip X)"
                    ).MirrorH = False
                if not hasattr(obj, "MirrorV"):
                    obj.addProperty(
                        "App::PropertyBool", "MirrorV", "Profile", "Mirror cross-section vertically (flip Y)"
                    ).MirrorV = False

                # update version
                obj.FrameforgeVersion = ff_version

        # ensure UnitPrice/Price/Thickness exist on all objects regardless of version
        if not hasattr(obj, "UnitPrice"):
            obj.addProperty("App::PropertyFloat", "UnitPrice", "Base", "Approximate linear price").UnitPrice = 0.0
        if not hasattr(obj, "Price"):
            obj.addProperty("App::PropertyFloat", "Price", "Base", "Profile Price").Price = 0.0
            obj.setEditorMode("Price", 1)
        if not hasattr(obj, "Thickness"):
            obj.addProperty("App::PropertyFloat", "Thickness", "Profile", "Thickness").Thickness = 0.0
        if not hasattr(obj, "ThicknessFlange"):
            obj.addProperty("App::PropertyFloat", "ThicknessFlange", "Profile", "Flange Thickness").ThicknessFlange = 0.0
        if not hasattr(obj, "RadiusLarge"):
            obj.addProperty("App::PropertyFloat", "RadiusLarge", "Profile", "Large radius").RadiusLarge = 0.0
        if not hasattr(obj, "RadiusSmall"):
            obj.addProperty("App::PropertyFloat", "RadiusSmall", "Profile", "Small radius").RadiusSmall = 0.0


class ViewProviderProfile:
    def __init__(self, vobj):
        """Set this object to the proxy object of the actual view provider"""
        vobj.Proxy = self

    def _ensureHelpers(self):
        from freecad.frameforgemod.preferences import (
            profile_show_helpers, profile_sphere_scale,
            profile_show_endpoints, profile_show_guide_lines, profile_show_labels,
            profile_point_size, profile_line_width,
        )

        if hasattr(self, "helpersSwitch") and self.helpersSwitch:
            self.ViewObject.RootNode.removeChild(self.helpersSwitch)
            self.helpersSwitch = None

        if not profile_show_helpers():
            return

        self.helpersSwitch = coin.SoSwitch()
        self.helpersSwitch.whichChild = coin.SO_SWITCH_NONE

        sph_d = profile_point_size() * profile_sphere_scale()
        lw = profile_line_width()
        font_size = int(1.4 * max(self.Object.Width.Value, self.Object.Height.Value))

        # Point 1
        if profile_show_endpoints():
            self.p1_tr = coin.SoTranslation()
            p1_sep = coin.SoSeparator()
            p1_sep.addChild(self.p1_tr)
            p1_sep.addChild(self._makeSphere(sph_d, (0, 0, 1)))  # blue

            # Point 2
            self.p2_tr = coin.SoTranslation()
            p2_sep = coin.SoSeparator()
            p2_sep.addChild(self.p2_tr)
            p2_sep.addChild(self._makeSphere(sph_d, (1, 0.25, 0)))  # orange

            self.helpersSwitch.addChild(p1_sep)
            self.helpersSwitch.addChild(p2_sep)

        # Line
        dir_sep = coin.SoSeparator()
        dir_style = coin.SoDrawStyle()
        dir_style.lineWidth = lw
        dir_sep.addChild(dir_style)
        self.dir_coords = coin.SoCoordinate3()
        self.dir_line = coin.SoLineSet()
        dir_sep.addChild(self.dir_coords)
        dir_sep.addChild(self.dir_line)
        self.helpersSwitch.addChild(dir_sep)

        # Guides
        if profile_show_guide_lines():
            self.p1_x_sep, self.p1_x_coords = self._makeGuideLine((1, 0, 0), lw)  # red
            self.p1_y_sep, self.p1_y_coords = self._makeGuideLine((0, 1, 0), lw)  # green
            self.p2_x_sep, self.p2_x_coords = self._makeGuideLine((1, 0, 0), lw)
            self.p2_y_sep, self.p2_y_coords = self._makeGuideLine((0, 1, 0), lw)
            self.helpersSwitch.addChild(self.p1_x_sep)
            self.helpersSwitch.addChild(self.p1_y_sep)
            self.helpersSwitch.addChild(self.p2_x_sep)
            self.helpersSwitch.addChild(self.p2_y_sep)

        # Labels
        if profile_show_labels():
            self.p1_label_tr = coin.SoTranslation()
            p1_label_sep = coin.SoSeparator()
            p1_label_sep.addChild(self.p1_label_tr)
            mat1 = coin.SoMaterial()
            mat1.diffuseColor = (1, 1, 1)
            p1_label_sep.addChild(mat1)
            font1 = coin.SoFont()
            font1.size = font_size
            p1_label_sep.addChild(font1)
            txt1 = coin.SoText2()
            txt1.string = "A"
            p1_label_sep.addChild(txt1)

            self.p2_label_tr = coin.SoTranslation()
            p2_label_sep = coin.SoSeparator()
            p2_label_sep.addChild(self.p2_label_tr)
            mat2 = coin.SoMaterial()
            mat2.diffuseColor = (1, 1, 1)
            p2_label_sep.addChild(mat2)
            font2 = coin.SoFont()
            font2.size = font_size
            p2_label_sep.addChild(font2)
            txt2 = coin.SoText2()
            txt2.string = "B"
            p2_label_sep.addChild(txt2)

            self.helpersSwitch.addChild(p1_label_sep)
            self.helpersSwitch.addChild(p2_label_sep)

        self.ViewObject.RootNode.addChild(self.helpersSwitch)

    def attach(self, vobj):
        self.ViewObject = vobj
        self.Object = vobj.Object
        self.ObjectName = vobj.Object.Name

        self._ensureHelpers()

        Gui.Selection.addObserver(self)

        self._updatePoints()

    def addSelection(self, doc, obj, sub, pnt):
        try:
            if obj == self.ObjectName:
                self.helpersSwitch.whichChild = coin.SO_SWITCH_ALL
        except Exception as e:
            App.Console.PrintMessage(f"ERROR addSelection {e} / {obj}\n")

    def clearSelection(self, other):
        self.helpersSwitch.whichChild = coin.SO_SWITCH_NONE

    def _makeSphere(self, dia, color):
        sep = coin.SoSeparator()
        mat = coin.SoMaterial()
        mat.diffuseColor = color
        sep.addChild(mat)
        sph = coin.SoSphere()
        sph.radius = dia
        sep.addChild(sph)
        return sep

    def _makeLocalFrame(self, p1, p2):
        # T = edge dir
        T = p2 - p1
        if T.Length == 0:
            return None, None
        T.normalize()

        # Choisir un vecteur "up" pas colinéaire
        up = App.Vector(0, 0, 1)
        if abs(T.dot(up)) > 0.9:
            up = App.Vector(0, 1, 0)

        # U et V dans le plan normal à l'edge
        U = T.cross(up)
        U.normalize()
        V = T.cross(U)
        V.normalize()

        return U, V

    def _makeGuideLine(self, color, line_width=2):
        sep = coin.SoSeparator()

        style = coin.SoDrawStyle()
        style.lineWidth = line_width
        sep.addChild(style)

        mat = coin.SoMaterial()
        mat.diffuseColor = color
        sep.addChild(mat)

        coords = coin.SoCoordinate3()
        line = coin.SoLineSet()
        sep.addChild(coords)
        sep.addChild(line)

        return sep, coords

    def _updatePoints(self):
        self._ensureHelpers()

        obj = self.Object
        if not obj or not hasattr(obj, "Target") or not obj.Target:
            return

        edge = obj.Target[0].getSubObject(obj.Target[1][0])
        p1 = edge.Vertexes[1].Point
        p2 = edge.Vertexes[0].Point

        # Local coordinates
        inv = obj.Placement.inverse()
        p1l = inv.multVec(p1) - App.Vector(0, 0, obj.OffsetA)
        p2l = inv.multVec(p2) + App.Vector(0, 0, obj.OffsetB)

        # Spheres
        self.p1_tr.translation.setValue(p1l.x, p1l.y, p1l.z)
        self.p2_tr.translation.setValue(p2l.x, p2l.y, p2l.z)

        offset = App.Vector(0, 0, max(obj.Width.Value, obj.Height.Value) / 2)

        p1_label_pos = p1l - offset
        p2_label_pos = p2l + offset

        self.p1_label_tr.translation.setValue(p1_label_pos.x, p1_label_pos.y, p1_label_pos.z)
        self.p2_label_tr.translation.setValue(p2_label_pos.x, p2_label_pos.y, p2_label_pos.z)

        # Normal Line
        self.dir_coords.point.setValues(0, 2, [(p1l.x, p1l.y, p1l.z), (p2l.x, p2l.y, p2l.z)])

        # Coord system
        L = max(obj.Width.Value, obj.Height.Value)

        self.p1_x_coords.point.setValues(
            0,
            2,
            [
                (p1l.x, p1l.y, p1l.z),
                (p1l.x + L, p1l.y, p1l.z),
            ],
        )

        self.p1_y_coords.point.setValues(
            0,
            2,
            [
                (p1l.x, p1l.y, p1l.z),
                (p1l.x, p1l.y + L, p1l.z),
            ],
        )

        self.p2_x_coords.point.setValues(
            0,
            2,
            [
                (p2l.x, p2l.y, p2l.z),
                (p2l.x + L, p2l.y, p2l.z),
            ],
        )

        self.p2_y_coords.point.setValues(
            0,
            2,
            [
                (p2l.x, p2l.y, p2l.z),
                (p2l.x, p2l.y + L, p2l.z),
            ],
        )

    def updateData(self, fp, prop):
        from PySide import QtCore
        def _apply_style():
            try:
                from freecad.frameforgemod.preferences import profile_point_size
                # LineWidth: controlled globally via FreeCAD → Edit → Preferences → Display → 3D View
                # self.ViewObject.LineWidth = profile_line_width()
                self.ViewObject.PointSize = profile_point_size()
            except Exception:
                pass
        QtCore.QTimer.singleShot(0, _apply_style)
        if prop in ["Target", "OffsetA", "OffsetB", "RotationAngle"]:
            try:
                self._updatePoints()
            except Exception:
                App.Console.PrintMessage(
                    f"Can't update profile {fp.Label} and helper in 3D, maybe linked to a migration\n"
                )

    def getDisplayModes(self, obj):
        """Return a list of display modes."""
        modes = []
        return modes

    def getDefaultDisplayMode(self):
        return "Flat Lines"

    def setDisplayMode(self, mode):
        """Map the display mode defined in attach with those defined in getDisplayModes.
        Since they have the same names nothing needs to be done. This method is optional.
        """
        return mode

    def claimChildren(self):
        children = []
        if self.Object.CustomProfile:
            children.append(self.Object.CustomProfile)
        return children

    def onChanged(self, vp, prop):
        """Print the name of the property that has changed"""
        # App.Console.PrintMessage("Change {} property: {}\n".format(str(vp), str(prop)))
        pass

    def onDelete(self, vobj, subelements):
        Gui.Selection.removeObserver(self)
        self.ViewObject.RootNode.removeChild(self.helpersSwitch)

        self.helpersSwitch = None

        return True

    def getIcon(self):
        """Return the icon in XMP format which will appear in the tree view. This method is optional
        and if not defined a default icon is shown.
        """
        return """
                /* XPM */
                static char * profile_xpm[] = {
                "16 16 15 1",
                " 	c None",
                ".	c #000000",
                "+	c #170000",
                "@	c #2E5DA2",
                "#	c #E8A200",
                "$	c #00172E",
                "%	c #A27400",
                "&	c #FFB900",
                "*	c #8B7400",
                "=	c #001717",
                "-	c #D1A200",
                ";	c #B98B00",
                ">	c #17172E",
                ",	c #2E1700",
                "'	c #171700",
                "                ",
                "                ",
                "                ",
                "                ",
                "  ....+.......  ",
                " .@@@@@@@@@@.#. ",
                " .@@@@@@@@@$%&* ",
                " =@@@@@@@@@$-&;.",
                " =@@@@@@@@@>-&;.",
                " >@@@@@@@@@=-&;.",
                " >@@@@@@@@@$%&* ",
                " .@@@@@@@@@@.-, ",
                "  '..'.+...'.'  ",
                "                ",
                "                ",
                "                "};
        	"""

    def dumps(self):
        return {}

    def loads(self, state):
        return

    def setEdit(self, vobj, mode):
        if mode != 0:
            return None

        if hasattr(self.Object, "CustomProfile") and self.Object.CustomProfile is not None:
            Gui.Selection.clearSelection()
            try:
                import freecad.frameforgemod.create_aluminum_profile

                taskd = freecad.frameforgemod.create_aluminum_profile.ImportAluminumProfileTaskPanel(
                    target_profile=self.Object
                )
                if Gui.Control.activeDialog():
                    Gui.Control.closeDialog()
                Gui.Control.showDialog(taskd)
                return True
            except Exception as e:
                App.Console.PrintError(f"setEdit failed: {e}\n")
                return None

        import freecad.frameforgemod.edit_profile_tool

        taskd = freecad.frameforgemod.edit_profile_tool.EditProfileTaskPanel(self.Object)
        if Gui.Control.activeDialog():
            Gui.Control.closeDialog()
        Gui.Control.showDialog(taskd)
        return True

    def unsetEdit(self, vobj, mode):
        if mode != 0:
            return None

        # self.helpersSwitch.whichChild = coin.SO_SWITCH_NONE

        Gui.Control.closeDialog()
        return True

    def edit(self):
        FreeCADGui.ActiveDocument.setEdit(self.Object, 0)


class ViewProviderCustomProfile(ViewProviderProfile):
    def getIcon(self):
        """Return the icon in XMP format which will appear in the tree view. This method is optional
        and if not defined a default icon is shown.
        """
        return """
            /* XPM */
            static char * custom_profile_xpm[] = {
            "16 16 44 1",
            " 	c None",
            ".	c #3463A1",
            "+	c #3465A4",
            "@	c #3464A1",
            "#	c #836628",
            "$	c #FBBC00",
            "%	c #304461",
            "&	c #335C92",
            "*	c #BC8D00",
            "=	c #FFBF00",
            "-	c #324C72",
            ";	c #32619D",
            ">	c #3364A2",
            ",	c #335888",
            "'	c #CF9B00",
            ")	c #B88A00",
            "!	c #1F6267",
            "~	c #27557E",
            "{	c #335889",
            "]	c #CE9B00",
            "^	c #3362A0",
            "/	c #2D578E",
            "(	c #06AE25",
            "_	c #0E9739",
            ":	c #2E5A93",
            "<	c #32619E",
            "[	c #3465A3",
            "}	c #335D93",
            "|	c #BA8C00",
            "1	c #274C7B",
            "2	c #088D24",
            "3	c #03BB1F",
            "4	c #00D61E",
            "5	c #00D41E",
            "6	c #03BC1F",
            "7	c #0A7D27",
            "8	c #3464A2",
            "9	c #7E632C",
            "0	c #FABB00",
            "a	c #03C01F",
            "b	c #00D81E",
            "c	c #05AB20",
            "d	c #01D21E",
            "e	c #01D31E",
            "                ",
            "                ",
            "                ",
            "                ",
            "                ",
            "  .++++++++@#$  ",
            " %+++++++++&*=  ",
            " -+++;>++++,'=) ",
            " -+++!~++++{]=) ",
            "  +^/(_:<[+}|=  ",
            "  1234567/+890  ",
            "    abb         ",
            "    cde         ",
            "                ",
            "                ",
            "                "};
        	"""

    def setEdit(self, vobj, mode):
        if mode != 0:
            return None

        Gui.Selection.clearSelection()

        try:
            import freecad.frameforgemod.create_aluminum_profile

            taskd = freecad.frameforgemod.create_aluminum_profile.ImportAluminumProfileTaskPanel(
                target_profile=self.Object
            )
            if Gui.Control.activeDialog():
                Gui.Control.closeDialog()
            Gui.Control.showDialog(taskd)
            return True
        except Exception as e:
            App.Console.PrintError(f"setEdit failed: {e}\n")
            import traceback
            traceback.print_exc()
            return None

    def unsetEdit(self, vobj, mode):
        if mode != 0:
            return None

        Gui.Control.closeDialog()
        return True

    def edit(self):
        FreeCADGui.ActiveDocument.setEdit(self.Object, 0)

    def onDelete(self, vobj, sub):
        """Delete associated Shape object if no other profile references it."""
        try:
            obj = vobj.Object
            if not hasattr(obj, "CustomProfile"):
                return True
            shape = obj.CustomProfile
            if shape is None or "_Shape_" not in shape.Name:
                return True
            doc = obj.Document
            for o in doc.Objects:
                if o is obj:
                    continue
                if hasattr(o, "CustomProfile") and o.CustomProfile is shape:
                    return True  # another profile still uses this shape
            # No other references: delete shape too
            doc.removeObject(shape.Name)
        except Exception:
            pass
        return True

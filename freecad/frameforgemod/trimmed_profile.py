import math

try:
    import ArchCommands
except ImportError:
    ArchCommands = None
try:
    import BOPTools.SplitAPI
except ImportError:
    BOPTools = None
import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtCore, QtGui

from freecad.frameforgemod._utils import (
    get_children_from_trimmedbody,
    get_profile_from_trimmedbody,
    get_readable_cutting_angles,
    get_trimmed_profile_all_cutting_angles,
    length_along_normal,
)
from freecad.frameforgemod.ff_tools import ICONPATH, PROFILEIMAGES_PATH, PROFILESPATH, UIPATH, translate
from freecad.frameforgemod.version import __version__ as ff_version


class TrimmedProfile:
    def __init__(self, obj):
        obj.addProperty(
            "App::PropertyString",
            "FrameforgeVersion",
            "Profile",
            translate("App::Property", "Frameforge Version used to create the profile"),
        ).FrameforgeVersion = ff_version

        obj.addProperty(
            "App::PropertyString",
            "PID",
            "Profile",
            translate("App::Property", "Profile ID"),
        ).PID = ""
        obj.setEditorMode("PID", 1)

        obj.addProperty(
            "App::PropertyLinkHidden", "TrimmedBody", "TrimmedProfile", translate("App::Property", "Body to be trimmed")
        ).TrimmedBody = None
        obj.addProperty(
            "App::PropertyLinkSubList",
            "TrimmingBoundary",
            "TrimmedProfile",
            translate("App::Property", "Bodies that define boundaries"),
        ).TrimmingBoundary = None

        obj.addProperty(
            "App::PropertyEnumeration",
            "TrimmedProfileType",
            "TrimmedProfile",
            translate("App::Property", "TrimmedProfile Type"),
        ).TrimmedProfileType = ["End Trim", "End Miter"]
        obj.addProperty(
            "App::PropertyEnumeration", "CutType", "TrimmedProfile", translate("App::Property", "Cut Type")
        ).CutType = [
            "Simple fit",
            "Perfect fit",
        ]

        obj.addProperty(
            "App::PropertyLength", "Gap", "TrimmedProfile", translate("App::Property", "Gap between mitered profiles")
        ).Gap = 0

        # related to Profile
        obj.addProperty("App::PropertyString", "Family", "Profile", "")
        obj.setEditorMode("Family", 1)

        obj.addProperty("App::PropertyLink", "CustomProfile", "Profile",
                        translate("App::Property", "Target profile")).CustomProfile = None
        obj.setEditorMode("CustomProfile", 1)

        obj.addProperty("App::PropertyString", "SizeName", "Profile", "")
        obj.setEditorMode("SizeName", 1)

        obj.addProperty("App::PropertyString", "Material", "Profile", "")
        obj.setEditorMode("Material", 1)

        obj.addProperty("App::PropertyFloat", "ApproxWeight", "Base",
                        translate("App::Property", "Approximate weight in Kilogram"))
        obj.setEditorMode("ApproxWeight", 1)

        obj.addProperty("App::PropertyFloat", "Price", "Base",
                        translate("App::Property", "Profile Price"))
        obj.setEditorMode("Price", 1)

        # structure
        obj.addProperty("App::PropertyLength", "Width", "Structure",
                        translate("App::Property", "Parameter for structure"))
        obj.addProperty("App::PropertyLength", "Height", "Structure",
                        translate("App::Property", "Parameter for structure"))
        obj.addProperty("App::PropertyLength", "Length", "Structure",
                        translate("App::Property", "Parameter for structure"))
        obj.addProperty("App::PropertyBool", "Cutout", "Structure",
                        translate("App::Property", "Has Cutout")).Cutout = False
        obj.setEditorMode("Width", 1)  # user doesn't change !
        obj.setEditorMode("Height", 1)
        obj.setEditorMode("Length", 1)
        obj.setEditorMode("Cutout", 1)

        obj.addProperty(
            "App::PropertyString",
            "CuttingAngleA",
            "Structure",
            translate("App::Property", "Cutting Angle A"),
        )
        obj.setEditorMode("CuttingAngleA", 1)
        obj.addProperty(
            "App::PropertyString",
            "CuttingAngleB",
            "Structure",
            translate("App::Property", "Cutting Angle B"),
        )
        obj.setEditorMode("CuttingAngleB", 1)

        obj.Proxy = self
        self._cached_key = None
        self._cached_shape = None

    def dumps(self):
        return None

    def loads(self, state):
        self._cached_key = None
        self._cached_shape = None

    def _trim_key(self, fp):
        try:
            key_parts = [fp.TrimmedProfileType, fp.CutType, fp.Gap]
            body = fp.TrimmedBody
            s = getattr(body, "Shape", None)
            if s and not s.isNull():
                bb = s.BoundBox
                key_parts.append(hash((bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax)))
            for link in fp.TrimmingBoundary:
                for sub in link[1]:
                    try:
                        face = link[0].getSubObject(sub)
                        if face and not face.isNull():
                            bb = face.BoundBox
                            key_parts.append(hash((bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax)))
                    except Exception:
                        pass
            return hash(tuple(key_parts))
        except Exception:
            return None

    def onChanged(self, fp, prop):
        """Clear cache when trimming parameters change, forcing fresh recompute."""
        if prop in ("TrimmedBody", "TrimmingBoundary", "Gap", "TrimmedProfileType", "CutType"):
            self._cached_key = None
            self._cached_shape = None

    def execute(self, fp):
        """Print a short message when doing a recomputation, this method is mandatory"""
        self.run_compatibility_migrations(fp)

        # TODO: Put these methods in proper functions
        if fp.TrimmedBody is None:
            return
        if len(fp.TrimmingBoundary) == 0:
            return

        # Cache disabled: matches original FrameForge behavior exactly
        # cache_key = self._trim_key(fp)
        # if cache_key is not None and self._cached_key == cache_key and self._cached_shape is not None:
        #     fp.Shape = self._cached_shape
        #     self._update_structure_data(fp)
        #     return

        # hide trimmed body
        for tb in get_children_from_trimmedbody(fp.TrimmedBody):
            tb.ViewObject.Visibility = False

        body = fp.TrimmedBody
        work_shape = body.Shape
        raw_shape = work_shape  # keep original for COG checks

        # Auto-extend body to reach each trimming plane
        extra_extend = 0.0
        if fp.TrimmedProfileType == "End Miter":
            try:
                prof = get_profile_from_trimmedbody(fp)
                if prof:
                    w = float(prof.ProfileWidth) if hasattr(prof, 'ProfileWidth') else 0
                    h = float(prof.ProfileHeight) if hasattr(prof, 'ProfileHeight') else 0
                    extra_extend = max(w, h) * 1.5
            except Exception:
                pass
            if extra_extend <= 0:
                extra_extend = 50.0

        if fp.TrimmedProfileType != "End Miter":
            for link in fp.TrimmingBoundary:
                for sub in link[1]:
                    face = link[0].getSubObject(sub)
                    if not hasattr(face, 'Surface') or not isinstance(face.Surface, Part.Plane):
                        continue
                    extended = self._extend_to_plane(work_shape, face, extra=extra_extend)
                    if extended is not work_shape:
                        work_shape = extended
                    break

        cut_shapes = []

        if fp.TrimmedProfileType == "End Trim":
            if fp.CutType in ["Perfect fit", "Coped cut"]:
                shapes = [x[0].Shape for x in fp.TrimmingBoundary]
                if BOPTools is not None:
                    shps = BOPTools.SplitAPI.slice(work_shape, shapes, mode="Split")
                    for solid in shps.Solids:
                        cg = work_shape.CenterOfGravity
                        if not solid.BoundBox.isInside(cg.x, cg.y, cg.z):
                            cut_shapes.append(Part.Shape(solid))
                else:
                    for link in fp.TrimmingBoundary:
                        part = link[0]
                        for sub in link[1]:
                            face = part.getSubObject(sub)
                            if isinstance(face.Surface, Part.Plane):
                                shp = self.getOutsideCV(face, work_shape, raw_shape)
                                cut_shapes.append(shp)

            elif fp.CutType in ["Simple fit", "Simple cut"]:
                for link in fp.TrimmingBoundary:
                    part = link[0]
                    for sub in link[1]:
                        face = part.getSubObject(sub)
                        if isinstance(face.Surface, Part.Plane):
                            shp = self.getOutsideCV(face, work_shape, raw_shape)
                            cut_shapes.append(shp)

        elif fp.TrimmedProfileType == "End Miter":
            doc = App.activeDocument()
            precision = 0.5

            def _endpoints(obj):
                """Get (start, end, dir_vec) from profile object.
                Uses Target edge if available, falls back to Placement+Length."""
                target = self.getTarget(obj)
                if target is not None:
                    try:
                        subname = target[1]
                        if isinstance(subname, (list, tuple)):
                            subname = subname[0]
                        edge = doc.getObject(target[0].Name).getSubObject(str(subname))
                        if edge is not None and hasattr(edge, 'Vertexes'):
                            s = edge.Vertexes[0].Point
                            e = edge.Vertexes[-1].Point
                            return s, e, s.sub(e)
                    except Exception:
                        pass
                # Fallback: derive from base profile's Placement + Length
                root = get_profile_from_trimmedbody(obj)
                if root is None:
                    root = obj
                pl = root.Placement
                ln = 0.0
                if hasattr(root, 'ProfileLength') and root.ProfileLength:
                    ln = float(root.ProfileLength)
                elif hasattr(obj, 'Length') and obj.Length:
                    ln = float(obj.Length)
                elif hasattr(obj, 'ProfileLength') and obj.ProfileLength:
                    ln = float(obj.ProfileLength)
                if ln > 0:
                    s = pl.Base
                    e = pl.multVec(App.Vector(0, 0, ln))
                    return s, e, s.sub(e)
                # Last resort: use longest edge of shape for direction
                try:
                    shape = root.Shape if root is not None else obj.Shape
                    if shape and shape.Edges:
                        longest = max(shape.Edges, key=lambda e: e.Length)
                        s = longest.Vertexes[0].Point
                        e = longest.Vertexes[-1].Point
                        return s, e, s.sub(e)
                except Exception:
                    pass
                # Failsafe: return zero vector (will be caught by angle check below)
                z = App.Vector(0, 0, 0)
                return z, z, z

            start1, end1, vec1 = _endpoints(fp.TrimmedBody)
            if vec1.Length >= precision:
                trimming_boundary_endpoints = []
                for bound in fp.TrimmingBoundary:
                    sp, ep, vp = _endpoints(bound[0])
                    if vp.Length < precision:
                        continue
                    trimming_boundary_endpoints.append((sp, ep, vp))
                if not trimming_boundary_endpoints:
                    App.Console.PrintMessage("End Miter: could not determine direction for boundary\n")
                for start2, end2, vec2 in trimming_boundary_endpoints:

                    angle = math.degrees(vec1.getAngle(vec2))

                    if (end1.distanceToPoint(start2) < precision
                            or start1.distanceToPoint(end2) < precision
                            or start1.distanceToPoint(start2) < precision):
                        angle = 180 - angle

                    bisect = angle / 2.0

                    if start1.distanceToPoint(start2) < precision:
                        p1 = start1
                        p2 = end1
                        p3 = end2
                    elif start1.distanceToPoint(end2) < precision:
                        p1 = start1
                        p2 = end1
                        p3 = start2
                    elif end1.distanceToPoint(start2) < precision:
                        p1 = end1
                        p2 = start1
                        p3 = end2
                    elif end1.distanceToPoint(end2) < precision:
                        p1 = end1
                        p2 = start1
                        p3 = start2
                    else:
                        App.Console.PrintMessage(
                            f"End Miter: no common endpoint found.\n"
                            f"  Beam1: start={start1} end={end1}\n"
                            f"  Beam2: start={start2} end={end2}\n"
                            f"  Distances: ss={start1.distanceToPoint(start2):.4f} "
                            f"se={start1.distanceToPoint(end2):.4f} "
                            f"es={end1.distanceToPoint(start2):.4f} "
                            f"ee={end1.distanceToPoint(end2):.4f}\n")
                        raise RuntimeError("End Miter: edges not aligned. Ensure they meet at a common endpoint.")

                    # Auto-extend body past the corner for miter clearance.
                    # The standard auto-extend loop above cannot handle edges stored
                    # in TrimmingBoundary, so we extend here directly.
                    body_dir = vec1.normalize()
                    proj_vals = [(v.Point.dot(body_dir), v.Point) for v in work_shape.Vertexes]
                    if proj_vals:
                        max_proj, _ = max(proj_vals, key=lambda x: x[0])
                        min_proj, _ = min(proj_vals, key=lambda x: x[0])
                        corner_proj = p1.dot(body_dir)
                        if abs(max_proj - corner_proj) < abs(min_proj - corner_proj):
                            side = 1
                            end_val = max_proj
                        else:
                            side = -1
                            end_val = min_proj
                        end_faces = []
                        for f in work_shape.Faces:
                            try:
                                fc = f.CenterOfGravity.dot(body_dir)
                                if abs(fc - end_val) > 0.1:
                                    continue
                                n = f.normalAt(0.5, 0.5)
                                if n.dot(body_dir) * side < 0.1:
                                    continue
                                end_faces.append(f)
                            except Exception:
                                continue
                        if end_faces:
                            end_face = max(end_faces, key=lambda f: f.Area)
                            gap_val = fp.Gap.Value if hasattr(fp.Gap, 'Value') else float(fp.Gap)
                            ext_dir = body_dir * side * max(0.0, extra_extend * 2 + 5 - gap_val)
                            try:
                                extruded = end_face.extrude(ext_dir)
                                if not extruded.isNull() and extruded.isValid():
                                    work_shape = work_shape.fuse(extruded)
                                    try:
                                        work_shape = work_shape.removeSplitter()
                                    except Exception:
                                        pass
                                    App.Console.PrintMessage(
                                        f"Auto-extended {extra_extend:.0f}mm for miter\n")
                            except Exception:
                                pass
                    # --- end auto-extend ---

                    # Offset cut plane along body direction to create visual gap
                    gap_val = float(fp.Gap) if hasattr(fp, 'Gap') else 0
                    if gap_val != 0:
                        body_dir = vec1.normalize()
                        corner_proj = p1.dot(body_dir)
                        proj_check = [(v.Point.dot(body_dir), v.Point) for v in work_shape.Vertexes]
                        if proj_check:
                            max_p, _ = max(proj_check, key=lambda x: x[0])
                            min_p, _ = min(proj_check, key=lambda x: x[0])
                            s = -1 if abs(max_p - corner_proj) < abs(min_p - corner_proj) else 1
                            p1 = p1 + body_dir * s * (gap_val / 2.0)

                    normal = Part.Plane(p1, p2, p3).toShape().normalAt(0, 0)
                    # Size the cutting plane to fully cover the profile cross-section
                    try:
                        prof = get_profile_from_trimmedbody(fp)
                        if prof:
                            pw = float(prof.ProfileWidth) if hasattr(prof, 'ProfileWidth') else 40
                            ph = float(prof.ProfileHeight) if hasattr(prof, 'ProfileHeight') else 40
                        else:
                            pw, ph = 40, 40
                    except Exception:
                        pw, ph = 40, 40
                    ps = max(pw, ph) * 3
                    cutplane = Part.makePlane(ps, ps, p1, vec1, normal)
                    cutplane.rotate(p1, normal, -90 + bisect)
                    cut_shapes.append(self.getOutsideCV(cutplane, work_shape, raw_shape))

        cut_shapes = [s for s in cut_shapes if s is not None and not s.isNull()]
        cut_shape = Part.Shape()
        if len(cut_shapes) > 0:
            cut_shape = Part.Shape(cut_shapes[0])
            for sh in cut_shapes[1:]:
                cut_shape = cut_shape.fuse(sh)

        self.makeShape(fp, cut_shape, work_shape)
        # self._cached_key = cache_key
        # self._cached_shape = fp.Shape
        self._update_structure_data(fp)

    def _update_structure_data(self, obj):
        try:
            prof = get_profile_from_trimmedbody(obj)
            if prof is None:
                return
            angles = get_trimmed_profile_all_cutting_angles(obj)
            obj.Length = length_along_normal(obj)
        except Exception:
            return

        obj.PID = getattr(prof, "PID", "")
        obj.Width = getattr(prof, "ProfileWidth", 0)
        obj.Height = getattr(prof, "ProfileHeight", 0)
        obj.Family = getattr(prof, "Family", "")
        obj.CustomProfile = getattr(prof, "CustomProfile", None)
        obj.SizeName = getattr(prof, "SizeName", "")
        obj.Material = getattr(prof, "Material", "")
        obj.ApproxWeight = getattr(prof, "ApproxWeight", 0)
        obj.Price = getattr(prof, "Price", 0)

        cut_angles = get_readable_cutting_angles(
            getattr(prof, "BevelACutY", "N/A"),
            getattr(prof, "BevelACutX", "N/A"),
            getattr(prof, "BevelBCutY", "N/A"),
            getattr(prof, "BevelBCutX", "N/A"),
            *angles,
        )

        obj.CuttingAngleA = cut_angles[0]
        obj.CuttingAngleB = cut_angles[1]

    def run_compatibility_migrations(self, obj):
        if not hasattr(obj, "FrameforgeVersion"):
            # migrate parents
            for link in obj.TrimmingBoundary:
                link[0].Proxy.execute(link[0])
            obj.TrimmedBody.Proxy.execute(obj.TrimmedBody)

            App.Console.PrintMessage(f"Frameforge::object migration : Migrate {obj.Label} to 0.1.8\n")

            # related to Profile
            obj.addProperty(
                "App::PropertyString",
                "PID",
                "Profile",
                "Profile ID",
            ).PID = ""
            obj.setEditorMode("PID", 1)

            obj.addProperty("App::PropertyString", "Family", "Profile", "")
            obj.setEditorMode("Family", 1)

            obj.addProperty("App::PropertyLink", "CustomProfile", "Profile", "Target profile").CustomProfile = None
            obj.setEditorMode("CustomProfile", 1)

            obj.addProperty("App::PropertyString", "SizeName", "Profile", "")
            obj.setEditorMode("SizeName", 1)

            obj.addProperty("App::PropertyString", "Material", "Profile", "")
            obj.setEditorMode("Material", 1)

            obj.addProperty("App::PropertyFloat", "ApproxWeight", "Base", "Approximate weight in Kilogram")
            obj.setEditorMode("ApproxWeight", 1)

            obj.addProperty("App::PropertyFloat", "Price", "Base", "Profile Price")
            obj.setEditorMode("Price", 1)

            # structure
            obj.addProperty("App::PropertyLength", "Width", "Structure", "Parameter for structure")
            obj.addProperty("App::PropertyLength", "Height", "Structure", "Parameter for structure")
            obj.addProperty("App::PropertyLength", "Length", "Structure", "Parameter for structure")
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

            # add version
            obj.addProperty(
                "App::PropertyString",
                "FrameforgeVersion",
                "Profile",
                "Frameforge Version used to create the profile",
            ).FrameforgeVersion = ff_version

    def getOutsideCV(self, cutplane, shape, cog_shape=None):
        """Return the offcut piece — ArchCommands, fallback to direct cut.
        cog_shape: optional shape used for COG check (when shape is extended).
        """
        cog_src = cog_shape if cog_shape is not None else shape
        if ArchCommands is not None:
            try:
                cv = ArchCommands.getCutVolume(cutplane, shape, clip=False, depth=0.0)
                if cv is not None and len(cv) >= 3:
                    half1, half2 = cv[1], cv[2]
                    if half1 is not None and not half1.isNull() and half2 is not None and not half2.isNull():
                        if half1.isInside(cog_src.CenterOfGravity, 0.001, False):
                            return half2
                        else:
                            return half1
                    if half1 is not None and not half1.isNull():
                        return half1
                    if half2 is not None and not half2.isNull():
                        return half2
            except Exception:
                pass

        # Fallback: extrude cutting face along shape's longest axis
        try:
            surf = getattr(cutplane, 'Surface', None)
            if surf is None and isinstance(cutplane, Part.Face):
                surf = cutplane.Surface
            if not isinstance(surf, Part.Plane):
                return Part.Shape()
            face_normal = surf.Axis

            # Find shape's longest axis (extrusion direction)
            bb = shape.BoundBox
            axes = [(bb.XLength, App.Vector(1,0,0)),
                    (bb.YLength, App.Vector(0,1,0)),
                    (bb.ZLength, App.Vector(0,0,1))]
            axes.sort(key=lambda x: -x[0])
            beam_dir = axes[0][1]

            pos = surf.Position
            d = 10000

            # Create large plane at face position, oriented along face normal
            plane = Part.makePlane(d, d, pos, face_normal)
            for direction in (beam_dir, -beam_dir):
                half = plane.extrude(direction * d)
                if half.isNull() or not half.isValid():
                    continue
                offcut = shape.common(half)
                if not offcut.isNull() and offcut.isValid() and offcut.Volume > 0:
                    return offcut
            return Part.Shape()
        except Exception:
            return Part.Shape()

    def makeShape(self, fp, cutshape, base_shape=None):
        if base_shape is None:
            base_shape = fp.TrimmedBody.Shape
        if not cutshape.isNull():
            fp.Shape = base_shape.cut(cutshape)
        else:
            fp.Shape = base_shape

    def getTarget(self, link):
        visited = set()
        while True:
            if id(link) in visited:
                return None
            visited.add(id(link))
            if hasattr(link, "Target"):
                return link.Target
            elif hasattr(link, "TrimmedProfileType"):
                link = link.TrimmedBody
            else:
                return None

    def _extend_to_plane(self, shape, trimming_face, extra=0.0):
        """Extend shape past trimming plane. Pure shape operation, no permanent body changes.
        extra: minimum extension beyond the plane (used by End Miter for diagonal clearance).
        """
        surf = trimming_face.Surface
        if not isinstance(surf, Part.Plane):
            return shape

        # Find the body's length direction from its longest edge (extrusion direction)
        length_dir = None
        max_len = 0
        for e in shape.Edges:
            if e.Length > max_len:
                max_len = e.Length
                try:
                    v = e.Vertexes[1].Point - e.Vertexes[0].Point
                    length_dir = v.normalize()
                except Exception:
                    pass
        if length_dir is None or max_len <= 0:
            return shape

        plane_p = surf.Position.dot(length_dir)
        proj = [v.Point.dot(length_dir) for v in shape.Vertexes]
        if not proj:
            return shape

        # Determine gap and direction along body length
        if min(proj) <= plane_p <= max(proj):
            # Body already reaches the plane
            if extra <= 0:
                return shape
            # Force extension for miter diagonal clearance.
            # Use 3D distance from face center to each body end for direction.
            face_center = surf.Position
            # Approximate the 3D end points of the body along length_dir
            min_pt_3d = None
            max_pt_3d = None
            best_min = None
            best_max = None
            for v in shape.Vertexes:
                d = v.Point.dot(length_dir)
                if best_min is None or d < best_min:
                    best_min = d
                    min_pt_3d = v.Point
                if best_max is None or d > best_max:
                    best_max = d
                    max_pt_3d = v.Point
            if min_pt_3d is not None and max_pt_3d is not None:
                dist_min = face_center.distanceToPoint(min_pt_3d)
                dist_max = face_center.distanceToPoint(max_pt_3d)
                if dist_max <= dist_min:
                    side = 1
                    end_val = max(proj)
                else:
                    side = -1
                    end_val = min(proj)
            else:
                side = 1
                end_val = max(proj)
            gap = extra
        else:
            # Body does not reach the plane
            if plane_p > max(proj):
                gap = plane_p - max(proj)
                side = 1
                end_val = max(proj)
            else:
                gap = min(proj) - plane_p
                side = -1
                end_val = min(proj)
            gap += extra

        # Find the end face: planar face at extreme end, facing outward,
        # with largest area (to prefer outer face over inner hole face)
        candidates = []
        for f in shape.Faces:
            try:
                fc = f.CenterOfGravity.dot(length_dir)
                if abs(fc - end_val) > 0.1:
                    continue
                # Face normal must point roughly toward the plane
                try:
                    n = f.normalAt(0.5, 0.5)
                    if n.dot(length_dir) * side < 0.1:
                        continue
                except Exception:
                    continue
                candidates.append(f)
            except Exception:
                continue

        if not candidates:
            App.Console.PrintMessage("Auto-extend: no end face found at extreme end\n")
            return shape

        # Pick the face with largest area (prefers outer wall over inner hole face)
        end_face = max(candidates, key=lambda f: f.Area)

        try:
            ext_dir = length_dir * side * (gap * 2 + 5)
            extruded = end_face.extrude(ext_dir)
            if extruded.isNull() or not extruded.isValid():
                return shape
            result = shape.fuse(extruded)
            if result.isNull() or not result.isValid():
                return shape
            # Remove seam edge at fusion boundary for seamless appearance
            try:
                result = result.removeSplitter()
            except Exception:
                pass
            App.Console.PrintMessage(f"Auto-extended {gap:.0f}mm\n")
            return result
        except Exception as e:
            App.Console.PrintMessage(f"Auto-extend failed: {e}\n")
            return shape


class ViewProviderTrimmedProfile:
    def __init__(self, vobj):
        """Set this object to the proxy object of the actual view provider"""
        vobj.Proxy = self
        self.ViewObject = vobj
        self.Object = vobj.Object
        vobj.ShapeColor = (0.6, 0.6, 0.6)
        vobj.Transparency = 0

    def attach(self, vobj):
        """Setup the scene sub-graph of the view provider, this method is mandatory"""
        self.ViewObject = vobj
        self.Object = vobj.Object
        vobj.ShapeColor = (0.6, 0.6, 0.6)
        vobj.Transparency = 0

    def updateData(self, fp, prop):
        """Sync visual properties from the original profile, but preserve user-customized colors."""
        if prop == "TrimmedBody" and fp.TrimmedBody:
            vp = fp.TrimmedBody.ViewObject
            self.ViewObject.ShapeColor = vp.ShapeColor
            self.ViewObject.Transparency = vp.Transparency
        return

    def getDisplayModes(self, obj):
        """Return a list of display modes."""
        modes = []
        return modes

    def getDefaultDisplayMode(self):
        """Return the name of the default display mode. It must be defined in getDisplayModes."""
        return "FlatLines"

    def setDisplayMode(self, mode):
        """Map the display mode defined in attach with those defined in getDisplayModes.
        Since they have the same names nothing needs to be done. This method is optional.
        """
        return mode

    def claimChildren(self):
        return [self.Object.TrimmedBody]

    def onChanged(self, vp, prop):
        """Print the name of the property that has changed"""
        # App.Console.PrintMessage("Change {} property: {}\n".format(str(vp), str(prop)))
        pass

    def onDelete(self, fp, sub):
        if self.Object.TrimmedBody:
            self.Object.TrimmedBody.ViewObject.Visibility = True
        return True

    def getIcon(self):
        """Return the icon in XMP format which will appear in the tree view. This method is optional
        and if not defined a default icon is shown.
        """
        return """
        	/* XPM */
                static char * corner_xpm[] = {
                "16 16 4 1",
                " 	c None",
                ".	c #000000",
                "+	c #3465A4",
                "@	c #ED2B00",
                "         ..     ",
                "       ..++..   ",
                "   .....+++++.  ",
                " ..@@@@@.+++... ",
                " .@.@@@@@.+.++. ",
                " .@@.@...@.+++. ",
                " .@@@.@@@@.+++. ",
                " .@@@.@@@@.+++. ",
                " ..@@.@@@@....  ",
                " .+.@.@@...     ",
                " .++....++.     ",
                " .+++.++++.     ",
                " .+++.++++.     ",
                "  .++.++++.     ",
                "   .+.+...      ",
                "    ...         "};
        	"""

    def __getstate__(self):
        """When saving the document this object gets stored using Python's cPickle module.
        Since we have some un-pickable here -- the Coin stuff -- we must define this method
        to return a tuple of all pickable objects or None.
        """
        return None

    def __setstate__(self, state):
        """When restoring the pickled object from document we have the chance to set some
        internals here. Since no data were pickled nothing needs to be done here.
        """
        return None

    def setEdit(self, vobj, mode):
        if mode != 0:
            return None

        import freecad.frameforgemod.create_trimmed_profiles_tool

        taskd = freecad.frameforgemod.create_trimmed_profiles_tool.CreateTrimmedProfileTaskPanel(
            self.Object, mode="edition"
        )
        Gui.Control.showDialog(taskd)
        return True

    def unsetEdit(self, vobj, mode):
        if mode != 0:
            return None

        Gui.Control.closeDialog()
        return True

    def edit(self):
        Gui.ActiveDocument.setEdit(self.Object, 0)

# **************************************************************************************
# *                                                                                    *
# *    BOLTS - Open Library of Technical Specifications                                *
# *                                                                                    *
# *    Copyright (C) 2014 Johannes Reinhardt <jreinhardt@ist-dein-freund.de>           *
# *                                                                                    *
# *    This library is free software; you can redistribute it and/or                   *
# *    modify it under the terms of the GNU Lesser General Public                      *
# *    License as published by the Free Software Foundation; either                    *
# *    version 2.1 of the License, or any later version.                               *
# *                                                                                    *
# *    This library is distributed in the hope that it will be useful,                 *
# *    but WITHOUT ANY WARRANTY; without even the implied warranty of                  *
# *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU                *
# *    Lesser General Public License for more details.                                 *
# *                                                                                    *
# *    You should have received a copy of the GNU Lesser General Public                *
# *    License along with this library; if not, write to the Free Software             *
# *    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA    *
# *                                                                                    *
# **************************************************************************************


import math
from functools import lru_cache

import Part
from DraftGeomUtils import fillet as draft_fillet
from FreeCAD import Vector


# ************************************************************************************************
# ************************************************************************************************
@lru_cache(maxsize=None)
def vslot20x20():
    # due to symmetry this can be nicely decomposed
    # x offset, y offset, reverse, switch, mir_x, mir_y
    symmetry = [
        (0, 0, False, False, False, False),
        (0, 0, True, True, False, False),
        (0, 0, False, True, True, False),
        (0, 0, True, False, True, False),
        (0, 0, False, False, True, True),
        (0, 0, True, True, True, True),
        (0, 0, False, True, False, True),
        (0, 0, True, False, False, True),
    ]

    vertices = 8 * [vslot_outline]
    fillets = [5, 17, 29, 41]
    corner_offset = 0
    circle_offsets = [0]

    face = vslot(symmetry, vertices, fillets, corner_offset, circle_offsets)

    return face


# ************************************************************************************************
@lru_cache(maxsize=None)
def vslot20x40():
    # due to symmetry this can be nicely decomposed
    # x offset, y offset, reverse, switch, mir_x, mir_y
    symmetry = [
        (0, 0, False, False, False, False),
        (0, 0, True, True, False, False),
        (0, 0, False, True, True, False),
        (-w, 0, True, True, False, False),
        (-w, 0, False, True, True, False),
        (-w, 0, True, False, True, False),
        (-w, 0, False, False, True, True),
        (-w, 0, True, True, True, True),
        (-w, 0, False, True, False, True),
        (0, 0, True, True, True, True),
        (0, 0, False, True, False, True),
        (0, 0, True, False, False, True),
    ]

    vertices = 12 * [vslot_outline]

    fillets = [5, 29, 41, 65]
    corner_offset = -1 * w
    circle_offsets = [0, -w]

    face = vslot(symmetry, vertices, fillets, corner_offset, circle_offsets)
    return face


# ************************************************************************************************
@lru_cache(maxsize=None)
def vslot20x60():
    # due to symmetry this can be nicely decomposed
    # x offset, y offset, reverse, switch, mir_x, mir_y
    symmetry = [
        (0, 0, False, False, False, False),
        (0, 0, True, True, False, False),
        (0, 0, False, True, True, False),
        (-w, 0, True, True, False, False),
        (-w, 0, False, True, True, False),
        (-2 * w, 0, True, True, False, False),
        (-2 * w, 0, False, True, True, False),
        (-2 * w, 0, True, False, True, False),
        (-2 * w, 0, False, False, True, True),
        (-2 * w, 0, True, True, True, True),
        (-2 * w, 0, False, True, False, True),
        (-w, 0, True, True, True, True),
        (-w, 0, False, True, False, True),
        (0, 0, True, True, True, True),
        (0, 0, False, True, False, True),
        (0, 0, True, False, False, True),
    ]

    vertices = 16 * [vslot_outline]

    # add fillets in reverse order, as this inserts additional edges
    fillets = [5, 41, 53, 89]
    corner_offset = -2 * w
    circle_offsets = [0, -w, -2 * w]

    face = vslot(symmetry, vertices, fillets, corner_offset, circle_offsets)
    return face


# ************************************************************************************************
@lru_cache(maxsize=None)
def vslot20x80():
    # due to symmetry this can be nicely decomposed
    # x offset, y offset, reverse, switch, mir_x, mir_y
    symmetry = [
        (0, 0, False, False, False, False),
        (0, 0, True, True, False, False),
        (0, 0, False, True, True, False),
        (-w, 0, True, True, False, False),
        (-w, 0, False, True, True, False),
        (-2 * w, 0, True, True, False, False),
        (-2 * w, 0, False, True, True, False),
        (-3 * w, 0, True, True, False, False),
        (-3 * w, 0, False, True, True, False),
        (-3 * w, 0, True, False, True, False),
        (-3 * w, 0, False, False, True, True),
        (-3 * w, 0, True, True, True, True),
        (-3 * w, 0, False, True, False, True),
        (-2 * w, 0, True, True, True, True),
        (-2 * w, 0, False, True, False, True),
        (-w, 0, True, True, True, True),
        (-w, 0, False, True, False, True),
        (0, 0, True, True, True, True),
        (0, 0, False, True, False, True),
        (0, 0, True, False, False, True),
    ]

    vertices = 20 * [vslot_outline]

    # add fillets in reverse order, as this inserts additional edges
    fillets = [5, 53, 65, 113]
    corner_offset = -3 * w
    circle_offsets = [0, -w, -2 * w, -3 * w]

    face = vslot(symmetry, vertices, fillets, corner_offset, circle_offsets)
    return face


# ************************************************************************************************
@lru_cache(maxsize=None)
def tslot20x20():
    # due to symmetry this can be nicely decomposed
    # x offset, y offset, reverse, switch, mir_x, mir_y
    symmetry = [
        (0, 0, False, False, False, False),
        (0, 0, True, True, False, False),
        (0, 0, False, True, True, False),
        (0, 0, True, False, True, False),
        (0, 0, False, False, True, True),
        (0, 0, True, True, True, True),
        (0, 0, False, True, False, True),
        (0, 0, True, False, False, True),
    ]

    vertices = 8 * [tslot_outline]
    fillets = [5, 17, 29, 41]
    corner_offset = 0
    circle_offsets = [0]

    face = tslot(symmetry, vertices, fillets, [], [], corner_offset, circle_offsets)
    return face


# ************************************************************************************************
@lru_cache(maxsize=None)
def tslot20x20_three_slot():
    # due to symmetry this can be nicely decomposed
    # x offset, y offset, reverse, switch, mir_x, mir_y
    symmetry = [
        (0, 0, False, False, False, False),
        (0, 0, True, True, False, False),
        (0, 0, False, True, True, False),
        (0, 0, True, False, True, False),
        (0, 0, False, False, True, True),
        (0, 0, True, True, True, True),
        (0, 0, False, True, False, True),
        (0, 0, True, False, False, True),
    ]

    vertices = [tslot_outline] + 2 * [tslot_closed] + 5 * [tslot_outline]
    fillets = [5, 7, 19, 31]

    closed_symmetry = [
        (0, 0, False, True, False, False),
    ]
    closed_vertices = [tslot_closed_space]

    corner_offset = 0
    circle_offsets = [0]

    face = tslot(
        symmetry,
        vertices,
        fillets,
        closed_symmetry,
        closed_vertices,
        corner_offset,
        circle_offsets,
    )
    return face


# ************************************************************************************************
@lru_cache(maxsize=None)
def tslot20x20_two_slot():
    # due to symmetry this can be nicely decomposed
    # x offset, y offset, reverse, switch, mir_x, mir_y
    symmetry = [
        (0, 0, False, False, False, False),
        (0, 0, True, True, False, False),
        (0, 0, False, True, True, False),
        (0, 0, True, False, True, False),
        (0, 0, False, False, True, True),
        (0, 0, True, True, True, True),
        (0, 0, False, True, False, True),
        (0, 0, True, False, False, True),
    ]

    vertices = [tslot_outline] + 4 * [tslot_closed] + 3 * [tslot_outline]
    fillets = [5, 7, 9, 21]

    closed_symmetry = [
        (0, 0, False, True, False, False),
        (0, 0, False, False, True, False),
    ]
    closed_vertices = 2 * [tslot_closed_space]

    corner_offset = 0
    circle_offsets = [0]

    face = tslot(
        symmetry,
        vertices,
        fillets,
        closed_symmetry,
        closed_vertices,
        corner_offset,
        circle_offsets,
    )
    return face


# ************************************************************************************************
@lru_cache(maxsize=None)
def tslot20x20_two_slot_opp():
    # due to symmetry this can be nicely decomposed
    # x offset, y offset, reverse, switch, mir_x, mir_y
    symmetry = [
        (0, 0, False, False, False, False),
        (0, 0, True, True, False, False),
        (0, 0, False, True, True, False),
        (0, 0, True, False, True, False),
        (0, 0, False, False, True, True),
        (0, 0, True, True, True, True),
        (0, 0, False, True, False, True),
        (0, 0, True, False, False, True),
    ]

    vertices = [tslot_outline] + 2 * [tslot_closed] + 2 * [tslot_outline] + 2 * [tslot_closed] + [tslot_outline]
    fillets = [5, 7, 19, 21]

    closed_symmetry = [
        (0, 0, False, True, False, False),
        (0, 0, False, True, False, True),
    ]
    closed_vertices = 2 * [tslot_closed_space]

    corner_offset = 0
    circle_offsets = [0]

    face = tslot(
        symmetry,
        vertices,
        fillets,
        closed_symmetry,
        closed_vertices,
        corner_offset,
        circle_offsets,
    )
    return face


# ************************************************************************************************
@lru_cache(maxsize=None)
def tslot20x20_one_slot():
    # due to symmetry this can be nicely decomposed
    # x offset, y offset, reverse, switch, mir_x, mir_y
    symmetry = [
        (0, 0, False, False, False, False),
        (0, 0, True, True, False, False),
        (0, 0, False, True, True, False),
        (0, 0, True, False, True, False),
        (0, 0, False, False, True, True),
        (0, 0, True, True, True, True),
        (0, 0, False, True, False, True),
        (0, 0, True, False, False, True),
    ]

    vertices = [tslot_outline] + 6 * [tslot_closed] + [tslot_outline]
    fillets = [5, 7, 9, 11]

    closed_symmetry = [
        (0, 0, False, True, False, False),
        (0, 0, False, False, True, False),
        (0, 0, False, True, False, True),
    ]
    closed_vertices = 3 * [tslot_closed_space]

    corner_offset = 0
    circle_offsets = [0]

    face = tslot(symmetry, vertices, fillets, closed_symmetry, closed_vertices, corner_offset, circle_offsets)
    return face


# ************************************************************************************************
# helper
def fillet(lines, indices, radius):
    """
    fillets the corner between the segments and their successors in lines indicated by indices
    """

    lines = lines[:]

    # sort them in descending order, as filleting inserts additional edges
    indices.sort()
    indices.reverse()

    for i in indices:
        lines[slice(i, i + 2)] = draft_fillet(lines[slice(i, i + 2)], radius)

    return lines


def assemble(symmetry, vertices, offset_global=(0, 0)):
    """
    Assemble a wire from a list of symmetry information and a list of list of vertices

    symmetry information is a tuple of
        offset x, offset y, bool reverse, bool switch_comp, bool mirror_x, bool mirror_y
    """

    offset = Vector(offset_global[0], offset_global[1], 0)

    lines = []

    vlast = None
    vcur = None

    for sym, verts in zip(symmetry, vertices):
        o_x, o_y, reverse, switch, mir_x, mir_y = sym
        mir_x = -1 if mir_x else 1
        mir_y = -1 if mir_y else 1
        if reverse:
            verts = verts[::-1]

        if vcur is None:
            vcur = Vector(verts[0])
            if switch:
                vcur[0], vcur[1] = vcur[1], vcur[0]

            vcur[0] = mir_x * vcur[0] + o_x + offset[0]
            vcur[1] = mir_y * vcur[1] + o_y + offset[1]

        for v in verts[1:]:
            vlast = vcur
            vcur = Vector(v)
            if switch:
                vcur[0], vcur[1] = vcur[1], vcur[0]

            vcur[0] = mir_x * vcur[0] + o_x + offset[0]
            vcur[1] = mir_y * vcur[1] + o_y + offset[1]

            lines.append(Part.makeLine(vlast, vcur))
    return lines


# ************************************************************************************************
# profile size
w = 20


# ************************************************************************************************
# Vslot profile:

# the size of the inner square
d = 5.68 + 3 / math.sqrt(2)

# one eight of the outline
vslot_outline = [
    (0.5 * d, 0, 0),
    (0.5 * d, 0.5 * 5.68, 0),
    (0.5 * w - 1.8 - 1.64, 0.5 * w - 1.8 - 1.64 - 1.5 / math.sqrt(2), 0),
    (0.5 * w - 1.8, 0.5 * w - 1.8 - 1.64 - 1.5 / math.sqrt(2), 0),
    (0.5 * w - 1.8, 0.5 * 5.68, 0),
    (0.5 * w, 0.5 * 5.68 + 1.8, 0),
    (0.5 * w, 0.5 * w, 0),
]

space_symmetry = [
    (0, 0, False, False, True, False),
    (-w, 0, True, False, False, False),
    (-w, 0, False, False, False, True),
    (0, 0, True, False, True, True),
]

# big spaces
vslot_space = [
    (0.5 * d, 0, 0),
    (0.5 * d, 0.5 * 5.68, 0),
    (0.5 * w - 2.7, 0.5 * w - 1.8 - 1.96, 0),
    (0.5 * w - 2.7, 0.5 * w - 1.8, 0),
    (0.5 * w, 0.5 * w - 1.8, 0),
]

# corner holes
vslot_cornerhole = [
    (0.5 * w - 1.8, 0.5 * w - 1.8 - 1.64 - 1.5 / math.sqrt(2) + 1.07, 0),
    (0.5 * w - 1.8, 0.5 * w - 1.8, 0),
    (0.5 * w - 1.8 - 1.64 - 1.5 / math.sqrt(2) + 1.07, 0.5 * w - 1.8, 0),
    (0.5 * w - 1.8, 0.5 * w - 1.8 - 1.64 - 1.5 / math.sqrt(2) + 1.07, 0),
]


def vslot(symmetry, vertices, fillets, corner_offset, circle_offsets):
    outline = assemble(symmetry, vertices)
    outline = fillet(outline, fillets, 1.5)
    outline = Part.Wire(outline)

    holes = []

    # corners
    # x offset, y offset, reverse, switch, mir_x, mir_y
    corner_symmetry = [
        (0, 0, False, False, False, False),
        (corner_offset, 0, False, False, True, False),
        (corner_offset, 0, False, False, True, True),
        (0, 0, False, False, False, True),
    ]

    for sym in corner_symmetry:
        holes.append(Part.Wire(assemble([sym], [vslot_cornerhole])))
        if sym[4] == sym[5]:
            holes[-1].reverse()

    # circular holes
    for offset in circle_offsets:
        holes.append(Part.Wire(Part.makeCircle(2.1, Vector(offset, 0, 0))))
        holes[-1].reverse()

    # big spaces
    for offset in circle_offsets[:-1]:
        holes.append(Part.Wire(assemble(space_symmetry, 4 * [vslot_space], (offset, 0))))
        holes[-1].reverse()

    # put everything together
    return Part.Face([outline] + holes)


# ************************************************************************************************
# T slot profile:

# outline
tslot_outline = [
    (5.0, 0, 0),
    (5.0, 3.5, 0),
    (7.5, 6.0, 0),
    (9.0, 6.0, 0),
    (9.0, 3.0, 0),
    (10.0, 3.0, 0),
    (10.0, 10.0, 0),
]

# closed slots ouline
tslot_closed = [
    (10.0, 0.0, 0),
    (10.0, 10.0, 0),
]

# closed slots spaces
tslot_closed_space = [
    (5.0, 0, 0),
    (5.0, 3.5, 0),
    (7.5, 6.0, 0),
    (9.0, 6.0, 0),
    (9.0, -6.0, 0),
    (7.5, -6.0, 0),
    (5.0, -3.5, 0),
    (5.0, 0, 0),
]

# big spaces
tslot_space = [
    (0.5 * d, 0, 0),
    (0.5 * d, 0.5 * 5.68, 0),
    (0.5 * w - 2.7, 0.5 * w - 1.8 - 1.96, 0),
    (0.5 * w - 2.7, 0.5 * w - 1.8, 0),
    (0.5 * w, 0.5 * w - 1.8, 0),
]


def tslot(symmetry, vertices, fillets, closed_symmetry, closed_vertices, corner_offset, circle_offsets):
    outline = assemble(symmetry, vertices)
    outline = fillet(outline, fillets, 1.5)
    outline = Part.Wire(outline)

    holes = []

    # closed holes
    for sym, vert in zip(closed_symmetry, closed_vertices):
        holes.append(Part.Wire(assemble([sym], [vert])))
        if not sym[5]:
            holes[-1].reverse()

    # circular holes
    for offset in circle_offsets:
        holes.append(Part.Wire(Part.makeCircle(2.25, Vector(offset, 0, 0))))
        holes[-1].reverse()

    # put everything together
    return Part.Face([outline] + holes)


# ************************************************************************************************
# Generic parametric profile generators (support any size)
# ************************************************************************************************


def _get_tslot_wedge(half):
    """Generate T-slot wedge outline for a given half-dimension.

    Returns a wedge outline (list of 3-tuples) suitable for the 8-way
    symmetry system.  The groove geometry is scaled to produce reasonable
    EU-standard-like proportions for each profile series.

    Important: points C and D (the undercut bottom) share the same
    y-coordinate so the undercut floor is horizontal — no spikes.
    """
    size = half * 2.0

    # -- T-slot groove parameters per series (mm) -----------------
    # inner  : distance from centre to innermost groove wall
    # opening: height of the slot opening (rise along the wall)
    # uc_in  : x-position of the undercut inner corner
    # uc_out : x-position of the undercut outer corner
    # uc_y   : y-position of the undercut bottom (both corners)
    # lip_y  : y-position where the outer lip starts (lip_y < uc_y)
    if size <= 20:
        inner, opening, uc_in, uc_out, uc_y, lip_y = 5.0, 3.5, 7.5, 9.0, 6.0, 3.0
    elif size <= 30:
        inner, opening, uc_in, uc_out, uc_y, lip_y = 7.0, 4.0, 10.5, 13.0, 7.0, 3.5
    elif size <= 40:
        # inner wall closer to centre, thicker lip + wider undercut
        inner, opening, uc_in, uc_out, uc_y, lip_y = 8.0, 5.0, 12.0, 16.0, 9.0, 4.5
    elif size <= 45:
        inner, opening, uc_in, uc_out, uc_y, lip_y = 9.0, 5.5, 13.5, 18.0, 10.0, 5.0
    elif size <= 50:
        inner, opening, uc_in, uc_out, uc_y, lip_y = 10.0, 6.0, 16.0, 20.0, 11.5, 5.5
    elif size <= 60:
        inner, opening, uc_in, uc_out, uc_y, lip_y = 12.0, 7.0, 19.0, 24.0, 13.0, 6.5
    else:  # 80
        inner, opening, uc_in, uc_out, uc_y, lip_y = 16.0, 8.0, 25.0, 32.0, 16.0, 8.0

    # Clamp to half so geometry never exceeds the outer dimension
    if uc_out >= half:
        uc_out = half - 1.0 if half > 2.0 else half * 0.8
    if inner >= half:
        inner = half * 0.5

    return [
        (inner, 0, 0),        # A – inner wall on centreline
        (inner, opening, 0),   # B – top of inner wall
        (uc_in, uc_y, 0),     # C – undercut inner corner (SAME y as D)
        (uc_out, uc_y, 0),    # D – undercut outer corner
        (uc_out, lip_y, 0),   # E – lip inner (drop down to lip_y)
        (half, lip_y, 0),     # F – lip outer (at the face)
        (half, half, 0),      # G – outer corner
    ]


def _make_tslot_square(size):
    """Generate a square T-slot profile via 8-wedge symmetry."""
    half = size / 2.0
    outline_vert = _get_tslot_wedge(half)

    symmetry = [
        (0, 0, False, False, False, False),
        (0, 0, True, True, False, False),
        (0, 0, False, True, True, False),
        (0, 0, True, False, True, False),
        (0, 0, False, False, True, True),
        (0, 0, True, True, True, True),
        (0, 0, False, True, False, True),
        (0, 0, True, False, False, True),
    ]

    vertices = 8 * [outline_vert]
    fillets = [5, 17, 29, 41]

    out = assemble(symmetry, vertices)
    out = fillet(out, fillets, 1.5)
    out = Part.Wire(out)

    bore_r = 2.25 * (half / 10.0)
    holes = [Part.Wire(Part.makeCircle(bore_r, Vector(0, 0, 0)))]
    holes[-1].reverse()

    return Part.Face([out] + holes)


def _build_rect_tslot_perimeter(w, h):
    """Build perimeter vertices for a rectangular T-slot profile.

    Returns a list of Vector points tracing the outer boundary
    (including T-slot groove indentations) clockwise, starting from
    the bottom-left corner.

    The groove has a **narrow opening at the surface** and a **wider
    undercut at depth** — the classic T-slot cross-section.
    """
    hw, hh = w * 0.5, h * 0.5
    series = min(w, h)

    # Groove dimensions based on DIN 650 T-slot standards per series
    if series <= 20:
        # T-slot 6
        open_w, uc_w, open_d, uc_d = 6.5, 11.0, 2.5, 2.0
    elif series <= 30:
        # T-slot 8 (small)
        open_w, uc_w, open_d, uc_d = 8.5, 15.0, 3.5, 2.5
    elif series <= 40:
        # T-slot 8 (standard)
        open_w, uc_w, open_d, uc_d = 8.5, 15.0, 4.0, 3.0
    elif series <= 50:
        # T-slot 10
        open_w, uc_w, open_d, uc_d = 10.5, 18.0, 4.5, 3.0
    elif series <= 60:
        # T-slot 12
        open_w, uc_w, open_d, uc_d = 12.5, 22.0, 5.5, 3.5
    else:
        # T-slot 16 (80mm+)
        open_w, uc_w, open_d, uc_d = 16.5, 27.0, 7.0, 4.5

    ho = open_w * 0.5    # opening half-width at surface
    hu = uc_w * 0.5      # undercut half-width at depth  (hu > ho)

    pts = []

    # ---- bottom face (y = -hh, x: -hw → +hw) — groove goes UP ----
    pts.append(Vector(-hw, -hh, 0))                   # 0  bottom-left corner
    pts.append(Vector(-ho, -hh, 0))                   # 1  opening left edge
    pts.append(Vector(-ho, -hh + open_d, 0))          # 2  opening inner
    pts.append(Vector(-hu, -hh + open_d, 0))          # 3  undercut (wider)
    pts.append(Vector(-hu, -hh + open_d + uc_d, 0))   # 4  undercut inner
    pts.append(Vector(hu, -hh + open_d + uc_d, 0))    # 5  undercut far side
    pts.append(Vector(hu, -hh + open_d, 0))           # 6  undercut outer
    pts.append(Vector(ho, -hh + open_d, 0))           # 7  opening inner (narrower)
    pts.append(Vector(ho, -hh, 0))                    # 8  opening right edge
    pts.append(Vector(hw, -hh, 0))                    # 9  bottom-right corner

    # ---- right face (x = hw, y: -hh → +hh) — groove goes LEFT ----
    pts.append(Vector(hw, -ho, 0))                    # 10  opening bottom edge
    pts.append(Vector(hw - open_d, -ho, 0))           # 11  opening inner
    pts.append(Vector(hw - open_d, -hu, 0))           # 12  undercut (wider)
    pts.append(Vector(hw - open_d - uc_d, -hu, 0))    # 13  undercut inner
    pts.append(Vector(hw - open_d - uc_d, hu, 0))     # 14  undercut far side
    pts.append(Vector(hw - open_d, hu, 0))            # 15  undercut outer
    pts.append(Vector(hw - open_d, ho, 0))            # 16  opening inner (narrower)
    pts.append(Vector(hw, ho, 0))                     # 17  opening top edge
    pts.append(Vector(hw, hh, 0))                     # 18  top-right corner

    # ---- top face (y = hh, x: +hw → -hw) — groove goes DOWN ----
    pts.append(Vector(ho, hh, 0))                     # 19  opening right edge
    pts.append(Vector(ho, hh - open_d, 0))            # 20  opening inner
    pts.append(Vector(hu, hh - open_d, 0))            # 21  undercut (wider)
    pts.append(Vector(hu, hh - open_d - uc_d, 0))     # 22  undercut inner
    pts.append(Vector(-hu, hh - open_d - uc_d, 0))    # 23  undercut far side
    pts.append(Vector(-hu, hh - open_d, 0))           # 24  undercut outer
    pts.append(Vector(-ho, hh - open_d, 0))           # 25  opening inner (narrower)
    pts.append(Vector(-ho, hh, 0))                    # 26  opening left edge
    pts.append(Vector(-hw, hh, 0))                    # 27  top-left corner

    # ---- left face (x = -hw, y: +hh → -hh) — groove goes RIGHT ---
    pts.append(Vector(-hw, ho, 0))                    # 28  opening top edge
    pts.append(Vector(-hw + open_d, ho, 0))           # 29  opening inner
    pts.append(Vector(-hw + open_d, hu, 0))           # 30  undercut (wider)
    pts.append(Vector(-hw + open_d + uc_d, hu, 0))    # 31  undercut inner
    pts.append(Vector(-hw + open_d + uc_d, -hu, 0))   # 32  undercut far side
    pts.append(Vector(-hw + open_d, -hu, 0))          # 33  undercut outer
    pts.append(Vector(-hw + open_d, -ho, 0))          # 34  opening inner (narrower)
    pts.append(Vector(-hw, -ho, 0))                   # 35  opening bottom edge
    # Edge 35 wraps back to pts[0] = (-hw, -hh)

    return pts


def _make_tslot_rect(w, h):
    """Generate a rectangular T-slot profile via direct perimeter wire."""
    pts = _build_rect_tslot_perimeter(w, h)
    n = len(pts)

    lines = [Part.makeLine(pts[i], pts[(i + 1) % n]) for i in range(n)]

    # Apply fillets at the four outer corners.
    # Corner indices in the *original* edge list:
    #   bottom-right: edges[8:10]   → idx 8
    #   top-right   : edges[17:19]  → idx 17
    #   top-left    : edges[26:28]  → idx 26
    #   bottom-left : edges[35] + edges[0] → handled separately
    # Every fillet replaces 2 edges with 3 → subsequent indices shift +1.
    cor_r = 1.5

    # Highest index first so earlier indices don't shift
    # corner top-left    original idx 26
    lines[26:28] = draft_fillet(lines[26:28], cor_r)
    # corner top-right   original idx 17 (unshifted — fillet at 26 is higher)
    lines[17:19] = draft_fillet(lines[17:19], cor_r)
    # corner bottom-right original idx 8 (unshifted — fillets at 26,17 are higher)
    lines[8:10] = draft_fillet(lines[8:10], cor_r)

    # corner bottom-left: wraps from last edge to edge 0.
    # After the 3 fillets above we gained 3 edges (one per fillet),
    # so the original 36 edges is now 39. The wrap-around involves
    # the very last edge (idx -1) and edge 0.
    last = len(lines) - 1
    wrap_edges = [lines[last], lines[0]]
    filleted = draft_fillet(wrap_edges, cor_r)
    # Replace the 2 edges: the last one and the first one.
    # We splice: lines[-1:] → filleted[0] (arc+line), lines[:1] → filleted[1:]
    lines[last:] = filleted[:1]
    lines[:1] = filleted[1:]

    wire = Part.Wire(lines)

    holes = []
    series = min(w, h)

    # Central bore
    bore_r = series * 0.1
    holes.append(Part.Wire(Part.makeCircle(bore_r, Vector(0, 0, 0))))
    holes[-1].reverse()

    # Near-perimeter cutouts (four corner cavities) for larger profiles.
    # Real EU T-slot extrusions have hollow chambers near each corner.
    if series >= 40:
        inset = series * 0.22      # diagonal distance from center
        hole_r = series * 0.045    # cavity radius
        for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            c = Vector(sx * inset, sy * inset, 0)
            holes.append(Part.Wire(Part.makeCircle(hole_r, c)))
            holes[-1].reverse()

    return Part.Face([wire] + holes)


@lru_cache(maxsize=128)
def make_tslot_face(w, h):
    """Generate a T-slot profile cross-section for width *w* and height *h*.

    Always uses the rectangular perimeter construction for consistent
    groove geometry across all profile dimensions.
    """
    return _make_tslot_rect(w, h)


def _build_profile_perimeter(w, h, sw, sd, uc_w, uc_d, v_d=2.28, v_bw=5.74, cr=1.0):
    import math
    hw, hh = w * 0.5, h * 0.5
    ho, hu = sw * 0.5, uc_w * 0.5
    v_hw = v_bw * 0.5

    pts = []
    # bottom face  (y = -hh, x: +hw → -hw)
    pts.append(Vector(-hw, -hh, 0))                           # 0 corner
    pts.append(Vector(-ho, -hh, 0))                           # 1 slot open L
    pts.append(Vector(-ho, -hh + sd, 0))                      # 2 open floor L
    pts.append(Vector(-hu, -hh + sd, 0))                      # 3 undercut L
    pts.append(Vector(-hu, -hh + sd + uc_d, 0))               # 4 uc floor L
    pts.append(Vector(-v_hw, -hh + sd + uc_d + v_d, 0))       # 5 V-bottom L
    pts.append(Vector(v_hw, -hh + sd + uc_d + v_d, 0))        # 6 V-bottom R
    pts.append(Vector(hu, -hh + sd + uc_d, 0))                # 7 uc floor R
    pts.append(Vector(hu, -hh + sd, 0))                       # 8 undercut R
    pts.append(Vector(ho, -hh + sd, 0))                       # 9 open floor R
    pts.append(Vector(ho, -hh, 0))                             # 10 slot open R
    pts.append(Vector(hw, -hh, 0))                             # 11 corner
    # right face  (x = hw, y: -hh → +hh)
    pts.append(Vector(hw, -ho, 0))                             # 12
    pts.append(Vector(hw - sd, -ho, 0))                        # 13
    pts.append(Vector(hw - sd, -hu, 0))                        # 14
    pts.append(Vector(hw - sd - uc_d, -hu, 0))                 # 15
    pts.append(Vector(hw - sd - uc_d - v_d, -v_hw, 0))         # 16 V-bottom
    pts.append(Vector(hw - sd - uc_d - v_d, v_hw, 0))          # 17 V-bottom
    pts.append(Vector(hw - sd - uc_d, hu, 0))                  # 18
    pts.append(Vector(hw - sd, hu, 0))                         # 19
    pts.append(Vector(hw - sd, ho, 0))                         # 20
    pts.append(Vector(hw, ho, 0))                              # 21
    pts.append(Vector(hw, hh, 0))                              # 22 corner
    # top face  (y = hh, x: +hw → -hw)
    pts.append(Vector(ho, hh, 0))                              # 23
    pts.append(Vector(ho, hh - sd, 0))                         # 24
    pts.append(Vector(hu, hh - sd, 0))                         # 25
    pts.append(Vector(hu, hh - sd - uc_d, 0))                  # 26
    pts.append(Vector(v_hw, hh - sd - uc_d - v_d, 0))          # 27 V-bottom
    pts.append(Vector(-v_hw, hh - sd - uc_d - v_d, 0))         # 28 V-bottom
    pts.append(Vector(-hu, hh - sd - uc_d, 0))                 # 29
    pts.append(Vector(-hu, hh - sd, 0))                        # 30
    pts.append(Vector(-ho, hh - sd, 0))                        # 31
    pts.append(Vector(-ho, hh, 0))                             # 32
    pts.append(Vector(-hw, hh, 0))                             # 33 corner
    # left face  (x = -hw, y: +hh → -hh)
    pts.append(Vector(-hw, ho, 0))                             # 34
    pts.append(Vector(-hw + sd, ho, 0))                        # 35
    pts.append(Vector(-hw + sd, hu, 0))                        # 36
    pts.append(Vector(-hw + sd + uc_d, hu, 0))                 # 37
    pts.append(Vector(-hw + sd + uc_d + v_d, v_hw, 0))         # 38 V-bottom
    pts.append(Vector(-hw + sd + uc_d + v_d, -v_hw, 0))        # 39 V-bottom
    pts.append(Vector(-hw + sd + uc_d, -hu, 0))                # 40
    pts.append(Vector(-hw + sd, -hu, 0))                       # 41
    pts.append(Vector(-hw + sd, -ho, 0))                       # 42
    pts.append(Vector(-hw, -ho, 0))                            # 43

    n = len(pts)
    lines = [Part.makeLine(pts[i], pts[(i + 1) % n]) for i in range(n)]

    lines[32:34] = draft_fillet(lines[32:34], cr)  # top-left corner
    lines[21:23] = draft_fillet(lines[21:23], cr)  # top-right corner
    lines[10:12] = draft_fillet(lines[10:12], cr)  # bottom-right corner
    last = len(lines) - 1
    wrap = draft_fillet([lines[last], lines[0]], cr)
    lines[last:] = wrap[:1]
    lines[:1] = wrap[1:]

    wire = Part.Wire(lines)
    holes = []
    bore_r = min(w, h) * 0.1
    holes.append(Part.Wire(Part.makeCircle(bore_r, Vector(0, 0, 0))))
    holes[-1].reverse()
    if min(w, h) >= 25:
        inset = min(w, h) * 0.35
        hole_r = min(w, h) * 0.105
        for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            c = Vector(sx * inset, sy * inset, 0)
            holes.append(Part.Wire(Part.makeCircle(hole_r, c)))
            holes[-1].reverse()
    return Part.Face([wire] + holes)


@lru_cache(maxsize=128)
def make_profile_face(w, h, sw=6.0, sd=2.0, uc_w=10.0, uc_d=3.0, v_d=2.28, v_bw=5.74, cr=1.0):
    return _build_profile_perimeter(w, h, sw, sd, uc_w, uc_d, v_d, v_bw, cr)


def make_yiheda_vslot(w, h, sw=None):
    """Generate 20-series yiheda V-slot profile. sw = slot opening width."""
    import math
    if sw is None:
        s_open, s_step_d, s_step_w = 7.2, 0.5, 6.2
        s_neck_d, s_flare_h, s_flare_bot = 1.5, 1.51, 11
        v_depth, v_bottom, cr = 2.59, 5.82, 1.5
    else:
        sc = sw / 7.2
        s_open = sw; s_step_d = 0.5*sc; s_step_w = 6.2*sc
        s_neck_d = 1.5*sc; s_flare_h = 1.51*sc; s_flare_bot = 11*sc
        v_depth = 2.59*sc; v_bottom = 5.82*sc; cr = 1.5*sc

    hw, hh = w*0.5, h*0.5
    hos, hsw = s_open*0.5, s_step_w*0.5
    hfb, hvb = s_flare_bot*0.5, v_bottom*0.5

    def slot_right(cy):
        return [Vector(hw-s_step_d,cy-hos,0),Vector(hw-s_step_d,cy-hsw,0),
            Vector(hw-s_step_d-s_neck_d,cy-hsw,0),Vector(hw-s_step_d-s_neck_d,cy-hfb,0),
            Vector(hw-s_step_d-s_neck_d-s_flare_h,cy-hfb,0),
            Vector(hw-s_step_d-s_neck_d-s_flare_h-v_depth,cy-hvb,0),
            Vector(hw-s_step_d-s_neck_d-s_flare_h-v_depth,cy+hvb,0),
            Vector(hw-s_step_d-s_neck_d-s_flare_h,cy+hfb,0),
            Vector(hw-s_step_d-s_neck_d,cy+hfb,0),Vector(hw-s_step_d-s_neck_d,cy+hsw,0),
            Vector(hw-s_step_d,cy+hsw,0),Vector(hw-s_step_d,cy+hos,0)]
    def slot_left(cy):
        return [Vector(-hw+s_step_d,cy+hos,0),Vector(-hw+s_step_d,cy+hsw,0),
            Vector(-hw+s_step_d+s_neck_d,cy+hsw,0),Vector(-hw+s_step_d+s_neck_d,cy+hfb,0),
            Vector(-hw+s_step_d+s_neck_d+s_flare_h,cy+hfb,0),
            Vector(-hw+s_step_d+s_neck_d+s_flare_h+v_depth,cy+hvb,0),
            Vector(-hw+s_step_d+s_neck_d+s_flare_h+v_depth,cy-hvb,0),
            Vector(-hw+s_step_d+s_neck_d+s_flare_h,cy-hfb,0),
            Vector(-hw+s_step_d+s_neck_d,cy-hfb,0),Vector(-hw+s_step_d+s_neck_d,cy-hsw,0),
            Vector(-hw+s_step_d,cy-hsw,0),Vector(-hw+s_step_d,cy-hos,0)]
    def slot_bottom(cx):
        return [Vector(cx-hos,-hh+s_step_d,0),Vector(cx-hsw,-hh+s_step_d,0),
            Vector(cx-hsw,-hh+s_step_d+s_neck_d,0),Vector(cx-hfb,-hh+s_step_d+s_neck_d,0),
            Vector(cx-hfb,-hh+s_step_d+s_neck_d+s_flare_h,0),
            Vector(cx-hvb,-hh+s_step_d+s_neck_d+s_flare_h+v_depth,0),
            Vector(cx+hvb,-hh+s_step_d+s_neck_d+s_flare_h+v_depth,0),
            Vector(cx+hfb,-hh+s_step_d+s_neck_d+s_flare_h,0),
            Vector(cx+hfb,-hh+s_step_d+s_neck_d,0),Vector(cx+hsw,-hh+s_step_d+s_neck_d,0),
            Vector(cx+hsw,-hh+s_step_d,0),Vector(cx+hos,-hh+s_step_d,0)]
    def slot_top(cx):
        return [Vector(cx+hos,hh-s_step_d,0),Vector(cx+hsw,hh-s_step_d,0),
            Vector(cx+hsw,hh-s_step_d-s_neck_d,0),Vector(cx+hfb,hh-s_step_d-s_neck_d,0),
            Vector(cx+hfb,hh-s_step_d-s_neck_d-s_flare_h,0),
            Vector(cx+hvb,hh-s_step_d-s_neck_d-s_flare_h-v_depth,0),
            Vector(cx-hvb,hh-s_step_d-s_neck_d-s_flare_h-v_depth,0),
            Vector(cx-hfb,hh-s_step_d-s_neck_d-s_flare_h,0),
            Vector(cx-hfb,hh-s_step_d-s_neck_d,0),Vector(cx-hsw,hh-s_step_d-s_neck_d,0),
            Vector(cx-hsw,hh-s_step_d,0),Vector(cx-hos,hh-s_step_d,0)]

    n_h = max(1, int(w/20)); n_v = max(1, int(h/20))
    sp_h, sp_v = w/n_h, h/n_v

    pts = []
    pts.append(Vector(-hw,-hh,0))
    for i in range(n_h):
        cx = -hw+sp_h/2+i*sp_h
        pts.append(Vector(cx-hos,-hh,0)); pts.extend(slot_bottom(cx))
        pts.append(Vector(cx+hos,-hh,0))
    pts.append(Vector(hw,-hh,0))

    for i in range(n_v):
        cy = -hh+sp_v/2+i*sp_v
        pts.append(Vector(hw,cy-hos,0)); pts.extend(slot_right(cy))
        pts.append(Vector(hw,cy+hos,0))
    pts.append(Vector(hw,hh,0))

    for i in range(n_h):
        cx = hw-sp_h/2-i*sp_h
        pts.append(Vector(cx+hos,hh,0)); pts.extend(slot_top(cx))
        pts.append(Vector(cx-hos,hh,0))
    pts.append(Vector(-hw,hh,0))

    for i in range(n_v):
        cy = hh-sp_v/2-i*sp_v
        pts.append(Vector(-hw,cy+hos,0)); pts.extend(slot_left(cy))
        pts.append(Vector(-hw,cy-hos,0))

    n = len(pts)
    lines = [Part.makeLine(pts[i],pts[(i+1)%n]) for i in range(n)]
    lines[44:46] = draft_fillet(lines[44:46],cr)
    lines[29:31] = draft_fillet(lines[29:31],cr)
    lines[14:16] = draft_fillet(lines[14:16],cr)
    last = len(lines)-1
    wrap = draft_fillet([lines[last],lines[0]],cr)
    lines[last:] = wrap[:1]; lines[:1] = wrap[1:]

    wire = Part.Wire(lines)
    holes = []
    bore_r = cr*1.667
    if n_v >= n_h:
        for i in range(n_v):
            cy = -hh+sp_v/2+i*sp_v
            holes.append(Part.Wire(Part.makeCircle(bore_r,Vector(0,cy,0))))
            holes[-1].reverse()
    else:
        for i in range(n_h):
            cx = -hw+sp_h/2+i*sp_h
            holes.append(Part.Wire(Part.makeCircle(bore_r,Vector(cx,0,0))))
            holes[-1].reverse()
    for i in range(n_h-1):
        mx = (-hw+sp_h/2+i*sp_h)+sp_h/2
        oct_pts = [Vector(mx-3.1,-8,0),Vector(mx+3.1,-8,0),
            Vector(mx+3.1,-5.91,0),Vector(mx+6.1,-2.91,0),
            Vector(mx+6.1,2.91,0),Vector(mx+3.1,5.91,0),
            Vector(mx+3.1,8,0),Vector(mx-3.1,8,0),
            Vector(mx-3.1,5.91,0),Vector(mx-6.1,2.91,0),
            Vector(mx-6.1,-2.91,0),Vector(mx-3.1,-5.91,0)]
        no = len(oct_pts)
        ow = [Part.makeLine(oct_pts[j],oct_pts[(j+1)%no]) for j in range(no)]
        holes.append(Part.Wire(ow)); holes[-1].reverse()
    return Part.Face([wire]+holes)


def make_aoh_vslot(w, h):
    """AOH V-slot for 30 series."""

    hw, hh = w * 0.5, h * 0.5

    L3030 = [(-15,-15),(-15,-13),(-15,-5.1),(-14.2,-5.1),(-14.2,-4.1),(-13,-4.1),
             (-13,-8.25),(-9.664,-8.25),(-5.8,-4.386),(-5.8,-0.52),
             (-5.5,0),(-5.8,0.52),(-5.8,4.386),(-9.664,8.25),
             (-13,8.25),(-13,4.1),(-14.2,4.1),(-14.2,5.1),(-15,5.1),(-15,13)]
    B3030 = [(-15,15),(-13,15),(-5.1,15),(-5.1,14.2),(-4.1,14.2),(-4.1,13),
             (-8.25,13),(-8.25,9.664),(-4.386,5.8),(-0.52,5.8),
             (0,5.5),(0.52,5.8),(4.386,5.8),(8.25,9.664),
             (8.25,13),(4.1,13),(4.1,14.2),(5.1,14.2),(5.1,15),(13,15)]
    R3030 = [(15,15),(15,13),(15,5.1),(14.2,5.1),(14.2,4.1),(13,4.1),
             (13,8.25),(9.664,8.25),(5.8,4.386),(5.8,0.52),
             (5.5,0),(5.8,-0.52),(5.8,-4.386),(9.664,-8.25),
             (13,-8.25),(13,-4.1),(14.2,-4.1),(14.2,-5.1),(15,-5.1),(15,-13)]
    T3030 = [(15,-15),(13,-15),(5.1,-15),(5.1,-14.2),(4.1,-14.2),(4.1,-13),
             (8.25,-13),(8.25,-9.664),(4.386,-5.8),(0.52,-5.8),
             (0,-5.5),(-0.52,-5.8),(-4.386,-5.8),(-8.25,-9.664),
             (-8.25,-13),(-4.1,-13),(-4.1,-14.2),(-5.1,-14.2),(-5.1,-15),(-13,-15)]

    L_int = L3030[3:18]
    B_int = B3030[3:18]
    R_int = R3030[3:18]
    T_int = T3030[3:18]

    n_v = max(1, int(h / 30))
    n_h = max(1, int(w / 30))
    sp_v = h / n_v
    sp_h = w / n_h

    def build_face(face_type):
        pts = []
        if face_type == 'L':
            pts.append((-hw, -hh))
            pts.append((-hw, -hh + 2))
            for i in range(n_v):
                yc = -hh + sp_v * 0.5 + i * sp_v
                pts.append((-hw, yc - 5.1))
                pts.extend([(x, y + yc) for x, y in L_int])
                pts.append((-hw, yc + 5.1))
            pts.append((-hw, hh - 2))
        elif face_type == 'B':
            pts.append((-hw, hh))
            pts.append((-hw + 2, hh))
            for i in range(n_h):
                xc = -hw + sp_h * 0.5 + i * sp_h
                pts.append((xc - 5.1, hh))
                pts.extend([(x + xc, y + hh - 15) for x, y in B_int])
                pts.append((xc + 5.1, hh))
            pts.append((hw - 2, hh))
        elif face_type == 'R':
            pts.append((hw, hh))
            pts.append((hw, hh - 2))
            for i in range(n_v):
                yc = hh - sp_v * 0.5 - i * sp_v
                pts.append((hw, yc + 5.1))
                pts.extend([(x, y + yc) for x, y in R_int])
                pts.append((hw, yc - 5.1))
            pts.append((hw, -hh + 2))
        elif face_type == 'T':
            pts.append((hw, -hh))
            pts.append((hw - 2, -hh))
            for i in range(n_h):
                xc = hw - sp_h * 0.5 - i * sp_h
                pts.append((xc + 5.1, -hh))
                pts.extend([(x + xc, y - hh + 15) for x, y in T_int])
                pts.append((xc - 5.1, -hh))
            pts.append((-hw + 2, -hh))
        return pts

    P = build_face('L') + build_face('B') + build_face('R') + build_face('T')
    pts = [Vector(x, y, 0) for x, y in P]
    n = len(pts)
    lines = [Part.makeLine(pts[i], pts[(i + 1) % n]) for i in range(n)]

    nL = len(build_face('L'))
    nB = len(build_face('B'))
    nR = len(build_face('R'))

    br = nL + nB + nR - 1
    tr = nL + nB - 1
    tl = nL - 1

    fillet_order = [br, tr, tl]
    for ci in fillet_order:
        lines[ci:ci + 2] = draft_fillet([lines[ci], lines[ci + 1]], 2)

    last = len(lines) - 1
    wrap = draft_fillet([lines[last], lines[0]], 2)
    lines[last:] = wrap[:1]
    lines[:1] = wrap[1:]

    wire = Part.Wire(lines)
    holes = []
    bore_r = 3.4
    if n_v >= n_h:
        for i in range(n_v):
            cy = -hh + sp_v * 0.5 + i * sp_v
            holes.append(Part.Wire(Part.makeCircle(bore_r, Vector(0, cy, 0))))
        for i in range(n_v - 1):
            my = (-hh + sp_v * 0.5 + i * sp_v) + sp_v * 0.5
            cao = [(13, my - 4.75), (13, my + 4.75),
                   (8.836, my + 4.75), (4.386, my + 9.2),
                   (-4.386, my + 9.2), (-8.836, my + 4.75),
                   (-13, my + 4.75), (-13, my - 4.75),
                   (-8.836, my - 4.75), (-4.386, my - 9.2),
                   (4.386, my - 9.2), (8.836, my - 4.75)]
            nc = len(cao)
            cao_edges = [Part.makeLine(Vector(cao[j][0], cao[j][1], 0),
                                        Vector(cao[(j + 1) % nc][0], cao[(j + 1) % nc][1], 0))
                         for j in range(nc)]
            holes.append(Part.Wire(cao_edges))
            holes[-1].reverse()
    else:
        for i in range(n_h):
            cx = -hw + sp_h * 0.5 + i * sp_h
            holes.append(Part.Wire(Part.makeCircle(bore_r, Vector(cx, 0, 0))))
        for i in range(n_h - 1):
            mx = (-hw + sp_h * 0.5 + i * sp_h) + sp_h * 0.5
            cao = [(mx + 13, -4.75), (mx + 13, 4.75),
                   (mx + 8.836, 4.75), (mx + 4.386, 9.2),
                   (mx - 4.386, 9.2), (mx - 8.836, 4.75),
                   (mx - 13, 4.75), (mx - 13, -4.75),
                   (mx - 8.836, -4.75), (mx - 4.386, -9.2),
                   (mx + 4.386, -9.2), (mx + 8.836, -4.75)]
            nc = len(cao)
            cao_edges = [Part.makeLine(Vector(cao[j][0], cao[j][1], 0),
                                        Vector(cao[(j + 1) % nc][0], cao[(j + 1) % nc][1], 0))
                         for j in range(nc)]
            holes.append(Part.Wire(cao_edges))
            holes[-1].reverse()
    return Part.Face([wire] + holes)


def make_40series_vslot(w, h):
    """40-series V-slot from 5.svg."""

    hw, hh = w * 0.5, h * 0.5

    R_slot = [( 0.000,  5.089), (-1.001,  5.089), (-1.001,  4.089),
              (-4.511,  4.089), (-4.511,  6.589), (-2.511,  6.589),
              (-3.011, 10.289), (-8.011, 10.289), (-12.401, 5.899),
              (-12.401, -5.911), (-8.011, -10.311), (-3.011, -10.289),
              (-2.511, -7.611), (-3.511, -6.611), (-4.511, -6.611),
              (-4.511, -4.111), (-1.001, -4.111), (-1.001, -5.111),
              ( 0.000, -5.111)]

    B_slot = [(-dy, dx) for dx, dy in R_slot]
    T_slot = [(dy, -dx) for dx, dy in R_slot]
    L_slot = [(-dx, -dy) for dx, dy in R_slot]

    n_v = max(1, int(h / 40))
    n_h = max(1, int(w / 40))
    sp_v = h / n_v
    sp_h = w / n_h

    SLOT_N = len(R_slot)

    def build_face_verts(face_type):
        verts = []
        if face_type == 'L':
            verts.append((-hw, -hh))
            verts.append((-hw, -hh + 4.5))
            for i in range(n_v):
                yc = -hh + sp_v * 0.5 + i * sp_v
                verts.extend([(-hw + dx, yc + dy) for dx, dy in L_slot])
            verts.append((-hw, hh - 4.5))
        elif face_type == 'B':
            verts.append((-hw, hh))
            verts.append((-hw + 4.5, hh))
            for i in range(n_h):
                xc = -hw + sp_h * 0.5 + i * sp_h
                verts.extend([(xc + dx, hh + dy) for dx, dy in B_slot])
            verts.append((hw - 4.5, hh))
        elif face_type == 'R':
            verts.append((hw, hh))
            verts.append((hw, hh - 4.5))
            for i in range(n_v):
                yc = hh - sp_v * 0.5 - i * sp_v
                verts.extend([(hw + dx, yc + dy) for dx, dy in R_slot])
            verts.append((hw, -hh + 4.5))
        elif face_type == 'T':
            verts.append((hw, -hh))
            verts.append((hw - 4.5, -hh))
            for i in range(n_h):
                xc = hw - sp_h * 0.5 - i * sp_h
                verts.extend([(xc + dx, -hh + dy) for dx, dy in T_slot])
            verts.append((-hw + 4.5, -hh))
        return [Vector(x, y, 0) for x, y in verts]

    def face_lines(verts, n_slots):
        nv = len(verts)
        lines = [Part.makeLine(verts[i], verts[i + 1]) for i in range(nv - 1)]
        for s in reversed(range(n_slots)):
            base = 2 + s * SLOT_N
            lines[base + 12:base + 14] = draft_fillet(
                [lines[base + 12], lines[base + 13]], 1.0)
            lines[base + 10:base + 12] = draft_fillet(
                [lines[base + 10], lines[base + 11]], 0.5)
            lines[base + 5:base + 7] = draft_fillet(
                [lines[base + 5], lines[base + 6]], 0.5)
        return lines

    Lv = build_face_verts('L'); Bv = build_face_verts('B')
    Rv = build_face_verts('R'); Tv = build_face_verts('T')

    Ll = face_lines(Lv, n_v); Bl = face_lines(Bv, n_h)
    Rl = face_lines(Rv, n_v); Tl = face_lines(Tv, n_h)

    lines = (Ll + [Part.makeLine(Lv[-1], Bv[0])] + Bl
           + [Part.makeLine(Bv[-1], Rv[0])] + Rl
           + [Part.makeLine(Rv[-1], Tv[0])] + Tl
           + [Part.makeLine(Tv[-1], Lv[0])])

    nLf = len(Ll) + 1; nBf = len(Bl) + 1; nRf = len(Rl) + 1

    corners = [(nLf + nBf + nRf, 4.5), (nLf + nBf, 4.5), (nLf, 4.5)]
    for ci, cr in corners:
        lines[ci - 1:ci + 1] = draft_fillet([lines[ci - 1], lines[ci]], cr)
    last = len(lines) - 1
    w = draft_fillet([lines[last], lines[0]], 4.5)
    lines[last:] = w[:1]
    lines[:1] = w[1:]

    wire = Part.Wire(lines)
    holes = []
    bore_r = 3.4
    if n_v >= n_h:
        for i in range(n_v):
            cy = -hh + sp_v * 0.5 + i * sp_v
            holes.append(Part.Wire(Part.makeCircle(bore_r, Vector(0, cy, 0))))
        for i in range(n_v - 1):
            my = (-hh + sp_v * 0.5 + i * sp_v) + sp_v * 0.5
            cao = [(-5.903, my - 12.4), (-11.003, my - 7.3), (-17.0, my - 7.3),
                   (-17.0, my + 7.3), (-11.003, my + 7.3), (-5.903, my + 12.4),
                   (5.903, my + 12.4), (11.003, my + 7.3), (17.0, my + 7.3),
                   (17.0, my - 7.3), (11.003, my - 7.3), (5.903, my - 12.4)]
            nc = len(cao)
            cao_edges = [Part.makeLine(Vector(cao[j][0], cao[j][1], 0),
                                        Vector(cao[(j + 1) % nc][0], cao[(j + 1) % nc][1], 0))
                         for j in range(nc)]
            holes.append(Part.Wire(cao_edges))
            holes[-1].reverse()
    else:
        for i in range(n_h):
            cx = -hw + sp_h * 0.5 + i * sp_h
            holes.append(Part.Wire(Part.makeCircle(bore_r, Vector(cx, 0, 0))))
        for i in range(n_h - 1):
            mx = (-hw + sp_h * 0.5 + i * sp_h) + sp_h * 0.5
            cao = [(mx - 5.903, -12.4), (mx - 11.003, -7.3), (mx - 17.0, -7.3),
                   (mx - 17.0, 7.3), (mx - 11.003, 7.3), (mx - 5.903, 12.4),
                   (mx + 5.903, 12.4), (mx + 11.003, 7.3), (mx + 17.0, 7.3),
                   (mx + 17.0, -7.3), (mx + 11.003, -7.3), (mx + 5.903, -12.4)]
            nc = len(cao)
            cao_edges = [Part.makeLine(Vector(cao[j][0], cao[j][1], 0),
                                        Vector(cao[(j + 1) % nc][0], cao[(j + 1) % nc][1], 0))
                         for j in range(nc)]
            holes.append(Part.Wire(cao_edges))
            holes[-1].reverse()

    c_base = [(0, 0), (0, 6.262), (6.262, 6.262), (6.262, 0)]
    for mx, my in [(-1, 1), (1, 1), (-1, -1), (1, -1)]:
        cx = (-hw + 2 + 6.262) if mx == -1 else (hw - 2 - 6.262)
        cy = (hh - 2) if my == -1 else (-hh + 2)
        cv = [Vector(mx * x + cx, my * y + cy, 0) for x, y in c_base]
        ncv = len(cv)
        c_edges = [Part.makeLine(cv[j], cv[(j + 1) % ncv]) for j in range(ncv)]
        c_edges[2:4] = draft_fillet([c_edges[2], c_edges[3]], 2.5)
        h = Part.Wire(c_edges)
        if mx == my:
            h.reverse()
        holes.append(h)
    return Part.Face([wire] + holes)


# ----- V-slot -----------------------------------------------------------------


@lru_cache(maxsize=128)
def make_vslot_face(w, h):
    """Generate a V-slot profile cross-section for width *w* and height *h*.

    Square profiles use 8-wedge symmetry with proportionally scaled
    V-groove geometry.  Rectangular profiles build the perimeter
    directly.
    """
    if w == h:
        return _make_vslot_square(w)
    return _make_vslot_rect(w, h)


def _make_vslot_square(size):
    """Square V-slot via 8-wedge symmetry with scaled groove."""
    half = size * 0.5
    scale = half / 10.0

    # 20 mm V-slot baseline — all values scale with size
    d_inner = (5.68 + 3 / math.sqrt(2)) * scale  # centre square diagonal
    neck = 5.68 * scale                           # ball-channel neck
    lip = 1.8 * scale                             # edge-to-groove lip
    v_ref = 1.64 * scale                          # V-groove reference depth
    v_diag = 1.5 / math.sqrt(2) * scale           # V-tip diagonal offset

    outline = [
        (0.5 * d_inner, 0, 0),
        (0.5 * d_inner, 0.5 * neck, 0),
        (half - lip - v_ref, half - lip - v_ref - v_diag, 0),
        (half - lip, half - lip - v_ref - v_diag, 0),
        (half - lip, 0.5 * neck, 0),
        (half, 0.5 * neck + lip, 0),
        (half, half, 0),
    ]

    symmetry = [
        (0, 0, False, False, False, False),
        (0, 0, True, True, False, False),
        (0, 0, False, True, True, False),
        (0, 0, True, False, True, False),
        (0, 0, False, False, True, True),
        (0, 0, True, True, True, True),
        (0, 0, False, True, False, True),
        (0, 0, True, False, False, True),
    ]

    vertices = 8 * [outline]
    fillets = [5, 17, 29, 41]
    corner_offset = 0
    circle_offsets = [0]

    out = assemble(symmetry, vertices)
    out = fillet(out, fillets, 1.5)
    out = Part.Wire(out)

    holes = []

    corner_sym = [
        (0, 0, False, False, False, False),
        (corner_offset, 0, False, False, True, False),
        (corner_offset, 0, False, False, True, True),
        (0, 0, False, False, False, True),
    ]
    cornerhole = [
        (half - lip, half - lip - v_ref - v_diag + 1.07 * scale, 0),
        (half - lip, half - lip, 0),
        (half - lip - v_ref - v_diag + 1.07 * scale, half - lip, 0),
        (half - lip, half - lip - v_ref - v_diag + 1.07 * scale, 0),
    ]
    for sym in corner_sym:
        holes.append(Part.Wire(assemble([sym], [cornerhole])))
        if sym[4] == sym[5]:
            holes[-1].reverse()

    bore_r = 2.1 * scale
    for offset in circle_offsets:
        holes.append(Part.Wire(Part.makeCircle(bore_r, Vector(offset, 0, 0))))
        holes[-1].reverse()

    # big spaces (only if more than one segment)
    if len(circle_offsets) > 1:
        space = [
            (0.5 * d_inner, 0, 0),
            (0.5 * d_inner, 0.5 * neck, 0),
            (half - 2.7 * scale, half - lip - 1.96 * scale, 0),
            (half - 2.7 * scale, half - lip, 0),
            (half, half - lip, 0),
        ]
        space_sym = [
            (0, 0, False, False, True, False),
            (-size, 0, True, False, False, False),
            (-size, 0, False, False, False, True),
            (0, 0, True, False, True, True),
        ]
        for offset in circle_offsets[:-1]:
            holes.append(Part.Wire(assemble(space_sym, 4 * [space], (offset, 0))))
            holes[-1].reverse()

    return Part.Face([out] + holes)


def _build_rect_vslot_perimeter(w, h):
    """Build perimeter vertices for a rectangular V-slot profile.

    All groove dimensions follow the 20×20 V-slot baseline, scaled by
    ``series / 20.0`` so that every size matches the proven 20 mm pattern.
    """
    hw, hh = w * 0.5, h * 0.5
    scale = min(w, h) / 20.0

    # 20 mm V-slot baseline dimensions
    neck = 5.68                     # V-opening width at surface (mm)
    lip  = 1.8                      # flat lip from edge to V-groove (mm)
    v_ref = 1.64                    # V-groove slope depth (mm)
    v_diag = 1.5 / math.sqrt(2)     # V-tip diagonal offset (mm)

    # Scaled groove geometry
    groove_w = neck * scale          # opening width at face
    groove_d = (lip + v_ref) * scale # depth from face to V-slope start
    # V-tip sits at groove_d + v_diag*scale below the face

    # Groove centred on each face, spans 55 %
    hs = w * 0.275
    vs = h * 0.275
    hg = groove_w * 0.5
    vg = groove_w * 0.5

    pts = []

    # ---- bottom face (y = -hh, x: -hw → +hw) — V-groove goes UP ----
    pts.append(Vector(-hw, -hh, 0))
    pts.append(Vector(-hs, -hh, 0))
    pts.append(Vector(-hs, -hh + groove_d, 0))
    pts.append(Vector(-hg, -hh + groove_d, 0))
    pts.append(Vector(0, -hh + groove_d + v_diag * scale, 0))  # V tip
    pts.append(Vector(hg, -hh + groove_d, 0))
    pts.append(Vector(hs, -hh + groove_d, 0))
    pts.append(Vector(hs, -hh, 0))
    pts.append(Vector(hw, -hh, 0))

    # ---- right face (x = hw, y: -hh → +hh) — V-groove goes LEFT ---
    pts.append(Vector(hw, -vs, 0))
    pts.append(Vector(hw - groove_d, -vs, 0))
    pts.append(Vector(hw - groove_d, -vg, 0))
    pts.append(Vector(hw - groove_d - v_diag * scale, 0, 0))  # V tip
    pts.append(Vector(hw - groove_d, vg, 0))
    pts.append(Vector(hw - groove_d, vs, 0))
    pts.append(Vector(hw, vs, 0))
    pts.append(Vector(hw, hh, 0))

    # ---- top face (y = hh, x: +hw → -hw) — V-groove goes DOWN ----
    pts.append(Vector(hs, hh, 0))
    pts.append(Vector(hs, hh - groove_d, 0))
    pts.append(Vector(hg, hh - groove_d, 0))
    pts.append(Vector(0, hh - groove_d - v_diag * scale, 0))  # V tip
    pts.append(Vector(-hg, hh - groove_d, 0))
    pts.append(Vector(-hs, hh - groove_d, 0))
    pts.append(Vector(-hs, hh, 0))
    pts.append(Vector(-hw, hh, 0))

    # ---- left face (x = -hw, y: +hh → -hh) — V-groove goes RIGHT --
    pts.append(Vector(-hw, vs, 0))
    pts.append(Vector(-hw + groove_d, vs, 0))
    pts.append(Vector(-hw + groove_d, vg, 0))
    pts.append(Vector(-hw + groove_d + v_diag * scale, 0, 0))  # V tip
    pts.append(Vector(-hw + groove_d, -vg, 0))
    pts.append(Vector(-hw + groove_d, -vs, 0))
    pts.append(Vector(-hw, -vs, 0))

    return pts


def _make_vslot_rect(w, h):
    """Generate a rectangular V-slot profile via direct perimeter wire."""
    pts = _build_rect_vslot_perimeter(w, h)
    n = len(pts)

    lines = [Part.makeLine(pts[i], pts[(i + 1) % n]) for i in range(n)]

    # The V-slot perimeter has 9+8+8+7 = 32 vertices → 32 edges.
    # Corner indices (original): bottom-right 7, top-right 15,
    # top-left 23, bottom-left wraps.
    cor_r = 1.5

    # Fillet from highest index downward so earlier indices stay valid
    lines[23:25] = draft_fillet(lines[23:25], cor_r)   # top-left   idx 23
    lines[15:17] = draft_fillet(lines[15:17], cor_r)   # top-right  idx 15 → +1 = 16
    lines[7:9] = draft_fillet(lines[7:9], cor_r)       # bottom-right idx 7 → +2 = 9

    last = len(lines) - 1
    wrap_edges = [lines[last], lines[0]]
    filleted = draft_fillet(wrap_edges, cor_r)
    lines[last:] = filleted[:1]
    lines[:1] = filleted[1:]

    wire = Part.Wire(lines)

    holes = []
    scale = min(w, h) / 20.0

    # Central bore matching the 20×20 V-slot pattern
    bore_r = 2.1 * scale
    holes.append(Part.Wire(Part.makeCircle(bore_r, Vector(0, 0, 0))))
    holes[-1].reverse()

    return Part.Face([wire] + holes)

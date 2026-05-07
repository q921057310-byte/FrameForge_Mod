"""Parse 40-series aluminum extrusion SVG profiles and extract vertex data."""

import re
import xml.etree.ElementTree as ET


def parse_svg_path_d(d_str):
    """Parse an SVG path 'd' attribute into a list of commands.
    
    Returns list of tuples: (cmd, params_list)
    cmd is one of: M, L, A
    """
    d_str = d_str.strip()
    tokens = re.findall(r'[MLVAZmlvaz]|[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', d_str)
    
    commands = []
    i = 0
    while i < len(tokens):
        cmd = tokens[i]
        i += 1
        if cmd in 'ML':
            # Expect pairs of x y
            params = []
            while i < len(tokens) and _is_number(tokens[i]):
                x = float(tokens[i])
                y = float(tokens[i + 1])
                params.append((x, y))
                i += 2
            commands.append((cmd, params))
        elif cmd in 'A':
            # Arc: rx ry x-axis-rotation large-arc-flag sweep-flag x y
            if i + 6 <= len(tokens):
                rx = float(tokens[i])
                ry = float(tokens[i + 1])
                x_rot = float(tokens[i + 2])
                large_arc = int(tokens[i + 3])
                sweep = int(tokens[i + 4])
                x = float(tokens[i + 5])
                y = float(tokens[i + 6])
                i += 7
                commands.append((cmd, [(rx, ry, x_rot, large_arc, sweep, x, y)]))
        elif cmd in 'Zz':
            commands.append((cmd, []))
    return commands


def _is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def parse_svg(svg_path, transform_scale_y=-1):
    """Parse SVG file and extract all path segments.
    
    Args:
        svg_path: Path to SVG file
        transform_scale_y: Y scale factor from the transform (for scale(1,-1) this is -1)
    
    Returns:
        list of dicts with: id, type ('line' or 'arc'), start, end (in profile coords),
        and for arcs: rx, ry, rotation, large_arc, sweep
    """
    tree = ET.parse(svg_path)
    root = tree.getroot()
    
    ns = {'svg': 'http://www.w3.org/2000/svg'}
    segments = []
    
    for path_elem in root.findall('.//svg:path', ns):
        elem_id = path_elem.get('id', '')
        d_str = path_elem.get('d', '')
        
        commands = parse_svg_path_d(d_str)
        
        for cmd, params_list in commands:
            if cmd == 'M':
                # Move to - start of segment
                # In our case, M always has exactly one coordinate pair, followed by L or A
                pass
            elif cmd == 'L':
                # Line from last point to new point
                # The M command precedes it, giving us start
                pass
            elif cmd == 'A':
                # Arc
                pass
            elif cmd == 'Z':
                # Close path
                pass
        
        # For our SVG structure, each path element starts with M x y followed by L/A
        # So we treat the M as the start point and the L/A as the end/target
        for cmd, params_list in commands:
            if cmd == 'M':
                last_point = params_list[0]  # (x, y) in SVG coords
            elif cmd == 'L':
                end_point = params_list[0]
                seg = {
                    'id': elem_id,
                    'type': 'line',
                    'start': (last_point[0], last_point[1] * transform_scale_y),
                    'end': (end_point[0], end_point[1] * transform_scale_y),
                }
                segments.append(seg)
                last_point = end_point
            elif cmd == 'A':
                rx, ry, x_rot, large_arc, sweep, x, y = params_list[0]
                seg = {
                    'id': elem_id,
                    'type': 'arc',
                    'start': (last_point[0], last_point[1] * transform_scale_y),
                    'end': (x, y * transform_scale_y),
                    'rx': rx,
                    'ry': ry,
                    'rotation': x_rot,
                    'large_arc': large_arc,
                    'sweep': sweep,
                }
                segments.append(seg)
                last_point = (x, y)
            elif cmd == 'Z':
                pass
    
    return segments


def build_vertex_list(segments):
    """Build continuous vertex chain from segments, tracking arc points separately."""
    vertices = []
    arc_vertices = []
    
    for seg in segments:
        start = seg['start']
        end = seg['end']
        
        if seg['type'] == 'line':
            vertices.append(end)
        elif seg['type'] == 'arc':
            vertices.append(f"ARC: start={start}, end={end}, r=({seg['rx']}, {seg['ry']})")
            arc_vertices.append(seg)
    
    return vertices, arc_vertices


def build_closed_chain(segments):
    """Build chain of all unique vertex points (closed loop).
    Returns list of (x, y) tuples and list of arc segment dicts.
    """
    points = []
    arcs = []
    
    for i, seg in enumerate(segments):
        start = seg['start']
        end = seg['end']
        
        if i == 0:
            points.append(start)
        
        if seg['type'] == 'line':
            points.append(end)
        elif seg['type'] == 'arc':
            arcs.append({
                'index': len(points) - 1,
                'start': start,
                'end': end,
                'rx': seg['rx'],
                'ry': seg['ry'],
                'rotation': seg['rotation'],
                'large_arc': seg['large_arc'],
                'sweep': seg['sweep'],
            })
            points.append(end)
    
    return points, arcs


print("=" * 80)
print("PARSING: 5.svg (40x40 full perimeter)")
print("=" * 80)

segments_5 = parse_svg(
    r"C:\Users\xing\AppData\Roaming\FreeCAD\v1-1\Mod\FrameForge2\freecad\frameforge2\resources\profiles\aluminum\svg\5.svg",
    transform_scale_y=-1
)

print(f"\nTotal segments: {len(segments_5)}")
line_count = sum(1 for s in segments_5 if s['type'] == 'line')
arc_count = sum(1 for s in segments_5 if s['type'] == 'arc')
print(f"Line segments: {line_count}")
print(f"Arc segments: {arc_count}")

# Check continuity
for i in range(1, len(segments_5)):
    prev_end = segments_5[i-1]['end']
    curr_start = segments_5[i]['start']
    dx = prev_end[0] - curr_start[0]
    dy = prev_end[1] - curr_start[1]
    dist = (dx**2 + dy**2)**0.5
    if dist > 0.01:
        print(f"  GAP at segment {i} ({segments_5[i]['id']}): prev_end={prev_end}, curr_start={curr_start}, dist={dist:.4f}")

# Build the vertex chain
points_5, arcs_5 = build_closed_chain(segments_5)

print(f"\nVertex chain length: {len(points_5)} points")
print(f"Arc segments: {len(arcs_5)}")

print("\n--- OUTER PERIMETER (line vertices) ---")
print("outer_perimeter_line = [")
for p in points_5:
    if isinstance(p, tuple):
        print(f"    ({p[0]:.6f}, {p[1]:.6f}),")
print("]")

print("\n--- ARC SEGMENTS ---")
print("outer_perimeter_arcs = [")
for arc in arcs_5:
    print(f"    {{")
    print(f"        'start': ({arc['start'][0]:.6f}, {arc['start'][1]:.6f}),")
    print(f"        'end': ({arc['end'][0]:.6f}, {arc['end'][1]:.6f}),")
    print(f"        'rx': {arc['rx']:.6f},")
    print(f"        'ry': {arc['ry']:.6f},")
    print(f"        'rotation': {arc['rotation']:.6f},")
    print(f"        'large_arc': {arc['large_arc']},")
    print(f"        'sweep': {arc['sweep']},")
    print(f"        'index': {arc['index']},")
    print(f"    }},")
print("]")

print("\n--- ALL VERTICES (with arc notations) ---")
print("all_vertices = [")
for p in points_5:
    if isinstance(p, tuple):
        print(f"    ({p[0]:.6f}, {p[1]:.6f}),")
    else:
        print(f"    # {p}")
print("]")


print()
print("=" * 80)
print("PARSING: 40槽口.svg (inner octagon hole)")
print("=" * 80)

segments_caokou = parse_svg(
    r"C:\Users\xing\AppData\Roaming\FreeCAD\v1-1\Mod\FrameForge2\freecad\frameforge2\resources\profiles\aluminum\svg\40槽口.svg",
    transform_scale_y=-1
)

print(f"\nTotal segments: {len(segments_caokou)}")

# The caokou is a simple 12-segment polygon - all lines
# Build vertices from endpoints
caokou_vertices = []
for i, seg in enumerate(segments_caokou):
    start = seg['start']
    end = seg['end']
    if i == 0:
        caokou_vertices.append(start)
    caokou_vertices.append(end)

# Check if closed
first = caokou_vertices[0]
last = caokou_vertices[-1]
dx_close = first[0] - last[0]
dy_close = first[1] - last[1]
dist_close = (dx_close**2 + dy_close**2)**0.5
print(f"Closure gap: {dist_close:.6f} (first={first}, last={last})")

# Remove duplicate last point if closed
if dist_close < 0.01:
    caokou_vertices = caokou_vertices[:-1]

print(f"\nPolygon vertices: {len(caokou_vertices)} points")

print("\n--- CAOKOU VERTICES (inner 12-sided polygon) ---")
print("caokou_vertices = [")
for v in caokou_vertices:
    print(f"    ({v[0]:.6f}, {v[1]:.6f}),")
print("]")


# Also output as raw lists for easy copying
print()
print("=" * 80)
print("CLEAN PYTHON LISTS (ready to copy)")
print("=" * 80)

print("\n# Outer perimeter vertices (line segments only)")
print("outer_perimeter_line_vertices = [")
for p in points_5:
    if isinstance(p, tuple):
        print(f"    ({p[0]:.6f}, {p[1]:.6f}),")
print("]")

print("\n# Outer perimeter arc segments")
print("outer_perimeter_arcs = [")
for arc in arcs_5:
    print(f"    (({arc['start'][0]:.6f}, {arc['start'][1]:.6f}),")
    print(f"     ({arc['end'][0]:.6f}, {arc['end'][1]:.6f}),")
    print(f"     {arc['rx']:.6f}, {arc['ry']:.6f}),")
print("]")

print("\n# Caokou (inner hole) vertices - 12-sided polygon")
print("caokou_vertices = [")
for v in caokou_vertices:
    print(f"    ({v[0]:.6f}, {v[1]:.6f}),")
print("]")

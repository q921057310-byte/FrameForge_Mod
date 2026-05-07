"""Reconstruct face generation code from bytecode disassembly."""
import re

# Read the disassembly
with open('profile_dis.txt', 'r') as f:
    dis_lines = f.readlines()

# Group instructions by line number
lines = {}  # line_no -> [(opname, argrepr_or_const)]
for line in dis_lines:
    m = re.match(r'^\s+L\s*(\d+)\s+(\d+)\s+(\w+)(?:\s+(.*))?$', line)
    if m:
        lineno = int(m.group(1))
        opname = m.group(3)
        argrepr = (m.group(4) or '').strip()
        if lineno not in lines:
            lines[lineno] = []
        lines[lineno].append((opname, argrepr))

# Now let's map what operations happen on each line
# Focus on lines with meaningful operations (not CACHE/NOP/RESUME)
print("=== Line-by-line operation summary (face gen area: lines 449-1068) ===")
for lineno in sorted(lines.keys()):
    if lineno < 449 or lineno > 1075:
        continue
    ops = lines[lineno]
    # Skip lines with only CACHE/NOP/RESUME/POP_TOP/PUSHNULL/PRECALL/CALL
    meaningful = [(op, arg) for op, arg in ops if op not in ('CACHE', 'NOP', 'RESUME', 'POP_TOP', 'PUSHNULL', 'PRECALL', 'CALL')]
    if not meaningful:
        continue
    # For family comparisons, show the LOAD_CONST
    consts = []
    for op, arg in ops:
        if op == 'LOAD_CONST' and arg and arg.startswith("'"):
            consts.append(arg)
    if consts:
        print(f"  L{lineno}: {', '.join(meaningful[:3][0])} — consts: {', '.join(consts)}")
    else:
        print(f"  L{lineno}: {', '.join([f'{op} {arg}' for op, arg in meaningful[:5]])}")

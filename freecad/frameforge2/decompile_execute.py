"""Reconstruct profile.py execute method source from bytecode."""
from xdis import load_module, Bytecode
from xdis.opcodes import opcode_311
import dis

result = load_module('__pycache__/profile.cpython-311.pyc')
code = result[3]

profile = next(c for c in code.co_consts if hasattr(c, 'co_name') and c.co_name == 'Profile')
execute = next(c for c in profile.co_consts if hasattr(c, 'co_name') and c.co_name == 'execute')

opc = opcode_311
bc = Bytecode(execute, opc)

# Build per-line instruction groups
line_instrs = {}
for instr in bc:
    line = instr.starts_line
    if line is None:
        continue
    if line not in line_instrs:
        line_instrs[line] = []
    line_instrs[line].append(instr)

# For tracking stack state
# Each line, we track what's on the stack
# We then generate Python source from the stack operations

def const_repr(value):
    if isinstance(value, str):
        return repr(value)
    if isinstance(value, float):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, bool):
        return 'True' if value else 'False'
    if value is None:
        return 'None'
    return repr(value)

def resolve_arg(instr):
    """Resolve instruction argument to a readable form."""
    if instr.argrepr:
        return instr.argrepr
    return str(instr.arg)

# Process each line
print("=== Line reconstruction (partial) ===")
for line_no in sorted(line_instrs.keys()):
    if line_no < 449 or line_no > 1075:
        continue

    instrs = line_instrs[line_no]

    # Get all meaningful instructions (skip CACHE)
    meaningful = [i for i in instrs if i.opname != 'CACHE']

    if not meaningful:
        continue

    # Show key operations
    ops_str = []
    for instr in meaningful:
        if instr.opname in ('RESUME', 'NOP', 'PUSHNULL'):
            continue
        ops_str.append(f"{instr.opname}:{resolve_arg(instr)[:30]}")

    if ops_str:
        print(f"L{line_no}: {'; '.join(ops_str)}")

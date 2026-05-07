"""Reconstruct execute() source from bytecode using stack-based approach.
Only handles the subset of Python used in the face generation code.
"""
from xdis import load_module, Bytecode
from xdis.opcodes import opcode_311

result = load_module('__pycache__/profile.cpython-311.pyc')
module_code = result[3]

profile_class = next(c for c in module_code.co_consts if hasattr(c, 'co_name') and c.co_name == 'Profile')
execute_code = next(c for c in profile_class.co_consts if hasattr(c, 'co_name') and c.co_name == 'execute')

bc = Bytecode(execute_code, opcode_311)

# Build instruction list
instrs = list(bc)

# Map offset -> instruction
offset_map = {i.offset: i for i in instrs}

# Constants and names from the code object
consts = execute_code.co_consts
names = execute_code.co_names
varnames = execute_code.co_varnames

def resolve_arg(instr):
    """Get the human-readable argument for an instruction."""
    if instr.opname in ('LOAD_CONST',):
        val = consts[instr.arg]
        if isinstance(val, str):
            return repr(val)
        if isinstance(val, float):
            return str(val)
        if isinstance(val, int):
            return str(val)
        if val is None:
            return 'None'
        if val is True:
            return 'True'
        if val is False:
            return 'False'
        return str(val)
    if instr.opname == 'LOAD_FAST':
        return varnames[instr.arg]
    if instr.opname == 'LOAD_GLOBAL':
        return names[instr.arg]
    if instr.opname == 'LOAD_ATTR':
        attr = names[instr.arg]
        return f'.{attr}'
    return instr.argrepr or ''

# Process instructions grouped by line
class StackVM:
    """Simple stack-based expression reconstructor."""
    def __init__(self):
        self.stack = []

    def _finalize(self):
        """Format final stack state as expression."""
        if self.stack:
            return self._format(self.stack[-1])
        return ""

    def process(self, instrs):
        """Process a list of instructions for one line."""
        self.stack = []
        for instr in instrs:
            self._handle(instr)
        return self._finalize()

    def _handle(self, instr):
        op = instr.opname
        if op == 'CACHE':
            return
        if op == 'RESUME':
            return
        if op == 'NOP':
            return
        if op == 'PUSHNULL':
            self.stack.append(None)
            return

        if op == 'LOAD_CONST':
            val = consts[instr.arg]
            self.stack.append(val)
        elif op == 'LOAD_FAST':
            self.stack.append(('var', varnames[instr.arg]))
        elif op == 'LOAD_GLOBAL':
            self.stack.append(('global', names[instr.arg]))
        elif op == 'LOAD_ATTR':
            obj = self.stack.pop()
            attr = names[instr.arg]
            if isinstance(obj, tuple) and obj[0] in ('global', 'var', 'attr'):
                self.stack.append(('attr', obj, attr))
            else:
                self.stack.append(('attr', obj, attr))
        elif op == 'LOAD_METHOD':
            # Similar to LOAD_ATTR but for method calls
            obj = self.stack.pop()
            method = names[instr.arg]
            self.stack.append(('method', obj, method))
        elif op == 'PRECALL':
            # Marks the call boundary, arg is number of positional args
            pass
        elif op == 'CALL':
            argc = instr.arg
            # Pop args in reverse order
            args = []
            for _ in range(argc):
                args.insert(0, self.stack.pop())
            # Pop the method/function
            fn = self.stack.pop()
            # Pop any PUSHNULL (for method calls)
            if self.stack and self.stack[-1] is None:
                self.stack.pop()

            if isinstance(fn, tuple) and fn[0] == 'method':
                obj = fn[1]
                method = fn[2]
                self.stack.append(('call', ('attr', obj, method), args))
            elif isinstance(fn, tuple) and fn[0] == 'attr':
                self.stack.append(('call', fn, args))
            else:
                self.stack.append(('call', fn, args))
        elif op == 'BUILD_LIST':
            n = instr.arg
            items = []
            for _ in range(n):
                items.insert(0, self.stack.pop())
            self.stack.append(('list', items))
        elif op == 'BUILD_TUPLE':
            n = instr.arg
            items = []
            for _ in range(n):
                items.insert(0, self.stack.pop())
            self.stack.append(('tuple', items))
        elif op == 'BINARY_SUBSCR':
            key = self.stack.pop()
            obj = self.stack.pop()
            self.stack.append(('subscr', obj, key))
        elif op in ('BINARY_OP',):
            rhs = self.stack.pop()
            lhs = self.stack.pop()
            opname = instr.argrepr
            if opname == '+':
                self.stack.append(('binop', '+', lhs, rhs))
            elif opname == '-':
                self.stack.append(('binop', '-', lhs, rhs))
            elif opname == '*':
                self.stack.append(('binop', '*', lhs, rhs))
            elif opname == '/':
                self.stack.append(('binop', '/', lhs, rhs))
            elif opname == '**':
                self.stack.append(('binop', '**', lhs, rhs))
            elif opname == '%':
                self.stack.append(('binop', '%', lhs, rhs))
            elif opname == '<<':
                self.stack.append(('binop', '<<', lhs, rhs))
            elif opname == '|':
                self.stack.append(('binop', '|', lhs, rhs))
            elif opname == '&':
                self.stack.append(('binop', '&', lhs, rhs))
            elif opname == '+=':
                self.stack.append(('aug', '+=', lhs, rhs))
            else:
                self.stack.append(('binop', opname, lhs, rhs))
        elif op == 'COMPARE_OP':
            rhs = self.stack.pop()
            lhs = self.stack.pop()
            opname = instr.argrepr
            self.stack.append(('compare', opname, lhs, rhs))
        elif op.startswith('POP_JUMP_FORWARD_IF'):
            cond = self.stack.pop()
            # Just keep it as-is
            self.stack.append(('cond', instr.opname, cond))
        elif op == 'JUMP_FORWARD':
            pass  # unconditional jump target
        elif op == 'STORE_FAST':
            val = self.stack.pop()
            varname = varnames[instr.arg]
            self.stack.append(('assign', varname, val))
        elif op == 'STORE_ATTR':
            val = self.stack.pop()
            obj = self.stack.pop()
            attr = names[instr.arg]
            self.stack.append(('store_attr', obj, attr, val))
        elif op == 'STORE_SUBSCR':
            val = self.stack.pop()
            key = self.stack.pop()
            obj = self.stack.pop()
        elif op == 'UNARY_NEGATIVE':
            val = self.stack.pop()
            self.stack.append(('unary', '-', val))
        elif op == 'UNARY_NOT':
            val = self.stack.pop()
            self.stack.append(('unary', 'not', val))
        elif op == 'DELETE_FAST':
            pass
        else:
            # For unrecognized ops, push the raw op
            self.stack.append(('raw', instr.opname, instr.argrepr))

    def _format(self, item, paren=False):
        """Format a stack item as Python expression."""
        if item is None:
            return 'None'
        if isinstance(item, bool):
            return 'True' if item else 'False'
        if isinstance(item, (int, float)):
            return str(item)
        if isinstance(item, str):
            return repr(item)
        if isinstance(item, tuple):
            tag = item[0]
            if tag == 'var':
                return item[1]
            elif tag == 'global':
                return item[1]
            elif tag == 'attr':
                base = self._format(item[1])
                return f'{base}.{item[2]}'
            elif tag == 'method':
                base = self._format(item[1])
                return f'{base}.{item[2]}'  # Method name without calling
            elif tag == 'call':
                fn = self._format(item[1])
                args = ', '.join(self._format(a) for a in item[2])
                return f'{fn}({args})'
            elif tag == 'list':
                if not item[1]:
                    return '[]'
                items = ', '.join(self._format(i) for i in item[1])
                return f'[{items}]'
            elif tag == 'tuple':
                if len(item[1]) == 1:
                    return f'({self._format(item[1][0])},)'
                items = ', '.join(self._format(i) for i in item[1])
                return f'({items})'
            elif tag == 'binop':
                lhs = self._format(item[2], paren=True)
                rhs = self._format(item[3], paren=True)
                op = item[1]
                if paren:
                    return f'({lhs} {op} {rhs})'
                return f'{lhs} {op} {rhs}'
            elif tag == 'aug':
                lhs = self._format(item[2])
                rhs = self._format(item[3])
                return f'{lhs} {item[1]} {rhs}'
            elif tag == 'compare':
                lhs = self._format(item[2])
                rhs = self._format(item[3])
                return f'{lhs} {item[1]} {rhs}'
            elif tag == 'subscr':
                obj = self._format(item[1])
                key = self._format(item[2])
                return f'{obj}[{key}]'
            elif tag == 'assign':
                return f'{item[1]} = {self._format(item[2])}'
            elif tag == 'store_attr':
                return f'{self._format(item[1])}.{item[2]} = {self._format(item[3])}'
            elif tag == 'unary':
                return f'{item[1]}{self._format(item[2])}'
            elif tag == 'cond':
                return f'if {self._format(item[2])}:'
            elif tag == 'raw':
                return f'# RAW: {item[1]} {item[2]}'
            else:
                return str(item)
        return str(item)

# Group instructions by line
from collections import defaultdict
line_ops = defaultdict(list)
for instr in instrs:
    if instr.starts_line is not None:
        line_ops[instr.starts_line].append(instr)

# Process each line in the face generation area
vm = StackVM()
print("=== Reconstructed source (face gen area, lines 449-1075) ===")
print()
for line_no in sorted(line_ops.keys()):
    if line_no < 449 or line_no > 1075:
        continue

    instrs_line = line_ops[line_no]
    meaningful = [i for i in instrs_line if i.opname != 'CACHE']
    if not meaningful:
        print(f"  # (empty line)")
        continue

    result = vm.process(meaningful)

    if vm.stack:
        # Get the expression
        expr = vm._format(vm.stack[-1])
        print(f"  L{line_no}: {expr}")
    else:
        print(f"  L{line_no}: # (no result)")

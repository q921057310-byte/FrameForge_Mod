"""Reconstruct profile.py execute() source from bytecode.
Processes instructions linearly, tracking expression stack.
Emits Python source at statement boundaries (STORE_FAST, POP_TOP).
"""
from xdis import load_module, Bytecode
from xdis.opcodes import opcode_311

result = load_module('__pycache__/profile.cpython-311.pyc')
module_code = result[3]
profile_class = next(c for c in module_code.co_consts if hasattr(c, 'co_name') and c.co_name == 'Profile')
execute_code = next(c for c in profile_class.co_consts if hasattr(c, 'co_name') and c.co_name == 'execute')

opc = opcode_311
bc = Bytecode(execute_code, opc)
instrs = list(bc)

consts = execute_code.co_consts
names = execute_code.co_names
varnames = execute_code.co_varnames

# Pre-compute jump targets
jump_targets = set()
for instr in instrs:
    if instr.opname in ('JUMP_FORWARD',):
        jump_targets.add(instr.offset + 2 + instr.arg * 2)
    elif instr.opname in ('POP_JUMP_FORWARD_IF_FALSE', 'POP_JUMP_FORWARD_IF_TRUE',
                          'JUMP_FORWARD_IF_COND', 'JUMP_IF_FALSE_OR_POP', 'JUMP_IF_TRUE_OR_POP'):
        jump_targets.add(instr.offset + 2 + instr.arg * 2)
    elif instr.opname == 'EXTENDED_ARG':
        pass  # handled by next instruction

# Expression stack frames
# Each frame is a list of stacks, one per basic block

def expr_repr(val):
    """Format a constant or expression as Python source."""
    if val is None:
        return 'None'
    if isinstance(val, bool):
        return 'True' if val else 'False'
    if isinstance(val, (int, float)):
        return str(val) if val != int(val) or isinstance(val, int) else str(val)
    if isinstance(val, str):
        return repr(val)
    if isinstance(val, tuple):
        # Expression tuple: (tag, ...)
        tag = val[0]
        if tag == 'var':
            return val[1]
        elif tag == 'global':
            return val[1]
        elif tag == 'attr':
            return f'{expr_repr(val[1])}.{val[2]}'
        elif tag == 'call':
            fn = expr_repr(val[1])
            args = ', '.join(expr_repr(a) for a in val[2])
            return f'{fn}({args})'
        elif tag == 'binop':
            lhs = expr_repr(val[2])
            rhs = expr_repr(val[3])
            return f'{lhs} {val[1]} {rhs}'
        elif tag == 'unary':
            return f'{val[1]}{expr_repr(val[2])}'
        elif tag == 'compare':
            lhs = expr_repr(val[2])
            rhs = expr_repr(val[3])
            return f'{lhs} {val[1]} {rhs}'
        elif tag == 'subscr':
            obj = expr_repr(val[1])
            key = expr_repr(val[2])
            return f'{obj}[{key}]'
        elif tag == 'list':
            items = ', '.join(expr_repr(i) for i in val[1])
            return f'[{items}]'
        elif tag == 'tuple':
            if len(val[1]) == 1:
                return f'({expr_repr(val[1][0])},)'
            items = ', '.join(expr_repr(i) for i in val[1])
            return f'({items})'
        elif tag == 'method':
            obj = expr_repr(val[1])
            return f'{obj}.{val[2]}'
    return str(val)


class Decompiler:
    def __init__(self):
        self.stack = []
        self.lines = {}  # line_no -> [source_lines]
        self.current_line = None
        self.stmts = []  # (line_no, source) list for current block

    def error(self, msg, instr=None):
        loc = f' (offset {instr.offset}, {instr.opname})' if instr else ''
        line_info = f' L{self.current_line}' if self.current_line else ''
        return f'# ERROR{line_info}{loc}: {msg}'

    def process(self):
        """Process all instructions and emit source code."""
        i = 0
        while i < len(instrs):
            instr = instrs[i]

            # Track current line
            if instr.starts_line is not None:
                self.current_line = instr.starts_line

            # Skip CACHE, RESUME, NOP
            if instr.opname in ('CACHE', 'RESUME', 'NOP'):
                i += 1
                continue

            # Handle EXTENDED_ARG - next instruction absorbs it
            if instr.opname == 'EXTENDED_ARG':
                i += 1
                continue

            # Handle PUSHNULL
            if instr.opname == 'PUSHNULL':
                self.stack.append(None)
                i += 1
                continue

            # LOAD_CONST
            if instr.opname == 'LOAD_CONST':
                val = consts[instr.arg]
                self.stack.append(val)
                i += 1
                continue

            # LOAD_FAST
            if instr.opname == 'LOAD_FAST':
                self.stack.append(('var', varnames[instr.arg]))
                i += 1
                continue

            # LOAD_GLOBAL
            if instr.opname == 'LOAD_GLOBAL':
                # In 3.11+, arg includes flag bit: name_index = arg >> 1, flag = arg & 1
                # flag=1 means push NULL before the global (method-call style)
                name = instr.argrepr
                if name.startswith('NULL + '):
                    name = name[7:]  # strip 'NULL + ' prefix
                    self.stack.append(None)  # implicit PUSHNULL
                self.stack.append(('global', name))
                i += 1
                continue

            # LOAD_ATTR
            if instr.opname == 'LOAD_ATTR':
                obj = self.stack.pop()
                attr = names[instr.arg]
                self.stack.append(('attr', obj, attr))
                i += 1
                continue

            # LOAD_METHOD
            if instr.opname == 'LOAD_METHOD':
                obj = self.stack.pop() if self.stack else None
                method = names[instr.arg]
                self.stack.append(('method', obj, method))
                i += 1
                continue

            # PRECALL - just marks call boundary
            if instr.opname == 'PRECALL':
                i += 1
                continue

            # CALL
            if instr.opname == 'CALL':
                argc = instr.arg
                args = []
                for _ in range(argc):
                    if self.stack:
                        args.insert(0, self.stack.pop())
                fn = self.stack.pop() if self.stack else None
                # Pop PUSHNULL (None marker for method calls)
                if self.stack and self.stack[-1] is None:
                    self.stack.pop()
                self.stack.append(('call', fn, args))
                i += 1
                continue

            # STORE_FAST
            if instr.opname == 'STORE_FAST':
                val = self.stack.pop() if self.stack else None
                vname = varnames[instr.arg]
                src = f'{vname} = {expr_repr(val)}' if val is not None else f'{vname} = None'
                self.stmts.append((self.current_line, src))
                i += 1
                continue

            # STORE_ATTR
            if instr.opname == 'STORE_ATTR':
                val = self.stack.pop() if self.stack else None
                obj = self.stack.pop() if self.stack else None
                attr = names[instr.arg]
                src = f'{expr_repr(obj)}.{attr} = {expr_repr(val)}'
                self.stmts.append((self.current_line, src))
                i += 1
                continue

            # POP_TOP
            if instr.opname == 'POP_TOP':
                val = self.stack.pop() if self.stack else None
                if val is not None:
                    self.stmts.append((self.current_line, expr_repr(val)))
                i += 1
                continue

            # BINARY_OP
            if instr.opname == 'BINARY_OP':
                rhs = self.stack.pop()
                lhs = self.stack.pop()
                opname = instr.argrepr
                self.stack.append(('binop', opname, lhs, rhs))
                i += 1
                continue

            # COMPARE_OP
            if instr.opname == 'COMPARE_OP':
                rhs = self.stack.pop()
                lhs = self.stack.pop()
                opname = instr.argrepr
                self.stack.append(('compare', opname, lhs, rhs))
                i += 1
                continue

            # UNARY_NEGATIVE
            if instr.opname == 'UNARY_NEGATIVE':
                val = self.stack.pop()
                self.stack.append(('unary', '-', val))
                i += 1
                continue

            # UNARY_NOT
            if instr.opname == 'UNARY_NOT':
                val = self.stack.pop()
                self.stack.append(('unary', 'not ', val))
                i += 1
                continue

            # BINARY_SUBSCR
            if instr.opname == 'BINARY_SUBSCR':
                key = self.stack.pop()
                obj = self.stack.pop()
                self.stack.append(('subscr', obj, key))
                i += 1
                continue

            # BUILD_LIST
            if instr.opname == 'BUILD_LIST':
                n = instr.arg
                items = []
                for _ in range(n):
                    items.insert(0, self.stack.pop())
                self.stack.append(('list', items))
                i += 1
                continue

            # BUILD_TUPLE
            if instr.opname == 'BUILD_TUPLE':
                n = instr.arg
                items = []
                for _ in range(n):
                    items.insert(0, self.stack.pop())
                self.stack.append(('tuple', items))
                i += 1
                continue

            # COPY
            if instr.opname == 'COPY':
                n = instr.arg
                if len(self.stack) >= n:
                    val = self.stack[-n]
                    self.stack.append(val)
                i += 1
                continue

            # POP_JUMP_FORWARD_IF_FALSE
            if instr.opname == 'POP_JUMP_FORWARD_IF_FALSE':
                cond = self.stack.pop() if self.stack else None
                target_offset = instr.offset + 2 + instr.arg * 2
                self.stmts.append((self.current_line, ('if_false', cond, target_offset)))
                i += 1
                continue

            # POP_JUMP_FORWARD_IF_TRUE
            if instr.opname == 'POP_JUMP_FORWARD_IF_TRUE':
                cond = self.stack.pop() if self.stack else None
                target_offset = instr.offset + 2 + instr.arg * 2
                self.stmts.append((self.current_line, ('if_true', cond, target_offset)))
                i += 1
                continue

            # JUMP_FORWARD
            if instr.opname == 'JUMP_FORWARD':
                target_offset = instr.offset + 2 + instr.arg * 2
                self.stmts.append((self.current_line, ('jump', target_offset)))
                i += 1
                continue

            # JUMP_BACKWARD
            if instr.opname == 'JUMP_BACKWARD':
                # Loop jumps - ignore for decompilation
                self.stmts.append((self.current_line, ('jump_back',)))
                i += 1
                continue

            # BUILD_MAP, etc. for comprehensions
            if instr.opname in ('BUILD_MAP', 'MAP_ADD', 'LIST_APPEND', 'LIST_EXTEND',
                                'DICT_ADD', 'SET_ADD', 'BUILD_SET', 'BUILD_STRING',
                                'FORMAT_VALUE', 'CONTAINS_OP', 'IS_OP', 'JUMP_IF_FALSE_OR_POP',
                                'JUMP_IF_TRUE_OR_POP', 'FOR_ITER', 'GET_ITER',
                                'YIELD_VALUE', 'SEND', 'MAKE_FUNCTION', 'RETURN_VALUE',
                                'UNPACK_SEQUENCE', 'UNPACK_EX', 'DICT_MERGE',
                                'LOAD_BUILD_CLASS', 'SETUP_ANNOTATIONS',
                                'DELETE_FAST', 'DELETE_ATTR', 'DELETE_SUBSCR',
                                'LOAD_ASSERTION_ERROR', 'RAISE_VARARGS',
                                'PUSH_EXC_INFO', 'POP_EXCEPT', 'RERAISE',
                                'COPY_FREE_VARS', 'LOAD_CLOSURE', 'LOAD_DEREF',
                                'STORE_DEREF', 'STORE_GLOBAL',
                                'LOAD_SUPER_ATTR', 'LOAD_SUPER_METHOD',
                                'KW_NAMES', 'PRECALL', 'CALL_FUNCTION_EX',
                                'SWAP', 'LOAD_LOCALS', 'LOAD_BUILD_CLASS',
                                'MATCH_CLASS', 'MATCH_KEYS', 'MATCH_MAPPING',
                                'MATCH_SEQUENCE', 'MATCH_STAR',
                                'CACHE', 'RESUME', 'NOP', 'EXTENDED_ARG',
                                'PUSHNULL', 'LOAD_CONST', 'LOAD_FAST', 'LOAD_GLOBAL',
                                'LOAD_ATTR', 'STORE_FAST', 'STORE_ATTR',
                                'POP_TOP', 'BINARY_OP', 'COMPARE_OP',
                                'UNARY_NEGATIVE', 'UNARY_NOT',
                                'BINARY_SUBSCR', 'BUILD_LIST', 'BUILD_TUPLE',
                                'COPY', 'POP_JUMP_FORWARD_IF_FALSE',
                                'POP_JUMP_FORWARD_IF_TRUE',
                                'JUMP_FORWARD', 'JUMP_BACKWARD',
                ):
                # Already handled above or skip silently
                i += 1
                continue

            # Unhandled instruction
            self.stmts.append((self.current_line, self.error(f'unhandled: {instr.opname} arg={instr.arg}', instr)))
            i += 1

        # Emit the reconstructed source
        self.emit_source()

    def emit_source(self):
        """Convert the collected statements into structured Python source."""
        print("# === Reconstructed execute() body (face generation section) ===\n")

        # Group by line for display
        line_groups = {}
        for line_no, stmt in self.stmts:
            if line_no not in line_groups:
                line_groups[line_no] = []
            line_groups[line_no].append(stmt)

        # We need to track if/else nesting
        # For simplicity, emit with line numbers and let the user reconstruct
        for line_no in sorted(line_groups.keys()):
            if line_no < 449 or line_no > 1075:
                continue

            stmts = line_groups[line_no]
            for stmt in stmts:
                if isinstance(stmt, str):
                    print(f'  L{line_no}: {stmt}')
                elif isinstance(stmt, tuple):
                    tag = stmt[0]
                    if tag == 'if_false':
                        cond = expr_repr(stmt[1])
                        print(f'  L{line_no}: if not ({cond}):  # jump to offset {stmt[2]}')
                    elif tag == 'if_true':
                        cond = expr_repr(stmt[1])
                        print(f'  L{line_no}: if ({cond}):  # jump to offset {stmt[2]}')
                    elif tag == 'jump':
                        print(f'  L{line_no}: # jump to offset {stmt[1]}')
                    else:
                        print(f'  L{line_no}: # {stmt}')


d = Decompiler()
d.process()

# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Dynamic Data addon.

################################################################################
#                                                                              #
#   Copyright (c) 2018 Mark Ganson ( TheMarkster )                             #
#                                                                              #
#   This library is free software; you can redistribute it and/or modify it    #
#   under the terms of the GNU Lesser General Public License as published      #
#   by the Free Software Foundation; either version 2.1 of the License, or     #
#   (at your option) any later version.                                        #
#                                                                              #
################################################################################

import FreeCAD, re
from PySide import QtCore, QtGui
from PySide.QtCore import Qt


def rewrite_same_object_expr(expression, obj):
    """Rewrite expressions referencing properties on the same object.

    E.g. '=l + 1' with property 'l' on obj becomes '=<<dd>>.l + 1'
    so FreeCAD's expression engine can resolve it.
    """
    if not expression or not expression.startswith("="):
        return expression

    expr = expression[1:]  # strip '='
    prop_names = set(obj.PropertiesList)

    # math functions that should never be rewritten
    math_fns = {
        "sin", "cos", "tan", "asin", "acos", "atan", "atan2",
        "sinh", "cosh", "tanh",
        "sqrt", "exp", "log", "log10", "abs", "floor", "ceil",
        "round", "min", "max", "pow", "mod",
    }

    # Split into tokens while preserving structure.
    # We look for standalone word tokens (not parts of dotted paths like Box.Height)
    result = []
    i = 0
    while i < len(expr):
        # Match a word token
        m = re.match(r'([A-Za-z_]\w*)', expr[i:])
        if m:
            token = m.group(1)
            # Check if this is a dotted access (e.g. Box.Height)
            rest = expr[i + len(token):]
            if rest.startswith('.') or rest.startswith('('):
                # It's a property access like Box.Height or function call like sin()
                result.append(token)
                i += len(token)
                continue

            # Check if token is a property name on this object
            if token in prop_names and token not in math_fns:
                # Rewrite to object-qualified reference
                obj_name = obj.Name if hasattr(obj, 'Name') else obj.Label
                result.append(f"<<{obj_name}>>.{token}")
            else:
                result.append(token)
            i += len(token)
        else:
            # Non-token character, copy as-is
            result.append(expr[i])
            i += 1

    return "=" + "".join(result)


class PropertyTableEditor(QtGui.QDialog):
    """Table-based property editor similar to SolidWorks Custom Properties.

    Shows all existing properties in a table with columns:
    Name | Type | Value/Expression | Result | Group
    Supports adding, deleting, and inline editing of properties.
    """

    def __init__(self, obj, cmd, parent=None):
        super().__init__(parent)
        self.obj = obj
        self.cmd = cmd
        self.property_types = cmd.PropertyTypes if hasattr(cmd, 'PropertyTypes') else []
        # Store original state for diff: {name: {type, value, group, tooltip, has_expr, is_new}}
        self.original_props = {}
        self.setWindowFlags(QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowCloseButtonHint)
        self.setupUI()
        self.loadProperties()

    def setupUI(self):
        self.setWindowTitle("Property Table Editor")
        self.resize(700, 450)
        layout = QtGui.QVBoxLayout(self)

        # Toolbar
        toolbar = QtGui.QHBoxLayout()
        self.addBtn = QtGui.QPushButton("Add Row")
        self.addBtn.clicked.connect(self.addRow)
        self.deleteBtn = QtGui.QPushButton("Delete Row")
        self.deleteBtn.clicked.connect(self.deleteRow)
        toolbar.addWidget(self.addBtn)
        toolbar.addWidget(self.deleteBtn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Table
        self.table = QtGui.QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Name", "Type", "Value / Expression", "Result", "Group", "Tooltip"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QtGui.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QtGui.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QtGui.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QtGui.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QtGui.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QtGui.QHeaderView.Stretch)
        self.table.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.table.cellChanged.connect(self.onCellChanged)
        layout.addWidget(self.table)

        # Info label
        self.infoLabel = QtGui.QLabel("Tip: Values starting with '=' are treated as expressions, e.g. =Length*2")
        self.infoLabel.setStyleSheet("color: gray;")
        layout.addWidget(self.infoLabel)

        # Buttons
        btnLayout = QtGui.QHBoxLayout()
        self.okBtn = QtGui.QPushButton("OK")
        self.okBtn.clicked.connect(self.accept)
        self.cancelBtn = QtGui.QPushButton("Cancel")
        self.cancelBtn.clicked.connect(self.reject)
        btnLayout.addStretch()
        btnLayout.addWidget(self.okBtn)
        btnLayout.addWidget(self.cancelBtn)
        layout.addLayout(btnLayout)

    def loadProperties(self):
        """Load all dynamic properties from the object into the table."""
        props = self.cmd.getDynamicProperties(self.obj)
        self.table.blockSignals(True)
        for prop in props:
            if prop == "DynamicData2":
                continue
            # Get property info
            full_type = self.obj.getTypeIdOfProperty(prop)
            type_name = full_type.replace("App::Property", "")
            group = self.obj.getGroupOfProperty(prop) or "DefaultGroup"
            tooltip = self.obj.getDocumentationOfProperty(prop) or ""

            # Check for expression
            has_expr = False
            value_str = str(getattr(self.obj, prop, ""))
            if hasattr(self.obj, 'ExpressionEngine'):
                for eprop, estr in self.obj.ExpressionEngine:
                    if eprop == prop:
                        value_str = "=" + estr
                        has_expr = True
                        break

            self.original_props[prop] = {
                'type': type_name,
                'value': value_str,
                'group': group,
                'tooltip': tooltip,
                'has_expr': has_expr,
                'is_new': False,
            }
            self._addRowToTable(prop, type_name, value_str, group, tooltip)
        self.table.blockSignals(False)

    def _evaluateResult(self, value):
        """Evaluate a value or expression and return the result string."""
        if not value:
            return ""
        if value.startswith("="):
            expr = value[1:]
            # First try with same-object rewrite
            try:
                rewritten = rewrite_same_object_expr(value, self.obj)
                result = self.obj.evalExpression(rewritten[1:])
                if result is not None:
                    return str(result)
            except:
                pass
            # Fall back to raw expression
            try:
                result = self.obj.evalExpression(expr)
                if result is not None:
                    return str(result)
            except:
                pass
            return "?"
        try:
            import ast
            return str(ast.literal_eval(value))
        except:
            return value

    def _addRowToTable(self, name, type_name, value, group, tooltip=""):
        """Add a single row to the table."""
        row = self.table.rowCount()
        self.table.insertRow(row)

        # Name
        nameItem = QtGui.QTableWidgetItem(name)
        nameItem.setToolTip(tooltip)
        self.table.setItem(row, 0, nameItem)

        # Type (QComboBox)
        combo = QtGui.QComboBox()
        combo.addItems(self.property_types)
        idx = combo.findText(type_name)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        self.table.setCellWidget(row, 1, combo)

        # Value/Expr (QLineEdit for real-time result updates)
        line_edit = QtGui.QLineEdit()
        line_edit.textChanged.connect(lambda txt, r=row: self._onValueChanged(r, txt))
        line_edit.blockSignals(True)
        line_edit.setText(value)
        line_edit.blockSignals(False)
        self.table.setCellWidget(row, 2, line_edit)

        # Result (read-only)
        result = self._evaluateResult(value)
        resultItem = QtGui.QTableWidgetItem(result)
        resultItem.setFlags(resultItem.flags() & ~Qt.ItemIsEditable)
        resultItem.setForeground(QtGui.QColor(100, 100, 100))
        self.table.setItem(row, 3, resultItem)

        # Group
        groupItem = QtGui.QTableWidgetItem(group)
        self.table.setItem(row, 4, groupItem)

        # Tooltip
        tooltipItem = QtGui.QTableWidgetItem(tooltip)
        self.table.setItem(row, 5, tooltipItem)

    def addRow(self):
        """Add a new empty row."""
        self._addRowToTable("", "Float", "", "DefaultGroup", "")
        # Focus the new row's name cell
        self.table.setCurrentCell(self.table.rowCount() - 1, 0)
        self.table.editItem(self.table.item(self.table.rowCount() - 1, 0))

    def deleteRow(self):
        """Delete the selected row."""
        row = self.table.currentRow()
        if row < 0:
            return
        name_item = self.table.item(row, 0)
        if name_item and name_item.text() in self.original_props:
            reply = QtGui.QMessageBox.question(
                self, "Confirm Delete",
                f"Delete property '{name_item.text()}'? This cannot be undone.",
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No
            )
            if reply != QtGui.QMessageBox.Yes:
                return
        self.table.removeRow(row)

    def _onValueChanged(self, row, text):
        result = self._evaluateResult(text)
        result_item = self.table.item(row, 3)
        if result_item:
            result_item.setText(result)

    def onCellChanged(self, row, col):
        """Validate name when cell changes."""
        if col == 0:
            item = self.table.item(row, 0)
            if item and item.text():
                name = item.text()
                # Check if name is valid
                if not self.cmd.isValidName(self.obj, name):
                    fixed = self.cmd.fixName(self.obj, name)
                    if fixed != name:
                        self.infoLabel.setText(f"Warning: '{name}' is reserved (unit or invalid), suggestion: {fixed}")
                        self.infoLabel.setStyleSheet("color: orange;")
                        return
                # Check for conflicts with other rows
                for r in range(self.table.rowCount()):
                    if r != row:
                        other = self.table.item(r, 0)
                        if other and other.text() == item.text():
                            self.infoLabel.setText(f"Warning: Name '{item.text()}' is used in multiple rows")
                            self.infoLabel.setStyleSheet("color: orange;")
                            return
                self.infoLabel.setStyleSheet("color: gray;")
                self.infoLabel.setText("Tip: Values starting with '=' are treated as expressions, e.g. =Length*2")
                # Auto-add a new empty row if last row was just filled
                if row == self.table.rowCount() - 1:
                    self.addRow()

    def getPropertyNameFromType(self, type_name):
        """Get the App::Property{Type} name."""
        return f"App::Property{type_name}"

    def collectTableData(self):
        """Collect all data from the table into a list of dicts."""
        rows = []
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            name = name_item.text().strip() if name_item else ""
            if not name:
                continue

            combo = self.table.cellWidget(row, 1)
            type_name = combo.currentText() if combo else "Float"

            line_edit = self.table.cellWidget(row, 2)
            value = line_edit.text() if line_edit else ""

            group_item = self.table.item(row, 4)
            group = group_item.text().strip() if group_item else "DefaultGroup"

            tooltip_item = self.table.item(row, 5)
            tooltip = tooltip_item.text().strip() if tooltip_item else ""

            rows.append({
                'name': name,
                'type': type_name,
                'value': value,
                'group': group,
                'tooltip': tooltip,
            })
        return rows

    def accept(self):
        """Save all changes: diff table vs original, create/update/delete as needed."""
        table_data = self.collectTableData()
        table_names = {r['name'] for r in table_data}
        original_names = set(self.original_props.keys())

        # Properties to delete (in original but not in table)
        to_delete = original_names - table_names

        # Properties to add (in table but not in original)
        to_add = [r for r in table_data if r['name'] not in original_names]

        # Properties to update (in both but changed)
        to_update = []
        for r in table_data:
            if r['name'] in original_names:
                orig = self.original_props[r['name']]
                # Check if anything changed
                type_changed = r['type'] != orig['type']
                value_changed = r['value'] != orig['value']
                group_changed = r['group'] != orig['group']
                tooltip_changed = r['tooltip'] != orig['tooltip']
                if type_changed or value_changed or group_changed or tooltip_changed:
                    to_update.append({
                        **r,
                        'type_changed': type_changed,
                        'orig_type': orig['type'],
                        'tooltip_changed': tooltip_changed,
                    })

        if not to_delete and not to_add and not to_update:
            self.done(0)
            return

        doc = FreeCAD.ActiveDocument
        doc.openTransaction("DynamicData2: Edit Properties")

        try:
            # 1. Delete removed properties
            for prop in to_delete:
                self.obj.removeProperty(prop)

            # 2. Update changed properties
            for entry in to_update:
                name = entry['name']
                if entry.get('type_changed'):
                    # Type changed: remove and recreate
                    self.obj.removeProperty(name)
                    self._createAndSetProperty(name, entry, doc)
                else:
                    # Just update value/group
                    self._updatePropertyValue(name, entry)
                    if entry['group']:
                        try:
                            self.obj.setGroupOfProperty(name, entry['group'])
                        except:
                            pass
                if entry.get('tooltip_changed') and entry['tooltip']:
                    try:
                        self.obj.setDocumentationOfProperty(name, entry['tooltip'])
                    except:
                        pass

            # 3. Add new properties
            for entry in to_add:
                self._createAndSetProperty(entry['name'], entry, doc)

        except Exception as e:
            doc.abortTransaction()
            QtGui.QMessageBox.warning(self, "Error", f"Failed to save properties:\n{str(e)}")
            return

        doc.commitTransaction()
        doc.recompute()
        self.done(1)

    def _createAndSetProperty(self, name, entry, doc):
        """Create a new property and set its value."""
        full_type = self.getPropertyNameFromType(entry['type'])
        tooltip = entry.get('tooltip', '')
        try:
            self.obj.addProperty(full_type, name, entry.get('group', 'DefaultGroup'), tooltip)
        except Exception as e:
            raise Exception(f"Failed to create property '{name}' ({entry['type']}): {str(e)}")
        self._updatePropertyValue(name, entry)

    def _updatePropertyValue(self, name, entry):
        """Set the value or expression of an existing property."""
        value = entry['value']
        if value.startswith("="):
            # Rewrite expression: replace same-object property refs
            rewritten = rewrite_same_object_expr(value, self.obj)
            expr_str = rewritten[1:]  # strip '='
            try:
                self.obj.setExpression(name, expr_str)
            except Exception as e:
                raise Exception(f"Failed to set expression on '{name}': {str(e)}")
        else:
            # Clear any existing expression first
            if hasattr(self.obj, 'ExpressionEngine'):
                for eprop, _ in self.obj.ExpressionEngine:
                    if eprop == name:
                        self.obj.setExpression(name, None)
                        break
            # Try to convert string to proper type before setting
            import ast
            typed_val = value
            try:
                typed_val = ast.literal_eval(value)
            except:
                try:
                    typed_val = self.cmd.eval_expr(value)
                except:
                    pass  # keep as string
            try:
                setattr(self.obj, name, typed_val)
            except Exception as e:
                raise Exception(f"Cannot set '{name}' to '{value}': {str(e)}")

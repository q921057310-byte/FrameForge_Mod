"""Import sketches from AluminumProfiles.FCStd and create profiles along edges."""
import math
import os
import re
import shutil
import tempfile
import zipfile

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui

from freecad.frameforge2.ff_tools import ICONPATH, PROFILESPATH, translate
from freecad.frameforge2.profile import Profile, ViewProviderCustomProfile
from freecad.frameforge2.trimmed_profile import TrimmedProfile, ViewProviderTrimmedProfile



class _EdgeMemory:
    def __init__(self):
        self._stored = []  # (doc_name, obj_name, [sub_names])
        Gui.Selection.addObserver(self)

    def addSelection(self, doc, obj, sub, pnt):
        if sub and sub.startswith("Edge"):
            for i, (d, o, subs) in enumerate(self._stored):
                if d == doc and o == obj:
                    if sub not in subs:
                        self._stored[i] = (d, o, subs + [sub])
                    return
            self._stored.append((doc, obj, [sub]))

    def removeSelection(self, doc, obj, sub):
        if sub and sub.startswith("Edge"):
            self._stored = [(d, o, subs) for d, o, subs in self._stored
                           if not (d == doc and o == obj and sub in subs)]

    def clearSelection(self, doc):
        pass  # Keep last selection — toolbar buttons often trigger clearSelection

    def setSelection(self, doc):
        pass

    def get_edge_selections(self):
        """Rehydrate stored selections into usable (Object, [edge_names]) pairs."""
        result = []
        for doc_name, obj_name, sub_names in self._stored:
            try:
                doc = App.getDocument(doc_name)
            except Exception:
                continue
            if doc is None:
                continue
            obj = doc.getObject(obj_name)
            if obj is None:
                continue
            valid = [s for s in sub_names if obj.getSubObject(s) is not None]
            if valid:
                result.append((obj, valid))
        return result




class _Sel:  # lightweight stand-in for SelectionObject
    __slots__ = ("Object", "ObjectName", "SubElementNames")
    def __init__(self, obj, subs):
        self.Object = obj
        self.ObjectName = obj.Name
        self.SubElementNames = subs


_edge_memory = _EdgeMemory()


class ImportAluminumProfileTaskPanel:
    def __init__(self, target_profile=None):
        self.target_profile = target_profile
        self.edge_selection = []
        self._section_cache = {}  # key: (filepath, name) -> {"label": ..., "shape": ...}
        self._category_dirs = {}  # name -> path
        self._last_category_text = ""
        self._preview_objects = []  # names of preview-created objects
        self._preview_pairs = []    # (profile_obj_name, sel_dict) for corner handling
        self._previewing = False     # guard against re-entrant calls
        self._preview_timer = QtCore.QTimer()
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._on_preview_timer)

        Gui.Selection.addObserver(self)

        # Read pre-existing selection once UI is fully built
        QtCore.QTimer.singleShot(0, self._on_init_selection)

        self.form = QtGui.QWidget()
        self.form.setWindowTitle("Import Profile")
        layout = QtGui.QVBoxLayout(self.form)

        # --- Group: Profile Selection (mimics icon1 cascade) ---
        group_profile = QtGui.QGroupBox("Profile")
        group_layout = QtGui.QVBoxLayout(group_profile)

        group_layout.addWidget(QtGui.QLabel("Category"))
        self.combo_category = QtGui.QComboBox()
        group_layout.addWidget(self.combo_category)

        group_layout.addWidget(QtGui.QLabel("File"))
        self.combo_file = QtGui.QComboBox()
        group_layout.addWidget(self.combo_file)

        group_layout.addWidget(QtGui.QLabel("Section"))
        self.combo_section = QtGui.QComboBox()
        group_layout.addWidget(self.combo_section)

        info_layout = QtGui.QHBoxLayout()
        info_layout.addWidget(QtGui.QLabel("Type:"))
        self.label_section_type = QtGui.QLabel("---")
        info_layout.addWidget(self.label_section_type)
        info_layout.addStretch()
        group_layout.addLayout(info_layout)

        self.label_image = QtGui.QLabel()
        self.label_image.setMinimumHeight(120)
        self.label_image.setMaximumHeight(140)
        self.label_image.setScaledContents(True)
        self.label_image.setAlignment(QtCore.Qt.AlignCenter)
        self.label_image.setStyleSheet("background: #f0f0f0; border: 1px solid #ccc;")

        preview_rot_layout = QtGui.QHBoxLayout()

        rot_vbox = QtGui.QVBoxLayout()
        rot_vbox.addWidget(QtGui.QLabel("Rotation:"))
        self.combo_rotation = QtGui.QComboBox()
        self.combo_rotation.addItems(["0", "90", "180", "270"])
        self.combo_rotation.setCurrentIndex(0)
        rot_vbox.addWidget(self.combo_rotation)
        rot_vbox.addSpacing(6)
        self.cb_group_in_part = QtGui.QCheckBox("Group into Part")
        self.cb_group_in_part.setToolTip("Place all created profiles into an App::Part container")
        rot_vbox.addWidget(self.cb_group_in_part)
        self.cb_group_in_folder = QtGui.QCheckBox("Group into Folder")
        self.cb_group_in_folder.setToolTip("Place all created profiles into a folder group")
        rot_vbox.addWidget(self.cb_group_in_folder)

        rot_vbox.addSpacing(6)
        rot_vbox.addWidget(QtGui.QLabel("Corner:"))
        self.combo_corner = QtGui.QComboBox()
        self.combo_corner.addItems(["Off", u"45\u00b0 Miter", "A \u538b B", "B \u538b A"])
        rot_vbox.addWidget(self.combo_corner)
        self.combo_corner.currentIndexChanged.connect(self._on_corner_changed)

        gap_layout = QtGui.QHBoxLayout()
        self.cb_gap = QtGui.QCheckBox(u"Gap")
        self.cb_gap.setChecked(False)
        gap_layout.addWidget(self.cb_gap)
        self.cb_gap.toggled.connect(self._on_corner_changed)
        self.sb_gap = QtGui.QDoubleSpinBox()
        self.sb_gap.setRange(-50, 50)
        self.sb_gap.setValue(0)
        self.sb_gap.setSuffix(" mm")
        self.sb_gap.setEnabled(False)
        self.sb_gap.valueChanged.connect(self._on_corner_changed)
        self.cb_gap.toggled.connect(self.sb_gap.setEnabled)
        gap_layout.addWidget(self.cb_gap)
        gap_layout.addWidget(self.sb_gap)
        rot_vbox.addLayout(gap_layout)
        rot_vbox.addStretch()
        preview_rot_layout.addLayout(rot_vbox, 0)

        preview_rot_layout.addWidget(self.label_image, 1)

        group_layout.addLayout(preview_rot_layout)

        layout.addWidget(group_profile)

        # --- Edge selection ---
        lbl2 = QtGui.QLabel("2. Select an edge in the 3D view:")
        layout.addWidget(lbl2)

        self.selection_label = QtGui.QLabel("(no edge selected)")
        self.selection_label.setStyleSheet("color: #888;")
        layout.addWidget(self.selection_label)

        len_layout = QtGui.QHBoxLayout()
        len_layout.addWidget(QtGui.QLabel("Length:"))
        self.sb_length = QtGui.QDoubleSpinBox()
        self.sb_length.setRange(0.1, 24000.0)
        self.sb_length.setValue(100.0)
        self.sb_length.setSuffix(" mm")
        self.sb_length.setDecimals(1)
        len_layout.addWidget(self.sb_length)
        len_layout.addStretch()
        layout.addLayout(len_layout)

        self.btn_refresh = QtGui.QPushButton("Refresh selection from 3D view")
        self.btn_refresh.clicked.connect(self._read_edge_selection)
        layout.addWidget(self.btn_refresh)

        lbl3 = QtGui.QLabel("3. Click OK to create profile:")
        layout.addWidget(lbl3)

        # --- Buttons ---
        btn_layout = QtGui.QHBoxLayout()
        self.btn_ok = QtGui.QPushButton("OK")
        self.btn_cancel = QtGui.QPushButton("Cancel")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.setEnabled(False)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

        self.btn_reload = QtGui.QPushButton(u"\u91cd\u65b0\u52a0\u8f7d")
        self.btn_reload.setFixedHeight(20)
        self.btn_reload.setStyleSheet("font-size:10px; color:#888;")
        self.btn_reload.clicked.connect(self._reload_modules)
        layout.addWidget(self.btn_reload)

        # --- Wire signals ---
        self.combo_category.currentIndexChanged.connect(self._on_category_changed)
        self.combo_file.currentIndexChanged.connect(self._on_file_changed)
        self.combo_section.currentIndexChanged.connect(self._on_section_changed)
        self.combo_rotation.currentIndexChanged.connect(self._on_rotation_changed)

        # --- Initial population ---
        self._populate_categories()
        restored = self._restore_last_selection()
        if not restored:
            try:
                self._on_category_changed(0)
            except Exception as e:
                App.Console.PrintError(f"Initial load failed: {e}\n")
        else:
            cur = self.combo_section.currentIndex()
            if cur >= 0:
                self._on_section_changed(cur)

        if self.target_profile is not None:
            try:
                self._select_current_cross_section()
            except Exception:
                pass
        try:
            self._read_edge_selection()
        except Exception:
            pass

    # ---- Category combo ----

    def _populate_categories(self):
        self.combo_category.blockSignals(True)
        self.combo_category.clear()
        self._category_dirs.clear()
        if os.path.isdir(PROFILESPATH):
            for d in sorted(os.listdir(PROFILESPATH)):
                dpath = os.path.join(PROFILESPATH, d)
                if os.path.isdir(dpath) and d != "__pycache__":
                    if any(f.endswith(".FCStd") for f in os.listdir(dpath)):
                        self._category_dirs[d] = dpath
        if not self._category_dirs:
            self._category_dirs["aluminum"] = os.path.join(PROFILESPATH, "aluminum")
        for name in self._category_dirs:
            self.combo_category.addItem(name)
        self.combo_category.addItem(u"\u9009\u62e9\u6587\u4ef6...")
        self.combo_category.blockSignals(False)

    def _restore_last_selection(self):
        """Restore last used selections. Returns True if a saved config was found."""
        param = App.ParamGet("User parameter:BaseApp/Preferences/FrameForge2")
        cat = param.GetString("AlProfileLastCategory", "")
        if cat:
            idx = self.combo_category.findText(cat)
            if idx >= 0:
                self.combo_category.blockSignals(True)
                self.combo_category.setCurrentIndex(idx)
                self._last_category_text = cat
                self.combo_category.blockSignals(False)
                self.combo_file.blockSignals(True)
                self.combo_file.clear()
                cat_dir = self._category_dirs.get(cat)
                if cat_dir and os.path.isdir(cat_dir):
                    for fname in sorted(os.listdir(cat_dir)):
                        if fname.endswith(".FCStd"):
                            self.combo_file.addItem(fname, os.path.join(cat_dir, fname))
                self.combo_file.blockSignals(False)
                fname = param.GetString("AlProfileLastFile", "")
                if fname:
                    fidx = self.combo_file.findText(fname)
                    if fidx >= 0:
                        self.combo_file.setCurrentIndex(fidx)
                section = param.GetString("AlProfileLastSection", "")
                if section:
                    self.combo_section.blockSignals(True)
                    for si in range(self.combo_section.count()):
                        if self.combo_section.itemText(si) == section:
                            self.combo_section.setCurrentIndex(si)
                            break
                    self.combo_section.blockSignals(False)
        corner = param.GetString("AlProfileLastCorner", "Off")
        cidx = self.combo_corner.findText(corner)
        if cidx >= 0:
            self.combo_corner.setCurrentIndex(cidx)
        rot = param.GetString("AlProfileLastRotation", "0")
        ridx = self.combo_rotation.findText(rot)
        if ridx >= 0:
            self.combo_rotation.setCurrentIndex(ridx)
        gap = param.GetFloat("AlProfileLastGap", 0)
        self.sb_gap.setValue(gap)
        gap_enabled = param.GetBool("AlProfileGapEnabled", False)
        self.cb_gap.setChecked(gap_enabled)
        return bool(cat)

    def _save_last_selection(self):
        param = App.ParamGet("User parameter:BaseApp/Preferences/FrameForge2")
        param.SetString("AlProfileLastCategory", self.combo_category.currentText())
        param.SetString("AlProfileLastFile", self.combo_file.currentText())
        param.SetString("AlProfileLastSection", self.combo_section.currentText())
        param.SetString("AlProfileLastCorner", self.combo_corner.currentText())
        param.SetString("AlProfileLastRotation", self.combo_rotation.currentText())
        param.SetFloat("AlProfileLastGap", self.sb_gap.value())
        param.SetBool("AlProfileGapEnabled", self.cb_gap.isChecked())

    def _get_gap(self):
        return self.sb_gap.value() if self.cb_gap.isChecked() else 0.0

    def _on_category_changed(self, index):
        cat_text = self.combo_category.currentText()
        if cat_text == u"\u9009\u62e9\u6587\u4ef6...":
            self._handle_select_file_via_combo()
            return
        self._last_category_text = cat_text
        self.combo_file.blockSignals(True)
        self.combo_file.clear()
        cat_dir = self._category_dirs.get(cat_text)
        if cat_dir and os.path.isdir(cat_dir):
            for fname in sorted(os.listdir(cat_dir)):
                if fname.endswith(".FCStd"):
                    self.combo_file.addItem(fname, os.path.join(cat_dir, fname))
        self.combo_file.blockSignals(False)
        self._on_file_changed(0)

    def _handle_select_file_via_combo(self):
        file_path, _ = QtGui.QFileDialog.getOpenFileName(
            self.form, u"\u9009\u62e9\u578b\u6750\u6587\u4ef6",
            PROFILESPATH, "FreeCAD Files (*.FCStd)"
        )
        if not file_path:
            self.combo_category.blockSignals(True)
            idx = self.combo_category.findText(self._last_category_text)
            if idx < 0:
                idx = 0
            self.combo_category.setCurrentIndex(idx)
            self.combo_category.blockSignals(False)
            return
        self._last_category_text = u"\u9009\u62e9\u6587\u4ef6..."
        self.combo_file.blockSignals(True)
        self.combo_file.clear()
        self.combo_file.addItem(os.path.basename(file_path), file_path)
        self.combo_file.blockSignals(False)
        self._on_file_changed(0)

    # ---- File combo ----

    def _on_file_changed(self, index):
        filepath = self.combo_file.itemData(index)
        if not filepath:
            self.combo_section.clear()
            self.btn_ok.setEnabled(False)
            return
        self.combo_section.blockSignals(True)
        self.combo_section.clear()
        sections = self._extract_sections(filepath)
        for sec in sections:
            key = (filepath, sec["name"])
            self._section_cache[key] = {"label": sec["label"], "shape": sec["shape"]}
            self.combo_section.addItem(sec["label"], key)
        self.combo_section.blockSignals(False)
        if self.combo_section.count() > 0:
            self.combo_section.setCurrentIndex(-1)
            self.combo_section.setCurrentIndex(0)

    # ---- Section combo ----

    def _on_rotation_changed(self, index):
        key = self.combo_section.itemData(self.combo_section.currentIndex())
        if key is None:
            return
        cached = self._section_cache.get(key)
        if cached and cached.get("shape"):
            self._update_preview(cached["shape"])
        # Debounce preview
        if self.edge_selection:
            self._preview_timer.start(100)

    def _on_corner_changed(self, index=None):
        """Re-trigger preview when corner mode or gap changes."""
        if self.edge_selection:
            self._preview_timer.start(100)

    def _on_section_changed(self, index):
        self.label_image.clear()
        key = self.combo_section.itemData(index)
        if key is None:
            self.label_section_type.setText("---")
            self.btn_ok.setEnabled(False)
            return
        self.btn_ok.setEnabled(True)
        cached = self._section_cache.get(key)
        if cached is None:
            self.label_section_type.setText("---")
            return
        shape = cached.get("shape")
        if shape is None:
            self.label_section_type.setText("no shape")
            return
        stype = shape.ShapeType
        info = stype
        if stype == "Face" and shape.Faces:
            bb = shape.BoundBox
            info = f"Face  {bb.XLength:.1f} x {bb.YLength:.1f} mm"
        elif stype == "Wire" or stype == "Edge":
            bb = shape.BoundBox
            info = f"{stype}  {bb.XLength:.1f} x {bb.YLength:.1f} mm"
        self.label_section_type.setText(info)
        self._update_preview(shape)
        if self.edge_selection:
            self._preview_timer.start(100)

    def _update_preview(self, shape):
        try:
            angle = float(self.combo_rotation.currentText())
            pixmap = self._render_shape(shape, 160, 130, angle)
            self.label_image.setPixmap(pixmap)
        except Exception:
            self.label_image.setText("(preview unavailable)")
            self.label_image.setPixmap(QtGui.QPixmap())

    def _render_shape(self, shape, width=200, height=140, rotation=0.0):
        pixmap = QtGui.QPixmap(width, height)
        pixmap.fill(QtGui.QColor(248, 248, 248))
        if shape is None or shape.isNull():
            return pixmap
        bb = shape.BoundBox
        if bb.XLength < 1e-7 or bb.YLength < 1e-7:
            return pixmap
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        margin = 2
        sc = min((width - 2 * margin) / bb.XLength, (height - 2 * margin) / bb.YLength)

        import math
        rad = math.radians(rotation)
        cos_a = abs(math.cos(rad))
        sin_a = abs(math.sin(rad))
        rw = bb.XLength * cos_a + bb.YLength * sin_a
        rh = bb.XLength * sin_a + bb.YLength * cos_a
        sc_r = min((width - 2 * margin) / rw, (height - 2 * margin) / rh) if rw > 1e-7 and rh > 1e-7 else sc
        sc = min(sc, sc_r)

        cx = width / 2.0
        cy = height / 2.0
        painter.translate(cx, cy)
        painter.rotate(rotation)
        painter.translate(-cx, -cy)

        ox = (width - bb.XLength * sc) / 2.0
        oy = (height - bb.YLength * sc) / 2.0

        def to_pixel(v):
            return (ox + (v.x - bb.XMin) * sc,
                    height - (oy + (v.y - bb.YMin) * sc))

        wires = []
        if shape.ShapeType == "Face":
            wires = [shape.OuterWire] + list(shape.Wires[1:]) if len(shape.Wires) > 1 else [shape.OuterWire]
        elif shape.ShapeType in ("Solid",):
            for face in shape.Faces:
                wires.append(face.OuterWire)
        elif shape.ShapeType in ("Wire", "Edge", "Compound", "Shell"):
            for w in (shape.Wires if hasattr(shape, 'Wires') else []):
                wires.append(w)
            if not wires and hasattr(shape, 'Edges') and shape.Edges:
                import Part
                try:
                    wires.append(Part.Wire(shape.Edges))
                except Exception:
                    wires.append(shape.Edges[0])
        if not wires and hasattr(shape, 'Wires'):
            for w in shape.Wires:
                wires.append(w)

        if not wires:
            painter.end()
            return pixmap

        paths = []
        for wire in wires:
            edges = wire.OrderedEdges if hasattr(wire, 'OrderedEdges') else wire.Edges
            if not edges:
                continue
            path = QtGui.QPainterPath()
            all_pts = []
            for edge in edges:
                pts = edge.discretize(30)
                if not all_pts:
                    all_pts = list(pts)
                else:
                    all_pts.extend(pts[1:])
            if not all_pts:
                continue
            p0 = to_pixel(all_pts[0])
            path.moveTo(p0[0], p0[1])
            for pt in all_pts[1:]:
                tp = to_pixel(pt)
                path.lineTo(tp[0], tp[1])
            path.closeSubpath()
            paths.append(path)

        for path in reversed(paths):
            painter.fillPath(path, QtGui.QColor(255, 255, 255))
        for path in paths:
            painter.setPen(QtGui.QPen(QtGui.QColor(40, 40, 60), 1.2))
            painter.drawPath(path)
        if len(paths) > 1:
            painter.setBrush(QtGui.QColor(160, 190, 220, 100))
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawPath(paths[0])
            for path in paths[1:]:
                painter.setBrush(QtGui.QColor(255, 255, 255))
                painter.drawPath(path)

        painter.end()
        return pixmap

    # ---- Extract sections from FCStd ----

    def _extract_sections(self, filepath):
        results = self._extract_via_zip(filepath)
        if not results:
            results = self._extract_via_opendoc(filepath)
        return results

    def _extract_via_zip(self, filepath):
        results = []
        import Part
        tmp_dir = None
        try:
            tmp_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(filepath, 'r') as zf:
                label_map = self._parse_labels(zf)
                shape_entries = [n for n in zf.namelist()
                               if n.endswith('.Shape.brp') and zf.getinfo(n).file_size > 0]
                for entry_name in shape_entries:
                    obj_name = entry_name.rsplit('.Shape.brp', 1)[0]
                    zf.extract(entry_name, tmp_dir)
                    brp_path = os.path.join(tmp_dir, entry_name)
                    try:
                        shape = Part.read(brp_path)
                        if shape is None or shape.isNull():
                            continue
                    except Exception:
                        continue
                    label = label_map.get(obj_name, obj_name)
                    if shape.ShapeType == "Face":
                        results.append({"label": label, "name": obj_name,
                                       "shape": shape.copy()})
                    elif shape.ShapeType in ("Compound", "Shell", "Solid"):
                        for i, face in enumerate(shape.Faces):
                            results.append({"label": f"{label}_Face{i + 1}",
                                           "name": f"{obj_name}_Face{i + 1}",
                                           "shape": face.copy()})
                    else:
                        results.append({"label": label, "name": obj_name,
                                       "shape": shape.copy()})
        except Exception as e:
            App.Console.PrintError(f"ZIP read failed {filepath}: {e}\n")
        finally:
            if tmp_dir:
                shutil.rmtree(tmp_dir, ignore_errors=True)
        return results

    def _extract_via_opendoc(self, filepath):
        results = []
        user_doc = App.ActiveDocument
        lib_doc = None
        try:
            lib_doc = App.openDocument(filepath, True)
            for obj in lib_doc.Objects:
                if not hasattr(obj, "Shape") or not obj.Shape:
                    continue
                label = obj.Label if obj.Label else obj.Name
                if obj.TypeId == "Sketcher::SketchObject":
                    results.append({"label": label, "name": obj.Name,
                                   "shape": obj.Shape.copy()})
                elif obj.Shape.ShapeType == "Face":
                    results.append({"label": label, "name": obj.Name,
                                   "shape": obj.Shape.copy()})
                elif obj.Shape.ShapeType in ("Compound", "Shell", "Solid"):
                    for i, face in enumerate(obj.Shape.Faces):
                        results.append({"label": f"{label}_Face{i + 1}",
                                       "name": f"{obj.Name}_Face{i + 1}",
                                       "shape": face.copy()})
        except Exception as e:
            App.Console.PrintError(f"OpenDoc read failed {filepath}: {e}\n")
        finally:
            if lib_doc is not None:
                try:
                    lib_doc.saved = True
                    App.closeDocument(lib_doc.Name)
                except Exception:
                    pass
        if user_doc is not None:
            try:
                App.setActiveDocument(user_doc.Name)
            except Exception:
                pass
        return results

    def _parse_labels(self, zf):
        """Extract object Label properties from Document.xml ObjectData section."""
        label_map = {}
        if "Document.xml" not in zf.namelist():
            return label_map
        try:
            xml_text = zf.read("Document.xml").decode("utf-8", errors="replace")
            objdata_m = re.search(r'<ObjectData.*?</ObjectData>', xml_text, re.DOTALL)
            if not objdata_m:
                return label_map
            objdata = objdata_m.group(0)
            for match in re.finditer(
                r'<Object\s+name="([^"]+)".*?</Object>',
                objdata, re.DOTALL
            ):
                obj_name = match.group(1)
                obj_block = match.group(0)
                label_m = re.search(
                    r'<Property\s+name="Label"[^>]*>.*?<String\s+value="([^"]*)"',
                    obj_block, re.DOTALL
                )
                if label_m:
                    label_map[obj_name] = label_m.group(1)
        except Exception:
            pass
        return label_map

    # ---- Get selected section ----

    def _get_selected_section(self):
        key = self.combo_section.itemData(self.combo_section.currentIndex())
        if key is None:
            return None
        cached = self._section_cache.get(key)
        if cached is None:
            return None
        result = dict(cached)
        result["source_file"] = key[0]
        return result

    # ---- Current cross-section matching (for edit mode) ----

    def _select_current_cross_section(self):
        shape_obj = getattr(self.target_profile, "CustomProfile", None)
        if shape_obj is None:
            return
        current_rot = int(getattr(self.target_profile, "RotationAngle", 0))
        idx = self.combo_rotation.findText(str(current_rot))
        if idx >= 0:
            self.combo_rotation.setCurrentIndex(idx)

        source_file = getattr(shape_obj, "SourceFile", "")
        target_label = shape_obj.Label.replace("_Shape", "").strip().lower().replace("_", " ")

        self.combo_category.blockSignals(True)
        self.combo_file.blockSignals(True)
        self.combo_section.blockSignals(True)

        try:
            if source_file and os.path.isfile(source_file):
                source_dir = os.path.dirname(source_file)
                source_fname = os.path.basename(source_file)
                for cat_name, cat_dir in self._category_dirs.items():
                    if os.path.normpath(cat_dir) == os.path.normpath(source_dir):
                        cidx = self.combo_category.findText(cat_name)
                        if cidx >= 0:
                            self.combo_category.setCurrentIndex(cidx)
                            self._last_category_text = cat_name
                        break
                self.combo_file.clear()
                cat_text = self.combo_category.currentText()
                cat_dir = self._category_dirs.get(cat_text)
                if cat_dir and os.path.isdir(cat_dir):
                    for fname in sorted(os.listdir(cat_dir)):
                        if fname.endswith(".FCStd"):
                            self.combo_file.addItem(fname, os.path.join(cat_dir, fname))
                fidx = self.combo_file.findText(source_fname)
                if fidx < 0:
                    self.combo_file.addItem(source_fname, source_file)
                    fidx = self.combo_file.count() - 1
                if fidx >= 0:
                    self.combo_file.setCurrentIndex(fidx)
                filepath = self.combo_file.itemData(fidx)
                if filepath:
                    self._populate_section_combo(filepath)
            else:
                self._restore_category_and_file()

            found = self._match_section(target_label)
            if not found and source_file:
                pass
            elif not found:
                for cat_name in self._category_dirs:
                    cat_dir = self._category_dirs[cat_name]
                    if not os.path.isdir(cat_dir):
                        continue
                    for fname in sorted(os.listdir(cat_dir)):
                        if not fname.endswith(".FCStd"):
                            continue
                        fpath = os.path.join(cat_dir, fname)
                        self._populate_section_combo(fpath)
                        if self._match_section(target_label):
                            self.combo_file.setCurrentText(fname)
                            found = True
                            break
                    if found:
                        break
        finally:
            self.combo_category.blockSignals(False)
            self.combo_file.blockSignals(False)
            self.combo_section.blockSignals(False)

        cur_idx = self.combo_section.currentIndex()
        if cur_idx >= 0:
            self._on_section_changed(cur_idx)
            self.btn_ok.setEnabled(True)

    def _populate_section_combo(self, filepath):
        self.combo_section.clear()
        sections = self._extract_sections(filepath)
        for sec in sections:
            key = (filepath, sec["name"])
            self._section_cache[key] = {"label": sec["label"], "shape": sec["shape"]}
            self.combo_section.addItem(sec["label"], key)

    def _match_section(self, target_label):
        tgt = target_label.strip().lower().replace("_", " ").replace("-", " ")
        for i in range(self.combo_section.count()):
            norm = self.combo_section.itemText(i).strip().lower().replace("_", " ").replace("-", " ")
            if norm == tgt:
                self.combo_section.setCurrentIndex(i)
                return True
        return False

    def _restore_category_and_file(self):
        self.combo_file.clear()
        cat_text = self.combo_category.currentText()
        cat_dir = self._category_dirs.get(cat_text)
        if cat_dir and os.path.isdir(cat_dir):
            for fname in sorted(os.listdir(cat_dir)):
                if fname.endswith(".FCStd"):
                    self.combo_file.addItem(fname, os.path.join(cat_dir, fname))
        if self.combo_file.count() > 0:
            self.combo_file.setCurrentIndex(0)
            self._populate_section_combo(self.combo_file.itemData(0))

    def addSelection(self, doc, obj, sub, pnt):
        self._read_edge_selection()
        # Debounce preview: wait 100ms after last selection before creating
        sketch_data = self._get_selected_section()
        if sketch_data is not None and self.edge_selection:
            self._preview_timer.start(100)
            App.Console.PrintMessage(f"Timer: start (100ms), edges={[e for s in self.edge_selection for e in s.SubElementNames]}\n")

    def clearSelection(self, doc):
        self._read_edge_selection()

    def _read_edge_selection(self):
        raw = Gui.Selection.getSelectionEx()
        self.edge_selection = []
        for sel in raw:
            top = [n for n in sel.SubElementNames if n.startswith("Edge") and ":" not in n]
            # If no specific edges selected but object has edges, use all
            if not top and hasattr(sel.Object, "Shape") and sel.Object.Shape and sel.Object.Shape.Edges:
                top = [f"Edge{i + 1}" for i in range(len(sel.Object.Shape.Edges))]
            if top:
                self.edge_selection.append(_Sel(sel.Object, top))
        self._update_edge_label()

    def _update_edge_label(self):
        if not hasattr(self, 'selection_label'):
            return
        if self.edge_selection:
            parts = []
            for sel in self.edge_selection:
                parts.append(f"{sel.ObjectName} / {','.join(sel.SubElementNames)}")
            self.selection_label.setText("\n".join(parts))
            self.selection_label.setStyleSheet("color: #000;")
            self.sb_length.setEnabled(False)
        else:
            self.selection_label.setText("(no edge selected)")
            self.selection_label.setStyleSheet("color: #888;")
            self.sb_length.setEnabled(True)

    # ---- Real-time Preview ----
    def _on_preview_timer(self):
        """Timer callback: run preview after user stops selecting for 100ms."""
        if self._previewing:
            return
        sketch_data = self._get_selected_section()
        if sketch_data is not None:
            self._do_preview(sketch_data)

    def _on_init_selection(self):
        """Read any pre-existing selection when the panel opens."""
        self._read_edge_selection()
        if self.edge_selection and self._get_selected_section():
            self._preview_timer.start(100)

    def _do_preview(self, sketch_data):
        """Create/update profile preview from current edge selection."""
        if self._previewing:
            return
        self._previewing = True
        sel_list = [s for s in self.edge_selection if s is not None and s.SubElementNames]
        # Log what edges are selected
        edges = []
        for s in sel_list:
            edges.extend(s.SubElementNames)
        App.Console.PrintMessage(f"Preview: {len(edges)} edges: {edges}\n")
        if not sel_list:
            if self.sb_length.value() <= 0:
                self._previewing = False
                return

        try:
            self._clear_preview()
            before = {o.Name for o in App.ActiveDocument.Objects}

            # Build deduplicated (selection_object, edge_name) pairs
            pairs = []
            seen = set()
            for sel in sel_list:
                for en in sel.SubElementNames:
                    key = (sel.ObjectName, en)
                    if key not in seen:
                        seen.add(key)
                        pairs.append((sel, en))
            App.Console.PrintMessage(f"Preview: {len(pairs)} pairs: {[(p[0].ObjectName, p[1]) for p in pairs]}\n")

            self._preview_pairs = []  # reset pairs
            # Group by parent object → one shared Shape per parent
            parent_shapes = {}
            for sel, edge_name in pairs:
                key = sel.ObjectName
                if key not in parent_shapes:
                    doc = App.ActiveDocument
                    name_base = sketch_data["label"].replace(" ", "_")
                    feat = doc.addObject("Part::Feature", f"{name_base}_Shape_{key}_shared")
                    feat.Shape = sketch_data["shape"]
                    source_file = sketch_data.get("source_file", "")
                    if source_file and not hasattr(feat, "SourceFile"):
                        feat.addProperty("App::PropertyString", "SourceFile", "FrameForge2", "Source FCStd file path")
                        feat.SourceFile = source_file
                        feat.setEditorMode("SourceFile", 2)
                    try:
                        feat.ViewObject.Visibility = False
                    except Exception:
                        pass
                    parent_shapes[key] = feat

            counter = 0
            for sel, edge_name in pairs:
                try:
                    shared = parent_shapes.get(sel.ObjectName)
                    obj = self.create_profile(sketch_data, sel, edge_name, counter, existing_shape=shared)
                    if obj is not None:
                        self._preview_pairs.append((obj.Name, _Sel(sel.Object, [edge_name])))
                    counter += 1
                except Exception as e:
                    App.Console.PrintError(f"Preview: {e}\n")

            # Apply placement + corner ops using the SAME code accept() uses
            created = [(App.ActiveDocument.getObject(n), s)
                       for n, s in self._preview_pairs
                       if App.ActiveDocument.getObject(n)]
            for obj, sel in created:
                if sel is not None and obj.TypeId == "Part::FeaturePython":
                    self._apply_placement(obj, sel)
            App.ActiveDocument.recompute()
            if len(created) > 1:
                cm = self.combo_corner.currentIndex()
                if cm == 1:
                    self._do_miter_corners(created)
                elif cm in (2, 3):
                    self._do_overlap_corners(created, cm)
            elif len(created) > 0:
                gap = self._get_gap()
                if gap != 0:
                    for obj, sel in created:
                        if obj.TypeId == "Part::FeaturePython":
                            obj.OffsetA = -gap / 2.0
                            obj.OffsetB = -gap / 2.0
            App.ActiveDocument.recompute()

            after = {o.Name for o in App.ActiveDocument.Objects}
            self._preview_objects = list(after - before)
            App.Console.PrintMessage(f"Preview: done ({len(self._preview_objects)} new objects)\n")
        finally:
            self._previewing = False

    def _clear_preview(self):
        """Remove all preview objects using name snapshot (only deletes new objects)."""
        if not self._preview_objects:
            return
        for name in self._preview_objects:
            try:
                App.ActiveDocument.removeObject(name)
            except Exception:
                pass
        self._preview_objects = []

    # ---- Accept / Reject ----
    def accept(self):
        sketch_data = self._get_selected_section()
        if sketch_data is None:
            QtGui.QMessageBox.warning(self.form, "No Sketch", "Please select a profile cross-section first.")
            return

        if self.target_profile is not None:
            App.Console.PrintMessage(f"AluminumProfile: replacing cross-section of {self.target_profile.Label}\n")
            doc = App.ActiveDocument
            doc.openTransaction("Edit Aluminum Profile")
            shape_obj = getattr(self.target_profile, "CustomProfile", None)
            if shape_obj is not None and hasattr(shape_obj, "Shape"):
                shape_obj.Shape = sketch_data["shape"]
                shape_obj.Label = sketch_data["label"] + "_Shape"

            proxy = getattr(self.target_profile, "Proxy", None)
            if proxy is not None:
                if hasattr(proxy, "_cached_key"):
                    proxy._cached_key = None
                if hasattr(proxy, "_cached_face"):
                    proxy._cached_face = None
            self.target_profile.Label = sketch_data["label"].replace(" ", "_") + "_Profile"
            if hasattr(self.target_profile, "RotationAngle"):
                old_rot = self.target_profile.RotationAngle
                new_rot = float(self.combo_rotation.currentText())
                self.target_profile.RotationAngle = new_rot
                if old_rot != new_rot:
                    try:
                        pl = self.target_profile.Placement
                        if old_rot:
                            rot_z_inv = App.Rotation(App.Vector(0, 0, 1), -old_rot)
                            pl.Rotation = pl.Rotation.multiply(rot_z_inv)
                        if new_rot:
                            rot_z = App.Rotation(App.Vector(0, 0, 1), new_rot)
                            pl.Rotation = pl.Rotation.multiply(rot_z)
                        self.target_profile.Placement = pl
                    except Exception:
                        pass

            siblings = self._find_part_siblings(self.target_profile)
            for sib in siblings:
                sib_shape = getattr(sib, "CustomProfile", None)
                if sib_shape is not None and hasattr(sib_shape, "Shape"):
                    sib_shape.Shape = sketch_data["shape"]
                    sib_shape.Label = sketch_data["label"] + "_Shape"
                sib.Label = sketch_data["label"].replace(" ", "_") + "_Profile"
                if hasattr(sib, "RotationAngle"):
                    sib.RotationAngle = new_rot
                sib_proxy = getattr(sib, "Proxy", None)
                if sib_proxy is not None:
                    if hasattr(sib_proxy, "_cached_key"):
                        sib_proxy._cached_key = None
                    if hasattr(sib_proxy, "_cached_face"):
                        sib_proxy._cached_face = None
                try:
                    sib.recompute()
                except Exception:
                    pass

            doc.commitTransaction()
            doc.recompute()
            try:
                self.target_profile.recompute()
            except Exception:
                pass
            for sib in siblings:
                try:
                    sib.recompute()
                except Exception:
                    pass
            self._save_last_selection()
            self._preview_timer.stop()
            Gui.Selection.removeObserver(self)
            Gui.Selection.clearSelection()
            Gui.Control.closeDialog()
            return True

        App.Console.PrintMessage("AluminumProfile: creating new profile\n")

        # If preview objects already exist, just finalize them
        if self._preview_objects:
            # Corner ops already done in preview — just save and close
            self._preview_pairs = []
            self._preview_objects = []
            self._preview_timer.stop()
            self._save_last_selection()
            Gui.Selection.removeObserver(self)
            Gui.Selection.clearSelection()
            Gui.Control.closeDialog()
            return True
        else:
            selections = self.edge_selection
            if not selections:
                if self.sb_length.value() > 0:
                    selections = [None]
                else:
                    QtGui.QMessageBox.warning(
                        self.form, "No Edge",
                        "Please select an edge in the 3D view, or set a Length value.\n\n"
                        "Tip: Click on an edge (line) in the 3D view, not in the tree view.",
                    )
                    return

            Gui.Selection.removeObserver(self)

            group_in_part = self.cb_group_in_part.isChecked()
            group_in_folder = self.cb_group_in_folder.isChecked()
            container = None
            if group_in_part:
                container = App.ActiveDocument.addObject("App::Part", "ProfileGroup")
            elif group_in_folder:
                container = App.ActiveDocument.addObject("App::DocumentObjectGroup", "ProfileGroup")

            created = []
            counter = 0
            for sel in selections:
                if sel is None:
                    try:
                        obj = self.create_profile_standalone(sketch_data, counter)
                        if obj is not None:
                            created.append((obj, None))
                            if container:
                                container.addObject(obj)
                        counter += 1
                    except Exception as e:
                        App.Console.PrintError(f"Failed to create standalone profile: {e}\n")
                    continue
                edge_names = [n for n in sel.SubElementNames if n.startswith("Edge")]
                if not edge_names and hasattr(sel.Object, "Shape") and sel.Object.Shape.Edges:
                    edge_names = [f"Edge{i + 1}" for i in range(len(sel.Object.Shape.Edges))]
                for edge_name in edge_names:
                    try:
                        obj = self.create_profile(sketch_data, sel, edge_name, counter)
                        if obj is not None:
                            created.append((obj, _Sel(sel.Object, [edge_name])))
                            if container:
                                container.addObject(obj)
                        counter += 1
                    except Exception as e:
                        App.Console.PrintError(f"Failed to create profile on edge: {e}\n")

        corner_mode = self.combo_corner.currentIndex()
        App.Console.PrintMessage(f"Corner mode: {corner_mode}, profiles: {len(created)}\n")

        for obj, sel in created:
            if sel is not None and obj.TypeId == "Part::FeaturePython":
                self._apply_placement(obj, sel)

        App.ActiveDocument.recompute()

        if corner_mode == 1 and len(created) > 1:
            self._do_miter_corners(created)
        elif corner_mode in (2, 3) and len(created) > 1:
            self._do_overlap_corners(created, corner_mode)
        elif corner_mode == 0 and len(created) > 0:
            gap = self._get_gap()
            if gap != 0:
                for obj, sel in created:
                    if obj.TypeId == "Part::FeaturePython":
                        obj.OffsetA = -gap / 2.0
                        obj.OffsetB = -gap / 2.0

        App.ActiveDocument.recompute()
        self._save_last_selection()
        self._preview_timer.stop()
        Gui.Selection.removeObserver(self)
        Gui.Selection.clearSelection()
        Gui.Control.closeDialog()
        return True

    def create_profile_standalone(self, sketch_data, counter=0):
        doc = App.ActiveDocument or App.newDocument("Unnamed")
        edge_length = self.sb_length.value()
        name_base = sketch_data["label"].replace(" ", "_")
        feat_name = f"{name_base}_Shape_{counter:03d}"
        feat = doc.addObject("Part::Feature", feat_name)
        feat.Shape = sketch_data["shape"]
        source_file = sketch_data.get("source_file", "")
        if source_file:
            if not hasattr(feat, "SourceFile"):
                feat.addProperty("App::PropertyString", "SourceFile", "FrameForge2", "Source FCStd file path")
            feat.SourceFile = source_file
            feat.setEditorMode("SourceFile", 2)
        try:
            feat.ViewObject.Visibility = False
        except Exception:
            pass
        name = f"{name_base}_Profile_{counter:03d}"
        obj = doc.addObject("Part::FeaturePython", name)
        obj.addExtension("Part::AttachExtensionPython")
        Profile(
            obj,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            edge_length,
            0.0, 0.0,
            False,
            1, 1,
            "Aluminum",
            "Custom Profile",
            sketch_data["label"],
            False,
            None,
            feat,
            init_rotation=float(self.combo_rotation.currentText()),
        )
        ViewProviderCustomProfile(obj.ViewObject)
        try:
            obj.MapMode = "Deactivated"
        except Exception:
            pass
        return obj

    def _find_part_siblings(self, profile):
        """Find other FrameForge profiles in the same App::Part or DocumentObjectGroup."""
        siblings = []
        try:
            parents = profile.InList
        except Exception:
            return siblings
        for parent in parents:
            if parent.TypeId not in ("App::Part", "App::DocumentObjectGroup"):
                continue
            for child in parent.Group:
                if child is profile:
                    continue
                if not hasattr(child, "Proxy"):
                    continue
                if not hasattr(child, "CustomProfile"):
                    continue
                if child.CustomProfile is None:
                    continue
                siblings.append(child)
            break
        return siblings

    def _face_containing(self, shape, point):
        import Part
        for i, face in enumerate(shape.Faces):
            if face.distToShape(Part.Point(point).toShape())[0] < 0.1:
                return f"Face{i + 1}"
        return None

    def _face_containing_obj(self, profile, world_point):
        import Part
        pl = profile.Placement
        local_pt = pl.inverse().multVec(App.Vector(world_point))
        best = (999.0, None)
        for i, face in enumerate(profile.Shape.Faces):
            try:
                d = face.BoundBox.distToPoint(local_pt)
            except Exception:
                d = 999
            if d < best[0]:
                best = (d, f"Face{i + 1}")
        if best[0] < 200:
            return best[1]
        return None

    def _corner_face_for(self, profile, own_edge, other_edge, corner_pt):
        """Find which face of profile faces the corner, based on where the other edge extends."""
        vb_s, vb_e = other_edge.Vertexes[0].Point, other_edge.Vertexes[-1].Point
        tol = 0.01
        other_end = vb_e if (vb_s - corner_pt).Length < tol else vb_s
        direction = (other_end - corner_pt).normalize()
        local_dir = profile.Placement.Rotation.inverted().multVec(direction)
        if local_dir.x > 0.5:
            return "Face2"
        elif local_dir.x < -0.5:
            return "Face4"
        elif local_dir.y > 0.5:
            return "Face3"
        elif local_dir.y < -0.5:
            return "Face1"
        return self._face_containing_obj(profile, corner_pt) or "Face1"

    def _trim_at_corner(self, prof_a, face_a, prof_b, face_b):
        doc = App.ActiveDocument
        mt_a = doc.addObject("Part::FeaturePython", f"{prof_a.Name}_Mt")
        TrimmedProfile(mt_a)
        ViewProviderTrimmedProfile(mt_a.ViewObject)
        mt_a.TrimmedBody = prof_a
        mt_a.TrimmingBoundary = [(prof_b, [face_b])]
        mt_a.TrimmedProfileType = "End Miter"

        mt_b = doc.addObject("Part::FeaturePython", f"{prof_b.Name}_Mt")
        TrimmedProfile(mt_b)
        ViewProviderTrimmedProfile(mt_b.ViewObject)
        mt_b.TrimmedBody = prof_b
        mt_b.TrimmingBoundary = [(prof_a, [face_a])]
        mt_b.TrimmedProfileType = "End Miter"

    def _do_miter_corners(self, created):
        profiles = [(obj, sel) for obj, sel in created if sel is not None and obj.TypeId == "Part::FeaturePython"]
        if len(profiles) < 2:
            return
        for obj, sel in profiles:
            ext = max(getattr(obj, "ProfileWidth", 30), getattr(obj, "ProfileHeight", 30)) * 0.6
            obj.OffsetA = ext
            obj.OffsetB = ext
        App.ActiveDocument.recompute()
        boundaries = {}
        for i in range(len(profiles)):
            for j in range(i + 1, len(profiles)):
                obja, sela = profiles[i]
                objb, selb = profiles[j]
                e1 = sela.SubElementNames[0] if sela.SubElementNames else ""
                e2 = selb.SubElementNames[0] if selb.SubElementNames else ""
                if not e1 or not e2:
                    continue
                ea = sela.Object.getSubObject(e1)
                eb = selb.Object.getSubObject(e2)
                if not ea or not eb:
                    continue
                shared = None
                for va in ea.Vertexes:
                    for vb in eb.Vertexes:
                        if (va.Point - vb.Point).Length < 0.01:
                            shared = va.Point
                            break
                    if shared:
                        break
                if shared is None:
                    continue
                face_a = self._face_containing_obj(obja, shared) or self._corner_face_for(obja, ea, eb, shared)
                face_b = self._face_containing_obj(objb, shared) or self._corner_face_for(objb, eb, ea, shared)
                if not face_a or not face_b:
                    continue
                boundaries.setdefault(obja, []).append((objb, face_b))
                boundaries.setdefault(objb, []).append((obja, face_a))
        App.ActiveDocument.openTransaction("Auto Miter")
        gap_val = self._get_gap()
        for prof, bounds in boundaries.items():
            mt = App.ActiveDocument.addObject("Part::FeaturePython", f"{prof.Name}_Mt")
            TrimmedProfile(mt)
            ViewProviderTrimmedProfile(mt.ViewObject)
            mt.TrimmedBody = prof
            mt.TrimmingBoundary = bounds
            mt.TrimmedProfileType = "End Miter"
            mt.Gap = gap_val
            try:
                prof.ViewObject.Visibility = False
            except Exception:
                pass
        App.ActiveDocument.commitTransaction()

    def _profile_face_dim_at_corner(self, profile, my_edge, other_edge, corner_pt):
        """Return the cross-section dimension (Width or Height) of `profile`
        that faces the adjacent profile at the shared corner.
        Uses edge direction + RotationAngle to determine local X/Y orientation."""
        z_dir = (my_edge.Vertexes[-1].Point - my_edge.Vertexes[0].Point).normalize()
        ob_s = other_edge.Vertexes[0].Point
        ob_e = other_edge.Vertexes[-1].Point
        other_far = ob_e if (ob_s - corner_pt).Length < 0.01 else ob_s
        dir_to_other = (other_far - corner_pt).normalize()
        world_up = App.Vector(0, 0, 1)
        if abs(z_dir.dot(world_up)) > 0.99:
            world_up = App.Vector(0, 1, 0)
        local_x = z_dir.cross(world_up).normalize()
        local_y = z_dir.cross(local_x).normalize()
        rot_angle = float(getattr(profile, "RotationAngle", 0))
        if rot_angle:
            rad = math.radians(rot_angle)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)
            local_x = local_x * cos_a + local_y * sin_a
            local_y = z_dir.cross(local_x).normalize()
        dir_in_xy = dir_to_other - dir_to_other.dot(z_dir) * z_dir
        if dir_in_xy.Length < 0.001:
            return max(profile.ProfileWidth, profile.ProfileHeight) * 0.5
        dir_in_xy.normalize()
        if abs(dir_in_xy.dot(local_x)) >= abs(dir_in_xy.dot(local_y)):
            return profile.ProfileWidth * 0.5
        else:
            return profile.ProfileHeight * 0.5

    def _overlap_dir_to_neighbor(self, my_edge, other_edge, shared):
        """Get the direction from the shared corner into the other profile's interior."""
        ob_s = other_edge.Vertexes[0].Point
        ob_e = other_edge.Vertexes[-1].Point
        other_far = ob_e if (ob_s - shared).Length < 0.01 else ob_s
        return (other_far - shared).normalize()

    def _store_overlap_end(self, profile, prop_prefix, sign, dir_to_neighbor, gap=0.0):
        """Store overlap config for one end of a profile."""
        sign_prop = f"Overlap{prop_prefix}Sign"
        dir_prop = f"Overlap{prop_prefix}Dir"
        gap_prop = f"Overlap{prop_prefix}Gap"
        if not hasattr(profile, sign_prop):
            profile.addProperty("App::PropertyFloat", sign_prop, "Overlap", "").OverlapASign = 0.0
            profile.setEditorMode(sign_prop, 2)
        if not hasattr(profile, dir_prop):
            profile.addProperty("App::PropertyVector", dir_prop, "Overlap", "").OverlapADir = App.Vector(0, 0, 0)
            profile.setEditorMode(dir_prop, 2)
        if not hasattr(profile, gap_prop):
            profile.addProperty("App::PropertyFloat", gap_prop, "Overlap", "").OverlapAGap = 0.0
            profile.setEditorMode(gap_prop, 2)
        setattr(profile, sign_prop, float(sign))
        setattr(profile, dir_prop, dir_to_neighbor)
        setattr(profile, gap_prop, float(gap))

    def _do_overlap_corners(self, created, mode):
        profiles = [(obj, sel) for obj, sel in created if sel is not None and obj.TypeId == "Part::FeaturePython"]
        if len(profiles) < 2:
            return
        for i in range(len(profiles)):
            for j in range(i + 1, len(profiles)):
                obja, sela = profiles[i]
                objb, selb = profiles[j]
                e1 = sela.SubElementNames[0] if sela.SubElementNames else ""
                e2 = selb.SubElementNames[0] if selb.SubElementNames else ""
                if not e1 or not e2:
                    continue
                ea = sela.Object.getSubObject(e1)
                eb = selb.Object.getSubObject(e2)
                if not ea or not eb:
                    continue
                shared = None
                for va in ea.Vertexes:
                    for vb in eb.Vertexes:
                        if (va.Point - vb.Point).Length < 0.01:
                            shared = va.Point
                            break
                    if shared:
                        break
                if shared is None:
                    continue
                va_s, va_e = ea.Vertexes[0].Point, ea.Vertexes[-1].Point
                end_a = (va_e - shared).Length < 0.01
                start_a = (va_s - shared).Length < 0.01
                vb_s, vb_e = eb.Vertexes[0].Point, eb.Vertexes[-1].Point
                end_b = (vb_e - shared).Length < 0.01
                start_b = (vb_s - shared).Length < 0.01

                # Direction from corner into each profile's interior
                dir_a_into_b = self._overlap_dir_to_neighbor(ea, eb, shared)
                dir_b_into_a = self._overlap_dir_to_neighbor(eb, ea, shared)

                # At each corner, the profile whose edge ENDS at the corner "flows into"
                # it (tail/尾), and the profile whose edge STARTS at the corner flows
                # away from it (head/首). For 首尾呼应 around closed loops:
                #   - mode 2 (A压B): A=tail=end cuts (-), B=head=start extends (+)
                #   - mode 3 (B压A): B=tail=end cuts (-), A=head=start extends (+)
                if end_a and start_b:
                    a_is_tail = True
                elif start_a and end_b:
                    a_is_tail = False
                else:
                    # Ambiguous (both ends or both starts at corner) → fall back to i<j
                    a_is_tail = True

                # Determine which Overlap prefix to use for each profile
                a_prefix = "B" if end_a else "A"  # OffsetB ↔ OverlapB, OffsetA ↔ OverlapA
                b_prefix = "B" if end_b else "A"

                gap_val = self._get_gap()

                if mode == 2:  # A压B: tail(A) cuts -, head(B) extends +
                    if a_is_tail:
                        # a (tail=A) cuts -, referencing B's dim; b (head=B) extends +, referencing A's dim
                        self._store_overlap_end(obja, a_prefix, -1, dir_a_into_b, gap_val)
                        self._store_overlap_end(objb, b_prefix, +1, dir_b_into_a, gap_val)
                    else:
                        # b (tail=A) cuts -, referencing A's dim; a (head=B) extends +, referencing B's dim
                        self._store_overlap_end(objb, b_prefix, -1, dir_b_into_a, gap_val)
                        self._store_overlap_end(obja, a_prefix, +1, dir_a_into_b, gap_val)
                else:  # mode == 3, B压A: tail(B) cuts -, head(A) extends +
                    if a_is_tail:
                        # b (tail=B) cuts -, referencing A's dim; a (head=A) extends +, referencing B's dim
                        self._store_overlap_end(objb, b_prefix, -1, dir_b_into_a, gap_val)
                        self._store_overlap_end(obja, a_prefix, +1, dir_a_into_b, gap_val)
                    else:
                        # a (tail=B) cuts -, referencing B's dim; b (head=A) extends +, referencing A's dim
                        self._store_overlap_end(obja, a_prefix, -1, dir_a_into_b, gap_val)
                        self._store_overlap_end(objb, b_prefix, +1, dir_b_into_a, gap_val)

        # Force recalculation to apply offsets immediately
        for obj, sel in profiles:
            try:
                obj.recompute()
            except Exception:
                pass

    def _reload_modules(self):
        import importlib
        import sys
        names = [m for m in sys.modules if "frameforge" in m or "frameforge2" in m]
        for name in sorted(names):
            try:
                importlib.reload(sys.modules[name])
            except Exception:
                pass
        App.Console.PrintMessage("FrameForge2 modules reloaded\n")

    def reject(self):
        self._preview_timer.stop()
        self._clear_preview()
        Gui.Selection.removeObserver(self)
        Gui.Selection.clearSelection()
        Gui.Control.closeDialog()

    # ---- Profile creation ----
    def create_profile(self, sketch_data, selection, edge_name, counter=0, existing_shape=None):
        import Part
        doc = App.ActiveDocument or App.newDocument("Unnamed")

        if not edge_name:
            return None
        edge_obj = selection.Object.getSubObject(edge_name)
        sketch = selection.Object

        is_curved = False
        if edge_obj and hasattr(edge_obj, 'Curve'):
            curve_type = edge_obj.Curve.__class__.__name__
            is_curved = curve_type not in ('GeomLineSegment', 'LineSegment', 'Line')

        if edge_obj and hasattr(edge_obj, "Length"):
            edge_length = edge_obj.Length
        else:
            edge_length = self.sb_length.value()

        name_base = sketch_data["label"].replace(" ", "_")

        # Use shared Shape if provided, otherwise create a new one
        if existing_shape is not None:
            feat = existing_shape
        else:
            feat_name = f"{name_base}_Shape_{counter:03d}"
            feat = doc.addObject("Part::Feature", feat_name)
            feat.Shape = sketch_data["shape"]
            source_file = sketch_data.get("source_file", "")
            if source_file:
                if not hasattr(feat, "SourceFile"):
                    feat.addProperty("App::PropertyString", "SourceFile", "FrameForge2", "Source FCStd file path")
                feat.SourceFile = source_file
                feat.setEditorMode("SourceFile", 2)
            try:
                feat.ViewObject.Visibility = False
            except Exception:
                pass

        if is_curved and edge_obj is not None:
            try:
                import Part
                section_shape = sketch_data["shape"].copy()

                plane = doc.addObject("Part::Feature", f"{name_base}_Plane_{counter:03d}")
                try:
                    plane.addExtension("Part::AttachExtensionPython")
                except Exception:
                    plane.addExtension("Part::AttachExtension")
                plane.MapMode = "NormalToEdge"
                plane.AttachmentSupport = [(selection.Object, edge_name)]
                doc.recompute()

                section_obj = doc.addObject("Part::Feature", f"{name_base}_Section_{counter:03d}")
                section_obj.Shape = section_shape
                section_obj.Placement = plane.Placement
                try:
                    section_obj.ViewObject.Visibility = False
                except Exception:
                    pass

                path_obj = doc.addObject("Part::Feature", f"{name_base}_Path_{counter:03d}")
                path_obj.Shape = Part.Wire([edge_obj])
                try:
                    path_obj.ViewObject.Visibility = False
                except Exception:
                    pass

                doc.recompute()

                sweep_obj = doc.addObject("Part::Sweep", f"{name_base}_Sweep_{counter:03d}")
                sweep_obj.Sections = [section_obj]
                sweep_obj.Spine = path_obj
                sweep_obj.Solid = True
                sweep_obj.Frenet = True
                doc.recompute()

                # hide helper objects
                try:
                    plane.ViewObject.Visibility = False
                    section_obj.ViewObject.Visibility = False
                    path_obj.ViewObject.Visibility = False
                except Exception:
                    pass

                sweep_obj.Label = sketch_data["label"] + "_Sweep"
                return sweep_obj
            except Exception as e:
                App.Console.PrintError(f"Sweep failed: {e}\n")
                import traceback
                traceback.print_exc()
                return None

        name = f"{name_base}_Profile_{counter:03d}"
        obj = doc.addObject("Part::FeaturePython", name)
        obj.addExtension("Part::AttachExtensionPython")

        Profile(
            obj,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            edge_length,
            0.0, 0.0,
            False,
            1, 1,
            "Aluminum",
            "Custom Profile",
            sketch_data["label"],
            False,
            (sketch, (edge_name,)),
            feat,
            init_rotation=float(self.combo_rotation.currentText()),
        )

        ViewProviderCustomProfile(obj.ViewObject)

        return obj

    def _apply_placement(self, obj, selection):
        edge_names = [n for n in selection.SubElementNames if n.startswith("Edge")]
        if not edge_names:
            return
        try:
            obj.AttachmentSupport = (selection.Object, edge_names[0])
            obj.MapPathParameter = 1
            obj.MapMode = "NormalToEdge"
        except Exception:
            pass


class CreateAluminumProfileCommand:
    def GetResources(self):
        return {
            "Pixmap": os.path.join(ICONPATH, "warehouse_profiles_lib.svg"),
            "MenuText": translate("FrameForge2", "Aluminum Profile Library"),
            "ToolTip": translate("FrameForge2",
                                "Import a profile cross-section from the aluminum profiles library"),
        }

    def Activated(self):
        panel = ImportAluminumProfileTaskPanel()
        Gui.Control.showDialog(panel)

    def IsActive(self):
        return App.ActiveDocument is not None


Gui.addCommand("FrameForge2_AluminumProfileLibrary", CreateAluminumProfileCommand())

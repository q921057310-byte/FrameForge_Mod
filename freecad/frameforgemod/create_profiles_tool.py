import glob
import json
import os
import re
from abc import ABC, abstractmethod

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui
try:
    from PySide import QtWidgets
except ImportError:
    QtWidgets = QtGui

from freecad.frameforgemod.ff_tools import ICONPATH, PROFILEIMAGES_PATH, PROFILESPATH, UIPATH, FormProxy, translate
from freecad.frameforgemod.profile import Profile, ViewProviderProfile
from freecad.frameforgemod.extrusions import make_tslot_face, make_vslot_face, make_profile_face, make_yiheda_vslot, make_aoh_vslot, make_40series_vslot


class BaseProfileTaskPanel(ABC):
    def __init__(self):
        self._objects = {}

        self.form = [
            Gui.PySideUic.loadUi(os.path.join(UIPATH, "create_profiles1.ui")),
            Gui.PySideUic.loadUi(os.path.join(UIPATH, "create_profiles2.ui")),
        ]

        self.form_proxy = FormProxy(self.form)

        # Top-right Apply button on first page
        _top_row = QtWidgets.QHBoxLayout()
        _top_row.addStretch()
        _apply_btn = QtWidgets.QPushButton(translate("frameforgemod", "Apply"))
        _apply_btn.setFixedWidth(60)
        _apply_btn.setFixedHeight(22)
        _apply_btn.clicked.connect(self.apply)
        _top_row.addWidget(_apply_btn)
        self.form[0].layout().insertLayout(0, _top_row)

        self.load_data()
        # self.initialize_ui() # Must be call in Child class, AFTER openTransaction

    def load_data(self):
        self.profiles = {}

        files = [f for f in os.listdir(PROFILESPATH) if f.endswith(".json")]

        for f in files:
            material_name = os.path.splitext(f)[0].capitalize()

            with open(os.path.join(PROFILESPATH, f), encoding="utf-8") as fd:
                self.profiles[material_name] = json.load(fd)

    def enable_signals(self, enable):
        # Block signals during initialization to prevent unintended side effects
        self.form_proxy.combo_material.blockSignals(not enable)
        self.form_proxy.combo_family.blockSignals(not enable)
        self.form_proxy.combo_size.blockSignals(not enable)

        self.form_proxy.sb_width.blockSignals(not enable)
        self.form_proxy.sb_height.blockSignals(not enable)
        self.form_proxy.sb_main_thickness.blockSignals(not enable)
        self.form_proxy.sb_flange_thickness.blockSignals(not enable)
        self.form_proxy.sb_radius1.blockSignals(not enable)
        self.form_proxy.sb_radius2.blockSignals(not enable)
        self.form_proxy.sb_length.blockSignals(not enable)
        self.form_proxy.cb_mirror_h.blockSignals(not enable)
        self.form_proxy.cb_mirror_v.blockSignals(not enable)
        self.form_proxy.combo_rotation.blockSignals(not enable)
        for ax in range(3):
            for ay in range(3):
                getattr(self.form_proxy, f"rb_anchor_{ax}_{ay}").blockSignals(not enable)

    def initialize_ui(self):
        def execute_if_has_bool(key, func):
            if key in [k for t, k, v in param.GetContents()]:
                func(param.GetBool(key))

        # Center anchor radio buttons in grid cells (create_profiles2.ui)
        form2 = self.form[1]
        grid_anchor = form2.group_anchor.layout()
        for ax in range(3):
            for ay in range(3):
                btn = getattr(form2, f"rb_anchor_{ax}_{ay}")
                grid_anchor.setAlignment(btn, QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)

        self.form_proxy.label_image.setPixmap(QtGui.QPixmap(os.path.join(PROFILEIMAGES_PATH, "Warehouse.png")))

        # sig/slot
        self.form_proxy.combo_material.currentIndexChanged.connect(self.on_material_changed)
        self.form_proxy.combo_family.currentIndexChanged.connect(self.on_family_changed)
        self.form_proxy.combo_size.currentIndexChanged.connect(self.on_size_changed)

        self.form_proxy.combo_material.addItems([k for k in self.profiles])

        for deg in ("0", "90", "180", "270"):
            self.form_proxy.combo_rotation.addItem(deg)
        self.form_proxy.combo_rotation.setCurrentIndex(0)

        param = App.ParamGet("User parameter:BaseApp/Preferences/Frameforge_mod")
        if not param.IsEmpty():
            default_material_index = self.form_proxy.combo_material.findText(
                param.GetString("Default Profile Material")
            )
            if default_material_index > -1:
                self.form_proxy.combo_material.setCurrentIndex(default_material_index)

                default_family_index = self.form_proxy.combo_family.findText(param.GetString("Default Profile Family"))
                if default_family_index > -1:
                    self.form_proxy.combo_family.setCurrentIndex(default_family_index)

                    default_size_index = self.form_proxy.combo_size.findText(param.GetString("Default Profile Size"))
                    if default_size_index > -1:
                        self.form_proxy.combo_size.setCurrentIndex(default_size_index)

            execute_if_has_bool("Default Sketch in Name", self.form_proxy.cb_sketch_in_name.setChecked)
            execute_if_has_bool("Default Family in Name", self.form_proxy.cb_family_in_name.setChecked)
            execute_if_has_bool("Default Size in Name", self.form_proxy.cb_size_in_name.setChecked)
            execute_if_has_bool("Default Prefix Profile in Name", self.form_proxy.cb_prefix_profile_in_name.setChecked)
            execute_if_has_bool("Default Make Fillet", self.form_proxy.cb_make_fillet.setChecked)
            execute_if_has_bool("Default Mirror Horizontally", self.form_proxy.cb_mirror_h.setChecked)
            execute_if_has_bool("Default Mirror Vertically", self.form_proxy.cb_mirror_v.setChecked)
            execute_if_has_bool("Default Pre Extend", self.form_proxy.cb_pre_extend.setChecked)
            keys = [k for t, k, v in param.GetContents()]
            if "Default AnchorX" in keys:
                ax = max(0, min(2, param.GetInt("Default AnchorX", 1)))
                ay = max(0, min(2, param.GetInt("Default AnchorY", 1)))
                self.set_anchor(ax, ay)
            elif "Default Width Centered" in keys or "Default Height Centered" in keys:
                ax = 1 if param.GetBool("Default Width Centered", False) else 0
                ay = 1 if param.GetBool("Default Height Centered", False) else 0
                self.set_anchor(ax, ay)
            if "Default RotationAngle" in keys:
                try:
                    val = float(param.GetString("Default RotationAngle", "0"))
                    self.form_proxy.combo_rotation.setCurrentText(str(int(val) if val == int(val) else val))
                except (TypeError, ValueError):
                    self.form_proxy.combo_rotation.setCurrentText("0")
            execute_if_has_bool("Default Centered Bevel", self.form_proxy.cb_combined_bevel.setChecked)

        self.form_proxy.cb_make_fillet.stateChanged.connect(self.on_cb_make_fillet_changed)

        self.form_proxy.cb_mirror_h.stateChanged.connect(self.proceed)
        self.form_proxy.cb_mirror_v.stateChanged.connect(self.proceed)
        self.form_proxy.cb_pre_extend.stateChanged.connect(self.proceed)
        self.form_proxy.combo_rotation.currentIndexChanged.connect(self.proceed)
        for ax in range(3):
            for ay in range(3):
                getattr(self.form_proxy, f"rb_anchor_{ax}_{ay}").clicked.connect(self.proceed)

        self.form_proxy.sb_width.valueChanged.connect(self.proceed)
        self.form_proxy.sb_height.valueChanged.connect(self.proceed)
        self.form_proxy.sb_main_thickness.valueChanged.connect(self.proceed)
        self.form_proxy.sb_flange_thickness.valueChanged.connect(self.proceed)
        self.form_proxy.sb_radius1.valueChanged.connect(self.proceed)
        self.form_proxy.sb_radius2.valueChanged.connect(self.proceed)
        self.form_proxy.sb_length.valueChanged.connect(self.proceed)

        self.form_proxy.cb_sketch_in_name.stateChanged.connect(self.proceed)
        self.form_proxy.cb_family_in_name.stateChanged.connect(self.proceed)
        self.form_proxy.cb_size_in_name.stateChanged.connect(self.proceed)
        self.form_proxy.cb_prefix_profile_in_name.stateChanged.connect(self.proceed)

    def get_anchor(self):
        """Return (anchor_x, anchor_y) 0=left/bottom, 1=center, 2=right/top."""
        for ax in range(3):
            for ay in range(3):
                if getattr(self.form_proxy, f"rb_anchor_{ax}_{ay}").isChecked():
                    return (ax, ay)
        return (1, 1)

    def set_anchor(self, anchor_x, anchor_y):
        ax = max(0, min(2, anchor_x))
        ay = max(0, min(2, anchor_y))
        getattr(self.form_proxy, f"rb_anchor_{ax}_{ay}").setChecked(True)

    def get_rotation(self):
        """Return rotation angle in degrees (float)."""
        try:
            return float(self.form_proxy.combo_rotation.currentText())
        except (TypeError, ValueError):
            return 0.0

    def set_rotation(self, degrees):
        t = str(int(degrees) if degrees == int(degrees) else degrees)
        i = self.form_proxy.combo_rotation.findText(t)
        if i >= 0:
            self.form_proxy.combo_rotation.setCurrentIndex(i)
        else:
            self.form_proxy.combo_rotation.setCurrentText(t)

    def on_material_changed(self, index):
        material = str(self.form_proxy.combo_material.currentText())

        self.enable_signals(False)

        self.form_proxy.combo_family.clear()
        self.form_proxy.combo_family.addItems([f for f in self.profiles[material]])

        self.enable_signals(True)

        self.form_proxy.combo_family.setCurrentIndex(0)
        self.on_family_changed(None)

    def on_family_changed(self, index):
        material = str(self.form_proxy.combo_material.currentText())
        family = str(self.form_proxy.combo_family.currentText())

        self.form_proxy.cb_make_fillet.setChecked(self.profiles[material][family]["fillet"])
        self.form_proxy.cb_make_fillet.setEnabled(self.profiles[material][family]["fillet"])

        self.update_image()

        self.form_proxy.label_norm.setText(self.profiles[material][family]["norm"])
        self.form_proxy.label_unit.setText(self.profiles[material][family]["unit"])

        self.form_proxy.combo_size.clear()
        self.form_proxy.combo_size.addItems([s for s in self.profiles[material][family]["sizes"]])

        self.form_proxy.combo_size.setCurrentIndex(0)
        self.on_size_changed(None)

    def on_size_changed(self, index):
        material = str(self.form_proxy.combo_material.currentText())
        family = str(self.form_proxy.combo_family.currentText())
        size = str(self.form_proxy.combo_size.currentText())

        if size != "":
            profile = self.profiles[material][family]["sizes"][size]

            SETTING_MAP = {
                "Height": self.form_proxy.sb_height,
                "Width": self.form_proxy.sb_width,
                "Thickness": self.form_proxy.sb_main_thickness,
                "Flange Thickness": self.form_proxy.sb_flange_thickness,
                "Radius1": self.form_proxy.sb_radius1,
                "Radius2": self.form_proxy.sb_radius2,
                "Weight": self.form_proxy.sb_weight,
            }

            self.enable_signals(False)

            self.form_proxy.sb_height.setEnabled(False)
            self.form_proxy.sb_height.setValue(0.0)
            self.form_proxy.sb_width.setEnabled(False)
            self.form_proxy.sb_width.setValue(0.0)
            self.form_proxy.sb_main_thickness.setEnabled(False)
            self.form_proxy.sb_main_thickness.setValue(0.0)
            self.form_proxy.sb_flange_thickness.setEnabled(False)
            self.form_proxy.sb_flange_thickness.setValue(0.0)
            self.form_proxy.sb_radius1.setEnabled(False)
            self.form_proxy.sb_radius1.setValue(0.0)
            self.form_proxy.sb_radius2.setEnabled(False)
            self.form_proxy.sb_radius2.setValue(0.0)
            self.form_proxy.sb_weight.setEnabled(False)
            self.form_proxy.sb_weight.setValue(0.0)

            for s in profile:
                if s == "Size":
                    continue

                if s not in SETTING_MAP:
                    raise ValueError("Setting Unkown")

                sb = SETTING_MAP[s]
                sb.setEnabled(True)

                sb.setValue(float(profile[s]))

            self.enable_signals(True)
            self.update_image()
            self.proceed()

    def on_cb_make_fillet_changed(self, state):
        self.update_image()
        self.proceed()

    def update_image(self):
        material = str(self.form_proxy.combo_material.currentText())
        family = str(self.form_proxy.combo_family.currentText())

        img_name = family.replace(" ", "_")
        if self.form_proxy.cb_make_fillet.isChecked():
            img_name += "_Fillet"
        img_name += ".png"

        img_path = os.path.join(PROFILEIMAGES_PATH, material, img_name)
        if os.path.isfile(img_path):
            self.form_proxy.label_image.setPixmap(QtGui.QPixmap(img_path))
        else:
            self._render_code_screenshot(family)

    def _render_code_screenshot(self, family):
        try:
            w = self.form_proxy.sb_width.value()
            h = self.form_proxy.sb_height.value()
            if w <= 0 or h <= 0:
                return
            if family.startswith("欧标"):
                import re
                m = re.search(r'\(([\d.]+)\)', family)
                sw = float(m.group(1)) if m else None
                if '40系列' in family:
                    shape = make_40series_vslot(w, h)
                elif '30系列' in family:
                    shape = make_aoh_vslot(w, h)
                else:
                    shape = make_yiheda_vslot(w, h, sw=sw)
            elif family.startswith("国标"):
                import re
                m = re.search(r'\(([\d.]+)\)', family)
                sw = float(m.group(1)) if m else 6.0
                sd = 1.6
                uc_w = 10.3
                uc_d = 4.62
                shape = make_profile_face(w, h, sw, sd, uc_w, uc_d)
            elif family.startswith("V-Slot"):
                shape = make_vslot_face(w, h)
            elif family.startswith("T-Slot"):
                shape = make_tslot_face(w, h)
            else:
                return
            if shape is None or shape.isNull():
                return
            shape = shape.copy()
            bb = shape.BoundBox
            if bb.XLength < 1e-7 or bb.YLength < 1e-7:
                return
            margin = 10
            pw, ph = 160, 130
            sc = min((pw - 2*margin)/bb.XLength, (ph - 2*margin)/bb.YLength)
            ox = (pw - bb.XLength*sc)/2
            oy = (ph - bb.YLength*sc)/2
            pixmap = QtGui.QPixmap(pw, ph)
            pixmap.fill(QtGui.QColor(248, 248, 248))
            painter = QtGui.QPainter(pixmap)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.setPen(QtGui.QPen(QtGui.QColor(50, 55, 70), 1.5))
            # Draw all wires (outer + inner holes) as outlines only
            all_wires = [shape.OuterWire] if hasattr(shape, "OuterWire") else [shape]
            if hasattr(shape, "Wires") and len(shape.Wires) > 1:
                all_wires = list(shape.Wires)
            for wire in all_wires:
                w_edges = wire.OrderedEdges if hasattr(wire, "OrderedEdges") else wire.Edges
                if not w_edges:
                    continue
                pts = []
                for e in w_edges:
                    raw = e.discretize(40)
                    for p in raw:
                        pts.append((p.x, p.y))
                if len(pts) < 3:
                    continue
                path = QtGui.QPainterPath()
                p0 = QtCore.QPointF(ox+(pts[0][0]-bb.XMin)*sc, ph-oy-(pts[0][1]-bb.YMin)*sc)
                path.moveTo(p0)
                for x, y in pts[1:]:
                    path.lineTo(QtCore.QPointF(ox+(x-bb.XMin)*sc, ph-oy-(y-bb.YMin)*sc))
                path.closeSubpath()
                painter.drawPath(path)
            painter.end()
            self.form_proxy.label_image.setPixmap(pixmap)
        except Exception:
            pass

    def update_profile(self, profile):
        profile.Proxy.set_properties(
            profile,
            self.form_proxy.sb_width.value(),
            self.form_proxy.sb_height.value(),
            self.form_proxy.sb_main_thickness.value(),
            self.form_proxy.sb_flange_thickness.value(),
            self.form_proxy.sb_radius1.value(),
            self.form_proxy.sb_radius2.value(),
            self.form_proxy.sb_length.value(),
            self.form_proxy.sb_weight.value(),
            self.form_proxy.sb_unitprice.value(),
            self.form_proxy.cb_make_fillet.isChecked(),  # and self.form_proxy.family.currentText() not in ["Flat Sections", "Square", "Round Bar"],
            *self.get_anchor(),
            self.form_proxy.combo_material.currentText(),
            self.form_proxy.combo_family.currentText(),
            self.form_proxy.combo_size.currentText(),
            init_mirror_h=self.form_proxy.cb_mirror_h.isChecked(),
            init_mirror_v=self.form_proxy.cb_mirror_v.isChecked(),
            init_rotation=self.get_rotation(),
        )

    @abstractmethod
    def proceed(self):
        pass

    @abstractmethod
    def open(self):
        pass

    @abstractmethod
    def reject(self):
        return True

    @abstractmethod
    def accept(self):
        return True


class CreateProfileTaskPanel(BaseProfileTaskPanel):
    def __init__(self):
        super().__init__()

    def open(self):
        App.ActiveDocument.openTransaction("Add Profile")

        self.initialize_ui()

        self.update_selection()
        self.proceed()

    def reject(self):
        self.clean()

        App.ActiveDocument.abortTransaction()

        return True

    def apply(self):
        App.Console.PrintMessage(translate("frameforgemod", "Applying...\n"))
        if not len(Gui.Selection.getSelectionEx()) and self.form_proxy.sb_length.value() == 0:
            App.Console.PrintMessage("Select edges or set length first.\n")
            return
        self.proceed()
        for o in self._objects.values():
            try:
                o.ViewObject.Transparency = 0
                o.ViewObject.ShapeColor = (0.44, 0.47, 0.5)
            except Exception:
                pass
        self._objects.clear()
        App.ActiveDocument.commitTransaction()
        App.ActiveDocument.recompute()
        try:
            Gui.updateGui()
        except Exception:
            pass
        App.ActiveDocument.openTransaction("Continue editing")
        self.form_proxy.sb_length.setValue(0)
        App.Console.PrintMessage(translate("frameforgemod", "Ready. Select next edge or click OK.\n"))

    def accept(self):
        if len(Gui.Selection.getSelectionEx()) or self.form_proxy.sb_length.value() != 0:
            App.Console.PrintMessage(translate("frameforgemod", "Accepting CreateProfile\n"))

            param = App.ParamGet("User parameter:BaseApp/Preferences/Frameforge_mod")
            param.SetString("Default Profile Material", self.form_proxy.combo_material.currentText())
            param.SetString("Default Profile Family", self.form_proxy.combo_family.currentText())
            param.SetString("Default Profile Size", self.form_proxy.combo_size.currentText())

            param.SetBool("Default Sketch in Name", self.form_proxy.cb_sketch_in_name.isChecked())
            param.SetBool("Default Family in Name", self.form_proxy.cb_family_in_name.isChecked())
            param.SetBool("Default Size in Name", self.form_proxy.cb_size_in_name.isChecked())
            param.SetBool("Default Prefix Profile in Name", self.form_proxy.cb_prefix_profile_in_name.isChecked())

            param.SetBool("Default Make Fillet", self.form_proxy.cb_make_fillet.isChecked())
            param.SetBool("Default Mirror Horizontally", self.form_proxy.cb_mirror_h.isChecked())
            param.SetBool("Default Mirror Vertically", self.form_proxy.cb_mirror_v.isChecked())
            param.SetBool("Default Pre Extend", self.form_proxy.cb_pre_extend.isChecked())

            ax, ay = self.get_anchor()
            param.SetInt("Default AnchorX", ax)
            param.SetInt("Default AnchorY", ay)
            param.SetString("Default RotationAngle", self.form_proxy.combo_rotation.currentText())
            param.SetBool("Default Centered Bevel", self.form_proxy.cb_combined_bevel.isChecked())

            param.RemBool("Default Reverse Attachement")

            self.clean()

            for o in self._objects.values():
                try:
                    o.ViewObject.Transparency = 0
                    o.ViewObject.ShapeColor = (0.44, 0.47, 0.5)
                except Exception:
                    pass

            App.ActiveDocument.commitTransaction()
            App.ActiveDocument.recompute()

            return True

        else:
            App.Console.PrintMessage(translate("frameforgemod", "Not Accepting CreateProfile\nSelect Edges or set Length"))

            diag = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Warning, "Create Profile", "Select Edges or set Length to create a profile"
            )
            diag.setWindowModality(QtCore.Qt.ApplicationModal)
            diag.exec_()

            return False

    def clean(self):
        Gui.Selection.removeObserver(self)
        Gui.Selection.removeSelectionGate()

    def proceed(self):
        seen_profiles = []

        selection_list = Gui.Selection.getSelectionEx()

        p_name = "Profile_" if self.form_proxy.cb_prefix_profile_in_name.isChecked() else ""

        if len(selection_list) == 1 and self.form_proxy.cb_sketch_in_name.isChecked():
            sketch_sel = selection_list[0]

            p_name += sketch_sel.Object.Name + "_"

        if self.form_proxy.cb_family_in_name.isChecked():
            p_name += self.form_proxy.combo_family.currentText().replace(" ", "_") + "_"

        if self.form_proxy.cb_size_in_name.isChecked():
            p_name += self.form_proxy.combo_size.currentText() + "_"

        p_name += "000"

        if len(selection_list):
            # create part or group and
            container = None
            if self.form_proxy.rb_profiles_in_part.isChecked():
                container = App.activeDocument().addObject("App::Part", "Part")
            # elif self.form_proxy.rb_profiles_in_group.isChecked(): # not working
            #     container = App.activeDocument().addObject('App::DocumentObjectGroup','Group')

            # creates profiles
            for sketch_sel in selection_list:
                # move the sketch inside the container
                if container:
                    container.addObject(sketch_sel.Object)

                if len(sketch_sel.SubElementNames) > 0:
                    edges = sketch_sel.SubElementNames
                else:  # use on the whole sketch
                    edges = [f"Edge{idx + 1}" for idx, e in enumerate(sketch_sel.Object.Shape.Edges)]

                for i, edge in enumerate(edges):
                    k = self.create_or_update_profile(sketch_sel.Object, edge, p_name)
                    seen_profiles.append(k)

        else:
            k = self.create_or_update_profile(None, None, p_name)
            seen_profiles.append(k)

        for k in list(self._objects.keys()):
            o = self._objects[k]
            if k in seen_profiles:
                try:
                    o.recompute()
                except Exception:
                    pass
            else:
                try:
                    App.ActiveDocument.removeObject(o.Name)
                except Exception:
                    pass
                try:
                    del o
                except Exception:
                    pass

    def has_name_prefix(self, internal_name, target_str):
        pattern = r"\d+$"

        prefix_obj = re.sub(pattern, "", internal_name)
        prefix_target = re.sub(pattern, "", target_str)

        return prefix_obj == prefix_target

    def create_or_update_profile(self, sketch, edge, name):
        key = (sketch, edge)

        if key in self._objects:
            o = self._objects[key]
            if self.has_name_prefix(o.Name, name):
                self.update_profile(o)

            else:
                # handle renames
                App.ActiveDocument.removeObject(o.Name)
                o = self.make_profile(sketch, edge, name)
                self._objects[key] = o

        else:
            o = self.make_profile(sketch, edge, name)
            self._objects[key] = o

        return key

    def make_profile(self, sketch, edge, name):
        # Create an object in current document
        obj = App.ActiveDocument.addObject("Part::FeaturePython", name)
        obj.addExtension("Part::AttachExtensionPython")

        obj.ViewObject.Transparency = 0
        obj.ViewObject.ShapeColor = (0.44, 0.47, 0.5)

        # move it to the sketch's parent if possible
        if sketch is not None and len(sketch.Parents) > 0:
            sk_parent = sketch.Parents[-1][0]
            sk_parent.addObject(obj)

        if sketch is not None and edge is not None:
            # Tuple assignment for edge
            feature = sketch
            link_sub = (feature, (edge))
            obj.MapMode = "NormalToEdge"

            try:
                obj.AttachmentSupport = (feature, edge)
            except AttributeError:  # for Freecad <= 0.21 support
                obj.Support = (feature, edge)

        else:
            link_sub = None

        init_offset = 0.0
        if self.form_proxy.cb_pre_extend.isChecked():
            init_offset = max(self.form_proxy.sb_width.value(), self.form_proxy.sb_height.value())

        obj.MapPathParameter = 1

        Profile(
            obj,
            self.form_proxy.sb_width.value(),
            self.form_proxy.sb_height.value(),
            self.form_proxy.sb_main_thickness.value(),
            self.form_proxy.sb_flange_thickness.value(),
            self.form_proxy.sb_radius1.value(),
            self.form_proxy.sb_radius2.value(),
            self.form_proxy.sb_length.value(),
            self.form_proxy.sb_weight.value(),
            self.form_proxy.sb_unitprice.value(),
            self.form_proxy.cb_make_fillet.isChecked(),  # and self.form_proxy.family.currentText() not in ["Flat Sections", "Square", "Round Bar"],
            *self.get_anchor(),
            self.form_proxy.combo_material.currentText(),
            self.form_proxy.combo_family.currentText(),
            self.form_proxy.combo_size.currentText(),
            self.form_proxy.cb_combined_bevel.isChecked(),
            link_sub,
            init_mirror_h=self.form_proxy.cb_mirror_h.isChecked(),
            init_mirror_v=self.form_proxy.cb_mirror_v.isChecked(),
            init_rotation=self.get_rotation(),
            init_offset_a=init_offset,
            init_offset_b=init_offset,
        )

        # Create a ViewObject in current GUI
        ViewProviderProfile(obj.ViewObject)

        return obj

    def addSelection(self, doc, obj, sub, other):
        try:
            self.update_selection()
            self.proceed()
        except Exception:
            pass

    def clearSelection(self, other):
        try:
            self.update_selection()
        except Exception:
            pass

    def update_selection(self):
        if len(Gui.Selection.getSelectionEx()) > 0:
            self.form_proxy.sb_length.setEnabled(False)
            self.form_proxy.sb_length.setValue(0.0)

            obj_name = ""
            for sel in Gui.Selection.getSelectionEx():
                selected_obj_name = sel.ObjectName
                subs = ""
                for sub in sel.SubElementNames:
                    subs += "{},".format(sub)

                obj_name += selected_obj_name
                obj_name += " / "
                obj_name += subs
                # obj_name += '\n'

        else:
            self.form_proxy.sb_length.setEnabled(True)
            obj_name = "Not Attached / Define length"

        self.form_proxy.label_attach.setText(obj_name)


class CreateProfilesCommand:
    """Create Profiles with standards dimensions"""

    def GetResources(self):
        return {
            "Pixmap": os.path.join(ICONPATH, "warehouse_profiles.svg"),
            "Accel": "Shift+S",  # 默认快捷键（可选）
            "MenuText": translate("frameforgemod", "Create Profile"),
            "ToolTip": translate("frameforgemod", "Create a new profile from selected edges"),
        }

    def Activated(self):
        """Do something here"""
        panel = CreateProfileTaskPanel()

        Gui.Selection.addObserver(panel)

        Gui.Control.showDialog(panel)

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""
        return App.ActiveDocument is not None


Gui.addCommand("frameforgemod_CreateProfiles", CreateProfilesCommand())


class ProfileToolGroup:
    def GetCommands(self):
        return ("frameforgemod_CreateProfiles", "frameforgemod_CreateCustomProfiles")

    def GetDefaultCommand(self):
        return 0

    def GetResources(self):
        return {
            "Pixmap": os.path.join(ICONPATH, "warehouse_profiles.svg"),
            "MenuText": translate("frameforgemod", "Create Profile"),
            "ToolTip": translate("frameforgemod", "Create profile from standard dimensions or custom profile"),
        }

    def IsActive(self):
        return App.ActiveDocument is not None


Gui.addCommand("frameforgemod_ProfileGroup", ProfileToolGroup())

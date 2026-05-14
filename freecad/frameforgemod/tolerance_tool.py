# -*- coding: utf-8 -*-
"""TechDraw Tolerance Query & Apply — ISO 286 full system."""

import os, math
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui

_inst = None

# ============================================================
# ISO 286 tolerance tables (values in mm, for sizes up to 500mm)
# ============================================================
# Size ranges (mm)
SIZES = [(0,3),(3,6),(6,10),(10,18),(18,30),(30,50),(50,80),(80,120),(120,180),(180,250),(250,315),(315,400),(400,500)]

# Hole IT grades: grade → list of values for each size range
H = {
 "H5": [0.004,0.005,0.006,0.008,0.009,0.011,0.013,0.015,0.018,0.020,0.023,0.025,0.027],
 "H6": [0.006,0.008,0.009,0.011,0.013,0.016,0.019,0.022,0.025,0.029,0.032,0.036,0.040],
 "H7": [0.010,0.012,0.015,0.018,0.021,0.025,0.030,0.035,0.040,0.046,0.052,0.057,0.063],
 "H8": [0.014,0.018,0.022,0.027,0.033,0.039,0.046,0.054,0.063,0.072,0.081,0.089,0.097],
 "H9": [0.025,0.030,0.036,0.043,0.052,0.062,0.074,0.087,0.100,0.115,0.130,0.140,0.155],
 "H10":[0.040,0.048,0.058,0.070,0.084,0.100,0.120,0.140,0.160,0.185,0.210,0.230,0.250],
 "H11":[0.060,0.075,0.090,0.110,0.130,0.160,0.190,0.220,0.250,0.290,0.320,0.360,0.400],
 "H12":[0.100,0.120,0.150,0.180,0.210,0.250,0.300,0.350,0.400,0.460,0.520,0.570,0.630],
}

# Shaft fundamental deviations (upper deviation for a-h, lower for j-zc)
# Each entry: label → list of (upper, lower) for each size range
S = {}
# a to h (upper deviation = negative, lower = upper - IT)
def _shaft_fund(letter, vals):
    for i, v in enumerate(vals):
        S.setdefault(letter, []).append(v)

_shaft_fund("a", [(-0.270,-0.330),(-0.270,-0.345),(-0.280,-0.370),(-0.290,-0.400),(-0.300,-0.430),(-0.310,-0.470),(-0.340,-0.530),(-0.390,-0.600),(-0.440,-0.680),(-0.490,-0.760),(-0.540,-0.840),(-0.600,-0.930),(-0.660,-1.010)])
_shaft_fund("b", [(-0.140,-0.200),(-0.140,-0.215),(-0.150,-0.240),(-0.150,-0.260),(-0.160,-0.290),(-0.170,-0.330),(-0.190,-0.380),(-0.220,-0.430),(-0.240,-0.480),(-0.260,-0.530),(-0.280,-0.580),(-0.310,-0.640),(-0.340,-0.690)])
_shaft_fund("c", [(-0.060,-0.120),(-0.070,-0.145),(-0.080,-0.170),(-0.095,-0.205),(-0.110,-0.240),(-0.130,-0.290),(-0.150,-0.340),(-0.180,-0.400),(-0.200,-0.440),(-0.220,-0.490),(-0.250,-0.550),(-0.260,-0.590),(-0.300,-0.660)])
_shaft_fund("d", [(-0.020,-0.050),(-0.030,-0.065),(-0.040,-0.085),(-0.050,-0.105),(-0.065,-0.130),(-0.080,-0.160),(-0.100,-0.195),(-0.120,-0.230),(-0.145,-0.270),(-0.170,-0.310),(-0.190,-0.350),(-0.210,-0.380),(-0.230,-0.420)])
_shaft_fund("e", [(-0.014,-0.034),(-0.020,-0.045),(-0.025,-0.055),(-0.032,-0.068),(-0.040,-0.083),(-0.050,-0.105),(-0.060,-0.120),(-0.072,-0.140),(-0.085,-0.165),(-0.100,-0.190),(-0.110,-0.210),(-0.125,-0.230),(-0.135,-0.260)])
_shaft_fund("f", [(-0.006,-0.016),(-0.010,-0.022),(-0.013,-0.027),(-0.016,-0.033),(-0.020,-0.041),(-0.025,-0.050),(-0.030,-0.060),(-0.036,-0.071),(-0.043,-0.085),(-0.050,-0.100),(-0.056,-0.110),(-0.062,-0.120),(-0.068,-0.135)])
_shaft_fund("g", [(-0.002,-0.008),(-0.004,-0.012),(-0.005,-0.014),(-0.006,-0.017),(-0.007,-0.020),(-0.009,-0.025),(-0.010,-0.029),(-0.012,-0.034),(-0.014,-0.039),(-0.015,-0.044),(-0.017,-0.049),(-0.018,-0.053),(-0.020,-0.058)])
_shaft_fund("h", [(0,0),(0,0),(0,0),(0,0),(0,0),(0,0),(0,0),(0,0),(0,0),(0,0),(0,0),(0,0),(0,0)])

# j to zc (lower deviation = positive, upper = lower + IT)
def _shaft_pos(letter, vals):
    for i, v in enumerate(vals):
        # Store as (upper, lower) where upper = lower + IT
        S.setdefault(letter, []).append(None)  # will fill with IT later

# We'll compute j-zc as: lower = fundamental, upper = lower + IT
# For j: js is symmetric, j has specific values
S["js"] = [(0,0)] * 13  # symmetric, handled specially
S["j"] = [(0,0)] * 13   # will fill
_j_low = [-0.004,-0.005,-0.005,-0.006,-0.008,-0.013, 0,0,0,0,0,0,0]
_j_up  = [ 0.002, 0.002, 0.002, 0.003, 0.004, 0.004, 0,0,0,0,0,0,0]

def _pos_fund(letter, vals):
    for i, v in enumerate(vals):
        S[letter][i] = v  # (lower, lower)

# k to zc fundamental lower deviations
_k = [0,0.001,0.001,0.002,0.002,0.002,0.003,0.003,0.004,0.004,0.004,0.005,0.005]
_m = [0.002,0.004,0.006,0.007,0.008,0.009,0.011,0.013,0.015,0.017,0.020,0.021,0.023]
_n = [0.004,0.008,0.010,0.012,0.015,0.017,0.020,0.023,0.025,0.028,0.033,0.039,0.045]
_p = [0.006,0.012,0.015,0.018,0.022,0.026,0.032,0.037,0.043,0.050,0.056,0.068,0.076]
_r = [0.010,0.015,0.019,0.023,0.028,0.034,0.041,0.048,0.056,0.066,0.075,0.088,0.097]
_s = [0.014,0.019,0.023,0.028,0.035,0.043,0.053,0.064,0.077,0.092,0.105,0.115,0.130]
_t = [0.018,0.023,0.028,0.033,0.041,0.051,0.064,0.077,0.093,0.112,0.128,0.140,0.155]
_u = [0.023,0.028,0.034,0.041,0.050,0.062,0.077,0.094,0.113,0.135,0.155,0.170,0.185]
_v = [0.028,0.035,0.042,0.050,0.060,0.074,0.092,0.113,0.135,0.160,0.185,0.200,0.220]
_x = [0.033,0.042,0.051,0.060,0.073,0.090,0.112,0.136,0.163,0.193,0.223,0.245,0.270]
_y = [0.039,0.050,0.061,0.073,0.089,0.109,0.135,0.165,0.200,0.238,0.275,0.300,0.330]
_z = [0.045,0.058,0.071,0.086,0.105,0.130,0.160,0.195,0.235,0.278,0.320,0.355,0.390]
_za = [0.055,0.068,0.086,0.104,0.128,0.158,0.192,0.234,0.285,0.342,0.395,0.435,0.480]
_zb = [0.065,0.082,0.105,0.125,0.155,0.192,0.232,0.285,0.345,0.415,0.475,0.530,0.580]
_zc = [0.075,0.098,0.125,0.150,0.185,0.232,0.282,0.345,0.415,0.495,0.565,0.620,0.685]

for label, fund in [("j",_j_low), ("k",_k), ("m",_m), ("n",_n), ("p",_p), ("r",_r),
                    ("s",_s), ("t",_t), ("u",_u), ("v",_v), ("x",_x), ("y",_y),
                    ("z",_z), ("za",_za), ("zb",_zb), ("zc",_zc)]:
    for i, v in enumerate(fund):
        S.setdefault(label, []).append(v)

SHAFT_ORDER = ["a","b","c","d","e","f","g","h","js","j","k","m","n","p","r","s","t","u","v","x","y","z","za","zb","zc"]
HOLE_ORDER = ["H5","H6","H7","H8","H9","H10","H11","H12"]


def _size_idx(n):
    for i, (lo, hi) in enumerate(SIZES):
        if lo <= n <= hi:
            return i
    return len(SIZES)-1


def _get_hole(grade, idx):
    if grade in H and 0 <= idx < len(H[grade]):
        return H[grade][idx]
    return 0


def _get_shaft(letter, idx):
    """Return (upper, lower) for given shaft letter at size index."""
    if letter not in S or idx >= len(S[letter]):
        return (0, 0)
    v = S[letter][idx]
    if v is None:
        return (0, 0)
    if letter in ("js", "j"):
        if letter == "js":
            it = _get_hole("H7", idx)  # approximate IT
            return (it*0.5, -it*0.5)
        # j: special
        if letter == "j" and idx < len(_j_low) and idx < len(_j_up):
            lo, up = _j_low[idx], _j_up[idx]
            if lo == 0 and up == 0:
                return (0, 0)
            return (up, lo)
    if isinstance(v, tuple):
        return v  # a-h: already (upper, lower)
    # k-zc: v is lower deviation, compute upper = lower + IT
    # Use IT6 for shaft grades up to IT6, IT7 for others
    it = _get_hole("H6" if letter in "kmnp" else "H7", idx)
    return (v + it, v)


class FitInfo:
    def __init__(self, nom, hole_grade, shaft_letter):
        self.nom = nom
        idx = _size_idx(nom)
        h_it = _get_hole(hole_grade, idx)
        self.hole_up = h_it
        self.hole_lo = 0
        s_up, s_lo = _get_shaft(shaft_letter, idx)
        self.shaft_up = s_up
        self.shaft_lo = s_lo
        self.min_clear = self.hole_lo - self.shaft_up if self.hole_lo > self.shaft_up else 0
        self.max_clear = self.hole_up - self.shaft_lo if self.hole_up > self.shaft_lo else 0
        self.min_inter = self.shaft_lo - self.hole_up if self.shaft_lo > self.hole_up else 0
        self.max_inter = self.shaft_up - self.hole_lo if self.shaft_up > self.hole_lo else 0
        if self.min_inter > 0:
            self.fit_type = "Interference / 过盈"
        elif self.min_clear > 0:
            self.fit_type = "Clearance / 间隙"
        else:
            self.fit_type = "Transition / 过渡"


# ============================================================
# UI
# ============================================================
def _set_tol(dim, over, under):
    try:
        dim.OverTolerance = f"{abs(over):.3f} mm"
        dim.UnderTolerance = f"{abs(under):.3f} mm"
        dim.ToleranceFormat = 2
        dim.recompute()
        return True
    except Exception:
        return False


def _clear_tol(dim):
    try:
        dim.OverTolerance = "0 mm"
        dim.UnderTolerance = "0 mm"
        dim.ToleranceFormat = 0
        dim.recompute()
    except Exception:
        pass


class TQueryPanel(QtGui.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tolerance Query / 公差查询")
        self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint)
        self.resize(720, 560)
        self._cells = {}
        self._last_fit = None

        main = QtGui.QVBoxLayout(self)
        main.setSpacing(3)

        # Toolbar
        tb = QtGui.QHBoxLayout()
        tb.addWidget(QtGui.QLabel("Nominal / 基本尺寸:"))
        self._sz = QtGui.QLineEdit("50")
        self._sz.setFixedWidth(60)
        tb.addWidget(self._sz)
        self._update_btn = QtGui.QPushButton("Refresh / 刷新")
        self._update_btn.clicked.connect(self._refresh_cells)
        tb.addWidget(self._update_btn)
        tb.addWidget(QtGui.QLabel("  Mode / 方式:"))
        self._mode = QtGui.QComboBox()
        self._mode.addItems(["Hole basis / 基孔制", "Shaft basis / 基轴制"])
        tb.addWidget(self._mode)
        self._hole_cb = QtGui.QCheckBox("Apply as hole / 按孔标注")
        self._hole_cb.setChecked(True)
        tb.addWidget(self._hole_cb)
        tb.addStretch()
        main.addLayout(tb)

        # Chart area
        scroll = QtGui.QScrollArea()
        scroll.setWidgetResizable(True)
        cw = QtGui.QWidget()
        self._chart = QtGui.QVBoxLayout(cw)
        self._chart.setSpacing(1)
        self._build_chart()
        scroll.setWidget(cw)
        main.addWidget(scroll, 1)

        # Detail bar
        self._detail = QtGui.QGroupBox("Select a fit / 选择一个配合")
        dl = QtGui.QVBoxLayout(self._detail)
        self._fit_label = QtGui.QLabel("Click a cell to see details / 点击格子查看详情")
        self._fit_label.setStyleSheet("font-size:14px;font-weight:bold;")
        dl.addWidget(self._fit_label)
        self._fit_detail = QtGui.QLabel("")
        self._fit_detail.setWordWrap(True)
        dl.addWidget(self._fit_detail)
        apply_btn = QtGui.QPushButton("Apply tolerance to selected TechDraw dims / 应用到选中尺寸")
        apply_btn.clicked.connect(self._apply_last)
        dl.addWidget(apply_btn)
        main.addWidget(self._detail)

    def _build_chart(self):
        # Clear existing
        while self._chart.count():
            item = self._chart.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cells.clear()

        is_hole = self._mode.currentIndex() == 0
        rows = HOLE_ORDER if is_hole else SHAFT_ORDER
        cols = SHAFT_ORDER if is_hole else HOLE_ORDER

        # Header
        hdr = QtGui.QHBoxLayout()
        hdr.addWidget(QtGui.QLabel(""))
        for c in cols:
            l = QtGui.QLabel(c.replace("H",""))
            l.setAlignment(QtCore.Qt.AlignCenter)
            l.setFixedWidth(26)
            l.setStyleSheet("font-size:9px;")
            hdr.addWidget(l)
        self._chart.addLayout(hdr)

        for r in rows:
            row = QtGui.QHBoxLayout()
            rl = QtGui.QLabel(r)
            rl.setFixedWidth(30)
            rl.setStyleSheet("font-weight:bold;font-size:9px;")
            row.addWidget(rl)
            for c in cols:
                fn = f"{r}/{c}" if is_hole else f"{c}/{r}"
                btn = QtGui.QPushButton()
                btn.setFixedSize(26, 22)
                btn.setToolTip(fn)
                btn.setStyleSheet("QPushButton{background:#1a1a2e;border:1px solid #333;border-radius:2px;font-size:6px;}"
                                  "QPushButton:hover{background:#0f3460;border-color:gold;}"
                                  "QPushButton:pressed{background:#e94560;}")
                btn.clicked.connect(lambda checked, x=fn: self._show_fit(x))
                self._cells[fn] = btn
                row.addWidget(btn)
            self._chart.addLayout(row)
        self._color_cells()

    def _color_cells(self):
        is_hole = self._mode.currentIndex() == 0
        rows = HOLE_ORDER if is_hole else SHAFT_ORDER
        cols = SHAFT_ORDER if is_hole else HOLE_ORDER
        try:
            nom = float(self._sz.text())
        except:
            nom = 50
        idx = _size_idx(nom)

        for r in rows:
            for c in cols:
                fn = f"{r}/{c}" if is_hole else f"{c}/{r}"
                btn = self._cells.get(fn)
                if not btn:
                    continue
                if is_hole:
                    fi = FitInfo(nom, r, c)
                else:
                    fi = FitInfo(nom, c, r) if c in HOLE_ORDER else None
                if fi and fi.min_inter > 0:
                    intensity = min(fi.max_inter * 20, 0.8)
                    rv = int(80 + (100-80)*intensity)
                    btn.setStyleSheet(f"QPushButton{{background:#{rv:02x}1a1a;border:1px solid #555;border-radius:2px;font-size:6px;color:#aaa;}}"
                                      f"QPushButton:hover{{border-color:gold;}}")
                elif fi and fi.min_clear > 0 and fi.min_inter == 0:
                    intensity = min(fi.max_clear * 15, 0.8)
                    rv = int(180 - 100*intensity)
                    gv = int(200 - 80*intensity)
                    btn.setStyleSheet(f"QPushButton{{background:#1a{rv:02x}{gv:02x};border:1px solid #555;border-radius:2px;font-size:6px;color:#aaa;}}"
                                      f"QPushButton:hover{{border-color:gold;}}")
                else:
                    intensity = min(fi.max_clear * 20, 0.6) if fi else 0.3
                    rv = int(100 + 80*intensity)
                    gv = int(80 + 60*intensity)
                    btn.setStyleSheet(f"QPushButton{{background:#{rv:02x}{gv:02x}1a;border:1px solid #555;border-radius:2px;font-size:6px;color:#aaa;}}"
                                      f"QPushButton:hover{{border-color:gold;}}")
                # Mark text
                if fi:
                    if fi.fit_type == "Interference / 过盈":
                        btn.setText("I")
                    elif fi.fit_type == "Clearance / 间隙":
                        btn.setText("C")
                    else:
                        btn.setText("T")

    def _refresh_cells(self):
        self._build_chart()

    def _show_fit(self, fn):
        self._last_fit = fn
        parts = fn.split("/")
        if len(parts) != 2:
            return
        is_hole = self._mode.currentIndex() == 0
        try:
            nom = float(self._sz.text())
        except:
            nom = 50
        if is_hole:
            fi = FitInfo(nom, parts[0], parts[1])
        else:
            fi = FitInfo(nom, parts[1], parts[0]) if parts[1] in HOLE_ORDER else None
        if not fi:
            return
        self._fit_label.setText(f"{fn}  —  {fi.fit_type}")
        txt = (f"Nominal / 基本尺寸: {nom} mm\n"
               f"Hole / 孔: {parts[0] if is_hole else parts[1]}  +{fi.hole_up:.3f}/+{fi.hole_lo:.3f}\n"
               f"Shaft / 轴: {parts[1] if is_hole else parts[0]}  +{fi.shaft_up:.3f}/{fi.shaft_lo:.3f}\n"
               f"Max clearance / 最大间隙: {fi.max_clear:.3f} mm\n"
               f"Min clearance / 最小间隙: {fi.min_clear:.3f} mm\n"
               f"Max interference / 最大过盈: {fi.max_inter:.3f} mm\n"
               f"Min interference / 最小过盈: {fi.min_inter:.3f} mm")
        self._fit_detail.setText(txt)

    def _apply_last(self):
        fn = self._last_fit
        if not fn:
            return
        parts = fn.split("/")
        if len(parts) != 2:
            return
        try:
            nom = float(self._sz.text())
        except:
            nom = 50
        is_hole = self._mode.currentIndex() == 0
        if is_hole:
            fi = FitInfo(nom, parts[0], parts[1])
        else:
            fi = FitInfo(nom, parts[1], parts[0])
        dims = [sobj.Object for sobj in Gui.Selection.getSelectionEx()
                if sobj.Object and hasattr(sobj.Object, "TypeId") and "DrawViewDimension" in sobj.Object.TypeId]
        if not dims:
            return
        ok = 0
        for d in dims:
            if self._hole_cb.isChecked():
                if _set_tol(d, fi.hole_up, fi.hole_lo):
                    ok += 1
            else:
                if _set_tol(d, fi.shaft_up, fi.shaft_lo):
                    ok += 1
        if ok:
            App.ActiveDocument.recompute()


class TQueryCommand:
    def GetResources(self):
        return {"MenuText": "Tolerance / 公差", "ToolTip": "Tolerance query & apply / 公差查询与标注"}

    def IsActive(self):
        return bool(App.ActiveDocument)

    def Activated(self):
        global _inst
        if _inst is not None:
            try: _inst.close()
            except: pass
        _inst = TQueryPanel()
        _inst.show()


Gui.addCommand("frameforgemod_TechDrawTolerance", TQueryCommand())

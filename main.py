import sys, os, math, json, re
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QRect, QRectF, QPoint, QPointF
from PySide6.QtGui import QPainter, QPen, QFont, QColor, QPixmap, QGuiApplication, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QComboBox,
    QFileDialog, QMessageBox, QDialog, QDialogButtonBox, QStyleFactory, QLineEdit   # <-- neu
)

# ---------------------------------------------------------
# Pfade / Ressourcen
# ---------------------------------------------------------
def resource_path(rel: str | Path) -> Path:
    rel = Path(rel)
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / rel  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent / rel

RES_DIR      = resource_path("resources")
ALT_RES      = resource_path("resourches")  # Fallback
APPDATA_DIR  = Path.home() / "SpielzeitApp"
DATA_DIR     = APPDATA_DIR / "data"
EXPORTS_DIR  = APPDATA_DIR / "exports"
CONFIG_PATH  = APPDATA_DIR / "config.json"
for p in (APPDATA_DIR, DATA_DIR, EXPORTS_DIR):
    p.mkdir(parents=True, exist_ok=True)

def resolve_logo_path() -> Path | None:
    for c in [
        RES_DIR / "siba_logo.png",
        ALT_RES / "siba_logo.png",
        resource_path('cropped-siba-system-integration-logo (1).png'),
    ]:
        if c.exists():
            return c
    return None

# ---------------------------------------------------------
# Config
# ---------------------------------------------------------
DEFAULT_CONFIG = {"theme": "light"}  # Startet jetzt hell

def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg: dict) -> None:
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except Exception:
        pass

# ---------------------------------------------------------
# Stylesheet laden (QSS)
# ---------------------------------------------------------
def _abs_url_rewrite(qss_text: str) -> str:
    def repl_url(match: re.Match):
        rel = match.group(1)
        return f'url("{resource_path(rel).as_posix()}")'
    return re.sub(r'url\(["\']?(resources/[^"\'\)]+)["\']?\)', repl_url, qss_text)

def _builtin_dark_qss() -> str:
    return """
    * { font-family: -apple-system, "Segoe UI", Roboto, Arial; }
    QMainWindow, QWidget { background: #0f1720; color: #dbe2eb; }
    #Sidebar            { background: #0c131b; border-right: 1px solid #1f2a37; }
    #SidebarButton      { background: #15202b; color: #dbe2eb; border: 1px solid #1f2a37; border-radius: 8px; padding: 8px; }
    #SidebarButton:hover{ background: #1b2a39; }
    #Topbar             { background: #0f1720; border-bottom: 1px solid #1f2a37; }
    #TopbarTitle        { color: #e5ecf5; font-weight: 600; }
    #DeviceCombo, #CaseCombo { background:#0c131b; border:1px solid #233042; padding:6px 8px; border-radius:8px; }
    #PrimaryButton      { background:#3b82f6; color: white; border:none; padding:8px 14px; border-radius:8px; }
    #PrimaryButton:hover{ background:#2f6fe0; }
    QTableWidget        { background:#0f1720; gridline-color:#243140; }
    QHeaderView::section{ background:#1a2532; color:#b9c7d8; padding:6px; border:none; }
    #H2                 { color:#e5ecf5; font-size:18px; font-weight:700; }
    #H3                 { color:#cbd5e1; font-size:14px; font-weight:600; }
    #Caption            { color:#aab8c6; font-size:12px; }
    QPushButton#SidebarButton > QIcon {
        color: #ffffff;
    }
    """

def _builtin_light_qss() -> str:
    return """
    * { font-family: -apple-system, "Segoe UI", Roboto, Arial; color:#0f1720; }
    QMainWindow, QWidget { background: #f7f9fb; }
    #Sidebar            { background: #ffffff; border-right: 1px solid #e5e9f0; }
    #SidebarButton      { background: #f0f3f7; border: 1px solid #e1e6ee; border-radius: 8px; padding: 8px; }
    #SidebarButton:hover{ background: #e8edf5; }
    #Topbar             { background: #ffffff; border-bottom: 1px solid #e5e9f0; }
    #TopbarTitle        { color: #0f1720; font-weight: 600; }
    #DeviceCombo, #CaseCombo { background:#ffffff; border:1px solid #d7dde5; padding:6px 8px; border-radius:8px; }
    #PrimaryButton      { background:#2563eb; color: white; border:none; padding:8px 14px; border-radius:8px; }
    #PrimaryButton:hover{ background:#1f54c8; }
    QTableWidget        { background:#ffffff; gridline-color:#e5e9f0; }
    QHeaderView::section{ background:#eef2f7; color:#334155; padding:6px; border:none; }
    #H2                 { color:#111827; font-size:18px; font-weight:700; }
    #H3                 { color:#374151; font-size:14px; font-weight:600; }
    #Caption            { color:#4b5563; font-size:12px; }
    QPushButton#SidebarButton > QIcon {
        color: #0f1720;
    }
    """

def load_stylesheet(app: QApplication, theme: str):
    name = "style_dark.qss" if theme == "dark" else "style_light.qss"
    qss_path = RES_DIR / name
    if not qss_path.exists() and (ALT_RES / name).exists():
        qss_path = ALT_RES / name
    if qss_path.exists():
        qss = _abs_url_rewrite(qss_path.read_text(encoding="utf-8"))
        app.setStyleSheet(qss)
    else:
        app.setStyleSheet(_builtin_dark_qss() if theme == "dark" else _builtin_light_qss())

# ---------------------------------------------------------
# Theme-Paletten für Zeichnen (Light-/Darkmode)
# ---------------------------------------------------------
def progress_palette(theme: str):
    if theme == "light":
        return dict(color="#2563EB", track="#E5E9F0", text="#0F1720")
    return dict(color="#5B8CFF", track="#2C3440", text="#D5DCE6")

def femview_palette(theme: str):
    if theme == "light":
        return dict(bg="#FFFFFF", rack="#E5E9F0", path="#2563EB", pt="#111827")
    return dict(bg="#111A24", rack="#243140", path="#6EA8FE", pt="#DDE6F1")

# ---------------------------------------------------------
# Circular Progress
# ---------------------------------------------------------
class CircularProgress(QWidget):
    def __init__(self, value=45, thickness=12, color="#5B8CFF", track="#2C3440", text_color="#D5DCE6", parent=None):
        super().__init__(parent)
        self._value = max(0, min(100, value))
        self._thickness = thickness
        self._color = QColor(color)
        self._track = QColor(track)
        self._text_color = QColor(text_color)
        self.setMinimumSize(160, 160)

    def set_palette(self, color: str, track: str, text: str):
        self._color = QColor(color)
        self._track = QColor(track)
        self._text_color = QColor(text)
        self.update()

    def setValue(self, v: int):
        self._value = max(0, min(100, int(v)))
        self.update()

    def paintEvent(self, e):
        w, h = self.width(), self.height()
        side = min(w, h)
        radius = side // 2 - self._thickness
        center = QPoint(w // 2, h // 2)
        start_angle = -90 * 16
        span_angle = -int(360 * 16 * (self._value / 100.0))

        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)

        pen = QPen(self._track, self._thickness, Qt.SolidLine, Qt.FlatCap)
        p.setPen(pen)
        p.drawArc(QRect(center.x() - radius, center.y() - radius, radius*2, radius*2), 0, -360 * 16)

        pen.setColor(self._color)
        p.setPen(pen)
        p.drawArc(QRect(center.x() - radius, center.y() - radius, radius*2, radius*2), start_angle, span_angle)

        p.setPen(self._text_color)
        font = QFont(); font.setPointSize(16); font.setBold(True)
        p.setFont(font)
        p.drawText(QRect(0, 0, w, h), Qt.AlignCenter, f"{self._value}%")

# ---------------------------------------------------------
# FEM-Skizze
# ---------------------------------------------------------
class FEMCaseView(QWidget):
    def __init__(self, theme: str = "dark", parent=None):
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.set_theme(theme)

    def set_theme(self, theme: str):
        pal = femview_palette(theme)
        self._bg   = QColor(pal["bg"])
        self._rack = QColor(pal["rack"])
        self._path = QColor(pal["path"])
        self._pt   = QColor(pal["pt"])
        self.update()

    def set_case(self, case_id: int):
        self.case_id = case_id
        self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        p.fillRect(self.rect(), self._bg)
        margin = 18
        area = QRectF(margin, margin, w - 2*margin, h - 2*margin)

        rack_w = 16
        p.fillRect(QRectF(area.left(), area.top(), rack_w, area.height()), self._rack)
        p.fillRect(QRectF(area.right()-rack_w, area.top(), rack_w, area.height()), self._rack)

        E  = QPointF(area.left()+40,  area.bottom()-20)
        A  = QPointF(area.right()-40, area.bottom()-20)
        P1 = QPointF(area.center().x(), area.center().y())
        P2 = QPointF(area.center().x(), area.top()+30)

        pen_path = QPen(self._path, 3); pen_path.setCapStyle(Qt.RoundCap)
        p.setPen(pen_path)

        if getattr(self, "case_id", 1) == 2:
            p.drawLine(E, QPointF(P2.x(), E.y()))
            p.drawLine(QPointF(P2.x(), E.y()), P2)
            p.drawLine(P2, QPointF(A.x(), P2.y()))
            p.drawLine(QPointF(A.x(), P2.y()), A)
        else:
            p.drawLine(E, QPointF(P1.x(), E.y()))
            p.drawLine(QPointF(P1.x(), E.y()), P1)
            p.drawLine(P1, QPointF(A.x(), P1.y()))
            p.drawLine(QPointF(A.x(), P1.y()), A)

        pen_pt = QPen(self._pt, 6); p.setPen(pen_pt)
        for pt, label in [(E, "E"), (A, "A"), (P1, "P1"), (P2, "P2")]:
            p.drawPoint(pt)
            p.drawText(pt + QPointF(6, -6), label)

class NewProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Neues Projekt")
        self.setMinimumSize(400, 240)
        self.result_data = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        self.nr_input = QLineEdit()
        self.nr_input.setPlaceholderText("Projektnummer")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Projektname")
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Projektbeschreibung (optional)")

        layout.addWidget(QLabel("Projektnummer:"))
        layout.addWidget(self.nr_input)
        layout.addWidget(QLabel("Projektname:"))
        layout.addWidget(self.name_input)
        layout.addWidget(QLabel("Projektbeschreibung:"))
        layout.addWidget(self.desc_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        nr = self.nr_input.text().strip()
        name = self.name_input.text().strip()
        desc = self.desc_input.text().strip()
        if not nr or not name:
            QMessageBox.warning(self, "Fehler", "Projektnummer und -name dürfen nicht leer sein.")
            return
        self.result_data = {
            "nummer": nr,
            "name": name,
            "beschreibung": desc
        }
        super().accept()

# ---------------------------------------------------------
# Settings
# ---------------------------------------------------------
class SettingsDialog(QDialog):
    def __init__(self, current_theme: str, on_apply, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Einstellungen")
        self.setMinimumSize(520, 360)
        self.setObjectName("SettingsDialog")
        self._on_apply = on_apply

        v = QVBoxLayout(self); v.setContentsMargins(24, 24, 24, 24); v.setSpacing(16)

        title = QLabel("Einstellungen"); title.setObjectName("H2"); v.addWidget(title, 0, Qt.AlignLeft)

        logo_lbl = QLabel(); logo_lbl.setAlignment(Qt.AlignHCenter)
        lp = resolve_logo_path()
        if lp:
            pm = QPixmap(str(lp))
            if not pm.isNull():
                logo_lbl.setPixmap(pm.scaledToWidth(220, Qt.SmoothTransformation))
        v.addWidget(logo_lbl)


        manual_btn = QPushButton("📘 User Manual")
        manual_btn.clicked.connect(self.show_manual)
        v.addWidget(manual_btn, 0, Qt.AlignLeft)

        v.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        v.addWidget(buttons)

    def show_manual(self):
        QMessageBox.information(
            self, "User Manual",
            "Kurzanleitung\n\n"
            "• Gerät & FEM-Fall wählen → „Berechnen“.\n"
            "• Menü links: New/Open/Save/Export.\n"
            "• Settings: Theme-Umschaltung, Manual.\n"
        )

    def accept(self):
        self._on_apply("dark")  # or remove this call entirely if not needed anymore
        super().accept()

# ---------------------------------------------------------
# Main Window
# ---------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.config = load_config()
        self.current_theme = self.config.get("theme", "light")

        self.setWindowTitle("Spielzeit – FEM 9.831 Tool")
        self.resize(1200, 740)

        root = QHBoxLayout()
        container = QWidget(); container.setLayout(root)
        self.setCentralWidget(container)

        self.sidebar = self._build_sidebar(); root.addWidget(self.sidebar)
        right = QVBoxLayout(); right.setContentsMargins(0, 0, 0, 0); right.setSpacing(0)
        right_wrap = QWidget(); right_wrap.setLayout(right); root.addWidget(right_wrap, 1)

        self.topbar = self._build_topbar(); right.addWidget(self.topbar)
        self.page = self._build_dashboard(); right.addWidget(self.page, 1)

        self.btn_new.clicked.connect(self.action_new)
        self.btn_open.clicked.connect(self.action_open)
        self.btn_save.clicked.connect(self.action_save)
        self.btn_export.clicked.connect(self.action_export)
        self.btn_settings.clicked.connect(self.action_settings)
        self.btn_calc.clicked.connect(self.action_calculate)
        self.combo_case.currentIndexChanged.connect(lambda idx: self.case_view.set_case(idx + 1))

        # nach Konstruktion: Paletten anwenden
        self.apply_runtime_palettes(self.current_theme)

    def _build_sidebar(self) -> QFrame:
        f = QFrame(); f.setObjectName("Sidebar"); f.setFixedWidth(60)
        lay = QVBoxLayout(f); lay.setContentsMargins(8, 8, 8, 8); lay.setSpacing(10)

        def icon_button(text: str, icon_path: str) -> QPushButton:
            b = QPushButton(); b.setObjectName("SidebarButton")
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedSize(44, 44)
            b.setToolTip(text)
            icon_file = resource_path(f"resources/icons/{icon_path}")
            if icon_file.exists():
                b.setIcon(QIcon(str(icon_file)))
                b.setIconSize(QSize(24, 24))
            return b

        self.btn_new    = icon_button("New",    "new.png")
        self.btn_open   = icon_button("Open",   "open.png")
        self.btn_save   = icon_button("Save",   "save.png")
        self.btn_export = icon_button("Export", "export.png")
        self.btn_settings = icon_button("Settings", "settings.png")
        # Theme toggle button (replaces sun and moon)
        self.btn_theme_toggle = icon_button("Dark Mode", "moon.png")
        self.btn_theme_toggle.clicked.connect(self.toggle_theme)

        for b in (self.btn_new, self.btn_open, self.btn_save, self.btn_export):
            lay.addWidget(b, 0, Qt.AlignHCenter)
        lay.addStretch(1)
        lay.addWidget(self.btn_theme_toggle, 0, Qt.AlignHCenter)
        lay.addWidget(self.btn_settings, 0, Qt.AlignHCenter)

        return f

    # Topbar
    def _build_topbar(self) -> QFrame:
        f = QFrame(); f.setObjectName("Topbar"); f.setFixedHeight(64)
        h = QHBoxLayout(f); h.setContentsMargins(18, 12, 18, 12); h.setSpacing(12)
        logo = QLabel()
        lp = resolve_logo_path()
        if lp:
            pm = QPixmap(str(lp))
            if not pm.isNull(): logo.setPixmap(pm.scaledToHeight(28, Qt.SmoothTransformation))
        h.addWidget(logo, 0, Qt.AlignVCenter)

        self.topbar_title = QLabel("Spielzeitberechnung"); self.topbar_title.setObjectName("TopbarTitle"); h.addWidget(self.topbar_title, 1)

        self.combo_device = QComboBox(); self.combo_device.setObjectName("DeviceCombo")  # <-- wichtig
        self.combo_device.clear()
        self.combo_device.addItems(["RBG 1 Mast", "RBG 2 Mast"]); self.combo_device.setFixedWidth(220)

        self.combo_case   = QComboBox(); self.combo_case.setObjectName("CaseCombo")       # <-- wichtig
        self.combo_case.addItems([f"FEM 9.851 – Fall {i}" for i in range(1,7)]); self.combo_case.setFixedWidth(160)

        self.btn_calc     = QPushButton("Berechnen"); self.btn_calc.setObjectName("PrimaryButton")

        for w in (self.combo_device, self.combo_case, self.btn_calc): h.addWidget(w, 0, Qt.AlignRight)
        return f

    # Dashboard
    def _build_dashboard(self) -> QWidget:
        from PySide6.QtWidgets import QFormLayout, QSizePolicy, QGroupBox, QSpacerItem
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(18, 18, 18, 18)
        v.setSpacing(16)

        # Main horizontal layout: Eingabemaske (left), right: donut row + graph below
        main_hbox = QHBoxLayout()
        main_hbox.setContentsMargins(0, 0, 0, 0)
        main_hbox.setSpacing(18)

        # --- Eingabemaske (left section) ---
        eingabe_box = QGroupBox()
        eingabe_layout = QFormLayout()
        eingabe_layout.setLabelAlignment(Qt.AlignLeft)
        eingabe_layout.setFormAlignment(Qt.AlignTop)
        eingabe_layout.setHorizontalSpacing(16)
        eingabe_layout.setVerticalSpacing(6)
        eingabe_box.setLayout(eingabe_layout)
        # Reduce Eingabemaske width to just fit content
        eingabe_box.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Expanding)
        # Define all input fields as QLineEdits, labels include units (not in input fields)
        self.input_fields = {}
        labels = [
            ("Verfahrw. (Gassenl.-Anfahrm.) [m]", "verfahrweg"),
            ("Gassenhöhe [m]", "gassenhoehe"),
            ("Geschw vx [m/s]", "geschw_vx"),
            ("Beschl ax [m/s²]", "beschl_ax"),
            ("Verschliffzeiten x [s]", "verschliff_x"),
            ("Geschw vy [m/s]", "geschw_vy"),
            ("Beschl ay [m/s²]", "beschl_ay"),
            ("Verschliffzeiten y [s]", "verschliff_y"),
            ("Übergabe Vorzone einlagern [s]", "vorzone_einlagern"),
            ("Übergabe Vorzone auslagern [s]", "vorzone_auslagern"),
            ("Übergabe Platz 1 [s]", "platz1"),
            ("Übergabe Platz 2 [s]", "platz2"),
            ("Verschliffzeit LAM [s]", "verschliff_lam"),
            ("Anteil der Umlagerungen [%]", "umlagerungen_anteil"),
        ]
        for label, key in labels:
            le = QLineEdit()
            le.setFixedWidth(100)
            self.input_fields[key] = le
            lbl = QLabel(label)
            eingabe_layout.addRow(lbl, le)
        eingabe_box.setMaximumWidth(eingabe_box.sizeHint().width())

        # --- Right section: donut row on top, graph below ---
        right_vbox = QVBoxLayout()
        right_vbox.setContentsMargins(0, 0, 0, 0)
        right_vbox.setSpacing(0)

        # Donut row (horizontal, top right, evenly spaced)
        progress_palette_dict = progress_palette(self.current_theme)
        self.progress1 = CircularProgress(value=72, thickness=8,
                                          color=progress_palette_dict["color"],
                                          track=progress_palette_dict["track"],
                                          text_color=progress_palette_dict["text"])
        self.progress2 = CircularProgress(value=38, thickness=8,
                                          color=progress_palette_dict["color"],
                                          track=progress_palette_dict["track"],
                                          text_color=progress_palette_dict["text"])
        self.progress3 = CircularProgress(value=55, thickness=8,
                                          color=progress_palette_dict["color"],
                                          track=progress_palette_dict["track"],
                                          text_color=progress_palette_dict["text"])
        for p in (self.progress1, self.progress2, self.progress3):
            p.setMinimumSize(80, 80)
            p.setMaximumSize(90, 90)
        donut_labels = [
            ("Durchsatz vs. Ziel", self.progress1),
            ("Anteil Fahr/Hub", self.progress2),
            ("Auslastung Gerät", self.progress3),
        ]
        donut_hbox = QHBoxLayout()
        donut_hbox.setContentsMargins(0, 0, 0, 0)
        donut_hbox.setSpacing(0)
        donut_hbox.addStretch(1)
        for text, prog in donut_labels:
            donut_wrap = QWidget()
            donut_wrap_lay = QVBoxLayout(donut_wrap)
            donut_wrap_lay.setContentsMargins(0, 0, 0, 0)
            donut_wrap_lay.setSpacing(2)
            donut_wrap_lay.addWidget(prog, 0, Qt.AlignHCenter)
            lbl = QLabel(text)
            lbl.setObjectName("Caption")
            lbl.setAlignment(Qt.AlignHCenter)
            donut_wrap_lay.addWidget(lbl, 0, Qt.AlignHCenter)
            donut_hbox.addWidget(donut_wrap, 0, Qt.AlignVCenter)
            donut_hbox.addStretch(1)
        right_vbox.addLayout(donut_hbox)

        # Visualization graph below donut row, aligns bottom with Eingabemaske's bottom
        self.case_view = FEMCaseView(theme=self.current_theme)
        self.case_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Remove any fixed height, instead use a layout trick to tightly align top and bottom

        # We'll use a vertical layout with donut row, then the visualization, then a spacer for possible future widgets
        # To align the visualization's top with the bottom of the donut row, and its bottom with the bottom of the Eingabemaske,
        # we use a QVBoxLayout with stretch factors.

        # To determine the height of Eingabemaske after layout, we need to defer setting the visualization height until after layout.
        # Instead, we'll use a QSpacerItem below the visualization to always leave space for possible future widgets.
        # The visualization will expand to fill the space between the donut row and the bottom of Eingabemaske.

        # Add visualization
        right_vbox.addWidget(self.case_view, 1)
        # Add a spacer below for future expansion (but nothing is shown yet)
        right_vbox.addSpacing(20)

        # Layout: Eingabemaske left, right_vbox right
        main_hbox.addWidget(eingabe_box, 0, Qt.AlignTop)
        # Add a little spacing between Eingabemaske and donuts/graph
        main_hbox.addSpacing(18)
        main_hbox.addLayout(right_vbox, 1)

        v.addLayout(main_hbox, 1)

        # Remove "Übersicht" and "Eingabemaske" labels if present
        # (None are explicitly added, so nothing to remove)

        return page

    def _update_input_form(self, idx):
        # Not used anymore; Eingabemaske is always visible now.
        pass

    # The _push_row method is no longer needed and has been removed.

    # ---- Theme anwenden (nur Laufzeit-Farben) ----
    def apply_runtime_palettes(self, theme: str):
        # Update progress indicators
        pal = progress_palette(theme)
        if hasattr(self, "progress1"):
            self.progress1.set_palette(pal["color"], pal["track"], pal["text"])
        if hasattr(self, "progress2"):
            self.progress2.set_palette(pal["color"], pal["track"], pal["text"])
        if hasattr(self, "progress3"):
            self.progress3.set_palette(pal["color"], pal["track"], pal["text"])
        self.case_view.set_theme(theme)

    # Actions
    def action_new(self):
        dlg = NewProjectDialog(self)
        if dlg.exec() == QDialog.Accepted and dlg.result_data:
            data = dlg.result_data
            ordnername = f"{data['nummer']} - {data['name']}".replace("/", "_")
            pfad = QFileDialog.getExistingDirectory(self, "Speicherort für neues Projekt wählen", str(DATA_DIR))
            if not pfad:
                return
            projektordner = Path(pfad) / ordnername
            projektordner.mkdir(parents=True, exist_ok=True)
            safe_name = f"{data['nummer']}_{data['name']}".replace("/", "_").replace(" ", "_")
            info_datei = projektordner / f"{safe_name}.json"
            info_datei.write_text(json.dumps(data, indent=2), encoding="utf-8")
            QMessageBox.information(self, "Projekt erstellt", f"Projekt gespeichert:\n{info_datei}")
            self.topbar_title.setText(f"Spielzeitberechnung {data['nummer']} {data['name']}")

    def action_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Projekt öffnen", str(DATA_DIR), "Projektdateien (*.json);;Alle Dateien (*)")
        if path:
            try:
                data = json.loads(Path(path).read_text(encoding="utf-8"))
                nummer = data.get("nummer", "Unbekannt")
                name = data.get("name", "Unbenannt")
                self.topbar_title.setText(f"Spielzeitberechnung {nummer} {name}")
                QMessageBox.information(self, "Projekt geöffnet", f"Projekt geladen:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Fehler beim Laden:\n{e}")
    def action_save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Projekt speichern", str(DATA_DIR / "projekt.json"), "Projektdateien (*.json)")
        if path:
            Path(path).write_text(json.dumps({"demo": True}, indent=2), encoding="utf-8")
            QMessageBox.information(self, "Gespeichert", f"Projekt gespeichert:\n{path}")
    def action_export(self):
        topbar_text = self.topbar_title.text().replace("Spielzeitberechnung", "").strip()
        safe_name = topbar_text.replace(" ", "_").replace("/", "_")
        path, _ = QFileDialog.getSaveFileName(self, "Exportieren als PDF", str(EXPORTS_DIR / f"{safe_name}.pdf"), "PDF (*.pdf)")
        if path:
            Path(path).write_bytes(b"%PDF-1.4\n%...\n")
            QMessageBox.information(self, "Export", f"PDF exportiert:\n{path}")

    def action_settings(self):
        dlg = SettingsDialog(self.current_theme, self.apply_theme, self); dlg.exec()

    def apply_theme(self, theme: str):
        self.current_theme = "light" if theme not in ("light","dark") else theme
        cfg = load_config(); cfg["theme"] = self.current_theme; save_config(cfg)
        load_stylesheet(self.app, self.current_theme)   # QSS
        self.apply_runtime_palettes(self.current_theme) # Zeichnen
        # Update theme toggle button icon
        new_icon = "moon.png" if self.current_theme == "light" else "sun.png"
        icon_file = resource_path(f"resources/icons/{new_icon}")
        if icon_file.exists():
            self.btn_theme_toggle.setIcon(QIcon(str(icon_file)))
            self.btn_theme_toggle.setIconSize(QSize(24, 24))

    def toggle_theme(self):
        new_theme = "dark" if self.current_theme == "light" else "light"
        self.apply_theme(new_theme)

    # Demo-Rechnung
    def action_calculate(self):
        # Calculation logic can be kept for future use, but progress indicators are removed.
        pass

# ---------------------------------------------------------
# Run
# ---------------------------------------------------------
if __name__ == "__main__":
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))  # <-- wichtig für konsistente QSS

    cfg = load_config()
    load_stylesheet(app, cfg.get("theme", "light"))

    w = MainWindow(app)
    w.show()
    sys.exit(app.exec())
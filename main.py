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
        from PySide6.QtWidgets import QFormLayout, QSizePolicy, QTextEdit, QLabel, QFrame, QVBoxLayout, QHBoxLayout, QWidget
        # -------- Eingabeformular vorbereiten --------
        input_form_layout = QFormLayout()
        input_form_layout.setLabelAlignment(Qt.AlignLeft)
        input_form_layout.setFormAlignment(Qt.AlignTop)
        input_form_layout.setHorizontalSpacing(12)
        input_form_layout.setVerticalSpacing(6)
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
        from PySide6.QtWidgets import QLineEdit
        for label, key in labels:
            le = QLineEdit()
            le.setFixedWidth(100)
            le.setObjectName("InputField")
            self.input_fields[key] = le
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            input_form_layout.addRow(lbl, le)

        # -------- KPIs vorbereiten --------
        progress_palette_dict = progress_palette(self.current_theme)
        self.kpi_throughput = CircularProgress(value=72, thickness=8,
                                               color=progress_palette_dict["color"],
                                               track=progress_palette_dict["track"],
                                               text_color=progress_palette_dict["text"])
        self.kpi_ratio = CircularProgress(value=38, thickness=8,
                                          color=progress_palette_dict["color"],
                                          track=progress_palette_dict["track"],
                                          text_color=progress_palette_dict["text"])
        self.kpi_utilization = CircularProgress(value=55, thickness=8,
                                               color=progress_palette_dict["color"],
                                               track=progress_palette_dict["track"],
                                               text_color=progress_palette_dict["text"])
        for p in (self.kpi_throughput, self.kpi_ratio, self.kpi_utilization):
            p.setMinimumSize(80, 80)
            p.setMaximumSize(90, 90)

        # -------- Leistungsbetrachtungstabelle vorbereiten --------
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem
        self.performance_table_layout = QVBoxLayout()
        self.performance_table_layout.setContentsMargins(0, 0, 0, 0)
        self.performance_table_layout.setSpacing(0)
        self.leistungs_table = QTableWidget(3, 3)
        self.leistungs_table.setHorizontalHeaderLabels(["Kriterium", "Wert", "Einheit"])
        self.leistungs_table.setVerticalHeaderLabels(["Leistung 1", "Leistung 2", "Leistung 3"])
        self.leistungs_table.setFixedHeight(200)
        beispiel_daten = [
            ("Durchsatz", "120", "Pal/h"),
            ("Fahrzeit", "35", "s"),
            ("Auslastung", "80", "%"),
        ]
        for row, (kriterium, wert, einheit) in enumerate(beispiel_daten):
            self.leistungs_table.setItem(row, 0, QTableWidgetItem(kriterium))
            self.leistungs_table.setItem(row, 1, QTableWidgetItem(wert))
            self.leistungs_table.setItem(row, 2, QTableWidgetItem(einheit))
        self.leistungs_table.horizontalHeader().setStretchLastSection(True)
        self.leistungs_table.horizontalHeader().setDefaultSectionSize(110)
        self.leistungs_table.verticalHeader().setDefaultSectionSize(32)
        self.performance_table_layout.addWidget(self.leistungs_table)

        # -------- Visualisierung vorbereiten --------
        self.canvas = FEMCaseView(theme=self.current_theme)
        self.canvas.setMinimumHeight(120)
        self.canvas.setMaximumHeight(180)

        # -------- Kommentarfeld vorbereiten --------
        self.notes_frame = QFrame()
        self.notes_frame.setObjectName("NotesFrame")
        notes_layout = QVBoxLayout()
        notes_layout.setContentsMargins(8, 8, 8, 8)
        self.notes_label = QLabel("Kommentarfeld")
        self.notes_label.setObjectName("NotesLabel")
        self.notes_edit = QTextEdit()
        self.notes_edit.setObjectName("NotesEdit")
        self.notes_edit.setPlaceholderText("Hier Notizen eingeben ...")
        notes_layout.addWidget(self.notes_label)
        notes_layout.addWidget(self.notes_edit)
        self.notes_frame.setLayout(notes_layout)

        # -------- Hauptlayout gemäß Vorgabe (neu) --------
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 10, 20, 10)
        main_layout.setSpacing(15)

        # --- Eingabe/KPI-Block ---
        top_row_layout = QHBoxLayout()
        top_row_layout.setSpacing(24)

        # Left: Eingabeformular (in Frame)
        input_frame = QFrame()
        input_frame.setObjectName("InputFrame")
        input_frame.setLayout(input_form_layout)
        input_frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        top_row_layout.addWidget(input_frame, stretch=3)

        # Right: KPIs (vertically centered)
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(22)
        kpi_layout.addWidget(self.kpi_throughput)
        kpi_layout.addWidget(self.kpi_ratio)
        kpi_layout.addWidget(self.kpi_utilization)
        kpi_wrapper = QFrame()
        kpi_wrapper.setLayout(kpi_layout)
        kpi_wrapper.setObjectName("KPIWrapper")
        top_row_layout.addWidget(kpi_wrapper, stretch=2)

        main_layout.addLayout(top_row_layout)

        # --- Visualisierung: Path chart uses full width below Eingabe/KPI ---
        canvas_wrapper = QFrame()
        canvas_layout = QVBoxLayout()
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.addWidget(self.canvas)
        canvas_wrapper.setLayout(canvas_layout)
        main_layout.addWidget(canvas_wrapper, stretch=0)

        # --- Tabelle + Kommentarfeld (unten) ---
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(20)

        table_frame = QFrame()
        table_frame.setObjectName("TableFrame")
        table_frame.setLayout(self.performance_table_layout)
        bottom_layout.addWidget(table_frame, stretch=3)

        bottom_layout.addWidget(self.notes_frame, stretch=1)

        main_layout.addLayout(bottom_layout)

        # Setze das neue Layout
        main_widget = QWidget()
        main_widget.setLayout(main_layout)

        # --------- Subtle highlighting for input and notes fields (via stylesheet) ---------
        highlight_qss = """
        QFrame#InputFrame {
            background: rgba(30, 120, 255, 0.04);
            border-radius: 12px;
            padding: 6px 4px;
        }
        QFrame#NotesFrame {
            background: rgba(30, 120, 255, 0.06);
            border-radius: 12px;
            padding: 6px 4px;
        }
        QLineEdit#InputField, QTextEdit#NotesEdit {
            background: rgba(200, 220, 255, 0.11);
            border: none;
            border-radius: 8px;
            padding: 6px 8px;
        }
        QTextEdit#NotesEdit {
            min-height: 80px;
        }
        """
        main_widget.setStyleSheet(highlight_qss)
        return main_widget

    def _update_input_form(self, idx):
        # Not used anymore; Eingabemaske is always visible now.
        pass

    # The _push_row method is no longer needed and has been removed.

    # ---- Theme anwenden (nur Laufzeit-Farben) ----
    def apply_runtime_palettes(self, theme: str):
        # Update progress indicators
        pal = progress_palette(theme)
        if hasattr(self, "kpi_throughput"):
            self.kpi_throughput.set_palette(pal["color"], pal["track"], pal["text"])
        if hasattr(self, "kpi_ratio"):
            self.kpi_ratio.set_palette(pal["color"], pal["track"], pal["text"])
        if hasattr(self, "kpi_utilization"):
            self.kpi_utilization.set_palette(pal["color"], pal["track"], pal["text"])
        if hasattr(self, "canvas"):
            self.canvas.set_theme(theme)

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
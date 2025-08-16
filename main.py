import sys, os, math, json, re
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QRect, QRectF, QPoint, QPointF
from PySide6.QtGui import QPainter, QPen, QFont, QColor, QPixmap, QGuiApplication
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QComboBox,
    QFileDialog, QMessageBox, QDialog, QDialogButtonBox
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
# Theme-Paletten für Zeichnen (Light/Dark)
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

        row = QHBoxLayout(); row.setSpacing(12)
        row.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["light", "dark"])
        self.theme_combo.setCurrentText(current_theme)
        row.addWidget(self.theme_combo, 1)
        v.addLayout(row)

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
        self._on_apply(self.theme_combo.currentText())
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

    # Sidebar
    def _sidebar_button(self, text: str) -> QPushButton:
        b = QPushButton(text); b.setObjectName("SidebarButton"); b.setCursor(Qt.PointingHandCursor); b.setMinimumHeight(44); return b

    def _build_sidebar(self) -> QFrame:
        f = QFrame(); f.setObjectName("Sidebar"); f.setFixedWidth(240)
        lay = QVBoxLayout(f); lay.setContentsMargins(14, 14, 14, 14); lay.setSpacing(10)
        lay.addWidget(QLabel("  ▸  MENU"))
        self.btn_home, self.btn_new, self.btn_open, self.btn_save, self.btn_export = [self._sidebar_button(t) for t in ("Home","New","Open","Save","Export")]
        for b in (self.btn_home, self.btn_new, self.btn_open, self.btn_save, self.btn_export): lay.addWidget(b)
        lay.addStretch(1)
        self.btn_settings = self._sidebar_button("Settings"); lay.addWidget(self.btn_settings)
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
        title = QLabel("Spielzeit-Berechnung  •  FEM 9.831/9.832/9.842-1"); title.setObjectName("TopbarTitle"); h.addWidget(title, 1)
        self.combo_device = QComboBox(); self.combo_device.addItems(["RBG Einmast (1x tief)","RBG Zweimast (2x tief)","Heber","AKF / Shuttle","AKL (Mini-Load)"]); self.combo_device.setFixedWidth(220)
        self.combo_case   = QComboBox(); self.combo_case.addItems([f"FEM 9.851 – Fall {i}" for i in range(1,7)]); self.combo_case.setFixedWidth(160)
        self.btn_calc     = QPushButton("Berechnen"); self.btn_calc.setObjectName("PrimaryButton")
        for w in (self.combo_device, self.combo_case, self.btn_calc): h.addWidget(w, 0, Qt.AlignRight)
        return f

    # Dashboard
    def _build_dashboard(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page); v.setContentsMargins(18, 18, 18, 18); v.setSpacing(16)

        hdr = QLabel("Übersicht"); hdr.setObjectName("H2"); v.addWidget(hdr)

        prog_row = QHBoxLayout(); prog_row.setSpacing(22)
        # vorerst neutrale Farbangaben, werden in apply_runtime_palettes überschrieben
        self.progress_a = CircularProgress(80)
        self.progress_b = CircularProgress(45)
        self.progress_c = CircularProgress(75)

        def col(caption):
            lay = QVBoxLayout(); lay.setContentsMargins(0,0,0,0); lay.setSpacing(8)
            lab = QLabel(caption); lab.setObjectName("Caption"); lab.setAlignment(Qt.AlignHCenter)
            lay.addWidget(lab, 0, Qt.AlignHCenter); return lay

        c1, c2, c3 = col("Durchsatz vs. Ziel"), col("Anteil Fahr/Hub"), col("Auslastung Gerät")
        for prog, lay in [(self.progress_a,c1),(self.progress_b,c2),(self.progress_c,c3)]:
            w = QWidget(); w.setLayout(lay); lay.insertWidget(0, prog, 0, Qt.AlignHCenter); prog_row.addWidget(w,1)
        v.addLayout(prog_row)

        self.case_view = FEMCaseView(theme=self.current_theme)
        v.addWidget(self.case_view)

        tbl_title = QLabel("Letzte Berechnungen"); tbl_title.setObjectName("H3"); v.addWidget(tbl_title)
        self.table = QTableWidget(0,5); self.table.setHorizontalHeaderLabels(["Gerät","vx [m/s]","vy [m/s]","Spielzeit [s]","Zyklus [s]"])
        self._push_row("RBG Einmast (1x tief)", "3.0", "1.4", "21.9", "26.1")
        self._push_row("RBG Zweimast (2x tief)", "3.5", "1.5", "19.8", "25.2")
        v.addWidget(self.table)

        return page

    def _push_row(self, device, vx, vy, spiel, zyklus):
        r = self.table.rowCount(); self.table.insertRow(r)
        for c, val in enumerate([device, vx, vy, spiel, zyklus]):
            self.table.setItem(r, c, QTableWidgetItem(val))

    # ---- Theme anwenden (nur Laufzeit-Farben, nicht QSS) ----
    def apply_runtime_palettes(self, theme: str):
        ppal = progress_palette(theme)
        for prog in (self.progress_a, self.progress_b, self.progress_c):
            prog.set_palette(ppal["color"], ppal["track"], ppal["text"])
        self.case_view.set_theme(theme)

    # Actions
    def action_new(self):  QMessageBox.information(self, "Neu", "Neues Projekt angelegt (Platzhalter).")
    def action_open(self): QFileDialog.getOpenFileName(self, "Projekt öffnen", str(DATA_DIR), "Projektdateien (*.json);;Alle Dateien (*)")
    def action_save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Projekt speichern", str(DATA_DIR / "projekt.json"), "Projektdateien (*.json)")
        if path:
            Path(path).write_text(json.dumps({"demo": True}, indent=2), encoding="utf-8")
            QMessageBox.information(self, "Gespeichert", f"Projekt gespeichert:\n{path}")
    def action_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportieren als PDF", str(EXPORTS_DIR / "bericht.pdf"), "PDF (*.pdf)")
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

    # Demo-Rechnung
    def action_calculate(self):
        dev = self.combo_device.currentText()
        vx, ax = 3.0, 0.35; vy, ay = 1.4, 0.8
        case_idx = self.combo_case.currentIndex() + 1
        x, y = (26.5, 24.7) if case_idx == 1 else (22.0, 28.0) if case_idx == 2 else (25.0, 25.0)

        def move_time(s, vmax, a):
            s_acc = vmax*vmax/(2*a)
            return 2*(vmax/a) + (s-2*s_acc)/vmax if 2*s_acc <= s else 2*math.sqrt(s/(2*a))

        t_x = move_time(x, vx, ax); t_y = move_time(y, vy, ay); t_fix = 2.5 + 2.5 + 9.3
        t_spiel = t_x + t_y + t_fix; t_zyklus = t_spiel + 3.0

        self._push_row(dev, f"{vx:.1f}", f"{vy:.1f}", f"{t_spiel:.1f}", f"{t_zyklus:.1f}")

        move = t_x + t_y
        move_pct = int(round(min(100, max(0, (move / max(0.001, t_spiel)) * 100))))
        t_ref = 25.0
        throughput_pct = int(round(min(100, max(0, (t_ref / max(0.001, t_spiel)) * 100))))
        cps = 3600.0 / max(0.001, t_zyklus)
        util_pct = int(round(min(100, max(0, (cps / 120.0) * 100))))

        self.progress_a.setValue(throughput_pct)
        self.progress_b.setValue(move_pct)
        self.progress_c.setValue(util_pct)

# ---------------------------------------------------------
# Run
# ---------------------------------------------------------
if __name__ == "__main__":
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)

    cfg = load_config()
    load_stylesheet(app, cfg.get("theme", "light"))

    w = MainWindow(app)
    w.show()
    sys.exit(app.exec())
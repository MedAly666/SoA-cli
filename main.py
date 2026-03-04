#!/usr/bin/env python3
"""
SOA-CLI  –  PyQt5 Desktop Interface
Ergonomic UI for the Multi-Agent State of the Art Generator.
"""

import sys
import json
import os
import shutil
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QListWidget, QListWidgetItem, QStackedWidget, QLabel,
    QPushButton, QLineEdit, QTextEdit, QComboBox, QSpinBox,
    QDoubleSpinBox, QCheckBox, QGroupBox, QFormLayout, QFileDialog,
    QProgressBar, QScrollArea, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy, QDialog, QDialogButtonBox,
    QMessageBox, QTabWidget, QPlainTextEdit, QAbstractItemView,
    QGridLayout, QAction, QMenuBar, QStatusBar, QToolButton,
    QSlider, QSpacerItem
)
from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, QProcess, QTimer, QSize,
    QPropertyAnimation, QEasingCurve, QRect, QSettings
)
from PyQt5.QtGui import (
    QFont, QColor, QPalette, QIcon, QPixmap, QPainter,
    QBrush, QPen, QLinearGradient, QFontDatabase, QTextCursor,
    QTextCharFormat
)

# ─────────────────────────────────────────────────────────────────────────────
# THEME / COLOUR PALETTE
# ─────────────────────────────────────────────────────────────────────────────

DARK = {
    "bg":         "#0f1117",
    "surface":    "#1a1d27",
    "surface2":   "#22263a",
    "border":     "#2e3248",
    "accent":     "#5c6ef8",
    "accent2":    "#7c8fff",
    "accent3":    "#3d52d5",
    "success":    "#3dd68c",
    "warning":    "#f5a623",
    "error":      "#f05454",
    "text":       "#e8eaf6",
    "text_dim":   "#7b82b4",
    "text_muted": "#4a5080",
    "running":    "#5c6ef8",
    "done":       "#3dd68c",
    "skip":       "#7b82b4",
    "header_bg":  "#13162b",
}

PIPELINE_STAGES = [
    ("theme_builder",  "Theme Builder",  "Builds thematic contract from research goals"),
    ("reader",         "Reader",         "Extracts structured info from each PDF"),
    ("extractor",      "Extractor",      "Extracts key facts, methods, results"),
    ("critic",         "Critic",         "Validates relevance and quality"),
    ("vectorize",      "Vectorize",      "Embeds papers for similarity search"),
    ("cluster",        "Cluster",        "Groups related papers together"),
    ("synthesis",      "Synthesis",      "Synthesises findings across papers"),
    ("writer",         "Writer",         "Generates LaTeX State of the Art"),
    ("verifier",       "Verifier",       "Verifies academic quality"),
    ("repair",         "Repair",         "Fixes LaTeX issues if needed"),
]


def global_stylesheet() -> str:
    c = DARK
    return f"""
    /* ── global ── */
    QWidget {{
        background: {c['bg']};
        color: {c['text']};
        font-family: 'Segoe UI', 'Inter', 'Ubuntu', sans-serif;
        font-size: 13px;
        border: none;
    }}
    QScrollBar:vertical {{
        background: {c['surface']};
        width: 8px; margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {c['border']};
        border-radius: 4px; min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c['accent']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar:horizontal {{
        background: {c['surface']};
        height: 8px; margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: {c['border']};
        border-radius: 4px; min-width: 24px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {c['accent']}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

    /* ── buttons ── */
    QPushButton {{
        background: {c['surface2']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 7px;
        padding: 8px 18px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background: {c['accent3']};
        border-color: {c['accent']};
    }}
    QPushButton:pressed {{ background: {c['accent']}; }}
    QPushButton:disabled {{
        background: {c['surface']};
        color: {c['text_muted']};
        border-color: {c['border']};
    }}
    QPushButton#accent_btn {{
        background: {c['accent']};
        color: white;
        border: none;
        font-weight: 600;
        font-size: 14px;
        padding: 10px 28px;
    }}
    QPushButton#accent_btn:hover {{ background: {c['accent2']}; }}
    QPushButton#accent_btn:disabled {{
        background: {c['surface2']};
        color: {c['text_muted']};
    }}
    QPushButton#danger_btn {{
        background: transparent;
        color: {c['error']};
        border: 1px solid {c['error']};
        border-radius: 7px;
        padding: 8px 18px;
    }}
    QPushButton#danger_btn:hover {{
        background: {c['error']};
        color: white;
    }}
    QPushButton#icon_btn {{
        background: transparent;
        border: none;
        padding: 4px;
        border-radius: 5px;
    }}
    QPushButton#icon_btn:hover {{ background: {c['surface2']}; }}

    /* ── inputs ── */
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background: {c['surface2']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 7px 10px;
        color: {c['text']};
        selection-background-color: {c['accent']};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
    QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
        border-color: {c['accent']};
    }}
    QComboBox::drop-down {{
        border: none;
        padding-right: 6px;
    }}
    QComboBox QAbstractItemView {{
        background: {c['surface2']};
        border: 1px solid {c['border']};
        selection-background-color: {c['accent']};
    }}
    QSpinBox::up-button, QSpinBox::down-button,
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
        background: {c['border']};
        width: 16px;
        border-radius: 3px;
    }}

    /* ── check box ── */
    QCheckBox {{ spacing: 8px; }}
    QCheckBox::indicator {{
        width: 18px; height: 18px;
        border: 1px solid {c['border']};
        border-radius: 4px;
        background: {c['surface2']};
    }}
    QCheckBox::indicator:checked {{
        background: {c['accent']};
        border-color: {c['accent']};
    }}

    /* ── group box ── */
    QGroupBox {{
        border: 1px solid {c['border']};
        border-radius: 8px;
        margin-top: 14px;
        padding: 10px;
        font-weight: 600;
        color: {c['text_dim']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 8px;
        left: 12px;
    }}

    /* ── tabs ── */
    QTabWidget::pane {{
        border: 1px solid {c['border']};
        border-radius: 8px;
        background: {c['surface']};
    }}
    QTabBar::tab {{
        background: {c['surface']};
        color: {c['text_dim']};
        border: 1px solid {c['border']};
        border-bottom: none;
        padding: 8px 20px;
        border-top-left-radius: 7px;
        border-top-right-radius: 7px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background: {c['surface2']};
        color: {c['accent2']};
        border-bottom-color: {c['surface2']};
    }}
    QTabBar::tab:hover:!selected {{ color: {c['text']}; }}

    /* ── table ── */
    QTableWidget {{
        background: {c['surface']};
        gridline-color: {c['border']};
        alternate-background-color: {c['surface2']};
        border: 1px solid {c['border']};
        border-radius: 8px;
    }}
    QTableWidget::item:selected {{
        background: {c['accent3']};
        color: white;
    }}
    QHeaderView::section {{
        background: {c['surface2']};
        color: {c['text_dim']};
        border: none;
        border-right: 1px solid {c['border']};
        padding: 8px 12px;
        font-weight: 600;
    }}
    QHeaderView::section:first {{ border-top-left-radius: 7px; }}

    /* ── list ── */
    QListWidget {{
        background: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        outline: none;
    }}
    QListWidget::item {{
        padding: 9px 12px;
        border-radius: 5px;
        margin: 1px 4px;
    }}
    QListWidget::item:hover {{
        background: {c['surface2']};
    }}
    QListWidget::item:selected {{
        background: {c['accent3']};
        color: white;
    }}

    /* ── progress bar ── */
    QProgressBar {{
        background: {c['surface2']};
        border: 1px solid {c['border']};
        border-radius: 5px;
        text-align: center;
        height: 8px;
        color: transparent;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
            stop:0 {c['accent3']}, stop:1 {c['accent']});
        border-radius: 5px;
    }}

    /* ── splitter ── */
    QSplitter::handle {{
        background: {c['border']};
        width: 1px;
    }}

    /* ── status bar ── */
    QStatusBar {{
        background: {c['header_bg']};
        color: {c['text_dim']};
        border-top: 1px solid {c['border']};
        font-size: 12px;
        padding: 2px 10px;
    }}
    QStatusBar::item {{ border: none; }}

    /* ── menu bar ── */
    QMenuBar {{
        background: {c['header_bg']};
        color: {c['text']};
        border-bottom: 1px solid {c['border']};
        padding: 2px 4px;
    }}
    QMenuBar::item:selected {{ background: {c['surface2']}; border-radius: 4px; }}
    QMenu {{
        background: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 4px;
    }}
    QMenu::item {{ padding: 7px 20px; border-radius: 4px; }}
    QMenu::item:selected {{ background: {c['accent3']}; color: white; }}
    QMenu::separator {{
        height: 1px;
        background: {c['border']};
        margin: 3px 8px;
    }}

    /* ── tool tip ── */
    QToolTip {{
        background: {c['surface2']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 5px;
        padding: 5px 8px;
    }}

    /* ── frame ── */
    QFrame#card {{
        background: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 10px;
    }}
    QFrame#header_bar {{
        background: {c['header_bg']};
        border-bottom: 1px solid {c['border']};
    }}
    """


# ─────────────────────────────────────────────────────────────────────────────
# NAV SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

class NavItem(QWidget):
    clicked = pyqtSignal()

    def __init__(self, icon_text: str, label: str, parent=None):
        super().__init__(parent)
        self._active = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(50)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(12)

        self.icon_lbl = QLabel(icon_text)
        self.icon_lbl.setFixedWidth(22)
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        self.icon_lbl.setFont(QFont("Segoe UI Emoji", 16))

        self.text_lbl = QLabel(label)
        self.text_lbl.setFont(QFont("Segoe UI", 12, QFont.Medium))

        self.indicator = QFrame()
        self.indicator.setFixedSize(3, 28)
        self.indicator.setStyleSheet("border-radius: 2px;")

        lay.addWidget(self.indicator)
        lay.addWidget(self.icon_lbl)
        lay.addWidget(self.text_lbl)
        lay.addStretch()

        self._render()

    def _render(self):
        c = DARK
        if self._active:
            self.setStyleSheet(f"background: {c['accent3']}20; border-radius: 8px;")
            self.indicator.setStyleSheet(f"background: {c['accent']}; border-radius: 2px;")
            self.text_lbl.setStyleSheet(f"color: {c['accent2']}; font-weight: 600;")
            self.icon_lbl.setStyleSheet(f"color: {c['accent2']};")
        else:
            self.setStyleSheet("background: transparent; border-radius: 8px;")
            self.indicator.setStyleSheet("background: transparent;")
            self.text_lbl.setStyleSheet(f"color: {c['text_dim']};")
            self.icon_lbl.setStyleSheet(f"color: {c['text_dim']};")

    def set_active(self, active: bool):
        self._active = active
        self._render()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()


class Sidebar(QWidget):
    page_changed = pyqtSignal(int)

    NAV = [
        ("🏠", "Dashboard"),
        ("📄", "Papers"),
        ("🎯", "Research Theme"),
        ("⚙️",  "Configuration"),
        ("▶️",  "Run Pipeline"),
        ("📊", "Results"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(210)
        self.setStyleSheet(f"background: {DARK['header_bg']};")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 0, 8, 12)
        outer.setSpacing(0)

        # Logo
        logo_frame = QFrame()
        logo_frame.setFixedHeight(68)
        logo_lay = QHBoxLayout(logo_frame)
        logo_lay.setContentsMargins(14, 0, 0, 0)
        logo_lbl = QLabel("⚗️  <b>SOA-CLI</b>")
        logo_lbl.setFont(QFont("Segoe UI", 15))
        logo_lbl.setStyleSheet(f"color: {DARK['text']}; letter-spacing: 1px;")
        logo_lay.addWidget(logo_lbl)
        outer.addWidget(logo_frame)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {DARK['border']};")
        outer.addWidget(sep)
        outer.addSpacing(8)

        self._items: list[NavItem] = []
        for i, (icon, label) in enumerate(self.NAV):
            item = NavItem(icon, label)
            item.clicked.connect(lambda idx=i: self._select(idx))
            outer.addWidget(item)
            self._items.append(item)

        outer.addStretch()

        # Version tag
        ver = QLabel("v2.0  ·  LangGraph")
        ver.setStyleSheet(f"color: {DARK['text_muted']}; font-size: 11px;")
        ver.setAlignment(Qt.AlignCenter)
        outer.addWidget(ver)

        self._select(0)

    def _select(self, idx: int):
        for i, item in enumerate(self._items):
            item.set_active(i == idx)
        self.page_changed.emit(idx)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

class StatCard(QFrame):
    def __init__(self, icon: str, title: str, value: str, color: str = None, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setFixedHeight(110)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        c = color or DARK['accent']
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(4)

        top = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Segoe UI Emoji", 20))
        icon_lbl.setStyleSheet(f"color: {c};")

        self.value_lbl = QLabel(value)
        self.value_lbl.setFont(QFont("Segoe UI", 22, QFont.Bold))
        self.value_lbl.setStyleSheet(f"color: {c};")
        self.value_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        top.addWidget(icon_lbl)
        top.addStretch()
        top.addWidget(self.value_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {DARK['text_dim']}; font-size: 12px;")

        lay.addLayout(top)
        lay.addWidget(title_lbl)


class DashboardPage(QScrollArea):
    go_to_run = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        self.setWidget(container)
        lay = QVBoxLayout(container)
        lay.setContentsMargins(28, 24, 28, 28)
        lay.setSpacing(20)

        # ── Header
        hdr = QLabel("Dashboard")
        hdr.setFont(QFont("Segoe UI", 20, QFont.Bold))
        hdr.setStyleSheet(f"color: {DARK['text']};")
        lay.addWidget(hdr)

        sub = QLabel("Overview of your State of the Art pipeline session")
        sub.setStyleSheet(f"color: {DARK['text_dim']}; font-size: 13px;")
        lay.addWidget(sub)

        # ── Stat cards row
        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)

        self.c_papers = StatCard("📄", "Papers loaded", "–", DARK['accent'])
        self.c_stages = StatCard("⚡", "Pipeline stages", str(len(PIPELINE_STAGES)), DARK['success'])
        self.c_artifacts = StatCard("📦", "Artifacts on disk", "–", DARK['warning'])
        self.c_output = StatCard("📝", "Output ready", "No", DARK['text_dim'])

        for card in (self.c_papers, self.c_stages, self.c_artifacts, self.c_output):
            cards_row.addWidget(card)

        lay.addLayout(cards_row)

        # ── Pipeline overview panel
        pipe_box = QGroupBox("Pipeline Stages")
        pipe_lay = QVBoxLayout(pipe_box)
        pipe_lay.setSpacing(8)

        self._stage_rows: dict[str, QLabel] = {}
        for key, name, desc in PIPELINE_STAGES:
            row = QHBoxLayout()
            dot = QLabel("⬤")
            dot.setFixedWidth(18)
            dot.setStyleSheet(f"color: {DARK['text_muted']};")

            name_lbl = QLabel(f"<b>{name}</b>")
            name_lbl.setFixedWidth(130)
            name_lbl.setStyleSheet(f"color: {DARK['text']};")

            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet(f"color: {DARK['text_dim']}; font-size: 12px;")

            status_lbl = QLabel("Waiting")
            status_lbl.setFixedWidth(90)
            status_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            status_lbl.setStyleSheet(f"color: {DARK['text_muted']}; font-size: 12px;")

            row.addWidget(dot)
            row.addWidget(name_lbl)
            row.addWidget(desc_lbl)
            row.addStretch()
            row.addWidget(status_lbl)
            pipe_lay.addLayout(row)
            self._stage_rows[key] = (dot, status_lbl)

        lay.addWidget(pipe_box)

        # ── Quick actions
        act_box = QGroupBox("Quick Actions")
        act_lay = QHBoxLayout(act_box)
        act_lay.setSpacing(12)

        btn_run = QPushButton("▶  Run Pipeline")
        btn_run.setObjectName("accent_btn")
        btn_run.setFixedHeight(40)
        btn_run.clicked.connect(self.go_to_run)

        btn_open_output = QPushButton("📂  Open Output")
        btn_open_output.setFixedHeight(40)
        btn_open_output.clicked.connect(self._open_output)

        btn_clean = QPushButton("🗑  Clear Cache")
        btn_clean.setObjectName("danger_btn")
        btn_clean.setFixedHeight(40)
        btn_clean.clicked.connect(self._clear_cache)

        for btn in (btn_run, btn_open_output, btn_clean):
            act_lay.addWidget(btn)
        act_lay.addStretch()

        lay.addWidget(act_box)
        lay.addStretch()

        # Initial refresh
        QTimer.singleShot(300, self.refresh)

    def refresh(self):
        # Count papers
        papers_dir = Path("papers")
        n_papers = len(list(papers_dir.glob("*.pdf"))) if papers_dir.exists() else 0
        self.c_papers.value_lbl.setText(str(n_papers))

        # Count artifacts
        artifacts_dir = Path("artifacts")
        n_art = sum(1 for _ in artifacts_dir.rglob("*.json")) if artifacts_dir.exists() else 0
        self.c_artifacts.value_lbl.setText(str(n_art))

        # Output ready?
        soa_file = Path("STATE_OF_THE_ART.tex")
        if soa_file.exists():
            self.c_output.value_lbl.setText("Yes")
            self.c_output.value_lbl.setStyleSheet(f"color: {DARK['success']}; font-size: 22px; font-weight: bold;")
        else:
            self.c_output.value_lbl.setText("No")
            self.c_output.value_lbl.setStyleSheet(f"color: {DARK['text_dim']}; font-size: 22px; font-weight: bold;")

    def update_stage(self, stage_key: str, status: str):
        """status: 'running' | 'done' | 'error' | 'skip'"""
        if stage_key not in self._stage_rows:
            return
        dot_lbl, status_lbl = self._stage_rows[stage_key]

        colors = {
            "running": (DARK['running'], "Running…"),
            "done":    (DARK['done'],    "Done ✓"),
            "error":   (DARK['error'],   "Error ✗"),
            "skip":    (DARK['skip'],    "Skipped"),
        }
        color, text = colors.get(status, (DARK['text_muted'], status.capitalize()))
        dot_lbl.setStyleSheet(f"color: {color};")
        status_lbl.setText(text)
        status_lbl.setStyleSheet(f"color: {color}; font-size: 12px;")

    def _open_output(self):
        f = Path("STATE_OF_THE_ART.tex")
        if f.exists():
            os.startfile(str(f)) if sys.platform == "win32" else os.system(f"xdg-open '{f}'")
        else:
            QMessageBox.information(self, "No Output", "STATE_OF_THE_ART.tex not found yet.\nRun the pipeline first.")

    def _clear_cache(self):
        reply = QMessageBox.question(
            self, "Clear Cache",
            "This will delete all <b>artifacts/</b> and <b>vector_db/</b> files.\n"
            "The pipeline will re-process all papers on the next run.\n\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            for d in ("artifacts", "vector_db"):
                p = Path(d)
                if p.exists():
                    shutil.rmtree(p)
            QMessageBox.information(self, "Done", "Cache cleared.")
            self.refresh()


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: PAPERS
# ─────────────────────────────────────────────────────────────────────────────

class PapersPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.papers_dir = Path("papers")
        self.papers_dir.mkdir(exist_ok=True)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 28)
        lay.setSpacing(16)

        # ── Header
        hdr_row = QHBoxLayout()
        hdr_lbl = QLabel("Research Papers")
        hdr_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))
        hdr_lbl.setStyleSheet(f"color: {DARK['text']};")

        self.count_badge = QLabel("0 papers")
        self.count_badge.setStyleSheet(
            f"background: {DARK['accent3']}40; color: {DARK['accent2']};"
            f"border: 1px solid {DARK['accent3']}; border-radius: 10px;"
            f"padding: 2px 10px; font-size: 12px;"
        )
        hdr_row.addWidget(hdr_lbl)
        hdr_row.addWidget(self.count_badge)
        hdr_row.addStretch()
        lay.addLayout(hdr_row)

        sub = QLabel("Manage the PDF papers to be processed by the pipeline")
        sub.setStyleSheet(f"color: {DARK['text_dim']}; font-size: 13px;")
        lay.addWidget(sub)

        # ── Toolbar
        tool_row = QHBoxLayout()
        tool_row.setSpacing(8)

        btn_add = QPushButton("➕  Add Papers")
        btn_add.setFixedHeight(36)
        btn_add.clicked.connect(self._add_papers)

        btn_remove = QPushButton("🗑  Remove Selected")
        btn_remove.setObjectName("danger_btn")
        btn_remove.setFixedHeight(36)
        btn_remove.clicked.connect(self._remove_selected)

        btn_open_dir = QPushButton("📂  Open Folder")
        btn_open_dir.setFixedHeight(36)
        btn_open_dir.clicked.connect(self._open_folder)

        btn_refresh = QPushButton("🔄  Refresh")
        btn_refresh.setFixedHeight(36)
        btn_refresh.clicked.connect(self.refresh)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍  Filter papers…")
        self.search_box.setFixedHeight(36)
        self.search_box.textChanged.connect(self._filter)

        for w in (btn_add, btn_remove, btn_open_dir, btn_refresh):
            tool_row.addWidget(w)
        tool_row.addStretch()
        tool_row.addWidget(self.search_box)
        lay.addLayout(tool_row)

        # ── Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Filename", "Size", "Status", "Artifacts"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().hide()
        lay.addWidget(self.table)

        # ── drop hint
        hint = QLabel("⬆  Drag and drop PDF files anywhere to add them")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(f"color: {DARK['text_muted']}; font-size: 12px; padding: 6px;")
        lay.addWidget(hint)

        self.setAcceptDrops(True)
        self.refresh()

    def refresh(self):
        self.table.setRowCount(0)
        pdfs = sorted(self.papers_dir.glob("*.pdf"))
        self.count_badge.setText(f"{len(pdfs)} paper{'s' if len(pdfs) != 1 else ''}")

        for pdf in pdfs:
            self._add_table_row(pdf)

    def _add_table_row(self, pdf: Path):
        row = self.table.rowCount()
        self.table.insertRow(row)

        self.table.setItem(row, 0, QTableWidgetItem(pdf.name))

        size_kb = pdf.stat().st_size / 1024
        size_str = f"{size_kb:.0f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
        self.table.setItem(row, 1, QTableWidgetItem(size_str))

        # Artifact status
        reader_f = Path(f"artifacts/reader/{pdf.stem}.json")
        extracted_f = Path(f"artifacts/extracted/{pdf.stem}.json")
        critic_f = Path(f"artifacts/critic/{pdf.stem}.json")

        has_reader = reader_f.exists()
        has_ext = extracted_f.exists()
        has_critic = critic_f.exists()

        if has_reader and has_ext and has_critic:
            status_item = QTableWidgetItem("✅ Fully processed")
            status_item.setForeground(QColor(DARK['success']))
        elif has_reader:
            status_item = QTableWidgetItem("⏳ Partially processed")
            status_item.setForeground(QColor(DARK['warning']))
        else:
            status_item = QTableWidgetItem("⬜ Not processed")
            status_item.setForeground(QColor(DARK['text_dim']))

        self.table.setItem(row, 2, status_item)

        arts = []
        if has_reader:   arts.append("reader")
        if has_ext:      arts.append("extractor")
        if has_critic:   arts.append("critic")
        arts_item = QTableWidgetItem(", ".join(arts) if arts else "none")
        arts_item.setForeground(QColor(DARK['text_muted']))
        self.table.setItem(row, 3, arts_item)

    def _add_papers(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select PDF papers", "", "PDF files (*.pdf)"
        )
        for f in files:
            dest = self.papers_dir / Path(f).name
            if not dest.exists():
                shutil.copy2(f, dest)
        self.refresh()

    def _remove_selected(self):
        rows = list(set(idx.row() for idx in self.table.selectedIndexes()))
        if not rows:
            return
        names = [self.table.item(r, 0).text() for r in rows]
        reply = QMessageBox.question(
            self, "Remove Papers",
            f"Remove {len(names)} paper(s) from the folder?\n\n" + "\n".join(f"• {n}" for n in names[:10]),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            for name in names:
                (self.papers_dir / name).unlink(missing_ok=True)
            self.refresh()

    def _open_folder(self):
        path = str(self.papers_dir.absolute())
        if sys.platform == "win32":
            os.startfile(path)
        else:
            os.system(f"xdg-open '{path}'")

    def _filter(self, text: str):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            self.table.setRowHidden(row, text.lower() not in item.text().lower())

    # drag-and-drop
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        added = 0
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.suffix.lower() == ".pdf":
                dest = self.papers_dir / path.name
                if not dest.exists():
                    shutil.copy2(path, dest)
                    added += 1
        if added:
            self.refresh()


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: RESEARCH THEME
# ─────────────────────────────────────────────────────────────────────────────

class DynamicListEditor(QWidget):
    """Editable list of strings."""

    def __init__(self, placeholder: str = "Enter item…", parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self.list_widget = QListWidget()
        self.list_widget.setFixedHeight(130)

        btn_row = QHBoxLayout()
        self.entry = QLineEdit()
        self.entry.setPlaceholderText(placeholder)
        self.entry.setFixedHeight(32)
        self.entry.returnPressed.connect(self._add)

        btn_add = QPushButton("+ Add")
        btn_add.setFixedSize(70, 32)
        btn_add.clicked.connect(self._add)

        btn_del = QPushButton("Remove")
        btn_del.setFixedSize(70, 32)
        btn_del.setObjectName("danger_btn")
        btn_del.clicked.connect(self._remove)

        btn_row.addWidget(self.entry)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_del)

        lay.addWidget(self.list_widget)
        lay.addLayout(btn_row)

    def _add(self):
        text = self.entry.text().strip()
        if text:
            self.list_widget.addItem(text)
            self.entry.clear()

    def _remove(self):
        for item in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(item))

    def get_items(self) -> list[str]:
        return [self.list_widget.item(i).text() for i in range(self.list_widget.count())]

    def set_items(self, items: list[str]):
        self.list_widget.clear()
        for it in items:
            self.list_widget.addItem(it)


class ThemePage(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self._json_path = Path("theme_input.json")

        container = QWidget()
        self.setWidget(container)
        lay = QVBoxLayout(container)
        lay.setContentsMargins(28, 24, 28, 28)
        lay.setSpacing(18)

        # Header
        hdr_row = QHBoxLayout()
        hdr_lbl = QLabel("Research Theme")
        hdr_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))
        hdr_lbl.setStyleSheet(f"color: {DARK['text']};")

        btn_save = QPushButton("💾  Save Theme")
        btn_save.setObjectName("accent_btn")
        btn_save.setFixedHeight(38)
        btn_save.clicked.connect(self._save)

        hdr_row.addWidget(hdr_lbl)
        hdr_row.addStretch()
        hdr_row.addWidget(btn_save)
        lay.addLayout(hdr_row)

        sub = QLabel("Define the scope and goals of your literature review — saved to theme_input.json")
        sub.setStyleSheet(f"color: {DARK['text_dim']}; font-size: 13px;")
        lay.addWidget(sub)

        # ── Title
        g1 = QGroupBox("Research Title")
        g1_lay = QVBoxLayout(g1)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("e.g. Analyze the Multimodal Impact of Textual Transcription Errors")
        self.title_edit.setFixedHeight(38)
        g1_lay.addWidget(self.title_edit)
        lay.addWidget(g1)

        # ── Research Goals
        g2 = QGroupBox("Research Goals")
        g2_lay = QVBoxLayout(g2)
        hint2 = QLabel("Each goal guides what the agents look for in each paper")
        hint2.setStyleSheet(f"color: {DARK['text_dim']}; font-size: 12px;")
        self.goals_editor = DynamicListEditor("Add a research goal…")
        g2_lay.addWidget(hint2)
        g2_lay.addWidget(self.goals_editor)
        lay.addWidget(g2)

        # ── Constraints
        g3 = QGroupBox("Specific Constraints")
        g3_lay = QVBoxLayout(g3)
        hint3 = QLabel("Papers must satisfy these conditions to be included")
        hint3.setStyleSheet(f"color: {DARK['text_dim']}; font-size: 12px;")
        self.constraints_editor = DynamicListEditor("Add a constraint…")
        g3_lay.addWidget(hint3)
        g3_lay.addWidget(self.constraints_editor)
        lay.addWidget(g3)

        # ── Exclusions
        g4 = QGroupBox("What to Exclude")
        g4_lay = QVBoxLayout(g4)
        hint4 = QLabel("Topics or paper types to filter out")
        hint4.setStyleSheet(f"color: {DARK['text_dim']}; font-size: 12px;")
        self.exclude_editor = DynamicListEditor("Add an exclusion rule…")
        g4_lay.addWidget(hint4)
        g4_lay.addWidget(self.exclude_editor)
        lay.addWidget(g4)

        # ── Raw JSON view
        g5 = QGroupBox("Raw JSON Preview  (read-only)")
        g5_lay = QVBoxLayout(g5)
        self.raw_view = QPlainTextEdit()
        self.raw_view.setReadOnly(True)
        self.raw_view.setFixedHeight(160)
        self.raw_view.setFont(QFont("Cascadia Code, Consolas, monospace", 11))
        self.raw_view.setStyleSheet(f"background: {DARK['bg']}; color: {DARK['text_dim']};")
        g5_lay.addWidget(self.raw_view)
        lay.addWidget(g5)

        lay.addStretch()
        self._load()

    def _load(self):
        if not self._json_path.exists():
            return
        try:
            data = json.loads(self._json_path.read_text(encoding="utf-8"))
            self.title_edit.setText(data.get("title", ""))
            self.goals_editor.set_items(data.get("research_goals", []))
            self.constraints_editor.set_items(data.get("specific_constraints", []))
            self.exclude_editor.set_items(data.get("what_to_exclude", []))
            self._update_raw(data)
        except Exception:
            pass

    def _save(self):
        data = {
            "title": self.title_edit.text().strip(),
            "research_goals": self.goals_editor.get_items(),
            "specific_constraints": self.constraints_editor.get_items(),
            "what_to_exclude": self.exclude_editor.get_items(),
        }
        self._json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        self._update_raw(data)
        QMessageBox.information(self, "Saved", "theme_input.json saved successfully.")

    def _update_raw(self, data: dict):
        self.raw_view.setPlainText(json.dumps(data, indent=2, ensure_ascii=False))


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

class ConfigPage(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self._env_path = Path(".env")

        container = QWidget()
        self.setWidget(container)
        lay = QVBoxLayout(container)
        lay.setContentsMargins(28, 24, 28, 28)
        lay.setSpacing(20)

        # Header
        hdr_row = QHBoxLayout()
        hdr_lbl = QLabel("Configuration")
        hdr_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))
        hdr_lbl.setStyleSheet(f"color: {DARK['text']};")

        btn_save = QPushButton("💾  Save Config")
        btn_save.setObjectName("accent_btn")
        btn_save.setFixedHeight(38)
        btn_save.clicked.connect(self._save)

        hdr_row.addWidget(hdr_lbl)
        hdr_row.addStretch()
        hdr_row.addWidget(btn_save)
        lay.addLayout(hdr_row)

        sub = QLabel("Settings are persisted to your <code>.env</code> file")
        sub.setStyleSheet(f"color: {DARK['text_dim']}; font-size: 13px;")
        lay.addWidget(sub)

        # ── LLM Configuration
        llm_box = QGroupBox("LLM Provider")
        llm_form = QFormLayout(llm_box)
        llm_form.setSpacing(10)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["qwen", "claude", "gemini", "gpt", "glm", "kilo"])
        self.provider_combo.setFixedHeight(34)

        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("Leave empty for provider default (e.g. qwen-oauth)")
        self.model_edit.setFixedHeight(34)

        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 1.0)
        self.temp_spin.setSingleStep(0.05)
        self.temp_spin.setDecimals(2)
        self.temp_spin.setFixedHeight(34)
        self.temp_spin.setFixedWidth(160)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(30, 1800)
        self.timeout_spin.setSuffix("  seconds")
        self.timeout_spin.setFixedHeight(34)
        self.timeout_spin.setFixedWidth(180)

        self.citation_combo = QComboBox()
        self.citation_combo.addItems(["ieee", "apa", "chicago", "harvard"])
        self.citation_combo.setFixedHeight(34)

        llm_form.addRow("Provider:", self.provider_combo)
        llm_form.addRow("Model:", self.model_edit)
        llm_form.addRow("Temperature:", self.temp_spin)
        llm_form.addRow("Timeout:", self.timeout_spin)
        llm_form.addRow("Citation Style:", self.citation_combo)
        lay.addWidget(llm_box)

        # ── Pipeline settings
        pipe_box = QGroupBox("Pipeline Settings")
        pipe_form = QFormLayout(pipe_box)
        pipe_form.setSpacing(10)

        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(1, 32)
        self.workers_spin.setSuffix("  workers")
        self.workers_spin.setFixedHeight(34)
        self.workers_spin.setFixedWidth(180)

        self.max_chars_spin = QSpinBox()
        self.max_chars_spin.setRange(10000, 500000)
        self.max_chars_spin.setSingleStep(10000)
        self.max_chars_spin.setSuffix("  chars")
        self.max_chars_spin.setFixedHeight(34)
        self.max_chars_spin.setFixedWidth(200)

        self.clusters_edit = QLineEdit()
        self.clusters_edit.setPlaceholderText("auto  (or an integer like 6)")
        self.clusters_edit.setFixedHeight(34)
        self.clusters_edit.setFixedWidth(180)

        pipe_form.addRow("Max Workers:", self.workers_spin)
        pipe_form.addRow("Max PDF chars:", self.max_chars_spin)
        pipe_form.addRow("Cluster count:", self.clusters_edit)
        lay.addWidget(pipe_box)

        # ── Semantic PDF
        pdf_box = QGroupBox("Semantic PDF Parsing")
        pdf_form = QFormLayout(pdf_box)
        pdf_form.setSpacing(10)

        self.semantic_pdf_chk = QCheckBox("Enable semantic parsing (sections / figures / tables)")
        self.extract_images_chk = QCheckBox("Extract and store figure images (needed for vision LLM)")
        self.include_figures_chk = QCheckBox("Include figure captions in LLM input")
        self.include_tables_chk = QCheckBox("Include tables (as markdown) in LLM input")

        for chk in (self.semantic_pdf_chk, self.extract_images_chk,
                    self.include_figures_chk, self.include_tables_chk):
            pdf_form.addRow(chk)

        lay.addWidget(pdf_box)
        lay.addStretch()

        self._load()

    def _load(self):
        env = self._read_env()

        _set_combo(self.provider_combo, env.get("LLM_PROVIDER", "qwen"))
        self.model_edit.setText(env.get("LLM_MODEL", ""))
        self.temp_spin.setValue(float(env.get("LLM_TEMPERATURE", "0.3")))
        self.timeout_spin.setValue(int(env.get("LLM_TIMEOUT", "120")))
        _set_combo(self.citation_combo, env.get("CITATION_STYLE", "ieee"))
        self.workers_spin.setValue(int(env.get("MAX_WORKERS", "10")))
        self.max_chars_spin.setValue(int(env.get("MAX_PDF_CHARS", "50000")))
        self.clusters_edit.setText(env.get("CLUSTER_COUNT", "auto"))

        self.semantic_pdf_chk.setChecked(env.get("USE_SEMANTIC_PDF", "true").lower() == "true")
        self.extract_images_chk.setChecked(env.get("EXTRACT_PDF_IMAGES", "false").lower() == "true")
        self.include_figures_chk.setChecked(env.get("INCLUDE_FIGURES_IN_TEXT", "true").lower() == "true")
        self.include_tables_chk.setChecked(env.get("INCLUDE_TABLES_IN_TEXT", "true").lower() == "true")

    def _save(self):
        env = self._read_env()  # Keep any keys we don't manage

        env["LLM_PROVIDER"] = self.provider_combo.currentText()
        env["LLM_MODEL"] = self.model_edit.text().strip()
        env["LLM_TEMPERATURE"] = str(self.temp_spin.value())
        env["LLM_TIMEOUT"] = str(self.timeout_spin.value())
        env["CITATION_STYLE"] = self.citation_combo.currentText()
        env["MAX_WORKERS"] = str(self.workers_spin.value())
        env["MAX_PDF_CHARS"] = str(self.max_chars_spin.value())
        env["CLUSTER_COUNT"] = self.clusters_edit.text().strip() or "auto"
        env["USE_SEMANTIC_PDF"] = "true" if self.semantic_pdf_chk.isChecked() else "false"
        env["EXTRACT_PDF_IMAGES"] = "true" if self.extract_images_chk.isChecked() else "false"
        env["INCLUDE_FIGURES_IN_TEXT"] = "true" if self.include_figures_chk.isChecked() else "false"
        env["INCLUDE_TABLES_IN_TEXT"] = "true" if self.include_tables_chk.isChecked() else "false"

        self._write_env(env)
        QMessageBox.information(self, "Saved", ".env file updated successfully.")

    def _read_env(self) -> dict:
        env = {}
        if not self._env_path.exists():
            return env
        for line in self._env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
        return env

    def _write_env(self, env: dict):
        lines = []
        existing = {}
        comments = {}  # key -> comment block preceding it

        if self._env_path.exists():
            raw_lines = self._env_path.read_text(encoding="utf-8").splitlines()
            pending_comments = []
            for line in raw_lines:
                stripped = line.strip()
                if stripped.startswith("#") or stripped == "":
                    pending_comments.append(line)
                elif "=" in stripped:
                    k = stripped.split("=")[0].strip()
                    existing[k] = line
                    if pending_comments:
                        comments[k] = pending_comments.copy()
                    pending_comments = []

        written = set()
        if self._env_path.exists():
            raw_lines = self._env_path.read_text(encoding="utf-8").splitlines()
            for line in raw_lines:
                stripped = line.strip()
                if stripped.startswith("#") or stripped == "":
                    lines.append(line)
                elif "=" in stripped:
                    k = stripped.split("=")[0].strip()
                    if k in env:
                        lines.append(f"{k}={env[k]}")
                        written.add(k)
                    else:
                        lines.append(line)

        # Add new keys not in original file
        for k, v in env.items():
            if k not in written:
                lines.append(f"{k}={v}")

        self._env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _set_combo(combo: QComboBox, value: str):
    idx = combo.findText(value, Qt.MatchFixedString)
    if idx >= 0:
        combo.setCurrentIndex(idx)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: RUN PIPELINE  (the core page)
# ─────────────────────────────────────────────────────────────────────────────

class StageIndicator(QWidget):
    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(52)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(10)

        self.dot = QLabel("⬤")
        self.dot.setFixedWidth(16)
        self.dot.setStyleSheet(f"color: {DARK['text_muted']}; font-size: 10px;")
        self.dot.setAlignment(Qt.AlignCenter)

        self.name_lbl = QLabel(name)
        self.name_lbl.setFont(QFont("Segoe UI", 11, QFont.Medium))
        self.name_lbl.setStyleSheet(f"color: {DARK['text_dim']};")

        self.bar = QProgressBar()
        self.bar.setRange(0, 0)
        self.bar.setFixedHeight(4)
        self.bar.setVisible(False)

        v = QVBoxLayout()
        v.setSpacing(3)
        v.addWidget(self.name_lbl)
        v.addWidget(self.bar)

        lay.addWidget(self.dot)
        lay.addLayout(v)

    def set_state(self, state: str):
        """state: idle | running | done | error | skip"""
        colors = {
            "idle":    (DARK['text_muted'],   DARK['text_dim'],  False),
            "running": (DARK['running'],       DARK['text'],      True),
            "done":    (DARK['done'],          DARK['text'],      False),
            "error":   (DARK['error'],         DARK['error'],     False),
            "skip":    (DARK['skip'],          DARK['text_muted'], False),
        }
        dot_c, name_c, show_bar = colors.get(state, colors["idle"])
        self.dot.setStyleSheet(f"color: {dot_c}; font-size: 10px;")
        self.name_lbl.setStyleSheet(f"color: {name_c};")
        self.bar.setVisible(show_bar)


class RunPage(QWidget):
    stage_update = pyqtSignal(str, str)   # (stage_key, status)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process: QProcess | None = None
        self._running = False

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(28, 24, 28, 28)
        main_lay.setSpacing(16)

        # ── Header
        hdr_lbl = QLabel("Run Pipeline")
        hdr_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))
        hdr_lbl.setStyleSheet(f"color: {DARK['text']};")
        main_lay.addWidget(hdr_lbl)

        # ── Options row
        opt_frame = QFrame()
        opt_frame.setObjectName("card")
        opt_lay = QHBoxLayout(opt_frame)
        opt_lay.setContentsMargins(18, 12, 18, 12)
        opt_lay.setSpacing(24)

        # Max repair
        r1 = QVBoxLayout()
        r1.addWidget(_label("Max Repair Iterations", dim=True))
        self.repair_spin = QSpinBox()
        self.repair_spin.setRange(0, 10)
        self.repair_spin.setValue(3)
        self.repair_spin.setFixedSize(90, 32)
        r1.addWidget(self.repair_spin)

        # Output format
        r2 = QVBoxLayout()
        r2.addWidget(_label("Output Format", dim=True))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["latex", "markdown", "docx", "all"])
        self.format_combo.setFixedSize(130, 32)
        r2.addWidget(self.format_combo)

        # Clean run
        r3 = QVBoxLayout()
        r3.addWidget(_label("Options", dim=True))
        self.clean_chk = QCheckBox("Clear cache before run")
        r3.addWidget(self.clean_chk)

        opt_lay.addLayout(r1)
        opt_lay.addLayout(r2)
        opt_lay.addLayout(r3)
        opt_lay.addStretch()
        main_lay.addWidget(opt_frame)

        # ── Progress + Log  (horizontal splitter)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        # Left: pipeline flow
        left_frame = QFrame()
        left_frame.setObjectName("card")
        left_frame.setMinimumWidth(220)
        left_frame.setMaximumWidth(260)
        left_lay = QVBoxLayout(left_frame)
        left_lay.setContentsMargins(10, 12, 10, 12)
        left_lay.setSpacing(2)

        flow_hdr = _label("Pipeline Flow", dim=True, bold=True)
        left_lay.addWidget(flow_hdr)
        left_lay.addSpacing(6)

        self._stage_widgets: dict[str, StageIndicator] = {}
        for key, name, _ in PIPELINE_STAGES:
            si = StageIndicator(name)
            left_lay.addWidget(si)
            self._stage_widgets[key] = si
        left_lay.addStretch()

        # Right: log output
        right_frame = QFrame()
        right_frame.setObjectName("card")
        right_lay = QVBoxLayout(right_frame)
        right_lay.setContentsMargins(12, 12, 12, 12)
        right_lay.setSpacing(8)

        log_hdr_row = QHBoxLayout()
        log_hdr_row.addWidget(_label("Live Output", dim=True, bold=True))
        log_hdr_row.addStretch()

        btn_clear_log = QPushButton("Clear")
        btn_clear_log.setObjectName("icon_btn")
        btn_clear_log.setFixedHeight(26)
        btn_clear_log.clicked.connect(lambda: self.log_box.clear())

        btn_copy_log = QPushButton("Copy")
        btn_copy_log.setObjectName("icon_btn")
        btn_copy_log.setFixedHeight(26)
        btn_copy_log.clicked.connect(lambda: QApplication.clipboard().setText(self.log_box.toPlainText()))

        log_hdr_row.addWidget(btn_clear_log)
        log_hdr_row.addWidget(btn_copy_log)
        right_lay.addLayout(log_hdr_row)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setFont(QFont("Cascadia Code, Consolas, Courier New", 11))
        self.log_box.setStyleSheet(
            f"background: {DARK['bg']}; color: {DARK['text_dim']}; "
            f"border: none; border-radius: 6px;"
        )
        right_lay.addWidget(self.log_box)

        splitter.addWidget(left_frame)
        splitter.addWidget(right_frame)
        splitter.setStretchFactor(1, 1)
        main_lay.addWidget(splitter, 1)

        # ── Bottom control strip
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(10)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, len(PIPELINE_STAGES))
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(10)

        self.status_lbl = QLabel("Idle  –  configure settings then press Run")
        self.status_lbl.setStyleSheet(f"color: {DARK['text_dim']}; font-size: 12px;")

        self.run_btn = QPushButton("▶  Run Pipeline")
        self.run_btn.setObjectName("accent_btn")
        self.run_btn.setFixedSize(160, 42)
        self.run_btn.clicked.connect(self._toggle_run)

        self.stop_btn = QPushButton("⏹  Stop")
        self.stop_btn.setObjectName("danger_btn")
        self.stop_btn.setFixedSize(100, 42)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop)

        v_status = QVBoxLayout()
        v_status.setSpacing(4)
        v_status.addWidget(self.progress_bar)
        v_status.addWidget(self.status_lbl)

        ctrl_row.addLayout(v_status)
        ctrl_row.addStretch()
        ctrl_row.addWidget(self.stop_btn)
        ctrl_row.addWidget(self.run_btn)
        main_lay.addLayout(ctrl_row)

        self.stage_update.connect(self._apply_stage_update)

    # ── stage helper
    def _apply_stage_update(self, key: str, state: str):
        if key in self._stage_widgets:
            self._stage_widgets[key].set_state(state)

    # ── run / stop
    def _toggle_run(self):
        if self._running:
            self._stop()
        else:
            self._start()

    def _start(self):
        # Reset stage indicators
        for si in self._stage_widgets.values():
            si.set_state("idle")
        self.progress_bar.setValue(0)
        self.log_box.clear()

        # Build command
        args = []
        if self.clean_chk.isChecked():
            args.append("--clean")
        args += ["--max-repair", str(self.repair_spin.value())]
        args += ["--format", self.format_combo.currentText()]

        # Find python
        python_exec = sys.executable

        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._read_output)
        self._process.finished.connect(self._on_finished)
        self._process.setWorkingDirectory(str(Path.cwd()))
        self._process.start(python_exec, ["soa_cli.py"] + args)

        self._running = True
        self._stage_done_count = 0
        self.run_btn.setText("▶  Running…")
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._set_status("⚡ Pipeline running…", DARK['running'])

    def _stop(self):
        if self._process and self._process.state() != QProcess.NotRunning:
            self._process.kill()
        self._running = False
        self.run_btn.setText("▶  Run Pipeline")
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._set_status("⏹  Stopped by user", DARK['error'])

    def _on_finished(self, exit_code: int, exit_status):
        self._running = False
        self.run_btn.setText("▶  Run Pipeline")
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        if exit_code == 0:
            self._set_status("✅  Pipeline complete!", DARK['success'])
            self.progress_bar.setValue(len(PIPELINE_STAGES))
        else:
            self._set_status(f"❌  Exited with code {exit_code}", DARK['error'])

    # ── output parsing
    _STAGE_PATTERNS = {
        "[Node: Theme Builder]":   ("theme_builder", "running"),
        "[Node: Reader Map]":      ("reader",        "running"),
        "[Node: Extractor Map]":   ("extractor",     "running"),
        "[Node: Critic Map]":      ("critic",        "running"),
        "[Node: Vectorize]":       ("vectorize",     "running"),
        "[Node: Cluster]":         ("cluster",       "running"),
        "[Node: Synthesis]":       ("synthesis",     "running"),
        "[Node: Writer]":          ("writer",        "running"),
        "[Node: Verifier]":        ("verifier",      "running"),
        "[Node: Repair]":          ("repair",        "running"),
        # done markers
        "thematic_contract":       ("theme_builder", "done"),
        "reader_complete":         ("reader",        "done"),
        "extractor_complete":      ("extractor",     "done"),
        "critic_complete":         ("critic",        "done"),
        "vectorize_complete":      ("vectorize",     "done"),
        "cluster_complete":        ("cluster",       "done"),
        "synthesis_complete":      ("synthesis",     "done"),
        "writer_complete":         ("writer",        "done"),
        "verifier_complete":       ("verifier",      "done"),
        "repair_complete":         ("repair",        "done"),
        "PIPELINE COMPLETE":       None,
    }

    def _read_output(self):
        raw = bytes(self._process.readAllStandardOutput())
        try:
            text = raw.decode("utf-8", errors="replace")
        except Exception:
            text = str(raw)

        for line in text.splitlines():
            self._append_log(line)
            self._parse_line(line)

    def _append_log(self, line: str):
        cursor = self.log_box.textCursor()
        cursor.movePosition(QTextCursor.End)

        fmt = QTextCharFormat()
        line_lower = line.lower()
        if "error" in line_lower or "✗" in line or "failed" in line_lower:
            fmt.setForeground(QColor(DARK['error']))
        elif "✓" in line or "done" in line_lower or "complete" in line_lower:
            fmt.setForeground(QColor(DARK['success']))
        elif "warning" in line_lower or "⚠" in line:
            fmt.setForeground(QColor(DARK['warning']))
        elif line.startswith("[Node:") or line.startswith("="):
            fmt.setForeground(QColor(DARK['accent2']))
            fmt.setFontWeight(QFont.Bold)
        else:
            fmt.setForeground(QColor(DARK['text_dim']))

        cursor.insertText(line + "\n", fmt)
        self.log_box.setTextCursor(cursor)
        self.log_box.ensureCursorVisible()

    def _parse_line(self, line: str):
        for pattern, action in self._STAGE_PATTERNS.items():
            if pattern in line:
                if action:
                    key, state = action
                    self.stage_update.emit(key, state)
                    if state == "done":
                        self._stage_done_count = getattr(self, "_stage_done_count", 0) + 1
                        self.progress_bar.setValue(self._stage_done_count)
                else:
                    # pipeline complete
                    for k in self._stage_widgets:
                        if self._stage_widgets[k].dot.styleSheet().find(DARK['text_muted']) == -1:
                            pass  # already set
                    self._stage_done_count = len(PIPELINE_STAGES)
                    self.progress_bar.setValue(len(PIPELINE_STAGES))
                break

    def _set_status(self, msg: str, color: str = DARK['text_dim']):
        self.status_lbl.setText(msg)
        self.status_lbl.setStyleSheet(f"color: {color}; font-size: 12px;")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: RESULTS
# ─────────────────────────────────────────────────────────────────────────────

class ResultsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 28)
        lay.setSpacing(16)

        # Header
        hdr_row = QHBoxLayout()
        hdr_lbl = QLabel("Results & Output")
        hdr_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))
        hdr_lbl.setStyleSheet(f"color: {DARK['text']};")

        btn_refresh = QPushButton("🔄  Refresh")
        btn_refresh.setFixedHeight(36)
        btn_refresh.clicked.connect(self._reload)

        hdr_row.addWidget(hdr_lbl)
        hdr_row.addStretch()
        hdr_row.addWidget(btn_refresh)
        lay.addLayout(hdr_row)

        sub = QLabel("Browse, preview and open generated output files")
        sub.setStyleSheet(f"color: {DARK['text_dim']}; font-size: 13px;")
        lay.addWidget(sub)

        # ── Splitter: file list  |  preview
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        # Left: file list
        left = QFrame()
        left.setObjectName("card")
        left.setMaximumWidth(280)
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(10, 10, 10, 10)
        left_lay.setSpacing(6)

        left_lay.addWidget(_label("Output Files", dim=True, bold=True))

        self.file_list = QListWidget()
        self.file_list.currentItemChanged.connect(self._preview_file)
        left_lay.addWidget(self.file_list)

        btn_open = QPushButton("📂  Open in System")
        btn_open.setFixedHeight(34)
        btn_open.clicked.connect(self._open_current)
        left_lay.addWidget(btn_open)

        btn_copy_path = QPushButton("📋  Copy Path")
        btn_copy_path.setFixedHeight(34)
        btn_copy_path.clicked.connect(self._copy_path)
        left_lay.addWidget(btn_copy_path)

        # Right: preview
        right = QFrame()
        right.setObjectName("card")
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(12, 12, 12, 12)
        right_lay.setSpacing(8)

        right_top = QHBoxLayout()
        self.preview_title = _label("No file selected", dim=True, bold=True)
        right_top.addWidget(self.preview_title)
        right_top.addStretch()
        right_lay.addLayout(right_top)

        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("Cascadia Code, Consolas, Courier New", 11))
        self.preview.setStyleSheet(
            f"background: {DARK['bg']}; color: {DARK['text_dim']}; border: none; border-radius: 6px;"
        )
        right_lay.addWidget(self.preview)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        lay.addWidget(splitter, 1)

        self._reload()

    def _reload(self):
        self.file_list.clear()
        candidates = [
            "STATE_OF_THE_ART.tex",
            "STATE_OF_THE_ART.md",
            "STATE_OF_THE_ART.docx",
            "THEMATIC_CONTRACT.json",
        ]
        # Also scan artifacts/soa/
        for p in Path("artifacts/soa").glob("*") if Path("artifacts/soa").exists() else []:
            candidates.append(str(p))

        for c in candidates:
            p = Path(c)
            if p.exists():
                item = QListWidgetItem(p.name)
                item.setData(Qt.UserRole, str(p.absolute()))
                suffix_icons = {".tex": "📄", ".md": "📝", ".json": "🔧", ".docx": "📘", ".pdf": "📕"}
                icon = suffix_icons.get(p.suffix, "📄")
                item.setText(f"{icon}  {p.name}")
                self.file_list.addItem(item)

    def _preview_file(self, current: QListWidgetItem | None, _prev):
        if current is None:
            return
        path = Path(current.data(Qt.UserRole))
        self.preview_title.setText(path.name)

        if path.suffix in (".tex", ".md", ".txt", ".json"):
            try:
                content = path.read_text(encoding="utf-8")
                # Show first 4000 chars to keep UI snappy
                if len(content) > 8000:
                    content = content[:8000] + "\n\n… (truncated for preview — open full file to read)"
                self.preview.setPlainText(content)
            except Exception as e:
                self.preview.setPlainText(f"[Could not read file: {e}]")
        elif path.suffix == ".docx":
            self.preview.setPlainText("Binary Word document — open with a compatible application.")
        else:
            self.preview.setPlainText(f"[Binary file: {path.suffix}]")

    def _open_current(self):
        item = self.file_list.currentItem()
        if not item:
            return
        path = item.data(Qt.UserRole)
        if sys.platform == "win32":
            os.startfile(path)
        else:
            os.system(f"xdg-open '{path}'")

    def _copy_path(self):
        item = self.file_list.currentItem()
        if item:
            QApplication.clipboard().setText(item.data(Qt.UserRole))


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _label(text: str, dim: bool = False, bold: bool = False) -> QLabel:
    lbl = QLabel(text)
    color = DARK['text_dim'] if dim else DARK['text']
    weight = " font-weight: bold;" if bold else ""
    lbl.setStyleSheet(f"color: {color}; font-size: 12px;{weight}")
    return lbl


# ─────────────────────────────────────────────────────────────────────────────
# MAIN WINDOW
# ─────────────────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SOA-CLI  ·  State of the Art Generator")
        self.resize(1280, 800)
        self.setMinimumSize(960, 620)

        # ── Central layout
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self._switch_page)
        root.addWidget(self.sidebar)

        # Vertical separator
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(f"background: {DARK['border']}; max-width: 1px;")
        root.addWidget(sep)

        # Page stack
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        # Build pages
        self.dashboard_page = DashboardPage()
        self.papers_page = PapersPage()
        self.theme_page = ThemePage()
        self.config_page = ConfigPage()
        self.run_page = RunPage()
        self.results_page = ResultsPage()

        for page in (
            self.dashboard_page,
            self.papers_page,
            self.theme_page,
            self.config_page,
            self.run_page,
            self.results_page,
        ):
            self.stack.addWidget(page)

        # Wire "go to run" from dashboard
        self.dashboard_page.go_to_run.connect(lambda: self._switch_page(4))
        # Wire stage updates from run page to dashboard
        self.run_page.stage_update.connect(
            lambda k, s: self.dashboard_page.update_stage(k, s)
        )
        # Refresh dashboard on page switch
        self._setup_refresh_timer()

        # ── Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("SOA-CLI ready")

        # ── Menu bar
        self._build_menu()

        self._switch_page(0)

    def _switch_page(self, idx: int):
        # Block sidebar signals to prevent page_changed → _switch_page recursion
        self.sidebar.blockSignals(True)
        self.sidebar._select(idx)
        self.sidebar.blockSignals(False)
        self.stack.setCurrentIndex(idx)
        # Refresh pages when switching
        if idx == 0:
            self.dashboard_page.refresh()
        elif idx == 1:
            self.papers_page.refresh()
        elif idx == 5:
            self.results_page._reload()

    def _setup_refresh_timer(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(lambda: (
            self.dashboard_page.refresh()
            if self.stack.currentIndex() == 0 else None
        ))
        self._timer.start(5000)

    def _build_menu(self):
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("File")
        act_papers = QAction("Open Papers Folder", self)
        act_papers.triggered.connect(self.papers_page._open_folder)
        act_output = QAction("Open Output File", self)
        act_output.triggered.connect(self.dashboard_page._open_output)
        act_quit = QAction("Quit", self)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_papers)
        file_menu.addAction(act_output)
        file_menu.addSeparator()
        file_menu.addAction(act_quit)

        # Pipeline
        pipe_menu = mb.addMenu("Pipeline")
        act_run = QAction("Run Pipeline", self)
        act_run.triggered.connect(self.run_page._start)
        act_stop = QAction("Stop Pipeline", self)
        act_stop.triggered.connect(self.run_page._stop)
        act_clean = QAction("Clear Cache", self)
        act_clean.triggered.connect(self.dashboard_page._clear_cache)
        pipe_menu.addAction(act_run)
        pipe_menu.addAction(act_stop)
        pipe_menu.addSeparator()
        pipe_menu.addAction(act_clean)

        # Help
        help_menu = mb.addMenu("Help")
        act_readme = QAction("Open README", self)
        act_readme.triggered.connect(self._open_readme)
        act_about = QAction("About", self)
        act_about.triggered.connect(self._about)
        help_menu.addAction(act_readme)
        help_menu.addSeparator()
        help_menu.addAction(act_about)

    def _open_readme(self):
        readme = Path("README.md")
        if readme.exists():
            os.system(f"xdg-open '{readme.absolute()}'")

    def _about(self):
        QMessageBox.about(
            self,
            "About SOA-CLI",
            "<b>SOA-CLI</b><br>"
            "Multi-Agent State of the Art Generator<br><br>"
            "Powered by <b>LangGraph</b> &amp; <b>PyQt5</b><br>"
            "Pipeline: Theme → Reader → Extractor → Critic →<br>"
            "Vectorize → Cluster → Synthesis → Writer → Verifier<br><br>"
            "<small>Configuration: .env &nbsp;|&nbsp; Theme: theme_input.json</small>"
        )

    def closeEvent(self, event):
        if self.run_page._running:
            reply = QMessageBox.question(
                self, "Pipeline Running",
                "The pipeline is still running. Stop it and quit?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
            self.run_page._stop()
        event.accept()


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # Change working directory to project root
    os.chdir(Path(__file__).parent)

    # High-DPI support — MUST be set before QApplication is created
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("SOA-CLI")
    app.setOrganizationName("SOA")
    app.setStyleSheet(global_stylesheet())

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

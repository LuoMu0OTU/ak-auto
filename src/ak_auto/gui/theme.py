"""深色主题：统一设计令牌 + QSS（AGENTS.md 第 4 节）。"""
from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

# 设计令牌
TOKENS = {
    "bg": "#1e1f22",
    "surface": "#2b2d31",
    "surface_alt": "#34363c",
    "primary": "#4c8bf5",
    "primary_hover": "#5d98f7",
    "text": "#e6e6e6",
    "muted": "#9aa0a6",
    "border": "#3c3e45",
    "success": "#57ab5a",
    "danger": "#e5534b",
    "warning": "#d29922",
}

QSS = """
QWidget { background: %(bg)s; color: %(text)s; font-size: 13px; }
QMainWindow, QDialog { background: %(bg)s; }
QListWidget, QTreeWidget, QTableWidget, QTextEdit, QPlainTextEdit {
    background: %(surface)s; border: 1px solid %(border)s; border-radius: 6px;
}
QListWidget::item { padding: 8px 12px; border-radius: 6px; }
QListWidget::item:selected { background: %(primary)s; color: white; }
QPushButton {
    background: %(surface_alt)s; border: 1px solid %(border)s;
    border-radius: 6px; padding: 7px 16px;
}
QPushButton:hover { border-color: %(primary)s; }
QPushButton:disabled { color: %(muted)s; }
QPushButton#primary {
    background: %(primary)s; border: none; color: white; font-weight: 600;
}
QPushButton#primary:hover { background: %(primary_hover)s; }
QPushButton#danger { background: transparent; border: 1px solid %(danger)s; color: %(danger)s; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: %(surface)s; border: 1px solid %(border)s;
    border-radius: 6px; padding: 5px 8px;
}
QLabel#muted { color: %(muted)s; }
QLabel#title { font-size: 18px; font-weight: 700; }
QStatusBar { background: %(surface)s; }
QTabBar::tab { padding: 8px 18px; }
QTabBar::tab:selected { color: %(primary)s; border-bottom: 2px solid %(primary)s; }
QCheckBox, QRadioButton { spacing: 6px; }
QScrollBar:vertical { background: %(surface)s; width: 10px; }
QScrollBar::handle:vertical { background: %(border)s; border-radius: 5px; min-height: 24px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
""" % TOKENS


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(TOKENS["bg"]))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(TOKENS["text"]))
    pal.setColor(QPalette.ColorRole.Base, QColor(TOKENS["surface"]))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(TOKENS["surface_alt"]))
    pal.setColor(QPalette.ColorRole.Text, QColor(TOKENS["text"]))
    pal.setColor(QPalette.ColorRole.Button, QColor(TOKENS["surface_alt"]))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(TOKENS["text"]))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(TOKENS["primary"]))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(TOKENS["muted"]))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(TOKENS["surface"]))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor(TOKENS["text"]))
    app.setPalette(pal)

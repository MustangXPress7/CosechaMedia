"""Paleta central de temas de CosechaMedia.

Todos los colores de la app se definen aqui. Cada tema es un dict cuyas claves
se usan como placeholders @clave dentro de la plantilla QSS (_QSS_TEMPLATE).
Para cambiar el color de la app entera basta con editar una clave de la paleta.
"""

import os

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from app.core.utils import resource_path

_ORG = "Audiovisual Production"
_APP = "CosechaMedia"
_SETTINGS_KEY = "theme"

DEFAULT_THEME = "dark"

DARK = {
    "name": "Oscuro",
    "bg": "#0d1117",
    "bg_elevated": "#161b22",
    "bg_hover": "#21262d",
    "border": "#404851",
    "gridline": "#2c333c",
    "border_strong": "#484f58",
    "text": "#f0f6fc",
    "text_secondary": "#8b949e",
    "text_disabled": "#484f58",
    "accent": "#58a6ff",
    "accent_selection": "#1f6feb",
    "accent_pressed": "#0d419d",
    "on_accent": "#ffffff",
    "success": "#3fb950",
    "success_bg": "#238636",
    "success_hover": "#2ea043",
    "warning": "#d29922",
    "danger": "#f85149",
    "danger_bg": "#da3633",
    "wheat": "#d4a72c",
}

LIGHT = {
    "name": "Claro",
    "bg": "#ffffff",
    "bg_elevated": "#f6f8fa",
    "bg_hover": "#eaeef2",
    "border": "#8b8f94",
    "gridline": "#9c9fa1",
    "border_strong": "#6e7781",
    "text": "#1f2328",
    "text_secondary": "#59636e",
    "text_disabled": "#8c959f",
    "accent": "#0969da",
    "accent_selection": "#0969da",
    "accent_pressed": "#0550ae",
    "on_accent": "#ffffff",
    "success": "#2f9e55",
    "success_bg": "#3ab764",
    "success_hover": "#31a857",
    "warning": "#9a6700",
    "danger": "#cf222e",
    "danger_bg": "#d1242f",
    "wheat": "#b08a00",
}

THEMES = {"dark": DARK, "light": LIGHT}

_ACCENT_SETTINGS_KEY = "accent"
DEFAULT_ACCENT = "default"

# Proporcion del tinte de acento sobre el fondo del tema (0..1, baja opacidad).
ACCENT_TINT_RATIO = 0.15

ACCENTS = {
    "default": {"name": "Neutro", "color": None},
    "green": {"name": "Verde", "color": "#2ea043"},
    "blue": {"name": "Azul", "color": "#58a6ff"},
    "pink": {"name": "Rosa", "color": "#f778ba"},
    "purple": {"name": "Morado", "color": "#a371f7"},
    "amber": {"name": "Ámbar", "color": "#d29922"},
}

_QSS_TEMPLATE = """
QMainWindow {
    background-color: @bg_tinted;
}

QWidget {
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    color: @text;
    font-size: 12px;
}

QCalendarWidget {
    font-size: 13px;
}

QLabel {
    color: @text;
    font-size: 11px;
}

QPushButton {
    background-color: @bg_hover;
    border: 1px solid @border;
    padding: 4px 10px;
    border-radius: 4px;
    color: @text;
    font-size: 11px;
    min-height: 16px;
}

QPushButton:hover {
    background-color: @border;
    border-color: @accent;
}

QPushButton:pressed {
    background-color: @accent_pressed;
}

QPushButton:disabled {
    background-color: @bg_hover;
    color: @text_disabled;
    border-color: @bg_hover;
}

QPushButton#PrimaryAction {
    background-color: @primary_bg;
    border: none;
    color: @on_accent;
    font-weight: bold;
    font-size: 13px;
    padding: 8px 20px;
}

QPushButton#PrimaryAction:hover {
    background-color: @primary_hover;
}

QPushButton#PrimaryAction:pressed {
    background-color: @primary_pressed;
}

QPushButton#PrimaryAction:disabled {
    background-color: @bg_hover;
    color: @text_disabled;
}

QPushButton#DangerAction {
    background-color: @danger_bg;
    border: none;
    color: @on_accent;
    padding: 4px 10px;
    font-size: 11px;
}

QPushButton#DangerAction:hover {
    background-color: @danger;
}

QPushButton#DangerAction:disabled {
    background-color: @bg_hover;
    color: @text_disabled;
}

QLineEdit, QComboBox, QDateEdit, QTimeEdit, QSpinBox, QDoubleSpinBox {
    background-color: @bg;
    border: 1px solid @border;
    padding: 3px 6px;
    border-radius: 4px;
    color: @text;
    selection-background-color: @accent_selection;
    selection-color: @on_accent;
    min-height: 14px;
    font-size: 11px;
}

QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTimeEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: @accent;
}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QDateEdit::up-button, QTimeEdit::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 16px;
    border-left: 1px solid @border;
    background-color: @bg_hover;
}

QSpinBox::down-button, QDoubleSpinBox::down-button,
QDateEdit::down-button, QTimeEdit::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 16px;
    border-left: 1px solid @border;
    background-color: @bg_hover;
}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QDateEdit::up-button:hover, QTimeEdit::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover,
QDateEdit::down-button:hover, QTimeEdit::down-button:hover {
    background-color: @bg_elevated;
}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow,
QDateEdit::up-arrow, QTimeEdit::up-arrow {
    image: @arrow_up;
    width: 8px;
    height: 8px;
}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow,
QDateEdit::down-arrow, QTimeEdit::down-arrow {
    image: @arrow_down;
    width: 8px;
    height: 8px;
}

QPushButton:focus {
    border: 2px solid @accent;
}

QComboBox::drop-down {
    border: none;
    padding-right: 4px;
}

QComboBox::down-arrow {
    image: @arrow_down;
    width: 10px;
    height: 10px;
    margin-right: 4px;
}

QComboBox QAbstractItemView {
    background-color: @bg_elevated;
    border: 1px solid @border;
    border-radius: 4px;
    selection-background-color: @accent_selection;
    selection-color: @on_accent;
    padding: 2px;
    font-size: 11px;
}

QProgressBar {
    border: 1px solid @border;
    border-radius: 4px;
    text-align: center;
    color: @text;
    background-color: @bg;
    min-height: 18px;
    font-weight: bold;
    font-size: 11px;
}

QProgressBar::chunk {
    background-color: @primary_bg;
    border-radius: 3px;
}

QTableWidget {
    background-color: transparent;
    gridline-color: @gridline;
    border: 1px solid @border;
    border-radius: 6px;
    selection-background-color: @accent_selection;
    selection-color: @on_accent;
    alternate-background-color: @bg_tinted_alt_50;
    font-size: 11px;
}

QTableWidget::item {
    padding: 4px 6px;
    border-bottom: 1px solid @gridline;
    color: @text;
}

QTableWidget::item:selected {
    background-color: @accent_selection;
    color: @on_accent;
}

QHeaderView::section {
    background-color: @bg_tinted_alt;
    padding: 4px 6px;
    border: none;
    border-bottom: 1px solid @border;
    color: @text_secondary;
    font-weight: 600;
    font-size: 10px;
}

QHeaderView::section:first {
    border-top-left-radius: 6px;
}

QHeaderView::section:last {
    border-top-right-radius: 6px;
}

QTableWidget QTableCornerButton {
    background-color: @bg_tinted_alt;
}

QTableWidget QTableCornerButton::section {
    background-color: @bg_tinted_alt;
    border: none;
    border-right: 1px solid @border;
    border-bottom: 1px solid @border;
    border-top-left-radius: 6px;
}

QListWidget {
    background-color: @bg_elevated;
    border: 1px solid @border;
    border-radius: 4px;
    color: @text;
    padding: 2px;
    font-size: 11px;
}

QListWidget::item {
    padding: 2px 6px;
    border-radius: 2px;
    color: @text;
}

QListWidget::item:hover {
    background-color: @bg_hover;
}

QListWidget::item:selected {
    background-color: @accent_selection;
    color: @on_accent;
}

QTreeWidget {
    background-color: @bg_elevated;
    border: 1px solid @border;
    border-radius: 4px;
    color: @text;
    padding: 2px;
    font-size: 11px;
}

QTreeWidget::item {
    padding: 2px 6px;
    border-radius: 2px;
    color: @text;
}

QTreeWidget::item:hover {
    background-color: @bg_hover;
}

QTreeWidget::item:selected, QTreeWidget::item:selected:active {
    background-color: @accent_selection;
    color: @on_accent;
}

QTreeWidget QHeaderView::section {
    background-color: @bg_tinted_alt;
}

QMenuBar {
    background-color: @bg_elevated;
    border-bottom: 1px solid @border;
    padding: 2px;
    font-size: 11px;
}

QMenuBar::item {
    padding: 4px 10px;
    border-radius: 4px;
    color: @text;
}

QMenuBar::item:selected {
    background-color: @bg_hover;
}

QMenu {
    background-color: @bg_elevated;
    border: 1px solid @border;
    border-radius: 6px;
    padding: 4px;
    font-size: 11px;
}

QMenu::item {
    padding: 4px 20px;
    border-radius: 4px;
    color: @text;
    font-size: 11px;
}

QMenu::item:selected {
    background-color: @accent_selection;
    color: @on_accent;
}

QMenu::separator {
    height: 1px;
    background-color: @border;
    margin: 4px 8px;
}

QScrollArea {
    background-color: transparent;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

QScrollBar:vertical {
    background-color: @bg_tinted;
    width: 8px;
    margin: 0;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: @border;
    min-height: 24px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: @border_strong;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: @bg_tinted;
    height: 8px;
    margin: 0;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background-color: @border;
    min-width: 24px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background-color: @border_strong;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

QToolTip {
    background-color: @bg_elevated;
    border: 1px solid @border;
    border-radius: 4px;
    padding: 4px 8px;
    color: @text;
    font-size: 11px;
}

QMessageBox {
    background-color: @bg_elevated;
}

QMessageBox QLabel {
    color: @text;
    font-size: 12px;
}

QGroupBox {
    border: 1px solid @border;
    border-radius: 6px;
    margin-top: 6px;
    padding-top: 10px;
    font-weight: 600;
    color: @text;
    font-size: 11px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 6px;
    background-color: @bg_elevated;
}

QGroupBox[checkable="true"]::indicator {
    width: 12px;
    height: 12px;
    margin-left: 2px;
}

QGroupBox[checkable="true"]::title {
    padding-left: 16px;
}

QGroupBox::title:hover {
    color: @accent;
}

QDialog {
    background-color: @bg_elevated;
    border: 1px solid @border;
}

QDialog QLabel {
    color: @text;
    font-size: 12px;
}

QDialog QPushButton {
    min-width: 70px;
}

QCheckBox {
    spacing: 4px;
    color: @text;
    font-size: 11px;
}

QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid @border;
    border-radius: 3px;
    background-color: @bg;
}

QCheckBox::indicator:checked {
    background-color: @primary_bg;
    border-color: @primary_bg;
}

QCheckBox::indicator:hover {
    border-color: @accent;
}

QRadioButton {
    color: @text;
    spacing: 6px;
    font-size: 11px;
}

QRadioButton::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid @border;
    border-radius: 7px;
    background-color: @bg;
}

QRadioButton::indicator:checked {
    background-color: @accent;
    border-color: @accent;
}

QCalendarWidget {
    background-color: @bg_elevated;
    color: @text;
}

QCalendarWidget QToolButton {
    background-color: transparent;
    color: @text;
    padding: 4px;
    border: none;
    font-weight: 600;
}

QCalendarWidget QTableView {
    background-color: @bg;
    selection-background-color: @accent_selection;
    selection-color: @on_accent;
    gridline-color: @border;
    color: @text;
}

QInputDialog {
    background-color: @bg_elevated;
}

QInputDialog QLabel {
    color: @text;
}

QTabWidget::pane {
    border: 1px solid @border;
    border-radius: 6px;
    background-color: @bg_elevated;
}

QTabBar::tab {
    background-color: @bg_hover;
    border: 1px solid @border;
    padding: 6px 14px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    color: @text_secondary;
    font-size: 11px;
}

QTabBar::tab:selected {
    background-color: @bg_elevated;
    color: @text;
    border-bottom-color: @bg_elevated;
}

QTabBar::tab:hover:!selected {
    background-color: @border;
    color: @text;
}

/* Header bar */
#HeaderBar {
    background-color: @bg_elevated;
    border-bottom: 1px solid @border;
}

/* Sessions panel */
#SessionsPanel {
    background-color: @bg_elevated;
    border-bottom: 1px solid @border;
}

/* Icon button (cuadrado pequeño) */
QPushButton#IconButton {
    padding: 2px;
    border: none;
    font-size: 14px;
    min-height: 20px;
}

QPushButton#IconButton:hover {
    background-color: @border;
    border-radius: 4px;
}

QSplitter::handle {
    background-color: @border;
}

QSplitter::handle:hover {
    background-color: @accent;
}
"""


def get_theme() -> str:
    settings = QSettings(_ORG, _APP)
    theme = settings.value(_SETTINGS_KEY, DEFAULT_THEME)
    return theme if theme in THEMES else DEFAULT_THEME


def set_theme(name: str) -> None:
    if name in THEMES:
        QSettings(_ORG, _APP).setValue(_SETTINGS_KEY, name)


def get_accent() -> str:
    settings = QSettings(_ORG, _APP)
    accent = settings.value(_ACCENT_SETTINGS_KEY, DEFAULT_ACCENT)
    return accent if accent in ACCENTS else DEFAULT_ACCENT


def set_accent(name: str) -> None:
    if name in ACCENTS:
        QSettings(_ORG, _APP).setValue(_ACCENT_SETTINGS_KEY, name)


def get_palette(name: str = None) -> dict:
    if name is None:
        name = get_theme()
    return THEMES.get(name, DARK)


def color(name: str) -> str:
    palette = dict(get_palette())
    palette.update(_effective_accent_colors())
    return palette[name]


def _parse_hex(value: str):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _mix(base_hex: str, tint_hex: str, ratio: float) -> str:
    """Mezcla tint_hex sobre base_hex (ratio 0..1) y devuelve un hex opaco."""
    base = _parse_hex(base_hex)
    tint = _parse_hex(tint_hex)
    mixed = tuple(round(b + (t - b) * ratio) for b, t in zip(base, tint))
    return "#{:02x}{:02x}{:02x}".format(*mixed)


def tinted_bg(name: str = None, accent: str = None) -> str:
    """Fondo del tema con el tinte de acento aplicado (low-opacity solid)."""
    return _tint(get_palette(name)["bg"], accent)


def tinted_bg_alt(name: str = None, accent: str = None) -> str:
    """Fondo elevado (paneles, filas alternas) con el tinte de acento aplicado."""
    return _tint(get_palette(name)["bg_elevated"], accent)


def _tint(base_hex: str, accent: str = None) -> str:
    if accent is None:
        accent = get_accent()
    color_hex = ACCENTS.get(accent, ACCENTS[DEFAULT_ACCENT]).get("color")
    if not color_hex:
        return base_hex
    return _mix(base_hex, color_hex, ACCENT_TINT_RATIO)


def _effective_accent_colors(name: str = None, accent: str = None) -> dict:
    """Claves accent/accent_selection/accent_pressed ajustadas al acento.

    Todo lo que en la paleta base es azul fijo (bordes hover/focus,
    selecciones, textos de acento, barra de proyecto) pasa a seguir el
    acento elegido. Con Neutro devuelve {} y manda la paleta tal cual.
    """
    palette = get_palette(name)
    if accent is None:
        accent = get_accent()
    base = ACCENTS.get(accent, ACCENTS[DEFAULT_ACCENT]).get("color")
    if not base:
        return {}
    if palette is DARK:
        return {
            "accent": base,
            "accent_selection": _mix(base, "#000000", 0.30),
            "accent_pressed": _mix(base, "#000000", 0.55),
        }
    return {
        "accent": _mix(base, "#000000", 0.25),
        "accent_selection": _mix(base, "#000000", 0.25),
        "accent_pressed": _mix(base, "#000000", 0.45),
    }


def _primary_action_colors(name: str = None, accent: str = None) -> dict:
    """Colores de la acción primaria derivados del acento efectivo.

    Sustituye a los verdes fijos: el botón primario, el progreso y los
    checks usan la misma familia de acento que selecciones y bordes;
    con Neutro caen al azul de la paleta.
    """
    palette = get_palette(name)
    eff = _effective_accent_colors(name, accent)
    acc = eff.get("accent", palette["accent"])
    sel = eff.get("accent_selection", palette["accent_selection"])
    pressed = eff.get("accent_pressed", palette["accent_pressed"])
    if palette is DARK:
        return {"primary_bg": sel, "primary_hover": acc, "primary_pressed": pressed}
    return {
        "primary_bg": acc,
        "primary_hover": _mix(acc, "#000000", 0.18),
        "primary_pressed": _mix(acc, "#000000", 0.38),
    }


def _rgba(hex_color: str, alpha: int) -> str:
    r, g, b = _parse_hex(hex_color)
    return "rgba({}, {}, {}, {})".format(r, g, b, alpha)


def rgba50(hex_color: str) -> str:
    """Devuelve 'rgba(r,g,b,128)' (50 % de opacidad) para usar en QSS o setStyleSheet."""
    return _rgba(hex_color, 128)


def _arrow_url(name: str) -> str:
    """URL de file:// para un SVG de flecha, con separadores QSS-safe."""
    path = resource_path(os.path.join("app", "ui", "assets", "icons", name + ".svg"))
    return 'url("%s")' % path.replace("\\", "/")


def build_qss(name: str = None, accent: str = None) -> str:
    palette = get_palette(name)
    mapping = dict(palette)
    is_dark = palette is DARK
    mapping["arrow_down"] = _arrow_url("arrow-down-dark" if is_dark else "arrow-down-light")
    mapping["arrow_up"] = _arrow_url("arrow-up-dark" if is_dark else "arrow-up-light")
    mapping["bg_tinted"] = tinted_bg(name, accent)
    mapping["bg_tinted_alt"] = tinted_bg_alt(name, accent)
    mapping["bg_tinted_50"] = _rgba(mapping["bg_tinted"], 128)
    mapping["bg_tinted_alt_50"] = _rgba(mapping["bg_tinted_alt"], 128)
    mapping.update(_effective_accent_colors(name, accent))
    mapping.update(_primary_action_colors(name, accent))
    qss = _QSS_TEMPLATE
    for key, value in sorted(mapping.items(), key=lambda kv: len(kv[0]), reverse=True):
        qss = qss.replace("@" + key, value)
    return qss


def apply_theme(app: QApplication = None, name: str = None, accent: str = None) -> None:
    if app is None:
        app = QApplication.instance()
    if app is None:
        return
    selected_theme = name or get_theme()
    selected_accent = accent or get_accent()
    app.setStyleSheet(build_qss(selected_theme, selected_accent))

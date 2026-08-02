"""Fondo de la app: mosaico de la espiga SVG con fade vertical de opacidad."""

import os

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from app.ui import theme
from app.core.utils import resource_path

_SVG_PATH = resource_path(os.path.join("app", "ui", "assets", "wheat_ear.svg"))
_PLACEHOLDER = "#D4A72C"
_TILE_H = 48
_MAX_OPACITY = 0.15

_tile_cache = None  # (name, accent) -> QPixmap
_HAS_SVG = os.path.exists(_SVG_PATH)
_enabled = True


def set_enabled(state: bool):
    global _enabled
    _enabled = state


def is_enabled() -> bool:
    return _enabled


def _svg_text(name):
    with open(_SVG_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    return content.replace(_PLACEHOLDER, theme.get_palette(name)["wheat"])


def _get_tile(name, accent):
    global _tile_cache
    if _tile_cache is not None and _tile_cache[0] == (name, accent):
        return _tile_cache[1]
    renderer = QSvgRenderer(QByteArray(_svg_text(name).encode("utf-8")))
    vb = renderer.viewBoxF()
    ar = vb.width() / vb.height() if vb.height() else 0.378
    w = max(1, int(_TILE_H * ar * 2))
    h = _TILE_H * 2
    pm = QPixmap(w, h)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    renderer.render(p)
    p.end()
    _tile_cache = ((name, accent), pm.scaled(
        int(_TILE_H * ar) if ar else _TILE_H, _TILE_H,
        Qt.KeepAspectRatio, Qt.SmoothTransformation))
    return _tile_cache[1]


def paint_wheat_field(painter, width, height, name=None, accent=None):
    if not _enabled or not _HAS_SVG:
        return
    if name is None:
        name = theme.get_theme()
    if accent is None:
        accent = theme.get_accent()
    try:
        pm = _get_tile(name, accent)
    except Exception:
        return
    if pm is None:
        return
    tw, th = pm.width(), pm.height()
    cols = (width + tw - 1) // tw if tw else 1
    rows = (height + th - 1) // th if th else 1
    if rows < 2 or cols < 1:
        return
    for r in range(rows):
        y = r * th
        opacity = (r / (rows - 1)) * _MAX_OPACITY
        if opacity <= 0.0:
            continue
        for c in range(cols):
            x = c * tw
            painter.save()
            painter.setOpacity(opacity)
            painter.drawPixmap(x, y, pm)
            painter.restore()
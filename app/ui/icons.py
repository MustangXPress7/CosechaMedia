"""Iconos SVG vectoriales tintados con la paleta del tema.

Reemplaza los glifos unicode/emoji que se usaban como iconos de botón por
iconos SVG propios, recoloreados con el color vigente de la paleta (mismo
patrón de recolor que ``wheat_field.py``: placeholder + replace +
QSvgRenderer + cache).

Los botones se registran por weakref para que ``refresh_all()`` los re-tinte
al cambiar de tema o acento sin reiniciar. Los botones de fila de tabla
(papelera) se crean y destruyen continuamente: el registro no debe
retenerlos vivos.
"""

import os
import weakref

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from app.core.utils import resource_path
from app.ui import theme

_PLACEHOLDER = "#FF00FF"
_ICON_DIR = resource_path(os.path.join("app", "ui", "assets", "icons"))
_HAS_ICONS = os.path.isdir(_ICON_DIR)

_icon_cache = {}  # (name, hex) -> QIcon
_registry = {}  # id(button) -> (weakref, name, size, color_key)


def _svg_text_for(name, color_hex):
    """Devuelve el contenido de ``<name>.svg`` con el placeholder recoloreado."""
    path = os.path.join(_ICON_DIR, name + ".svg")
    if not os.path.exists(path):
        print(f"Icon not found: {path}")
        return None
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return content.replace(_PLACEHOLDER, color_hex)


def pixmap(name, color_hex, size=16):
    """Renderiza el icono ``<name>`` a 2× (nítido en HiDPI) con el color dado."""
    if not _HAS_ICONS:
        return QPixmap()
    svg = _svg_text_for(name, color_hex)
    if not svg:
        return QPixmap()
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pm = QPixmap(size * 2, size * 2)
    pm.fill(Qt.transparent)
    pm.setDevicePixelRatio(2.0)
    p = QPainter(pm)
    renderer.render(p, QRectF(0, 0, size, size))
    p.end()
    return pm


def icon(name, color_key="text", size=16):
    """Devuelve un QIcon del SVG ``<name>`` tintado con la paleta vigente.

    El modo Normal usa ``color_key`` y el modo Disabled ``text_disabled``
    (paridad con el dimming que el QSS aplicaba a los glifos). Si el SVG no
    existe, devuelve un QIcon nulo sin lanzar excepción.
    """
    hex_color = theme.color(color_key)
    cache_key = (name, hex_color)
    cached = _icon_cache.get(cache_key)
    if cached is not None:
        return cached
    normal = pixmap(name, hex_color, size)
    disabled = pixmap(name, theme.color("text_disabled"), size)
    qicon = QIcon()
    if not normal.isNull():
        qicon.addPixmap(normal, QIcon.Mode.Normal, QIcon.State.Off)
        qicon.addPixmap(disabled, QIcon.Mode.Disabled, QIcon.State.Off)
    _icon_cache[cache_key] = qicon
    return qicon


def apply(button, name, size=16, color_key="text"):
    """Aplica el icono ``<name>`` a un botón y lo registra para re-tinte."""
    _registry[id(button)] = (weakref.ref(button), name, size, color_key)
    button.setIcon(icon(name, color_key, size))
    button.setIconSize(QSize(size, size))


def refresh_all():
    """Re-aplica los iconos registrados con la paleta vigente (tema/acento)."""
    dead = []
    for key, (ref, name, size, color_key) in _registry.items():
        button = ref()
        if button is None:
            dead.append(key)
            continue
        button.setIcon(icon(name, color_key, size))
        button.setIconSize(QSize(size, size))
    for key in dead:
        del _registry[key]

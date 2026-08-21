"""Pruebas del módulo de iconos SVG tintables (app/ui/icons.py).

Cobertura:
- ``icon(name)`` devuelve un QIcon no nulo con pixmap renderizado para los
  13 iconos del catálogo.
- ``_svg_text_for`` sustituye el placeholder ``#FF00FF`` por el color pedido.
- ``apply`` fija el icono en un QPushButton (modos Normal y Disabled) y
  registra el botón para el re-tinte de ``refresh_all``.
- ``refresh_all`` re-aplica iconos con la paleta vigente y descarta las
  weakrefs muertas (los botones de fila se crean y destruyen continuamente).
"""
import gc
import os
import unittest
import weakref

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QPushButton

from app.ui import icons

ICON_NAMES = [
    "refresh", "plus", "minus", "x", "pencil", "copy", "folder", "gear",
    "wrench", "trash", "camera", "phone", "wifi", "globe",
]


class TestIcons(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_icon_returns_non_null_for_all_names(self):
        for name in ICON_NAMES:
            with self.subTest(name=name):
                self.assertFalse(icons.icon(name).isNull())

    def test_icon_pixmap_renders_for_all_names(self):
        for name in ICON_NAMES:
            with self.subTest(name=name):
                pm = icons.icon(name).pixmap(QSize(16, 16))
                self.assertFalse(pm.isNull())

    def test_svg_text_for_replaces_placeholder(self):
        text = icons._svg_text_for("refresh", "#123456")
        self.assertIsNotNone(text)
        self.assertNotIn("#FF00FF", text)
        self.assertIn("#123456", text)

    def test_apply_sets_icon_and_registers(self):
        btn = QPushButton()
        icons.apply(btn, "trash", size=16)
        self.assertFalse(btn.icon().isNull())
        disabled = btn.icon().pixmap(QSize(16, 16), mode=QIcon.Mode.Disabled)
        self.assertFalse(disabled.isNull())
        self.assertEqual(btn.iconSize(), QSize(16, 16))
        self.assertIn(id(btn), icons._registry)

    def test_refresh_all_discards_dead_weakrefs(self):
        alive = QPushButton()
        icons.apply(alive, "folder", size=18)
        dead = QPushButton()
        icons.apply(dead, "gear", size=18)
        dead_key = id(dead)
        self.assertIn(dead_key, icons._registry)
        # Sin otras referencias, la weakref muere al recoger el objeto.
        ref = weakref.ref(dead)
        self.assertIsNotNone(ref())
        del dead
        gc.collect()
        self.assertIsNone(ref())
        icons.refresh_all()  # no debe lanzar con weakrefs muertas
        self.assertNotIn(dead_key, icons._registry)
        self.assertIn(id(alive), icons._registry)
        self.assertFalse(alive.icon().isNull())


if __name__ == "__main__":
    unittest.main()

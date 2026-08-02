import os
import re

from PySide6.QtCore import QCoreApplication, QSettings, QTranslator

from app.core.utils import resource_path

_PLACEHOLDER_RE = re.compile(r"%([1-9][0-9]*)")

LANGUAGES = {
    "es": "Español",
    "en": "English",
}

DEFAULT_LANGUAGE = "es"

_translator = None


class QtString(str):
    """Cadena traducible con interpolación estilo Qt (%1, %2...)."""

    def arg(self, *values):
        result = str(self)
        for value in values:
            match = _PLACEHOLDER_RE.search(result)
            if match is None:
                break
            result = result.replace(f"%{match.group(1)}", str(value), 1)
        return QtString(result)


def _translations_dir() -> str:
    return resource_path(os.path.join("app", "i18n"))


def current_language() -> str:
    code = QSettings().value("language", DEFAULT_LANGUAGE)
    return code if code in LANGUAGES else DEFAULT_LANGUAGE


def set_language(code: str) -> bool:
    if code not in LANGUAGES:
        return False
    QSettings().setValue("language", code)
    return load_translation(code)


def load_translation(code: str = None):
    """Instala el QTranslator correspondiente al idioma (no-op si es el idioma fuente)."""
    global _translator
    code = code or current_language()
    if _translator is not None:
        QCoreApplication.removeTranslator(_translator)
        _translator = None
    if code == DEFAULT_LANGUAGE:
        return None
    qm = os.path.join(_translations_dir(), f"cosechamedia_{code}.qm")
    if not os.path.exists(qm):
        return None
    tr = QTranslator()
    if tr.load(qm):
        _translator = tr
        QCoreApplication.installTranslator(tr)
        return tr
    return None


def tr(text: str) -> str:
    """Traducción a nivel de módulo (contexto 'app')."""
    return QtString(QCoreApplication.translate("app", text))

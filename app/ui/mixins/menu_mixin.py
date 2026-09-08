"""Métodos de menú e idioma extraídos de MainWindow (quick 260906-menu-mixin)."""

from PySide6.QtWidgets import QMessageBox
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtCore import QSettings

from app.core import translator
from app.ui import theme
import app.ui.wheat_field as wheat_field
from app.core.db import db


class MenuMixin:
    """Mixin que provee build_menu y _switch_language para MainWindow."""

    def build_menu(self):
        menu_bar = self.menuBar()
        settings = QSettings("Audiovisual Production", "CosechaMedia")

        m_project = menu_bar.addMenu(self.tr("&Proyecto"))

        act_new = QAction(self.tr("&Nuevo Proyecto…"), self)
        act_new.setShortcut("Ctrl+N")
        act_new.triggered.connect(self._show_create_project)
        m_project.addAction(act_new)

        act_pick_dest = QAction(self.tr("Seleccionar &destino del proyecto…"), self)
        act_pick_dest.setShortcut("Ctrl+D")
        act_pick_dest.triggered.connect(self.select_dest_path)
        m_project.addAction(act_pick_dest)

        m_project.addSeparator()

        self.act_auto_detect = QAction(self.tr("Auto-detectar &unidades extraíbles al inicio"), self)
        self.act_auto_detect.setCheckable(True)
        self.act_auto_detect.setChecked(
            settings.value("autoDetectDrives", False, type=bool)
        )
        self.act_auto_detect.triggered.connect(self._on_auto_detect_toggled)
        m_project.addAction(self.act_auto_detect)

        act_dump_targets = QAction(self.tr("Gestionar &destinos de volcado…"), self)
        act_dump_targets.triggered.connect(self._manage_dump_locations)
        m_project.addAction(act_dump_targets)

        m_project.addSeparator()

        act_quit = QAction(self.tr("&Salir"), self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)
        m_project.addAction(act_quit)

        m_data = menu_bar.addMenu(self.tr("&Datos"))

        act_open_data = QAction(self.tr("Abrir carpeta &datos…"), self)
        act_open_data.triggered.connect(self.open_data_folder)
        m_data.addAction(act_open_data)

        act_delete_all = QAction(self.tr("&Eliminar todos los proyectos…"), self)
        act_delete_all.triggered.connect(self.delete_all_projects)
        m_data.addAction(act_delete_all)

        m_data.addSeparator()

        act_del_devices = QAction(self.tr("Borrar &dispositivos guardados…"), self)
        act_del_devices.triggered.connect(self._delete_all_saved_devices)
        m_data.addAction(act_del_devices)

        act_del_cameras = QAction(self.tr("Borrar &nombres de dispositivos…"), self)
        act_del_cameras.triggered.connect(self._delete_all_known_cameras)
        m_data.addAction(act_del_cameras)

        act_detect_sd = QAction(self.tr("Detectar &información de tarjeta SD…"), self)
        act_detect_sd.triggered.connect(self._detect_sd_card)
        m_data.addAction(act_detect_sd)

        act_clear_cache = QAction(self.tr("Limpiar &caché…"), self)
        act_clear_cache.triggered.connect(self._clear_app_cache)
        m_data.addAction(act_clear_cache)

        m_config = menu_bar.addMenu(self.tr("&Configuración"))

        act_cam_detect = QAction(self.tr("Configuración del proyecto…"), self)
        act_cam_detect.triggered.connect(self._show_metadata_dialog)
        m_config.addAction(act_cam_detect)

        m_config.addSeparator()

        act_footage = QAction(self.tr("Personalizar &carpeta de footage…"), self)
        act_footage.triggered.connect(self._manage_footage_folders)
        m_config.addAction(act_footage)

        act_containers = QAction(self.tr("Personalizar &contenedores de archivos…"), self)
        act_containers.triggered.connect(self._manage_containers)
        m_config.addAction(act_containers)

        m_utils = menu_bar.addMenu(self.tr("&Utilidades"))

        act_reorganize = QAction(self.tr("Reorganizar &footage…"), self)
        act_reorganize.triggered.connect(self._reorganize_by_metadata)
        m_utils.addAction(act_reorganize)

        self._view_menu = menu_bar.addMenu(self.tr("&Vista"))
        self._theme_menu = self._view_menu.addMenu(self.tr("Tema"))
        self._theme_group = QActionGroup(self)
        self._theme_group.setExclusive(True)
        current_theme = theme.get_theme()
        theme_names = {
            "dark": self.tr("Oscuro"),
            "light": self.tr("Claro"),
        }
        for key in theme.THEMES:
            act = QAction(theme_names.get(key, key), self)
            act.setCheckable(True)
            act.setChecked(key == current_theme)
            act.triggered.connect(lambda checked=False, k=key: self._switch_theme(k))
            self._theme_group.addAction(act)
            self._theme_menu.addAction(act)

        self._accent_menu = self._view_menu.addMenu(self.tr("Acento"))
        self._accent_group = QActionGroup(self)
        self._accent_group.setExclusive(True)
        current_accent = theme.get_accent()
        accent_names = {
            "default": self.tr("Neutro"),
            "green": self.tr("Verde"),
            "blue": self.tr("Azul"),
            "pink": self.tr("Rosa"),
            "purple": self.tr("Morado"),
            "amber": self.tr("Ámbar"),
        }
        for key in theme.ACCENTS:
            act = QAction(accent_names.get(key, key), self)
            act.setCheckable(True)
            act.setChecked(key == current_accent)
            act.triggered.connect(lambda checked=False, k=key: self._switch_accent(k))
            self._accent_group.addAction(act)
            self._accent_menu.addAction(act)

        self._view_menu.addSeparator()
        bg_enabled = settings.value("wheatBg", True, type=bool)
        if not bg_enabled:
            wheat_field.set_enabled(False)
        self._act_wheat_bg = QAction(self.tr("Fondo de trigo"), self)
        self._act_wheat_bg.setCheckable(True)
        self._act_wheat_bg.setChecked(wheat_field.is_enabled())
        self._act_wheat_bg.triggered.connect(self._toggle_wheat_background)
        self._view_menu.addAction(self._act_wheat_bg)

        m_help = menu_bar.addMenu(self.tr("A&yuda"))
        act_check_updates = QAction(self.tr("&Búsqueda de actualizaciones…"), self)
        act_check_updates.triggered.connect(self._check_for_updates)
        m_help.addAction(act_check_updates)
        m_help.addSeparator()
        act_about = QAction(self.tr("&Acerca de…"), self)
        act_about.triggered.connect(self.show_about)
        m_help.addAction(act_about)

        m_lang = m_help.addMenu(self.tr("&Idioma"))
        lang_group = QActionGroup(self)
        lang_group.setExclusive(True)
        current_lang = translator.current_language()
        for code, name in translator.LANGUAGES.items():
            act = QAction(name, self)
            act.setCheckable(True)
            act.setChecked(code == current_lang)
            act.triggered.connect(lambda checked=False, c=code: self._switch_language(c))
            lang_group.addAction(act)
            m_lang.addAction(act)

    def _clear_app_cache(self):
        from app.core.metadata_engine import metadata_engine
        metadata_engine.clear_cache()
        QMessageBox.information(self, self.tr("Caché"), self.tr("Caché de metadatos limpiada."))

    def _switch_language(self, code):
        if code == translator.current_language():
            return
        translator.set_language(code)
        QMessageBox.information(
            self, self.tr("Idioma"),
            self.tr("Reinicia la aplicación para aplicar el idioma.")
        )
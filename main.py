# CosechaMedia — herramienta de ingesta verificada para producción audiovisual.
# Copyright (C) 2026 JMW Studio / Joan Ramon Viñas
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

from app import __version__
from app.ui.main_window import MainWindow
from app.ui import theme
from app.core.utils import resource_path
from app.core import translator
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QIcon
import sys
import os

def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 9))
    app.setApplicationName("CosechaMedia")
    app.setOrganizationName("Audiovisual Production")
    app.setApplicationVersion(__version__)

    translator.load_translation()

    logo_path = resource_path(os.path.join("app", "ui", "logo.png"))
    if os.path.exists(logo_path):
        app.setWindowIcon(QIcon(logo_path))

    theme.apply_theme(app)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

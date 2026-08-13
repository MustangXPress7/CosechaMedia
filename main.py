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
    app.setApplicationVersion("1.2.1")

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

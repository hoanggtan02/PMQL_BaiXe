import sys
from pmql.config import Settings
def launch(settings: Settings) -> int:
    from PySide6.QtWidgets import QApplication
    from pmql.ui.login import Login
    from pmql.ui.main_window import MainWindow
    app = QApplication(sys.argv)
    login = Login(settings, MainWindow)
    login.show()
    return app.exec()

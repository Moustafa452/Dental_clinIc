import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from dental_lab.database import Database
from dental_lab.services import DentalLabService
from dental_lab.ui import APP_STYLE, LoginDialog, MainWindow


def main():
    app = QApplication(sys.argv)
    # DENTALLAB_LIGHT_PALETTE_V0_3
    # Fusion + explicit light palette prevents Windows dark mode from
    # turning combo popup lists dark while leaving their text dark too.
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#f1f5f9"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#172033"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#fbfcfd"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#172033"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#172033"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#149f94"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#0f172a"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#ffffff"))
    try:
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#94a3b8"))
    except Exception:
        pass
    app.setPalette(palette)
    app.setApplicationName("DentalLabSystem")
    app.setOrganizationName("Elite Dental Lab")
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    app.setStyleSheet(APP_STYLE)

    db = Database()
    login = LoginDialog(db)
    if login.exec() != LoginDialog.DialogCode.Accepted:
        return 0

    service = DentalLabService(db, login.user)
    try:
        service.automatic_backup_if_due()
    except Exception:
        pass
    win = MainWindow(service)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

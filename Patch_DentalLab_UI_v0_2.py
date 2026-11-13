from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

PATCH_MARKER = "# UI_UX_PATCH_V0_2"

NEW_STYLE = r'''APP_STYLE = """
/* ============================================================
   Dental Lab UI/UX v0.2 — light professional desktop theme
   ============================================================ */
QWidget {
    font-family: 'Segoe UI';
    font-size: 10pt;
    color: #1d2939;
}
QMainWindow, QWidget#root {
    background: #eef2f7;
}
QToolTip {
    background: #1f2937;
    color: #ffffff;
    border: 1px solid #475467;
    padding: 5px 7px;
}

/* Sidebar */
QFrame#sidebar {
    background: #1f2937;
    border: none;
}
QLabel#brand {
    color: #ffffff;
    font-size: 18pt;
    font-weight: 700;
    padding: 18px 10px;
}
QPushButton#nav {
    color: #d0d5dd;
    text-align: right;
    padding: 11px 14px;
    border: none;
    border-radius: 8px;
    background: transparent;
}
QPushButton#nav:hover {
    background: #344054;
    color: #ffffff;
}
QPushButton#nav:checked {
    background: #4f63d8;
    color: #ffffff;
    font-weight: 700;
}

/* Page headings and cards */
QLabel#pageTitle {
    font-size: 21pt;
    font-weight: 700;
    color: #101828;
    padding-bottom: 4px;
}
QFrame#card {
    background: #f8fafc;
    border: 1px solid #dfe5ee;
    border-radius: 12px;
}
QLabel#kpiTitle {
    color: #667085;
    font-size: 9pt;
}
QLabel#kpiValue {
    color: #101828;
    font-size: 18pt;
    font-weight: 700;
}

/* Inputs — intentionally off-white, not harsh white */
QLineEdit,
QComboBox,
QDateEdit,
QDoubleSpinBox,
QSpinBox {
    background: #f8fafc;
    color: #101828;
    border: 1px solid #cfd7e6;
    border-radius: 8px;
    padding: 6px 10px;
    min-height: 26px;
    max-height: 38px;
    min-width: 150px;
}
QLineEdit:focus,
QComboBox:focus,
QDateEdit:focus,
QDoubleSpinBox:focus,
QSpinBox:focus,
QTextEdit:focus,
QListWidget:focus {
    border: 1px solid #6172e8;
    background: #ffffff;
}
QLineEdit:disabled,
QComboBox:disabled,
QDateEdit:disabled,
QDoubleSpinBox:disabled,
QSpinBox:disabled,
QTextEdit:disabled {
    color: #98a2b3;
    background: #eef2f6;
}
QTextEdit,
QListWidget {
    background: #f8fafc;
    color: #101828;
    border: 1px solid #cfd7e6;
    border-radius: 8px;
    padding: 7px 9px;
}
QListWidget {
    min-height: 88px;
}
QComboBox::drop-down,
QDateEdit::drop-down {
    border: none;
    width: 26px;
}

/* Buttons */
QPushButton {
    background: #4f63d8;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 8px 14px;
    min-height: 22px;
    font-weight: 600;
}
QPushButton:hover {
    background: #4052c3;
}
QPushButton:pressed {
    background: #3546ad;
}
QPushButton:disabled {
    background: #c7cdd8;
    color: #f2f4f7;
}
QPushButton.secondary {
    background: #e9edf5;
    color: #344054;
}
QPushButton.danger,
QPushButton[class="danger"] {
    background: #d92d20;
}

/* Tables */
QTableWidget {
    background: #f9fbfd;
    alternate-background-color: #f2f5f9;
    color: #1d2939;
    border: 1px solid #dfe5ee;
    border-radius: 10px;
    gridline-color: #e8ecf2;
    selection-background-color: #dfe4ff;
    selection-color: #182230;
}
QHeaderView::section {
    background: #e9eef6;
    color: #344054;
    padding: 9px;
    border: none;
    border-bottom: 1px solid #d6dde8;
    font-weight: 700;
}
QTableWidget::item {
    padding: 7px;
}

/* Dialogs — explicit styling fixes dark OS dialog inheritance */
QDialog {
    background: #f3f6fa;
    color: #1d2939;
}
QDialog QLabel {
    color: #344054;
}
QDialog#dataDialog QLabel {
    color: #344054;
    font-weight: 600;
    padding: 1px 0;
}
QDialog#dataDialog QLineEdit,
QDialog#dataDialog QComboBox,
QDialog#dataDialog QDateEdit,
QDialog#dataDialog QDoubleSpinBox,
QDialog#dataDialog QSpinBox {
    background: #fbfcfe;
    min-height: 30px;
    max-height: 40px;
    min-width: 300px;
}
QDialog#dataDialog QTextEdit {
    background: #fbfcfe;
    min-width: 300px;
}
QDialog#dataDialog QListWidget {
    background: #fbfcfe;
    min-width: 300px;
}
QDialogButtonBox QPushButton {
    min-width: 86px;
    min-height: 26px;
}
QMessageBox {
    background: #f3f6fa;
}
QMessageBox QLabel {
    color: #1d2939;
    min-width: 260px;
}

QScrollArea {
    border: none;
    background: transparent;
}
QScrollArea > QWidget > QWidget {
    background: transparent;
}
"""'''

NEW_SIMPLE_DIALOG = r'''class SimpleDialog(QDialog):
    """Shared Add/Edit dialog used throughout the application.

    The form is scrollable for long screens, labels stay visible in dark-mode
    Windows environments, and all field sizes/spacing are standardized.
    """
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("dataDialog")
        self.setWindowTitle(title)
        self.setModal(True)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setMinimumWidth(560)
        self.setMaximumWidth(760)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(22, 20, 22, 18)
        self.layout.setSpacing(14)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.form_host = QWidget()
        self.form_host.setStyleSheet("background: transparent;")
        self.form = QFormLayout(self.form_host)
        self.form.setContentsMargins(2, 2, 8, 2)
        self.form.setHorizontalSpacing(18)
        self.form.setVerticalSpacing(11)
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.form.setFormAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        self.form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)

        self.scroll.setWidget(self.form_host)
        self.layout.addWidget(self.scroll, 1)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setText("حفظ")
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("إلغاء")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons, 0, Qt.AlignmentFlag.AlignLeft)

    def exec(self):
        # Small forms stay compact; long forms become scrollable instead of
        # stretching beyond the screen.
        rows = max(1, self.form.rowCount())
        target_height = min(720, max(250, 128 + rows * 49))
        self.resize(620, target_height)
        return super().exec()

    def add_line(self, label, value=""):
        w = QLineEdit(str(value or ""))
        w.setClearButtonEnabled(True)
        self.form.addRow(label, w)
        return w

    def add_text(self, label, value=""):
        w = QTextEdit(str(value or ""))
        w.setMinimumHeight(82)
        w.setMaximumHeight(118)
        self.form.addRow(label, w)
        return w

    def add_number(self, label, value=0, maximum=1_000_000_000, decimals=2):
        w = QDoubleSpinBox()
        w.setDecimals(decimals)
        w.setMaximum(maximum)
        w.setMinimum(-maximum)
        w.setValue(float(value or 0))
        w.setGroupSeparatorShown(True)
        self.form.addRow(label, w)
        return w

    def add_combo(self, label, items, current=None):
        w = QComboBox()
        w.addItems(items)
        if current in items:
            w.setCurrentText(current)
        self.form.addRow(label, w)
        return w

    def add_date(self, label, value=None, allow_empty=False):
        w = QDateEdit()
        w.setCalendarPopup(True)
        w.setDisplayFormat("yyyy-MM-dd")
        w.setDate(QDate.fromString(value, "yyyy-MM-dd") if value else QDate.currentDate())
        if allow_empty:
            w.setSpecialValueText("بدون")
            w.setMinimumDate(QDate(1900, 1, 1))
        self.form.addRow(label, w)
        return w
'''


def patch_file(ui_path: Path) -> Path:
    if not ui_path.exists():
        raise FileNotFoundError(f"Could not find: {ui_path}")

    original = ui_path.read_text(encoding="utf-8")
    if PATCH_MARKER in original:
        print("[INFO] UI v0.2 patch is already installed. No changes made.")
        return ui_path

    backup = ui_path.with_name("ui_before_v0_2.py")
    if not backup.exists():
        shutil.copy2(ui_path, backup)
        print(f"[BACKUP] {backup}")

    text = original

    # Replace the global stylesheet.
    style_pattern = re.compile(
        r'APP_STYLE\s*=\s*""".*?"""(?=\n\n\ndef money)',
        re.DOTALL,
    )
    text, n = style_pattern.subn(NEW_STYLE, text, count=1)
    if n != 1:
        raise RuntimeError("Could not locate the APP_STYLE block. No file was written.")

    # Replace every shared Add/Edit dialog through the central dialog class.
    dialog_pattern = re.compile(
        r'class SimpleDialog\(QDialog\):.*?(?=\n\nclass LoginDialog)',
        re.DOTALL,
    )
    text, n = dialog_pattern.subn(NEW_SIMPLE_DIALOG.rstrip(), text, count=1)
    if n != 1:
        raise RuntimeError("Could not locate SimpleDialog. No file was written.")

    # Make table rows easier to read and reduce harsh white blocks.
    text = text.replace(
        't.verticalHeader().setVisible(False)\n        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)',
        't.verticalHeader().setVisible(False)\n        t.verticalHeader().setDefaultSectionSize(38)\n        t.setAlternatingRowColors(True)\n        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)',
        1,
    )

    # Standardize toolbar spacing.
    text = text.replace(
        'w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(0,0,0,0)\n        for x in widgets: l.addWidget(x)',
        'w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(0,0,0,0); l.setSpacing(8)\n        for x in widgets: l.addWidget(x)',
        1,
    )

    # Improve the settings form so fields do not stretch awkwardly across the page.
    text = text.replace(
        's=service.settings();form=QFormLayout();self.outer.addLayout(form)',
        's=service.settings();form=QFormLayout();form.setHorizontalSpacing(18);form.setVerticalSpacing(11);form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter);form.setFormAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight);self.outer.addLayout(form)',
        1,
    )

    # Improve login dialog field spacing and sizing.
    text = text.replace('self.setFixedSize(420, 280)', 'self.setFixedSize(460, 300)', 1)
    text = text.replace(
        'f = QFormLayout(); lay.addLayout(f)',
        'f = QFormLayout(); f.setHorizontalSpacing(16); f.setVerticalSpacing(12); f.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter); lay.addLayout(f)',
        1,
    )

    # Replace the one hard-coded pure-white financial summary block.
    text = text.replace(
        'background:white;border:1px solid #e1e5ec;border-radius:8px;padding:14px;font-size:11pt',
        'background:#f8fafc;border:1px solid #dfe5ee;border-radius:10px;padding:14px;font-size:11pt;color:#1d2939',
    )

    # Add a marker so rerunning the script is safe/idempotent.
    text = text.replace('from __future__ import annotations\n', f'from __future__ import annotations\n\n{PATCH_MARKER}\n', 1)

    ui_path.write_text(text, encoding="utf-8", newline="\n")
    print(f"[PATCHED] {ui_path}")
    return ui_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply Dental Lab UI/UX v0.2 patch")
    parser.add_argument(
        "project",
        nargs="?",
        default=".",
        help="DentalLab project root (default: current directory)",
    )
    args = parser.parse_args()

    root = Path(args.project).expanduser().resolve()
    ui_path = root / "dental_lab" / "ui.py"

    try:
        patch_file(ui_path)
    except Exception as exc:
        print(f"[ERROR] {exc}")
        return 1

    print("\nDone. Start the app with Launch_Windows.bat to review the new UI.")
    print("If needed, restore dental_lab/ui_before_v0_2.py over dental_lab/ui.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import re
import shutil
from datetime import datetime
from pathlib import Path

PATCH_MARKER = "# UI_UX_PATCH_V0_3_REFERENCE"

NEW_STYLE = r'''APP_STYLE = """
/* ============================================================
   Dental Lab UI/UX v0.3 — reference-inspired desktop system
   White cards / cool gray canvas / navy text / teal actions
   ============================================================ */
QWidget {
    font-family: 'Segoe UI';
    font-size: 10pt;
    color: #172033;
}
QMainWindow, QWidget#root {
    background: #f1f5f9;
}
QToolTip {
    background: #0f172a;
    color: #ffffff;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 8px;
}

/* ===== Sidebar ===== */
QFrame#sidebar {
    background: #111827;
    border: none;
}
QLabel#brand {
    color: #ffffff;
    font-size: 18pt;
    font-weight: 800;
    padding: 20px 12px 14px 12px;
}
QLabel#brandSub {
    color: #94a3b8;
    font-size: 9pt;
    padding: 0 12px 12px 12px;
}
QPushButton#nav {
    color: #cbd5e1;
    text-align: right;
    padding: 12px 15px;
    margin: 2px 0;
    border: 1px solid transparent;
    border-radius: 10px;
    background: transparent;
    font-weight: 600;
}
QPushButton#nav:hover {
    background: #1f2937;
    color: #ffffff;
}
QPushButton#nav:checked {
    background: #11998e;
    color: #ffffff;
    border-color: #1db5a8;
    font-weight: 800;
}
QLabel#userCard {
    color: #dbe4ee;
    background: #1f2937;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 10px 12px;
}

/* ===== Page shell ===== */
QFrame#pageHeader {
    background: #ffffff;
    border: 1px solid #dce4ec;
    border-radius: 16px;
}
QLabel#pageTitle {
    font-size: 23pt;
    font-weight: 800;
    color: #162238;
}
QLabel#pageSubtitle {
    color: #7a8aa0;
    font-size: 9.5pt;
}
QFrame#toolbarCard {
    background: #ffffff;
    border: 1px solid #dce4ec;
    border-radius: 14px;
}
QFrame#card, QFrame#chartCard {
    background: #ffffff;
    border: 1px solid #dce4ec;
    border-radius: 16px;
}
QLabel#chartTitle {
    color: #162238;
    font-size: 12.5pt;
    font-weight: 800;
}
QLabel#kpiTitle {
    color: #718096;
    font-size: 9.5pt;
}
QLabel#kpiValue {
    color: #111827;
    font-size: 20pt;
    font-weight: 800;
}

/* ===== Inputs ===== */
QLineEdit,
QComboBox,
QDateEdit,
QDoubleSpinBox,
QSpinBox {
    background: #ffffff;
    color: #172033;
    border: 1px solid #cbd6e2;
    border-radius: 9px;
    padding: 7px 11px;
    min-height: 27px;
    max-height: 40px;
    min-width: 145px;
    selection-background-color: #bce9e4;
    selection-color: #0f3d38;
}
QLineEdit:hover,
QComboBox:hover,
QDateEdit:hover,
QDoubleSpinBox:hover,
QSpinBox:hover,
QTextEdit:hover,
QListWidget:hover {
    border-color: #9fb0c4;
}
QLineEdit:focus,
QComboBox:focus,
QDateEdit:focus,
QDoubleSpinBox:focus,
QSpinBox:focus,
QTextEdit:focus,
QListWidget:focus {
    border: 2px solid #149f94;
    background: #ffffff;
}
QLineEdit:disabled,
QComboBox:disabled,
QDateEdit:disabled,
QDoubleSpinBox:disabled,
QSpinBox:disabled,
QTextEdit:disabled {
    color: #94a3b8;
    background: #eef2f6;
}
QTextEdit,
QListWidget {
    background: #ffffff;
    color: #172033;
    border: 1px solid #cbd6e2;
    border-radius: 9px;
    padding: 8px 10px;
    selection-background-color: #d9f3ef;
    selection-color: #0f3d38;
}
QListWidget {
    min-height: 92px;
}
QComboBox::drop-down,
QDateEdit::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center left;
    width: 28px;
    border: none;
}

/* CRITICAL: readable combo popups on Windows dark mode */
QComboBox QAbstractItemView {
    background: #ffffff;
    color: #172033;
    border: 1px solid #cbd6e2;
    border-radius: 8px;
    outline: 0;
    selection-background-color: #d9f3ef;
    selection-color: #0d756d;
}
QComboBox QAbstractItemView::item {
    min-height: 32px;
    padding: 6px 10px;
    color: #172033;
    background: #ffffff;
}
QComboBox QAbstractItemView::item:hover,
QComboBox QAbstractItemView::item:selected {
    color: #0d756d;
    background: #d9f3ef;
}

/* ===== Buttons ===== */
QPushButton {
    background: #149f94;
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 9px 15px;
    min-height: 24px;
    font-weight: 700;
}
QPushButton:hover {
    background: #0f8f85;
}
QPushButton:pressed {
    background: #0c7c73;
}
QPushButton:disabled {
    background: #cbd5df;
    color: #f8fafc;
}
QPushButton[role="secondary"] {
    background: #eef3f7;
    color: #475569;
    border: 1px solid #dae3eb;
}
QPushButton[role="secondary"]:hover {
    background: #e3eaf1;
}
QPushButton[class="danger"], QPushButton[role="danger"] {
    background: #e11d48;
    color: #ffffff;
}
QPushButton[class="danger"]:hover, QPushButton[role="danger"]:hover {
    background: #be123c;
}

/* ===== Tables ===== */
QTableWidget {
    background: #ffffff;
    alternate-background-color: #fbfcfd;
    color: #172033;
    border: 1px solid #dce4ec;
    border-radius: 14px;
    gridline-color: #e7edf3;
    selection-background-color: #d9f3ef;
    selection-color: #0e4f49;
}
QHeaderView::section {
    background: #f5f8fb;
    color: #435268;
    padding: 10px 8px;
    border: none;
    border-bottom: 1px solid #dce4ec;
    font-weight: 800;
}
QTableWidget::item {
    padding: 8px 7px;
    border-bottom: 1px solid #edf1f5;
}
QTableCornerButton::section {
    background: #f5f8fb;
    border: none;
}

/* ===== Dialogs ===== */
QDialog, QMessageBox {
    background: #f4f7fa;
    color: #172033;
}
QDialog QLabel, QMessageBox QLabel {
    color: #172033;
}
QDialog#dataDialog QFrame#dialogCard,
QDialog#loginDialog QFrame#dialogCard {
    background: #ffffff;
    border: 1px solid #dce4ec;
    border-radius: 14px;
}
QLabel#dialogTitle {
    color: #162238;
    font-size: 16pt;
    font-weight: 800;
}
QLabel#dialogHint {
    color: #7a8aa0;
    font-size: 9pt;
}
QDialog#dataDialog QLabel#fieldLabel {
    color: #344054;
    font-weight: 700;
    padding: 2px 0;
}
QDialog#dataDialog QLineEdit,
QDialog#dataDialog QComboBox,
QDialog#dataDialog QDateEdit,
QDialog#dataDialog QDoubleSpinBox,
QDialog#dataDialog QSpinBox,
QDialog#dataDialog QTextEdit,
QDialog#dataDialog QListWidget {
    background: #ffffff;
    color: #172033;
    min-width: 350px;
}
QDialogButtonBox QPushButton {
    min-width: 92px;
    min-height: 28px;
}
QMessageBox QLabel {
    min-width: 280px;
}

/* ===== Scrollbars ===== */
QScrollArea {
    border: none;
    background: transparent;
}
QScrollArea > QWidget > QWidget {
    background: transparent;
}
QScrollBar:vertical {
    background: transparent;
    width: 11px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #cbd5e1;
    min-height: 34px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
    height: 0px;
}
QScrollBar:horizontal {
    background: transparent;
    height: 11px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background: #cbd5e1;
    min-width: 34px;
    border-radius: 5px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
    width: 0px;
}
"""'''

HELPERS = r'''
COMBO_POPUP_STYLE = """
QAbstractItemView {
    background: #ffffff;
    color: #172033;
    border: 1px solid #cbd6e2;
    outline: 0;
    selection-background-color: #d9f3ef;
    selection-color: #0d756d;
}
QAbstractItemView::item {
    min-height: 32px;
    padding: 6px 10px;
    color: #172033;
    background: #ffffff;
}
QAbstractItemView::item:selected, QAbstractItemView::item:hover {
    color: #0d756d;
    background: #d9f3ef;
}
"""


def style_combo_popup(combo: QComboBox):
    """Force combo popup readability even when Windows is using dark mode."""
    combo.setMaxVisibleItems(12)
    try:
        view = combo.view()
        view.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        view.setStyleSheet(COMBO_POPUP_STYLE)
        view.setMinimumWidth(max(260, combo.sizeHint().width()))
    except Exception:
        pass
    return combo
'''

NEW_SIMPLE_DIALOG = r'''class SimpleDialog(QDialog):
    """Shared premium Add/Edit dialog for every module."""
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("dataDialog")
        self.setWindowTitle(title)
        self.setModal(True)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setMinimumWidth(650)
        self.setMaximumWidth(860)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(12)

        card = QFrame()
        card.setObjectName("dialogCard")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(22, 18, 22, 20)
        card_lay.setSpacing(12)

        title_label = QLabel(title)
        title_label.setObjectName("dialogTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        card_lay.addWidget(title_label)

        hint = QLabel("أدخل البيانات المطلوبة ثم اضغط حفظ")
        hint.setObjectName("dialogHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignRight)
        card_lay.addWidget(hint)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.form_host = QWidget()
        self.form_host.setStyleSheet("background: transparent;")
        self.form = QFormLayout(self.form_host)
        self.form.setContentsMargins(2, 6, 4, 4)
        self.form.setHorizontalSpacing(20)
        self.form.setVerticalSpacing(12)
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.form.setFormAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        self.form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)

        self.scroll.setWidget(self.form_host)
        card_lay.addWidget(self.scroll, 1)
        outer.addWidget(card, 1)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        save_btn = self.buttons.button(QDialogButtonBox.StandardButton.Save)
        cancel_btn = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        save_btn.setText("حفظ")
        cancel_btn.setText("إلغاء")
        save_btn.setProperty("role", "primary")
        cancel_btn.setProperty("role", "secondary")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        outer.addWidget(self.buttons, 0, Qt.AlignmentFlag.AlignLeft)

    def _label(self, text):
        label = QLabel(text)
        label.setObjectName("fieldLabel")
        label.setMinimumWidth(120)
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return label

    def exec(self):
        for combo in self.findChildren(QComboBox):
            style_combo_popup(combo)
        rows = max(1, self.form.rowCount())
        target_height = min(760, max(320, 190 + rows * 50))
        self.resize(700, target_height)
        return super().exec()

    def add_line(self, label, value=""):
        w = QLineEdit(str(value or ""))
        w.setClearButtonEnabled(True)
        w.setMinimumHeight(40)
        self.form.addRow(self._label(label), w)
        return w

    def add_text(self, label, value=""):
        w = QTextEdit(str(value or ""))
        w.setMinimumHeight(92)
        w.setMaximumHeight(128)
        self.form.addRow(self._label(label), w)
        return w

    def add_number(self, label, value=0, maximum=1_000_000_000, decimals=2):
        w = QDoubleSpinBox()
        w.setDecimals(decimals)
        w.setMaximum(maximum)
        w.setMinimum(-maximum)
        w.setValue(float(value or 0))
        w.setGroupSeparatorShown(True)
        w.setMinimumHeight(40)
        self.form.addRow(self._label(label), w)
        return w

    def add_combo(self, label, items, current=None):
        w = style_combo_popup(QComboBox())
        w.addItems(items)
        if current in items:
            w.setCurrentText(current)
        w.setMinimumHeight(40)
        self.form.addRow(self._label(label), w)
        return w

    def add_date(self, label, value=None, allow_empty=False):
        w = QDateEdit()
        w.setCalendarPopup(True)
        w.setDisplayFormat("yyyy-MM-dd")
        w.setDate(QDate.fromString(value, "yyyy-MM-dd") if value else QDate.currentDate())
        if allow_empty:
            w.setSpecialValueText("بدون")
            w.setMinimumDate(QDate(1900, 1, 1))
        w.setMinimumHeight(40)
        self.form.addRow(self._label(label), w)
        return w
'''

NEW_LOGIN = r'''class LoginDialog(QDialog):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.user = None
        self.setObjectName("loginDialog")
        self.setWindowTitle("تسجيل الدخول - نظام إدارة معمل الأسنان")
        self.setFixedSize(520, 380)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)

        card = QFrame()
        card.setObjectName("dialogCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(28, 24, 28, 26)
        lay.setSpacing(14)
        outer.addWidget(card)

        title = QLabel("Elite Dental Lab")
        title.setObjectName("dialogTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)
        sub = QLabel("نظام إدارة معمل الأسنان")
        sub.setObjectName("dialogHint")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(sub)

        f = QFormLayout()
        f.setHorizontalSpacing(18)
        f.setVerticalSpacing(14)
        f.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lay.addLayout(f)
        self.username = QLineEdit("admin")
        self.password = QLineEdit("admin123")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.username.setMinimumHeight(40)
        self.password.setMinimumHeight(40)
        f.addRow("اسم المستخدم", self.username)
        f.addRow("كلمة المرور", self.password)
        hint = QLabel("أول تشغيل: admin / admin123")
        hint.setObjectName("dialogHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(hint)
        btn = QPushButton("دخول")
        btn.setMinimumHeight(42)
        btn.clicked.connect(self.try_login)
        lay.addWidget(btn)
        self.password.returnPressed.connect(self.try_login)

    def try_login(self):
        self.user = self.db.authenticate(self.username.text(), self.password.text())
        if self.user:
            self.accept()
        else:
            QMessageBox.warning(self, "رفض الدخول", "اسم المستخدم أو كلمة المرور غير صحيحة")
'''

NEW_BASE = r'''class BasePage(QWidget):
    def __init__(self, service: DentalLabService, title: str):
        super().__init__()
        self.service = service
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(26, 22, 26, 22)
        self.outer.setSpacing(15)

        header = QFrame()
        header.setObjectName("pageHeader")
        hl = QVBoxLayout(header)
        hl.setContentsMargins(20, 15, 20, 15)
        hl.setSpacing(2)
        h = QLabel(title)
        h.setObjectName("pageTitle")
        h.setAlignment(Qt.AlignmentFlag.AlignRight)
        hl.addWidget(h)
        try:
            s = service.settings()
            meta = " | ".join(x for x in [s.get('lab_address', ''), ("هاتف: " + s.get('lab_phone', '')) if s.get('lab_phone') else ''] if x)
        except Exception:
            meta = ""
        if meta:
            sub = QLabel(meta)
            sub.setObjectName("pageSubtitle")
            sub.setAlignment(Qt.AlignmentFlag.AlignRight)
            hl.addWidget(sub)
        self.outer.addWidget(header)

    def make_table(self, headers):
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.verticalHeader().setVisible(False)
        t.verticalHeader().setDefaultSectionSize(46)
        t.setAlternatingRowColors(True)
        t.setShowGrid(False)
        t.setWordWrap(False)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        t.horizontalHeader().setMinimumSectionSize(70)
        self.outer.addWidget(t, 1)
        return t

    def row(self, *widgets):
        card = QFrame()
        card.setObjectName("toolbarCard")
        l = QHBoxLayout(card)
        l.setContentsMargins(12, 10, 12, 10)
        l.setSpacing(9)
        for x in widgets:
            if isinstance(x, QComboBox):
                style_combo_popup(x)
            l.addWidget(x)
        l.addStretch(1)
        self.outer.addWidget(card)
        return card
'''

NEW_MAIN = r'''class MainWindow(QMainWindow):
    def __init__(self, service: DentalLabService):
        super().__init__()
        self.service = service
        self.setWindowTitle("نظام إدارة معمل الأسنان - Elite Dental Lab")
        self.resize(1500, 900)
        self.setMinimumSize(1120, 700)

        root = QWidget()
        root.setObjectName('root')
        self.setCentralWidget(root)
        main = QHBoxLayout(root)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(255)
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(12, 10, 12, 14)
        sl.setSpacing(4)

        brand = QLabel("Elite Dental Lab")
        brand.setObjectName('brand')
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sl.addWidget(brand)
        brand_sub = QLabel("إدارة معمل الأسنان")
        brand_sub.setObjectName('brandSub')
        brand_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sl.addWidget(brand_sub)

        self.stack = QStackedWidget()
        main.addWidget(self.stack, 1)
        main.addWidget(sidebar)

        self.pages = []
        self.nav = []
        defs = [
            ("لوحة التحكم", DashboardPage), ("إدارة الأطباء", DoctorsPage), ("إدارة الحالات", CasesPage), ("المنتجات", ProductsPage),
            ("المخزون والجرد", InventoryPage), ("الفنيين والعمولات", TechniciansPage), ("التركيبات الفاشلة", FailuresPage),
            ("الفواتير", InvoicesPage)
        ]
        if service.user.get('role') == 'owner':
            defs += [("الإيرادات والمصروفات", FinancePage), ("التقارير والإحصائيات", ReportsPage), ("الإعدادات والنسخ الاحتياطي", SettingsPage)]

        for idx, (name, cls) in enumerate(defs):
            page = cls(service)
            self.stack.addWidget(page)
            self.pages.append(page)
            b = QPushButton(name)
            b.setObjectName('nav')
            b.setCheckable(True)
            b.clicked.connect(lambda _, i=idx: self.goto(i))
            sl.addWidget(b)
            self.nav.append(b)

        sl.addStretch(1)
        u = QLabel(f"المستخدم: {service.user.get('username', '')}\nالصلاحية: {service.user.get('role', '')}")
        u.setObjectName('userCard')
        sl.addWidget(u)

        # Force every page-level combo popup to use the readable light list.
        for combo in self.findChildren(QComboBox):
            style_combo_popup(combo)

        self.goto(0)

    def goto(self, index):
        self.stack.setCurrentIndex(index)
        for i, b in enumerate(self.nav):
            b.setChecked(i == index)
        page = self.pages[index]
        if hasattr(page, 'refresh'):
            try:
                page.refresh()
            except Exception as e:
                error(self, e)
'''


def replace_class(text: str, class_name: str, replacement: str, next_class: str | None) -> str:
    if next_class:
        pat = rf"class {re.escape(class_name)}\b.*?(?=\nclass {re.escape(next_class)}\b)"
    else:
        pat = rf"class {re.escape(class_name)}\b.*\Z"
    new_text, count = re.subn(pat, lambda _m: replacement.rstrip() + "\n", text, flags=re.S)
    if count != 1:
        raise RuntimeError(f"Could not replace {class_name}; matches={count}")
    return new_text


def patch_ui(path: Path):
    text = path.read_text(encoding="utf-8")
    if PATCH_MARKER in text:
        print(f"[SKIP] UI already contains {PATCH_MARKER}")
        return

    # Keep only the latest marker.
    text = re.sub(r"\n?# UI_UX_PATCH_V0_\d+[^\n]*\n", "\n", text)
    insert_at = text.find("\n", text.find("from __future__ import annotations")) + 1
    text = text[:insert_at] + "\n" + PATCH_MARKER + "\n" + text[insert_at:]

    # Replace global QSS.
    pat = r'APP_STYLE = \"\"\".*?\"\"\"\s*(?=def money)'
    text, count = re.subn(pat, NEW_STYLE + "\n\n", text, flags=re.S)
    if count != 1:
        raise RuntimeError(f"Could not replace APP_STYLE; matches={count}")

    # Add combo helper before money().
    text = text.replace("\ndef money(v):", "\n" + HELPERS.strip() + "\n\n\ndef money(v):", 1)

    text = replace_class(text, "SimpleDialog", NEW_SIMPLE_DIALOG, "LoginDialog")
    text = replace_class(text, "LoginDialog", NEW_LOGIN, "BasePage")
    text = replace_class(text, "BasePage", NEW_BASE, "DashboardPage")
    text = replace_class(text, "MainWindow", NEW_MAIN, None)

    # Dashboard spacing / reference-style cards and chart colors.
    text = text.replace(
        "self.kpi_grid = QGridLayout(); self.v.addLayout(self.kpi_grid)\n        self.chart_grid = QGridLayout(); self.v.addLayout(self.chart_grid)",
        "self.kpi_grid = QGridLayout(); self.kpi_grid.setHorizontalSpacing(14); self.kpi_grid.setVerticalSpacing(14); self.v.addLayout(self.kpi_grid)\n        self.chart_grid = QGridLayout(); self.chart_grid.setHorizontalSpacing(16); self.chart_grid.setVerticalSpacing(16); self.v.addLayout(self.chart_grid)",
        1,
    )
    text = re.sub(
        r"    def card\(self, title, value\):.*?(?=\n    def bar_chart)",
        '''    def card(self, title, value):\n        f = QFrame(); f.setObjectName("card"); f.setMinimumHeight(112)\n        l = QVBoxLayout(f); l.setContentsMargins(18, 15, 18, 15); l.setSpacing(7)\n        a = QLabel(title); a.setObjectName("kpiTitle"); a.setAlignment(Qt.AlignmentFlag.AlignRight)\n        b = QLabel(value); b.setObjectName("kpiValue"); b.setAlignment(Qt.AlignmentFlag.AlignRight)\n        l.addWidget(a); l.addWidget(b); l.addStretch(1)\n        return f\n''',
        text,
        flags=re.S,
        count=1,
    )
    text = re.sub(
        r"    def bar_chart\(self, title, data\):.*?(?=\n    def pie_chart)",
        '''    def bar_chart(self, title, data):\n        chart = QChart(); chart.legend().hide(); chart.setBackgroundVisible(False); chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)\n        series = QBarSeries(); s = QBarSet(title); s.setColor(QColor("#7c3aed")); cats = []\n        for x in data:\n            cats.append(str(x["label"])); s.append(float(x["value"] or 0))\n        series.append(s); chart.addSeries(series)\n        ax = QBarCategoryAxis(); ax.append(cats); ax.setLabelsColor(QColor("#64748b")); chart.addAxis(ax, Qt.AlignmentFlag.AlignBottom); series.attachAxis(ax)\n        ay = QValueAxis(); ay.setLabelFormat("%.0f"); ay.setLabelsColor(QColor("#64748b")); ay.setGridLineColor(QColor("#e8eef4")); chart.addAxis(ay, Qt.AlignmentFlag.AlignLeft); series.attachAxis(ay)\n        view = QChartView(chart); view.setRenderHint(QPainter.RenderHint.Antialiasing); view.setMinimumHeight(285); view.setStyleSheet("background:transparent;border:none")\n        card = QFrame(); card.setObjectName("chartCard"); lay = QVBoxLayout(card); lay.setContentsMargins(15, 14, 15, 14); lay.setSpacing(8)\n        lbl = QLabel(title); lbl.setObjectName("chartTitle"); lbl.setAlignment(Qt.AlignmentFlag.AlignRight); lay.addWidget(lbl); lay.addWidget(view)\n        return card\n''',
        text,
        flags=re.S,
        count=1,
    )
    text = re.sub(
        r"    def pie_chart\(self, title, data\):.*?(?=\n    def refresh)",
        '''    def pie_chart(self, title, data):\n        chart = QChart(); chart.setBackgroundVisible(False); series = QPieSeries()\n        palette = [QColor("#10b981"), QColor("#e11d48"), QColor("#f59e0b"), QColor("#7c3aed"), QColor("#149f94")]\n        for i, x in enumerate(data):\n            sl = series.append(str(x["label"]), float(x["value"] or 0)); sl.setColor(palette[i % len(palette)])\n        for sl in series.slices():\n            sl.setLabelVisible(True); sl.setLabelColor(QColor("#334155")); sl.setLabel(f"{sl.label()} {sl.value():.0f}")\n        chart.addSeries(series); chart.legend().setVisible(False)\n        view = QChartView(chart); view.setRenderHint(QPainter.RenderHint.Antialiasing); view.setMinimumHeight(285); view.setStyleSheet("background:transparent;border:none")\n        card = QFrame(); card.setObjectName("chartCard"); lay = QVBoxLayout(card); lay.setContentsMargins(15, 14, 15, 14); lay.setSpacing(8)\n        lbl = QLabel(title); lbl.setObjectName("chartTitle"); lbl.setAlignment(Qt.AlignmentFlag.AlignRight); lay.addWidget(lbl); lay.addWidget(view)\n        return card\n''',
        text,
        flags=re.S,
        count=1,
    )

    # Give the multi-select technician list a proper label object too.
    text = text.replace('d.form.addRow("الفنيون",lw)', 'd.form.addRow(d._label("الفنيون"), lw)')

    path.write_text(text, encoding="utf-8")
    print(f"[OK] Patched {path}")


def patch_app(path: Path):
    text = path.read_text(encoding="utf-8")
    if "DENTALLAB_LIGHT_PALETTE_V0_3" in text:
        print(f"[SKIP] app.py already patched")
        return

    text = text.replace("from PySide6.QtCore import Qt\nfrom PySide6.QtWidgets import QApplication",
                        "from PySide6.QtCore import Qt\nfrom PySide6.QtGui import QColor, QPalette\nfrom PySide6.QtWidgets import QApplication")

    anchor = "def main():\n    app = QApplication(sys.argv)\n"
    replacement = '''def main():\n    app = QApplication(sys.argv)\n    # DENTALLAB_LIGHT_PALETTE_V0_3\n    # Fusion + explicit light palette prevents Windows dark mode from\n    # turning combo popup lists dark while leaving their text dark too.\n    app.setStyle("Fusion")\n    palette = QPalette()\n    palette.setColor(QPalette.ColorRole.Window, QColor("#f1f5f9"))\n    palette.setColor(QPalette.ColorRole.WindowText, QColor("#172033"))\n    palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))\n    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#fbfcfd"))\n    palette.setColor(QPalette.ColorRole.Text, QColor("#172033"))\n    palette.setColor(QPalette.ColorRole.Button, QColor("#ffffff"))\n    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#172033"))\n    palette.setColor(QPalette.ColorRole.Highlight, QColor("#149f94"))\n    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))\n    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#0f172a"))\n    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#ffffff"))\n    try:\n        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#94a3b8"))\n    except Exception:\n        pass\n    app.setPalette(palette)\n'''
    if anchor not in text:
        raise RuntimeError("Could not locate QApplication startup block in app.py")
    text = text.replace(anchor, replacement, 1)
    path.write_text(text, encoding="utf-8")
    print(f"[OK] Patched {path}")


def main():
    parser = argparse.ArgumentParser(description="Apply Dental Lab UI/UX v0.3 reference-inspired redesign")
    parser.add_argument("project", nargs="?", default=".", help="DentalLab project directory")
    args = parser.parse_args()
    root = Path(args.project).resolve()
    ui = root / "dental_lab" / "ui.py"
    app = root / "app.py"
    if not ui.exists() or not app.exists():
        raise SystemExit("[ERROR] Run this from the DentalLab project root (app.py + dental_lab/ui.py required).")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = root / "ui_patch_backups" / f"v0_3_{stamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ui, backup_dir / "ui.py.before_v0_3")
    shutil.copy2(app, backup_dir / "app.py.before_v0_3")
    print(f"[BACKUP] {backup_dir}")

    try:
        patch_ui(ui)
        patch_app(app)
        compile(ui.read_text(encoding="utf-8"), str(ui), "exec")
        compile(app.read_text(encoding="utf-8"), str(app), "exec")
    except Exception:
        shutil.copy2(backup_dir / "ui.py.before_v0_3", ui)
        shutil.copy2(backup_dir / "app.py.before_v0_3", app)
        print("[ROLLBACK] Patch failed; original ui.py and app.py were restored.")
        raise

    print("[VERIFY] Python syntax check passed.")
    print("[DONE] UI/UX v0.3 applied. Launch with Launch_Windows.bat")


if __name__ == "__main__":
    main()

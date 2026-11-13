from __future__ import annotations

# UI_UX_PATCH_V0_3_REFERENCE


from pathlib import Path

from PySide6.QtCore import Qt, QDate, QUrl
from PySide6.QtGui import QAction, QColor, QFont, QPainter, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QAbstractItemView, QCheckBox, QComboBox, QDateEdit, QDialog,
    QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFormLayout, QFrame, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPushButton, QScrollArea, QSpinBox, QStackedWidget,
    QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget
)
from PySide6.QtCharts import QBarCategoryAxis, QBarSeries, QBarSet, QChart, QChartView, QPieSeries, QValueAxis

from .exporters import export_rows_excel, export_table_pdf, invoice_pdf
from .services import BusinessError, DentalLabService

STATUS_AR = {
    "New": "جديدة",
    "In Progress": "قيد التنفيذ",
    "Waiting for Doctor": "انتظار الطبيب",
    "Completed": "مكتملة",
    "Delivered": "تم التسليم",
    "Failed": "فاشلة",
    "Rework": "إعادة عمل",
    "Cancelled": "ملغاة",
}
AR_STATUS = {v: k for k, v in STATUS_AR.items()}
COMMISSION_AR = {
    "selling_percent": "نسبة من سعر البيع",
    "profit_percent": "نسبة من صافي الربح",
    "fixed": "مبلغ ثابت لكل وحدة",
    "custom": "عمولة مخصصة للحالة",
}
AR_COMMISSION = {v: k for k, v in COMMISSION_AR.items()}
ORDER_AR = {"original": "طلب أصلي", "free_remake": "إعادة مجانية", "charged_reorder": "إعادة مدفوعة"}
AR_ORDER = {v: k for k, v in ORDER_AR.items()}

APP_STYLE = """
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
"""

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


def money(v):
    return f"{float(v or 0):,.2f} ج.م"


def is_owner(service: DentalLabService):
    return service.user.get("role") == "owner"

def owner_only(service: DentalLabService):
    if not is_owner(service):
        raise BusinessError("هذه الخاصية متاحة لمالك النظام فقط")

def selected_id(table: QTableWidget):
    row = table.currentRow()
    if row < 0:
        return None
    item = table.item(row, 0)
    return int(item.data(Qt.ItemDataRole.UserRole)) if item and item.data(Qt.ItemDataRole.UserRole) is not None else None


def info(parent, text):
    QMessageBox.information(parent, "تم", text)


def error(parent, exc):
    QMessageBox.critical(parent, "خطأ", str(exc))


class SimpleDialog(QDialog):
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

# DENTALLAB_DYNAMIC_BRANDING_V0_6
def _saved_lab_name(db, fallback="Elite Dental Lab"):
    """Read the saved lab display name before authentication."""
    try:
        with db.connect() as con:
            row = con.execute("SELECT value FROM settings WHERE key='lab_name'").fetchone()
        if row and str(row["value"] or "").strip():
            return str(row["value"]).strip()
    except Exception:
        pass
    return fallback


class LoginDialog(QDialog):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.user = None
        self.setObjectName("loginDialog")
        lab_name = _saved_lab_name(self.db)
        self.setWindowTitle(f"تسجيل الدخول - {lab_name}")
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

        title = QLabel(lab_name)
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

class BasePage(QWidget):
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

class DashboardPage(BasePage):
    def __init__(self, service):
        super().__init__(service, "لوحة التحكم")
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.container = QWidget(); self.v = QVBoxLayout(self.container); self.v.setContentsMargins(0,0,0,0)
        self.outer.addWidget(self.scroll,1); self.scroll.setWidget(self.container)
        self.kpi_grid = QGridLayout(); self.kpi_grid.setHorizontalSpacing(14); self.kpi_grid.setVerticalSpacing(14); self.v.addLayout(self.kpi_grid)
        self.chart_grid = QGridLayout(); self.chart_grid.setHorizontalSpacing(16); self.chart_grid.setVerticalSpacing(16); self.v.addLayout(self.chart_grid)
        self.recent = QTableWidget(0,5); self.recent.setHorizontalHeaderLabels(["رقم الحالة","المريض","الطبيب","الحالة","موعد التسليم"])
        self.recent.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); self.recent.verticalHeader().hide(); self.recent.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.v.addWidget(QLabel("أحدث الحالات")); self.v.addWidget(self.recent)
        self.refresh()

    def card(self, title, value):
        f = QFrame(); f.setObjectName("card"); f.setMinimumHeight(112)
        l = QVBoxLayout(f); l.setContentsMargins(18, 15, 18, 15); l.setSpacing(7)
        a = QLabel(title); a.setObjectName("kpiTitle"); a.setAlignment(Qt.AlignmentFlag.AlignRight)
        b = QLabel(value); b.setObjectName("kpiValue"); b.setAlignment(Qt.AlignmentFlag.AlignRight)
        l.addWidget(a); l.addWidget(b); l.addStretch(1)
        return f

    def bar_chart(self, title, data):
        chart = QChart(); chart.legend().hide(); chart.setBackgroundVisible(False); chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        series = QBarSeries(); s = QBarSet(title); s.setColor(QColor("#7c3aed")); cats = []
        for x in data:
            cats.append(str(x["label"])); s.append(float(x["value"] or 0))
        series.append(s); chart.addSeries(series)
        ax = QBarCategoryAxis(); ax.append(cats); ax.setLabelsColor(QColor("#64748b")); chart.addAxis(ax, Qt.AlignmentFlag.AlignBottom); series.attachAxis(ax)
        ay = QValueAxis(); ay.setLabelFormat("%.0f"); ay.setLabelsColor(QColor("#64748b")); ay.setGridLineColor(QColor("#e8eef4")); chart.addAxis(ay, Qt.AlignmentFlag.AlignLeft); series.attachAxis(ay)
        view = QChartView(chart); view.setRenderHint(QPainter.RenderHint.Antialiasing); view.setMinimumHeight(285); view.setStyleSheet("background:transparent;border:none")
        card = QFrame(); card.setObjectName("chartCard"); lay = QVBoxLayout(card); lay.setContentsMargins(15, 14, 15, 14); lay.setSpacing(8)
        lbl = QLabel(title); lbl.setObjectName("chartTitle"); lbl.setAlignment(Qt.AlignmentFlag.AlignRight); lay.addWidget(lbl); lay.addWidget(view)
        return card

    def pie_chart(self, title, data):
        chart = QChart(); chart.setBackgroundVisible(False); series = QPieSeries()
        palette = [QColor("#10b981"), QColor("#e11d48"), QColor("#f59e0b"), QColor("#7c3aed"), QColor("#149f94")]
        for i, x in enumerate(data):
            sl = series.append(str(x["label"]), float(x["value"] or 0)); sl.setColor(palette[i % len(palette)])
        for sl in series.slices():
            sl.setLabelVisible(True); sl.setLabelColor(QColor("#334155")); sl.setLabel(f"{sl.label()} {sl.value():.0f}")
        chart.addSeries(series); chart.legend().setVisible(False)
        view = QChartView(chart); view.setRenderHint(QPainter.RenderHint.Antialiasing); view.setMinimumHeight(285); view.setStyleSheet("background:transparent;border:none")
        card = QFrame(); card.setObjectName("chartCard"); lay = QVBoxLayout(card); lay.setContentsMargins(15, 14, 15, 14); lay.setSpacing(8)
        lbl = QLabel(title); lbl.setObjectName("chartTitle"); lbl.setAlignment(Qt.AlignmentFlag.AlignRight); lay.addWidget(lbl); lay.addWidget(view)
        return card

    def refresh(self):
        while self.kpi_grid.count():
            item=self.kpi_grid.takeAt(0); item.widget().deleteLater() if item.widget() else None
        while self.chart_grid.count():
            item=self.chart_grid.takeAt(0); item.widget().deleteLater() if item.widget() else None
        d=self.service.dashboard()
        items=[
            ("إيراد الشهر",money(d['monthly_revenue'])),("إيراد السنة",money(d['yearly_revenue'])),
            ("مصروفات الشهر",money(d['monthly_expenses'])),("مصروفات السنة",money(d['yearly_expenses'])),
            ("صافي ربح الشهر",money(d['monthly_profit'])),("صافي ربح السنة",money(d['yearly_profit'])),
            ("إجمالي الحالات",str(d['total_cases'])),("الحالات المكتملة",str(d['completed_cases'])),
            ("الحالات المعلقة",str(d['pending_cases'])),("الحالات الفاشلة",str(d['failed_cases'])),
            ("مديونيات الأطباء",money(d['outstanding'])),("عمولات الفنيين - هذا الشهر",money(d['monthly_technician_commissions'])),
            ("إجمالي عمولات الفنيين",money(d['technician_commissions'])),("تنبيهات المخزون",str(d['low_stock'])),
        ]
        for i,(a,b) in enumerate(items): self.kpi_grid.addWidget(self.card(a,b),i//4,i%4)
        c=self.service.dashboard_charts()
        charts=[
            self.bar_chart("الإيراد الشهري",c['monthly_revenue']), self.bar_chart("مقارنة الإيراد السنوي",c['yearly_revenue']),
            self.pie_chart("الإيرادات مقابل المصروفات",c['revenue_expense']), self.pie_chart("الحالات الناجحة مقابل الفاشلة",c['success_failed']),
            self.bar_chart("المنتجات الأكثر طلباً",c['products']), self.bar_chart("إيراد كل طبيب",c['doctors']),
            self.bar_chart("أداء وعمولات الفنيين",c['technicians'])
        ]
        for i,ch in enumerate(charts): self.chart_grid.addWidget(ch,i//2,i%2)
        self.recent.setRowCount(len(d['recent_cases']))
        for r,x in enumerate(d['recent_cases']):
            vals=[x['case_no'],x['patient_name'],x['doctor_name'],STATUS_AR.get(x['status'],x['status']),x['delivery_date'] or '']
            for c2,v in enumerate(vals): self.recent.setItem(r,c2,QTableWidgetItem(str(v)))


class DoctorsPage(BasePage):
    def __init__(self, service):
        super().__init__(service,"إدارة الأطباء")
        self.search=QLineEdit(); self.search.setPlaceholderText("بحث بالاسم أو الهاتف..."); self.search.textChanged.connect(self.refresh)
        add=QPushButton("إضافة طبيب"); add.clicked.connect(self.add)
        edit=QPushButton("تعديل"); edit.clicked.connect(self.edit); delete=QPushButton("حذف / أرشفة"); delete.setProperty("class","danger"); delete.clicked.connect(self.delete_selected); stmt=QPushButton("كشف حساب PDF"); stmt.clicked.connect(self.statement)
        if not is_owner(service): edit.hide(); delete.hide()
        self.row(self.search,add,edit,delete,stmt)
        self.table=self.make_table(["ID","الاسم","الهاتف","العيادة","إجمالي الحالات","إجمالي الفواتير","المدفوع","المتبقي","فاشلة"])
        self.table.cellDoubleClicked.connect(lambda *_: self.edit() if is_owner(self.service) else None)
        self.rows=[]; self.refresh()
    def refresh(self):
        self.rows=self.service.list_doctors(self.search.text() if hasattr(self,'search') else '')
        self.table.setRowCount(len(self.rows))
        for r,x in enumerate(self.rows):
            vals=[x['id'],x['name'],x['phone'] or '',x['clinic_name'] or '',x['total_cases'],money(x['total_invoices']),money(x['total_payments']),money(x['remaining_balance']),x['failed_cases']]
            for c,v in enumerate(vals):
                it=QTableWidgetItem(str(v));
                if c==0: it.setData(Qt.ItemDataRole.UserRole,x['id'])
                self.table.setItem(r,c,it)
    def form(self,x=None):
        existing=x is not None; d=SimpleDialog("بيانات الطبيب",self); x=x or {}
        a=d.add_line("اسم الطبيب",x.get('name','')); b=d.add_line("الهاتف",x.get('phone','')); c=d.add_line("اسم العيادة",x.get('clinic_name','')); e=d.add_line("العنوان",x.get('address','')); f=d.add_text("ملاحظات",x.get('notes','')); arch=d.add_combo("حالة السجل",["نشط","مؤرشف"],"مؤرشف" if x.get('archived') else "نشط") if existing else None
        summary=None
        if existing:
            sep=QLabel("تصحيح ملخص الحساب - المالك فقط");sep.setStyleSheet("font-weight:800;color:#0f766e;padding-top:8px");d.form.addRow(sep)
            tc=d.add_number("إجمالي الحالات",x.get('total_cases',0),decimals=0);ti=d.add_number("إجمالي الفواتير",x.get('total_invoices',0));tp=d.add_number("المدفوع",x.get('total_payments',0));rb=d.add_number("المتبقي",x.get('remaining_balance',0));fc=d.add_number("الحالات الفاشلة",x.get('failed_cases',0),decimals=0)
            summary=(tc,ti,tp,rb,fc)
        if d.exec():
            ret=dict(name=a.text(),phone=b.text(),clinic_name=c.text(),address=e.text(),notes=f.toPlainText())
            if existing:
                ret['archived']=1 if arch.currentText()=="مؤرشف" else 0
                tc,ti,tp,rb,fc=summary;ret['_summary']=dict(total_cases=tc.value(),total_invoices=ti.value(),total_payments=tp.value(),remaining_balance=rb.value(),failed_cases=fc.value())
            return ret
    def add(self):
        try:
            v=self.form();
            if v: self.service.add_doctor(**v); self.refresh()
        except Exception as e: error(self,e)
    def edit(self):
        if not is_owner(self.service): return
        i=selected_id(self.table)
        if not i:return
        x=next(r for r in self.rows if r['id']==i)
        try:
            v=self.form(x)
            if v:
                summary=v.pop('_summary',None);self.service.update_doctor(i,**v)
                if summary:self.service.owner_set_doctor_summary(i,**summary)
                self.refresh()
        except Exception as e:error(self,e)
    def delete_selected(self):
        i=selected_id(self.table)
        if not i:return
        if QMessageBox.question(self,"تأكيد","حذف الطبيب؟ إذا كان مرتبطاً بحالات أو فواتير سيتم أرشفته بدلاً من حذف التاريخ.")==QMessageBox.StandardButton.Yes:
            try:
                result=self.service.delete_doctor(i);self.refresh()
                info(self,"تمت الأرشفة للحفاظ على السجل التاريخي." if result=="archived" else "تم حذف الطبيب.")
            except Exception as e:error(self,e)
    def statement(self):
        i=selected_id(self.table)
        if not i:return
        doc=next(r for r in self.rows if r['id']==i); invs=self.service.doctor_invoices(i)
        headers=["رقم الفاتورة","التاريخ","الإجمالي","المدفوع","المتبقي","الحالة"]
        rows=[[x['invoice_no'],x['invoice_date'],x['total'],x['paid'],x['balance'],x['status']] for x in invs]
        try:
            path=export_table_pdf(f"كشف حساب - {doc['name']}",headers,rows);info(self,f"تم إنشاء كشف الحساب:\n{path}")
        except Exception as e:error(self,e)


class ProductsPage(BasePage):
    def __init__(self,service):
        super().__init__(service,"المنتجات والأسعار")
        self.search=QLineEdit(); self.search.setPlaceholderText("بحث..."); self.search.textChanged.connect(self.refresh)
        a=QPushButton("إضافة منتج");a.clicked.connect(self.add); e=QPushButton("تعديل");e.clicked.connect(self.edit); delete=QPushButton("حذف / أرشفة");delete.setProperty("class","danger");delete.clicked.connect(self.delete_selected); s=QPushButton("حركة مخزون");s.clicked.connect(self.stock)
        if not is_owner(service): e.hide(); delete.hide()
        self.row(self.search,a,e,delete,s)
        self.table=self.make_table(["ID","المنتج","الفئة","تكلفة العبوة/البلوك","الوحدات الناتجة","تكلفة الوحدة","سعر البيع","المتاح","حد التنبيه","الوحدة","المورد","تنبيه"])
        self.table.cellDoubleClicked.connect(lambda *_: self.edit() if is_owner(self.service) else None)
        self.rows=[];self.refresh()
    def refresh(self):
        self.rows=self.service.list_products(self.search.text() if hasattr(self,'search') else '')
        self.table.setRowCount(len(self.rows))
        for r,x in enumerate(self.rows):
            vals=[x['id'],x['name'],x['category'] or '',money(x['purchase_cost']),f"{x['yield_units']:g}",money(x['unit_material_cost']),money(x['selling_price']),f"{x['stock_qty']:g}",f"{x['min_stock']:g}",x['unit'],x['supplier'] or '',"منخفض" if x['low_stock'] else '']
            for c,v in enumerate(vals):
                it=QTableWidgetItem(str(v));
                if c==0: it.setData(Qt.ItemDataRole.UserRole,x['id'])
                if x['low_stock']: it.setBackground(QColor('#fff1f0'))
                self.table.setItem(r,c,it)
    def form(self,x=None,new=False):
        d=SimpleDialog("بيانات المنتج",self);x=x or {}
        n=d.add_line("اسم المنتج",x.get('name',''));cat=d.add_line("الفئة",x.get('category',''));desc=d.add_text("الوصف",x.get('description',''))
        cost=d.add_number("تكلفة شراء العبوة / البلوك",x.get('purchase_cost',0));yield_units=d.add_number("عدد الوحدات الناتجة من العبوة / البلوك",x.get('yield_units',1),decimals=2);unit_cost=d.add_number("تكلفة الوحدة",x.get('unit_material_cost',(float(x.get('purchase_cost',0) or 0)/max(float(x.get('yield_units',1) or 1),1e-9))));price=d.add_number("سعر بيع الوحدة",x.get('selling_price',0));
        def sync_unit_from_package():
            unit_cost.blockSignals(True);unit_cost.setValue(cost.value()/max(yield_units.value(),1e-9));unit_cost.blockSignals(False)
        def sync_package_from_unit():
            cost.blockSignals(True);cost.setValue(unit_cost.value()*max(yield_units.value(),1e-9));cost.blockSignals(False)
        cost.valueChanged.connect(lambda *_: sync_unit_from_package());yield_units.valueChanged.connect(lambda *_: sync_unit_from_package());unit_cost.valueChanged.connect(lambda *_: sync_package_from_unit())
        stock=d.add_number("الرصيد الحالي (بوحدات البيع)" if not new else "الرصيد الافتتاحي (بوحدات البيع)",x.get('stock_qty',0),decimals=3)
        minimum=d.add_number("حد التنبيه",x.get('min_stock',0),decimals=3);unit=d.add_line("الوحدة",x.get('unit','وحدة'));sup=d.add_line("المورد",x.get('supplier',''));arch=d.add_combo("حالة السجل",["نشط","مؤرشف"],"مؤرشف" if x.get('archived') else "نشط") if not new else None
        if d.exec():
            ret=dict(name=n.text(),category=cat.text(),description=desc.toPlainText(),purchase_cost=cost.value(),yield_units=yield_units.value(),selling_price=price.value(),min_stock=minimum.value(),unit=unit.text(),supplier=sup.text(),stock_qty=stock.value())
            if not new: ret['archived']=1 if arch.currentText()=="مؤرشف" else 0
            return ret
    def add(self):
        try:
            v=self.form(new=True)
            if v:self.service.add_product(**v);self.refresh()
        except Exception as e:error(self,e)
    def edit(self):
        if not is_owner(self.service): return
        i=selected_id(self.table)
        if not i:return
        x=next(r for r in self.rows if r['id']==i)
        try:
            v=self.form(x)
            if v:
                stock=v.pop('stock_qty',None);self.service.owner_update_product_full(i,stock_qty=stock,**v);self.refresh()
        except Exception as e:error(self,e)
    def delete_selected(self):
        i=selected_id(self.table)
        if not i:return
        if QMessageBox.question(self,"تأكيد","حذف المنتج؟ إذا كان مستخدماً في حالات أو مخزون تاريخي مرتبط بحالات سيتم أرشفته.")==QMessageBox.StandardButton.Yes:
            try:
                result=self.service.delete_product(i);self.refresh()
                info(self,"تمت الأرشفة للحفاظ على السجل التاريخي." if result=="archived" else "تم حذف المنتج.")
            except Exception as e:error(self,e)

    def stock(self):
        i=selected_id(self.table)
        if not i:return
        d=SimpleDialog("حركة مخزون",self);typ=d.add_combo("النوع",["IN","OUT","ADJUSTMENT","WASTE","RETURN"]);q=d.add_number("الكمية",0,decimals=3);notes=d.add_line("ملاحظات")
        if d.exec():
            try:self.service.stock_movement(i,typ.currentText(),q.value(),notes.text());self.refresh()
            except Exception as e:error(self,e)


class InventoryPage(BasePage):
    def __init__(self,service):
        super().__init__(service,"المخزون والجرد")
        b=QPushButton("تحديث");b.clicked.connect(self.refresh);delete=QPushButton("حذف حركة المخزون");delete.setProperty("class","danger");delete.clicked.connect(self.delete_movement)
        if not is_owner(service):delete.hide()
        self.row(b,delete)
        self.table=self.make_table(["ID","التاريخ","المنتج","النوع","الكمية","الرصيد بعد الحركة","الحالة المرتبطة","ملاحظات"]);self.table.cellDoubleClicked.connect(lambda *_: self.edit_movement() if is_owner(self.service) else None);self.rows=[];self.refresh()
    def refresh(self):
        rows=self.service.list_stock_movements();self.rows=rows;self.table.setRowCount(len(rows))
        for r,x in enumerate(rows):
            vals=[x['id'],x['movement_date'],x['product_name'],x['movement_type'],f"{x['quantity']:g}",f"{x['balance_after']:g}",x['case_no'] or '',x['notes'] or '']
            for c,v in enumerate(vals):
                it=QTableWidgetItem(str(v));
                if c==0:it.setData(Qt.ItemDataRole.UserRole,x['id'])
                self.table.setItem(r,c,it)

    def delete_movement(self):
        if not is_owner(self.service):return
        i=selected_id(self.table)
        if not i:return
        if QMessageBox.question(self,"حذف حركة مخزون","سيتم حذف الحركة وإعادة حساب رصيد المنتج وكافة الأرصدة اللاحقة. إذا كانت الحركة مرتبطة بحالة سيبقى سجل الحالة موجوداً. متابعة؟")==QMessageBox.StandardButton.Yes:
            try:self.service.delete_stock_movement(i);self.refresh();info(self,"تم حذف حركة المخزون وإعادة حساب الرصيد.")
            except Exception as e:error(self,e)

    def edit_movement(self):
        if not is_owner(self.service): return
        i=selected_id(self.table)
        if not i:return
        x=next((r for r in self.rows if r['id']==i),None)
        if not x:return
        d=SimpleDialog("تعديل حركة المخزون - مالك النظام",self);dt=d.add_date("التاريخ",x.get('movement_date'));notes=d.add_text("ملاحظات",x.get('notes',''))
        hint=QLabel("المنتج/النوع/الكمية/الرصيد حقول دفترية مترابطة؛ عدّلها من المنتج أو الحالة حتى يبقى المخزون صحيحاً.");hint.setWordWrap(True);d.form.addRow(hint)
        if d.exec():
            try:self.service.update_manual_stock_movement(i,movement_date=dt.date().toString('yyyy-MM-dd'),notes=notes.toPlainText());self.refresh()
            except Exception as e:error(self,e)


class TechniciansPage(BasePage):
    def __init__(self,service):
        super().__init__(service,"الفنيين والعمولات")
        a=QPushButton("إضافة فني");a.clicked.connect(self.add);e=QPushButton("تعديل");e.clicked.connect(self.edit);delete=QPushButton("حذف / أرشفة");delete.setProperty("class","danger");delete.clicked.connect(self.delete_selected);p=QPushButton("تسجيل دفع عمولة");p.clicked.connect(self.pay)
        if not is_owner(service): e.hide(); delete.hide()
        self.row(a,e,delete,p);self.table=self.make_table(["ID","الاسم","الهاتف","طريقة العمولة","النسبة %","الثابت","الحالات","مكتملة","فاشلة","إجمالي العمولة","المدفوع","المتبقي"]);self.table.cellDoubleClicked.connect(lambda *_: self.edit() if is_owner(self.service) else None);self.rows=[];self.refresh()
    def refresh(self):
        self.rows=self.service.list_technicians();self.table.setRowCount(len(self.rows))
        for r,x in enumerate(self.rows):
            vals=[x['id'],x['name'],x['phone'] or '',COMMISSION_AR.get(x['commission_method'],x['commission_method']),x['commission_rate'],money(x['fixed_amount']),x['assigned_cases'],x['completed_cases'],x['failed_cases'],money(x['total_commission']),money(x['paid_commission']),money(x['outstanding_commission'])]
            for c,v in enumerate(vals):
                it=QTableWidgetItem(str(v));
                if c==0:it.setData(Qt.ItemDataRole.UserRole,x['id'])
                self.table.setItem(r,c,it)
    def form(self,x=None):
        existing=x is not None;d=SimpleDialog("بيانات الفني",self);x=x or {};n=d.add_line("الاسم",x.get('name',''));ph=d.add_line("الهاتف",x.get('phone',''));m=d.add_combo("طريقة العمولة",list(COMMISSION_AR.values()),COMMISSION_AR.get(x.get('commission_method','selling_percent')));rate=d.add_number("النسبة %",x.get('commission_rate',0),100);fixed=d.add_number("المبلغ الثابت",x.get('fixed_amount',0));arch=d.add_combo("حالة السجل",["نشط","مؤرشف"],"مؤرشف" if x.get('archived') else "نشط") if existing else None
        summary=None
        if existing:
            sep=QLabel("تصحيح ملخص الفني - المالك فقط");sep.setStyleSheet("font-weight:800;color:#0f766e;padding-top:8px");d.form.addRow(sep)
            assigned=d.add_number("الحالات",x.get('assigned_cases',0),decimals=0);completed=d.add_number("مكتملة",x.get('completed_cases',0),decimals=0);failed=d.add_number("فاشلة",x.get('failed_cases',0),decimals=0);total=d.add_number("إجمالي العمولة",x.get('total_commission',0));paid=d.add_number("المدفوع",x.get('paid_commission',0));out=d.add_number("المتبقي",x.get('outstanding_commission',0));summary=(assigned,completed,failed,total,paid,out)
        if d.exec():
            ret=dict(name=n.text(),phone=ph.text(),commission_method=AR_COMMISSION[m.currentText()],commission_rate=rate.value(),fixed_amount=fixed.value())
            if existing:
                ret['archived']=1 if arch.currentText()=="مؤرشف" else 0
                assigned,completed,failed,total,paid,out=summary;ret['_summary']=dict(assigned_cases=assigned.value(),completed_cases=completed.value(),failed_cases=failed.value(),total_commission=total.value(),paid_commission=paid.value(),outstanding_commission=out.value())
            return ret
    def add(self):
        try:
            v=self.form();
            if v:self.service.add_technician(**v);self.refresh()
        except Exception as e:error(self,e)
    def edit(self):
        if not is_owner(self.service): return
        i=selected_id(self.table)
        if not i:return
        x=next(r for r in self.rows if r['id']==i)
        try:
            v=self.form(x)
            if v:
                summary=v.pop('_summary',None);self.service.update_technician(i,**v)
                if summary:self.service.owner_set_technician_summary(i,**summary)
                self.refresh()
        except Exception as e:error(self,e)
    def delete_selected(self):
        i=selected_id(self.table)
        if not i:return
        if QMessageBox.question(self,"تأكيد","حذف الفني؟ إذا كان لديه حالات أو دفعات عمولة سيتم أرشفته للحفاظ على الحسابات.")==QMessageBox.StandardButton.Yes:
            try:
                result=self.service.delete_technician(i);self.refresh()
                info(self,"تمت الأرشفة للحفاظ على سجل العمولات." if result=="archived" else "تم حذف الفني.")
            except Exception as e:error(self,e)

    def pay(self):
        i=selected_id(self.table)
        if not i:return
        d=SimpleDialog("دفع عمولة",self);a=d.add_number("المبلغ",0);n=d.add_line("ملاحظات")
        if d.exec():
            try:self.service.record_commission_payment(i,a.value(),n.text());self.refresh()
            except Exception as e:error(self,e)


class CasesPage(BasePage):
    def __init__(self,service):
        super().__init__(service,"إدارة الحالات")
        self.search=QLineEdit();self.search.setPlaceholderText("بحث بالمريض أو الطبيب أو رقم الحالة/الفاتورة...");self.search.textChanged.connect(self.refresh)
        self.status=QComboBox();self.status.addItem("كل الحالات","");
        for k,v in STATUS_AR.items():
            if k!='Cancelled':self.status.addItem(v,k)
        self.status.currentIndexChanged.connect(self.refresh)
        a=QPushButton("تسجيل حالة جديدة");a.clicked.connect(self.add);ap=QPushButton("إضافة منتج للحالة");ap.clicked.connect(self.add_product);merge=QPushButton("ضم لفاتورة أخرى");merge.clicked.connect(self.merge_invoice);e=QPushButton("تعديل شامل");e.clicked.connect(self.edit_case);s=QPushButton("تغيير الحالة");s.clicked.connect(self.change_status);c=QPushButton("إلغاء الحالة");c.clicked.connect(self.cancel_case);delete=QPushButton("حذف الحالة نهائياً");delete.setProperty("class","danger");delete.clicked.connect(self.delete_case)
        if not is_owner(service): e.hide(); delete.hide()
        self.row(self.search,self.status,a,ap,merge,e,s,c,delete)
        self.table=self.make_table(["ID","رقم الحالة","الفاتورة","المريض","الطبيب","المنتج","الفني","الحالة","الاستلام","التسليم","الإجمالي"]);self.table.cellDoubleClicked.connect(lambda *_: self.edit_case() if is_owner(self.service) else None);self.rows=[];self.refresh()
    def refresh(self):
        self.rows=self.service.list_cases(self.search.text() if hasattr(self,'search') else '',self.status.currentData() if hasattr(self,'status') else '')
        self.table.setRowCount(len(self.rows))
        for r,x in enumerate(self.rows):
            vals=[x['id'],x['case_no'],x['invoice_no'] or '',x['patient_name'],x['doctor_name'],x['product_names'] or '',x['technician_names'] or '',STATUS_AR.get(x['status'],x['status']),x['received_date'],x['delivery_date'] or '',money(x['total'])]
            for c,v in enumerate(vals):
                it=QTableWidgetItem(str(v));
                if c==0:it.setData(Qt.ItemDataRole.UserRole,x['id'])
                self.table.setItem(r,c,it)
    def add(self):
        docs=self.service.list_doctors();products=self.service.list_products();techs=self.service.list_technicians()
        if not docs or not products:
            error(self,"يجب إضافة طبيب ومنتج أولاً");return
        d=SimpleDialog("تسجيل حالة جديدة",self)
        doc=d.add_combo("الطبيب",[x['name'] for x in docs]);patient=d.add_line("اسم المريض");prod=d.add_combo("المنتج",[x['name'] for x in products]);qty=d.add_number("الكمية",1,decimals=2);teeth=d.add_line("أرقام الأسنان");disc=d.add_number("الخصم",0);received=d.add_date("تاريخ الاستلام");delivery=d.add_date("تاريخ التسليم");status=d.add_combo("الحالة",[v for k,v in STATUS_AR.items() if k!='Cancelled'],"جديدة");kind=d.add_combo("نوع الطلب",list(ORDER_AR.values()),"طلب أصلي");notes=d.add_text("ملاحظات")
        lw=QListWidget();lw.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        for t in techs:
            item=QListWidgetItem(t['name']);item.setData(Qt.ItemDataRole.UserRole,t['id']);lw.addItem(item)
        d.form.addRow(d._label("الفنيون"), lw)
        if d.exec():
            try:
                did=next(x['id'] for x in docs if x['name']==doc.currentText());pid=next(x['id'] for x in products if x['name']==prod.currentText());tids=[x.data(Qt.ItemDataRole.UserRole) for x in lw.selectedItems()]
                self.service.create_case(did,patient.text(),pid,qty.value(),teeth.text(),tids,received.date().toString('yyyy-MM-dd'),delivery.date().toString('yyyy-MM-dd'),disc.value(),AR_STATUS[status.currentText()],notes.toPlainText(),AR_ORDER[kind.currentText()]);self.refresh();info(self,"تم إنشاء الحالة والفاتورة وخصم المخزون")
            except Exception as e:error(self,e)
    def add_product(self):
        i=selected_id(self.table)
        if not i:return
        products=self.service.list_products()
        if not products:return
        d=SimpleDialog("إضافة منتج للحالة والفاتورة",self);p=d.add_combo("المنتج",[x['name'] for x in products]);q=d.add_number("الكمية",1,decimals=2);teeth=d.add_line("أرقام الأسنان");disc=d.add_number("الخصم",0)
        if d.exec():
            try:
                pid=products[p.currentIndex()]['id'];self.service.add_product_to_case(i,pid,q.value(),teeth.text(),disc.value());self.refresh();info(self,"تمت إضافة المنتج إلى نفس الحالة ونفس الفاتورة")
            except Exception as e:error(self,e)
    def merge_invoice(self):
        i=selected_id(self.table)
        if not i:return
        row=next((x for x in self.rows if x['id']==i),None)
        invoices=[x for x in self.service.list_invoices() if x['doctor_name']==row['doctor_name'] and x['status']!='cancelled' and x['invoice_no']!=row['invoice_no']]
        if not invoices:
            error(self,"لا توجد فاتورة أخرى صالحة لنفس الطبيب");return
        d=SimpleDialog("ضم الحالة إلى فاتورة أخرى",self);cb=d.add_combo("فاتورة الهدف",[f"{x['invoice_no']} - المتبقي {x['balance']:.2f}" for x in invoices])
        if d.exec():
            try:self.service.merge_case_into_invoice(i,invoices[cb.currentIndex()]['id']);self.refresh();info(self,"تم ضم الحالة إلى الفاتورة المحددة")
            except Exception as e:error(self,e)
    def edit_case(self):
        if not is_owner(self.service): return
        i=selected_id(self.table)
        if not i:return
        try:c,items,inv,tech_ids=self.service.case_full_detail(i)
        except Exception as e:error(self,e);return
        if not c or not inv:return
        docs=self.service.list_doctors(include_archived=True);products=self.service.list_products(include_archived=True);techs=self.service.list_technicians(True)
        d=SimpleDialog("تعديل شامل للحالة - المالك",self)
        case_no=d.add_line("رقم الحالة",c['case_no']);invoice_no=d.add_line("رقم الفاتورة",inv['invoice_no']);doc=d.add_combo("الطبيب",[x['name'] for x in docs],next((x['name'] for x in docs if x['id']==c['doctor_id']),None));patient=d.add_line("اسم المريض",c['patient_name']);received=d.add_date("تاريخ الاستلام",c['received_date']);delivery=d.add_date("تاريخ التسليم",c['delivery_date']);status=d.add_combo("الحالة",list(STATUS_AR.values()),STATUS_AR.get(c['status'],c['status']));kind=d.add_combo("نوع الطلب",list(ORDER_AR.values()),ORDER_AR.get(c['order_kind'],c['order_kind']));notes=d.add_text("ملاحظات",c['notes'] or '')
        lw=QListWidget();lw.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        for t in techs:
            it=QListWidgetItem(t['name']);it.setData(Qt.ItemDataRole.UserRole,t['id']);lw.addItem(it);it.setSelected(t['id'] in tech_ids)
        d.form.addRow(d._label("الفنيون"),lw)
        item_widgets=[]
        for n,it in enumerate(items,1):
            sep=QLabel(f"المنتج داخل الحالة #{n}");sep.setStyleSheet("font-weight:800;color:#0f766e;padding-top:8px");d.form.addRow(sep)
            pcb=d.add_combo(f"المنتج #{n}",[x['name'] for x in products],next((x['name'] for x in products if x['id']==it['product_id']),None));teeth=d.add_line(f"أرقام الأسنان #{n}",it.get('tooth_numbers',''));qty=d.add_number(f"الكمية #{n}",it['quantity'],decimals=3);price=d.add_number(f"سعر الوحدة المحفوظ #{n}",it['unit_price_snapshot']);cost=d.add_number(f"تكلفة خام الوحدة المحفوظة #{n}",it['purchase_cost_snapshot']);disc=d.add_number(f"الخصم #{n}",it['discount'])
            item_widgets.append((pcb,teeth,qty,price,cost,disc))
        if d.exec():
            try:
                did=docs[doc.currentIndex()]['id'];tids=[x.data(Qt.ItemDataRole.UserRole) for x in lw.selectedItems()];new_items=[]
                for pcb,teeth,qty,price,cost,disc in item_widgets:
                    new_items.append(dict(product_id=products[pcb.currentIndex()]['id'],tooth_numbers=teeth.text(),quantity=qty.value(),unit_price_snapshot=price.value(),purchase_cost_snapshot=cost.value(),discount=disc.value()))
                self.service.owner_edit_case_full(i,case_no=case_no.text(),invoice_no=invoice_no.text(),doctor_id=did,patient_name=patient.text(),received_date=received.date().toString('yyyy-MM-dd'),delivery_date=delivery.date().toString('yyyy-MM-dd'),status=AR_STATUS[status.currentText()],order_kind=AR_ORDER[kind.currentText()],notes=notes.toPlainText(),technician_ids=tids,items=new_items);self.refresh();info(self,"تم حفظ التعديل الشامل مع تحديث المخزون والفاتورة والعمولات")
            except Exception as e:error(self,e)

    def change_status(self):
        i=selected_id(self.table)
        if not i:return
        d=SimpleDialog("تغيير حالة الحالة",self);cb=d.add_combo("الحالة",[v for k,v in STATUS_AR.items() if k!='Cancelled'])
        if d.exec():
            try:self.service.update_case_status(i,AR_STATUS[cb.currentText()]);self.refresh()
            except Exception as e:error(self,e)
    def cancel_case(self):
        i=selected_id(self.table)
        if not i:return
        if QMessageBox.question(self,"تأكيد","إلغاء الحالة سيعيد المخزون ويصفر الفاتورة إذا لم توجد تحصيلات. متابعة؟")==QMessageBox.StandardButton.Yes:
            try:self.service.cancel_case(i);self.refresh();info(self,"تم إلغاء الحالة مع تسجيل حركات الإرجاع")
            except Exception as e:error(self,e)

    def delete_case(self):
        i=selected_id(self.table)
        if not i:return
        if QMessageBox.question(self,"حذف نهائي","هذه العملية مخصصة للحالات المسجلة بالخطأ. سيتم حذف الحالة وإلغاء أثرها على المخزون والفاتورة والعمولات. لا يمكن التراجع. متابعة؟")==QMessageBox.StandardButton.Yes:
            try:self.service.delete_case(i);self.refresh();info(self,"تم حذف الحالة وإرجاع آثارها التشغيلية بنجاح")
            except Exception as e:error(self,e)


class FailuresPage(BasePage):
    def __init__(self,service):
        super().__init__(service,"التركيبات الفاشلة والخسائر")
        a=QPushButton("تسجيل حالة فاشلة");a.clicked.connect(self.add);delete=QPushButton("حذف سجل الفشل");delete.setProperty("class","danger");delete.clicked.connect(self.delete_failure)
        if not is_owner(service):delete.hide()
        self.row(a,delete)
        self.table=self.make_table(["ID","التاريخ","رقم الحالة","المريض","الطبيب","المنتج","الفني","السبب","تكلفة خامات","عمولة","إضافي","إجمالي الخسارة","نوع الإعادة"]);self.table.cellDoubleClicked.connect(lambda *_: self.edit_failure() if is_owner(self.service) else None);self.rows=[];self.refresh()
    def refresh(self):
        rows=self.service.list_failures();self.rows=rows;self.table.setRowCount(len(rows))
        for r,x in enumerate(rows):
            vals=[x['id'],x['failure_date'],x['case_no'],x['patient_name'],x['doctor_name'],x['product_names'] or '',x['technician_names'] or '',x['reason'],money(x['material_cost']),money(x['technician_commission']),money(x['additional_expenses']),money(x['total_loss']),ORDER_AR.get(x['remake_type'],x['remake_type'])]
            for c,v in enumerate(vals):
                it=QTableWidgetItem(str(v));
                if c==0:it.setData(Qt.ItemDataRole.UserRole,x['id'])
                self.table.setItem(r,c,it)
    def add(self):
        cases=[x for x in self.service.list_cases() if x['status']!='Cancelled']
        if not cases:error(self,"لا توجد حالات");return
        d=SimpleDialog("تسجيل فشل",self);cb=d.add_combo("الحالة",[f"{x['case_no']} - {x['patient_name']}" for x in cases]);reason=d.add_line("سبب الفشل");m=d.add_number("تكلفة الخامات",0);tc=d.add_number("عمولة الفني",0);extra=d.add_number("مصروفات إضافية",0);kind=d.add_combo("نوع الإعادة",["إعادة مجانية","إعادة مدفوعة"],"إعادة مجانية");notes=d.add_text("ملاحظات")
        if d.exec():
            try:
                case=cases[cb.currentIndex()];self.service.record_failure(case['id'],reason.text(),m.value(),tc.value(),extra.value(),"free_remake" if kind.currentText()=="إعادة مجانية" else "charged_reorder",notes.toPlainText());self.refresh()
            except Exception as e:error(self,e)

    def delete_failure(self):
        if not is_owner(self.service):return
        i=selected_id(self.table)
        if not i:return
        if QMessageBox.question(self,"حذف سجل الفشل","سيتم حذف سجل الفشل وتحديث حالة الحالة إذا لم يبق لها أي سجل فشل. متابعة؟")==QMessageBox.StandardButton.Yes:
            try:self.service.delete_failure(i);self.refresh();info(self,"تم حذف سجل الفشل.")
            except Exception as e:error(self,e)

    def edit_failure(self):
        if not is_owner(self.service):return
        i=selected_id(self.table)
        if not i:return
        x=next((r for r in self.rows if r['id']==i),None)
        if not x:return
        d=SimpleDialog("تعديل سجل فشل - المالك",self);dt=d.add_date("تاريخ الفشل",x['failure_date']);reason=d.add_line("السبب",x['reason']);m=d.add_number("تكلفة الخامات",x['material_cost']);tc=d.add_number("عمولة الفني",x['technician_commission']);extra=d.add_number("مصروفات إضافية",x['additional_expenses']);kind=d.add_combo("نوع الإعادة",["إعادة مجانية","إعادة مدفوعة"],"إعادة مجانية" if x['remake_type']=="free_remake" else "إعادة مدفوعة");notes=d.add_text("ملاحظات",x.get('notes',''))
        if d.exec():
            try:self.service.update_failure(i,failure_date=dt.date().toString('yyyy-MM-dd'),reason=reason.text(),material_cost=m.value(),technician_commission=tc.value(),additional_expenses=extra.value(),remake_type="free_remake" if kind.currentText()=="إعادة مجانية" else "charged_reorder",notes=notes.toPlainText());self.refresh()
            except Exception as e:error(self,e)


class InvoicesPage(BasePage):
    def __init__(self,service):
        super().__init__(service,"الفواتير والتحصيل")
        self.search=QLineEdit();self.search.setPlaceholderText("بحث...");self.search.textChanged.connect(self.refresh);p=QPushButton("تسجيل تحصيل");p.clicked.connect(self.pay);pdf=QPushButton("PDF الفاتورة");pdf.clicked.connect(self.pdf)
        self.row(self.search,p,pdf);self.table=self.make_table(["ID","رقم الفاتورة","التاريخ","الطبيب","المريض","الحالات","الإجمالي","المدفوع","المتبقي","الحالة"]);self.table.cellDoubleClicked.connect(lambda *_: self.edit_invoice() if is_owner(self.service) else None);self.rows=[];self.refresh()
    def refresh(self):
        self.rows=self.service.list_invoices(self.search.text() if hasattr(self,'search') else '');self.table.setRowCount(len(self.rows))
        for r,x in enumerate(self.rows):
            vals=[x['id'],x['invoice_no'],x['invoice_date'],x['doctor_name'],x['patients'] or '',x['case_numbers'] or '',money(x['total']),money(x['paid']),money(x['balance']),x['status']]
            for c,v in enumerate(vals):
                it=QTableWidgetItem(str(v));
                if c==0:it.setData(Qt.ItemDataRole.UserRole,x['id'])
                self.table.setItem(r,c,it)
    def edit_invoice(self):
        if not is_owner(self.service):return
        i=selected_id(self.table)
        if not i:return
        try:inv,items,payments=self.service.invoice_detail(i)
        except Exception as e:error(self,e);return
        docs=self.service.list_doctors(include_archived=True)
        d=SimpleDialog("تعديل الفاتورة - المالك",self);no=d.add_line("رقم الفاتورة",inv['invoice_no']);dt=d.add_date("تاريخ الفاتورة",inv['invoice_date']);doc=d.add_combo("الطبيب",[x['name'] for x in docs],next((x['name'] for x in docs if x['id']==inv['doctor_id']),None));total=d.add_number("الإجمالي",inv['total']);paid=d.add_number("المدفوع",inv['paid']);balance=d.add_number("المتبقي",inv['balance']);status=d.add_combo("الحالة",["unpaid","partial","paid","cancelled"],inv['status']);notes=d.add_text("ملاحظات",inv.get('notes',''))
        hint=QLabel("المريض والحالات تأتي من الحالات المرتبطة. تعديل الطبيب هنا يحدّث الطبيب للحالات المرتبطة أيضاً. تعديل الإجمالي/المدفوع ينشئ تسوية مالك قابلة للتدقيق.");hint.setWordWrap(True);d.form.addRow(hint)
        if d.exec():
            try:
                if abs((paid.value()+balance.value())-total.value())>0.02:raise BusinessError("الإجمالي يجب أن يساوي المدفوع + المتبقي")
                self.service.owner_update_invoice_full(i,invoice_no=no.text(),invoice_date=dt.date().toString('yyyy-MM-dd'),doctor_id=docs[doc.currentIndex()]['id'],total=total.value(),paid=paid.value(),status=status.currentText(),notes=notes.toPlainText());self.refresh()
            except Exception as e:error(self,e)

    def pay(self):
        i=selected_id(self.table)
        if not i:return
        d=SimpleDialog("تسجيل تحصيل",self);a=d.add_number("المبلغ",0);m=d.add_combo("الطريقة",["نقدي","تحويل بنكي","محفظة إلكترونية","أخرى"]);n=d.add_line("ملاحظات")
        if d.exec():
            try:self.service.record_payment(i,a.value(),m.currentText(),n.text());self.refresh()
            except Exception as e:error(self,e)
    def pdf(self):
        i=selected_id(self.table)
        if not i:return
        try:
            path=invoice_pdf(self.service,i);QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)));info(self,f"تم إنشاء وفتح الفاتورة. يمكنك طباعتها أو مشاركتها من قارئ PDF:\n{path}")
        except Exception as e:error(self,e)


class FinancePage(BasePage):
    def __init__(self,service):
        super().__init__(service,"الإيرادات والمصروفات")
        self.summary=QLabel();self.summary.setStyleSheet("background:#f8fafc;border:1px solid #dfe5ee;border-radius:10px;padding:14px;font-size:11pt;color:#1d2939")
        self.outer.addWidget(self.summary)
        a=QPushButton("إضافة مصروف");a.clicked.connect(self.expense);b=QPushButton("إضافة إيراد آخر");b.clicked.connect(self.income);delete=QPushButton("حذف المصروف المحدد");delete.setProperty("class","danger");delete.clicked.connect(self.delete_expense);r=QPushButton("تحديث");r.clicked.connect(self.refresh);self.row(a,b,delete,r)
        self.outer.addWidget(QLabel("المصروفات"));self.table=self.make_table(["ID","التاريخ","الفئة","الوصف","المبلغ"]);self.table.cellDoubleClicked.connect(lambda *_: self.edit_expense() if is_owner(self.service) else None)
        self.outer.addWidget(QLabel("الإيرادات الأخرى"));self.income_table=self.make_table(["ID","التاريخ","الفئة","الوصف","المبلغ"]);self.income_table.cellDoubleClicked.connect(lambda *_: self.edit_income() if is_owner(self.service) else None);self.income_rows=[];self.refresh()
    def refresh(self):
        s=self.service.financial_summary();self.summary.setText(
            f"الإيراد المفوتر: {money(s['invoiced_revenue'])}    |    النقد المحصل: {money(s['cash_collected'])}    |    المديونيات: {money(s['outstanding'])}\n"
            f"تكلفة الخامات: {money(s['material_cost'])}    |    العمولات: {money(s['technician_commissions'])}    |    خسائر الفشل: {money(s['failed_losses'])}\n"
            f"المصروفات: {money(s['expenses'])}    |    مجمل الربح: {money(s['gross_profit'])}    |    صافي الربح: {money(s['net_profit'])}"
        )
        rows=self.service.list_expenses();self.rows=rows;self.table.setRowCount(len(rows))
        for r,x in enumerate(rows):
            vals=[x['id'],x['expense_date'],x['category'],x['description'] or '',money(x['amount'])]
            for c,v in enumerate(vals):
                it=QTableWidgetItem(str(v));
                if c==0:it.setData(Qt.ItemDataRole.UserRole,x['id'])
                self.table.setItem(r,c,it)
        self.income_rows=self.service.list_other_income();self.income_table.setRowCount(len(self.income_rows))
        for r,x in enumerate(self.income_rows):
            vals=[x['id'],x['income_date'],x['category'],x['description'] or '',money(x['amount'])]
            for c,v in enumerate(vals):
                it=QTableWidgetItem(str(v));
                if c==0:it.setData(Qt.ItemDataRole.UserRole,x['id'])
                self.income_table.setItem(r,c,it)
    def edit_expense(self):
        if not is_owner(self.service):return
        i=selected_id(self.table)
        if not i:return
        x=next((r for r in self.rows if r['id']==i),None)
        if not x:return
        d=SimpleDialog("تعديل مصروف - المالك",self);dt=d.add_date("التاريخ",x['expense_date']);cat=d.add_line("الفئة",x['category']);desc=d.add_line("الوصف",x.get('description',''));amount=d.add_number("المبلغ",x['amount'])
        if d.exec():
            try:self.service.update_expense(i,expense_date=dt.date().toString('yyyy-MM-dd'),category=cat.text(),description=desc.text(),amount=amount.value());self.refresh()
            except Exception as e:error(self,e)

    def edit_income(self):
        if not is_owner(self.service):return
        i=selected_id(self.income_table)
        if not i:return
        x=next((r for r in self.income_rows if r['id']==i),None)
        if not x:return
        d=SimpleDialog("تعديل إيراد آخر - المالك",self);dt=d.add_date("التاريخ",x['income_date']);cat=d.add_line("الفئة",x['category']);desc=d.add_line("الوصف",x.get('description',''));amount=d.add_number("المبلغ",x['amount'])
        if d.exec():
            try:self.service.update_other_income(i,income_date=dt.date().toString('yyyy-MM-dd'),category=cat.text(),description=desc.text(),amount=amount.value());self.refresh()
            except Exception as e:error(self,e)

    def delete_expense(self):
        i=selected_id(self.table)
        if not i:return
        if QMessageBox.question(self,"تأكيد","حذف المصروف المحدد؟")==QMessageBox.StandardButton.Yes:
            try:self.service.delete_expense(i);self.refresh();info(self,"تم حذف المصروف.")
            except Exception as e:error(self,e)

    def expense(self):
        d=SimpleDialog("إضافة مصروف",self);cat=d.add_line("الفئة");amount=d.add_number("المبلغ",0);desc=d.add_line("الوصف");dt=d.add_date("التاريخ")
        if d.exec():
            try:self.service.add_expense(cat.text(),amount.value(),desc.text(),dt.date().toString('yyyy-MM-dd'));self.refresh()
            except Exception as e:error(self,e)
    def income(self):
        d=SimpleDialog("إضافة إيراد آخر",self);cat=d.add_line("الفئة");amount=d.add_number("المبلغ",0);desc=d.add_line("الوصف");dt=d.add_date("التاريخ")
        if d.exec():
            try:self.service.add_other_income(cat.text(),amount.value(),desc.text(),dt.date().toString('yyyy-MM-dd'));self.refresh()
            except Exception as e:error(self,e)


class ReportsPage(BasePage):
    def __init__(self,service):
        super().__init__(service,"التقارير والإحصائيات")
        note=QLabel("يمكن تصدير التقارير إلى Excel أو PDF. الملفات تحفظ افتراضياً داخل مجلد Exports الخاص بالبرنامج.");self.outer.addWidget(note)
        grid=QGridLayout();self.outer.addLayout(grid)
        reports=[
            ("التقرير الشهري","monthly"),("التقرير السنوي","yearly"),("أداء الأطباء","doctors"),
            ("مبيعات المنتجات","productsales"),("تقرير المخزون","inventory"),("الحالات الفاشلة","failures"),
            ("عمولات الفنيين","technicians"),("الإيرادات والمصروفات","incomeexpense"),("الأرباح والخسائر","finance"),
            ("المديونيات المستحقة","outstanding")
        ]
        for i,(name,key) in enumerate(reports):
            f=QFrame();f.setObjectName('card');l=QVBoxLayout(f);lbl=QLabel(name);lbl.setStyleSheet('font-weight:700;font-size:11pt');l.addWidget(lbl)
            x=QPushButton("تصدير Excel");p=QPushButton("تصدير PDF");x.clicked.connect(lambda _,k=key,n=name:self.export(k,n,'xlsx'));p.clicked.connect(lambda _,k=key,n=name:self.export(k,n,'pdf'));l.addWidget(x);l.addWidget(p);grid.addWidget(f,i//3,i%3)
        self.outer.addStretch(1)
    def data(self,key):
        from datetime import date
        today=date.today(); month_start=today.replace(day=1).isoformat(); year_start=today.replace(month=1,day=1).isoformat(); end=today.isoformat()
        if key=='monthly':
            s=self.service.financial_summary(month_start,end);h=["البند","القيمة"];r=[[k,v] for k,v in s.items()]
        elif key=='yearly':
            s=self.service.financial_summary(year_start,end);h=["البند","القيمة"];r=[[k,v] for k,v in s.items()]
        elif key=='doctors':
            h=["الطبيب","الهاتف","الحالات","إجمالي الفواتير","المدفوع","المتبقي","فاشلة"];r=[[x['name'],x['phone'] or '',x['total_cases'],x['total_invoices'],x['total_payments'],x['remaining_balance'],x['failed_cases']] for x in self.service.list_doctors()]
        elif key=='productsales':
            h=["المنتج","الفئة","الكمية المباعة","الإيراد"];r=[[x['name'],x['category'] or '',x['quantity'],x['revenue']] for x in self.service.product_sales_report()]
        elif key=='inventory':
            h=["المنتج","الفئة","تكلفة العبوة/البلوك","الوحدات الناتجة","تكلفة الوحدة","سعر البيع","الرصيد","حد التنبيه","الوحدة"];r=[[x['name'],x['category'] or '',x['purchase_cost'],x['yield_units'],x['unit_material_cost'],x['selling_price'],x['stock_qty'],x['min_stock'],x['unit']] for x in self.service.list_products()]
        elif key=='failures':
            h=["التاريخ","الحالة","المريض","الطبيب","السبب","الخسارة"];r=[[x['failure_date'],x['case_no'],x['patient_name'],x['doctor_name'],x['reason'],x['total_loss']] for x in self.service.list_failures()]
        elif key=='technicians':
            h=["الفني","الحالات","مكتملة","فاشلة","إجمالي العمولة","المدفوع","المتبقي"];r=[[x['name'],x['assigned_cases'],x['completed_cases'],x['failed_cases'],x['total_commission'],x['paid_commission'],x['outstanding_commission']] for x in self.service.technician_commission_report()]
        elif key=='incomeexpense':
            s=self.service.financial_summary();h=["البند","القيمة"];r=[["الإيراد المفوتر",s['invoiced_revenue']],["النقد المحصل",s['cash_collected']],["إيرادات أخرى",s['other_income']],["المصروفات",s['expenses']]]
        elif key=='outstanding':
            h=["الفاتورة","التاريخ","الطبيب","الإجمالي","المدفوع","المتبقي","الحالة"];r=[[x['invoice_no'],x['invoice_date'],x['doctor_name'],x['total'],x['paid'],x['balance'],x['status']] for x in self.service.outstanding_report()]
        else:
            s=self.service.financial_summary();h=["البند","القيمة"];r=[[k,v] for k,v in s.items()]
        return h,r
    def export(self,key,name,kind):
        try:
            h,r=self.data(key);path=export_rows_excel(name,h,r) if kind=='xlsx' else export_table_pdf(name,h,r);info(self,f"تم التصدير:\n{path}")
        except Exception as e:error(self,e)


class SettingsPage(BasePage):
    def __init__(self,service):
        super().__init__(service,"الإعدادات والنسخ الاحتياطي")
        s=service.settings();form=QFormLayout();form.setHorizontalSpacing(18);form.setVerticalSpacing(11);form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter);form.setFormAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight);self.outer.addLayout(form)
        self.lab=QLineEdit(s.get('lab_name',''));self.phone=QLineEdit(s.get('lab_phone',''));self.addr=QLineEdit(s.get('lab_address',''));self.footer=QLineEdit(s.get('invoice_footer',''))
        form.addRow("اسم المعمل",self.lab);form.addRow("الهاتف",self.phone);form.addRow("العنوان",self.addr);form.addRow("تذييل الفاتورة",self.footer)
        save=QPushButton("حفظ الإعدادات");save.clicked.connect(self.save);backup=QPushButton("إنشاء نسخة احتياطية");backup.clicked.connect(self.backup);restore=QPushButton("استعادة نسخة");restore.clicked.connect(self.restore);demo=QPushButton("تحميل بيانات تجريبية");demo.clicked.connect(self.demo)
        add_user=QPushButton("إضافة مستخدم");add_user.clicked.connect(self.add_user);password=QPushButton("تغيير كلمة مرور");password.clicked.connect(self.change_password);reset=QPushButton("مسح بيانات التشغيل");reset.setProperty("class","danger");reset.clicked.connect(self.reset_data)
        self.row(save,backup,restore,demo);self.row(add_user,password,reset);self.outer.addStretch(1)
    def save(self):
        try:
            for k,v in [('lab_name',self.lab.text().strip()),('lab_phone',self.phone.text()),('lab_address',self.addr.text()),('invoice_footer',self.footer.text())]:self.service.set_setting(k,v)
            window = self.window()
            if hasattr(window, "refresh_branding"):
                window.refresh_branding()
            info(self,"تم حفظ الإعدادات")
        except Exception as e:error(self,e)
    def backup(self):
        try:info(self,f"تم إنشاء النسخة:\n{self.service.create_backup()}")
        except Exception as e:error(self,e)
    def restore(self):
        path,_=QFileDialog.getOpenFileName(self,"اختر نسخة SQLite","","SQLite (*.sqlite3 *.db);;All files (*.*)")
        if path and QMessageBox.question(self,"تأكيد","سيتم استبدال قاعدة البيانات الحالية بعد إنشاء نسخة أمان. متابعة؟")==QMessageBox.StandardButton.Yes:
            try:self.service.restore_backup(path);info(self,"تمت الاستعادة. أغلق البرنامج وافتحه مرة أخرى.")
            except Exception as e:error(self,e)
    def demo(self):
        try:self.service.seed_demo_data();info(self,"تم تحميل البيانات التجريبية")
        except Exception as e:error(self,e)
    def add_user(self):
        d=SimpleDialog("إضافة مستخدم",self);u=d.add_line("اسم المستخدم");p=d.add_line("كلمة المرور");p.setEchoMode(QLineEdit.EchoMode.Password);r=d.add_combo("الصلاحية",["employee","owner"],"employee")
        if d.exec():
            try:self.service.add_user(u.text(),p.text(),r.currentText());info(self,"تمت إضافة المستخدم")
            except Exception as e:error(self,e)
    def change_password(self):
        try: users=self.service.list_users()
        except Exception as e:error(self,e);return
        d=SimpleDialog("تغيير كلمة المرور",self);cb=d.add_combo("المستخدم",[x['username'] for x in users]);p=d.add_line("كلمة المرور الجديدة");p.setEchoMode(QLineEdit.EchoMode.Password)
        if d.exec():
            try:self.service.change_password(users[cb.currentIndex()]['id'],p.text());info(self,"تم تغيير كلمة المرور")
            except Exception as e:error(self,e)
    def reset_data(self):
        if QMessageBox.warning(self,"تحذير","سيتم مسح كل بيانات التشغيل (الأطباء والحالات والفواتير والمخزون...) بعد إنشاء نسخة احتياطية. هل أنت متأكد؟",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        if QMessageBox.question(self,"تأكيد نهائي","هذا الإجراء لا يمكن التراجع عنه إلا باستعادة النسخة الاحتياطية. متابعة؟")==QMessageBox.StandardButton.Yes:
            try:
                b=self.service.reset_operational_data();info(self,f"تم المسح بعد إنشاء نسخة أمان:\n{b}")
            except Exception as e:error(self,e)


class MainWindow(QMainWindow):
    def __init__(self, service: DentalLabService):
        super().__init__()
        self.service = service
        self.setWindowTitle("نظام إدارة معمل الأسنان")
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

        self.brand = QLabel("")
        self.brand.setObjectName('brand')
        self.brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sl.addWidget(self.brand)
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

        self.refresh_branding()
        self.goto(0)

    def refresh_branding(self):
        try:
            settings = self.service.settings()
            lab_name = str(settings.get("lab_name") or "Elite Dental Lab").strip() or "Elite Dental Lab"
        except Exception:
            lab_name = "Elite Dental Lab"
        self.brand.setText(lab_name)
        self.setWindowTitle(f"نظام إدارة معمل الأسنان - {lab_name}")
        app = QApplication.instance()
        if app is not None:
            app.setApplicationDisplayName(lab_name)

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

from __future__ import annotations

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
QWidget { font-family: 'Segoe UI'; font-size: 10pt; color: #172033; }
QMainWindow, QWidget#root { background: #f5f7fb; }
QFrame#sidebar { background: #192235; border: none; }
QLabel#brand { color: white; font-size: 18pt; font-weight: 700; padding: 18px 10px; }
QPushButton#nav { color: #d6dbea; text-align: right; padding: 11px 14px; border: none; border-radius: 7px; }
QPushButton#nav:hover { background: #26324a; color: white; }
QPushButton#nav:checked { background: #5066e6; color: white; font-weight: 700; }
QLabel#pageTitle { font-size: 21pt; font-weight: 700; color: #172033; }
QFrame#card { background: white; border: 1px solid #e7eaf1; border-radius: 10px; }
QLabel#kpiTitle { color: #667085; font-size: 9pt; }
QLabel#kpiValue { color: #172033; font-size: 18pt; font-weight: 700; }
QLineEdit, QTextEdit, QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox, QListWidget {
    background: white; border: 1px solid #d7dce5; border-radius: 6px; padding: 6px; min-height: 24px;
}
QPushButton { background: #5066e6; color: white; border: none; border-radius: 6px; padding: 8px 13px; }
QPushButton:hover { background: #4054ca; }
QPushButton.secondary { background: #eef1f7; color: #26324a; }
QPushButton.danger { background: #d92d20; }
QTableWidget { background: white; border: 1px solid #e1e5ec; border-radius: 8px; gridline-color: #edf0f5; }
QHeaderView::section { background: #eef2f8; padding: 8px; border: none; border-bottom: 1px solid #d7dce5; font-weight: 700; }
QTableWidget::item { padding: 6px; }
"""


def money(v):
    return f"{float(v or 0):,.2f} ج.م"


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
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(480)
        self.layout = QVBoxLayout(self)
        self.form = QFormLayout()
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.layout.addLayout(self.form)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setText("حفظ")
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("إلغاء")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

    def add_line(self, label, value=""):
        w = QLineEdit(str(value or "")); self.form.addRow(label, w); return w

    def add_text(self, label, value=""):
        w = QTextEdit(str(value or "")); w.setFixedHeight(80); self.form.addRow(label, w); return w

    def add_number(self, label, value=0, maximum=1_000_000_000, decimals=2):
        w = QDoubleSpinBox(); w.setDecimals(decimals); w.setMaximum(maximum); w.setMinimum(-maximum); w.setValue(float(value or 0)); self.form.addRow(label, w); return w

    def add_combo(self, label, items, current=None):
        w = QComboBox(); w.addItems(items)
        if current in items: w.setCurrentText(current)
        self.form.addRow(label, w); return w

    def add_date(self, label, value=None, allow_empty=False):
        w = QDateEdit(); w.setCalendarPopup(True); w.setDisplayFormat("yyyy-MM-dd")
        w.setDate(QDate.fromString(value, "yyyy-MM-dd") if value else QDate.currentDate())
        if allow_empty: w.setSpecialValueText("بدون"); w.setMinimumDate(QDate(1900,1,1))
        self.form.addRow(label, w); return w


class LoginDialog(QDialog):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.user = None
        self.setWindowTitle("تسجيل الدخول - نظام إدارة معمل الأسنان")
        self.setFixedSize(420, 280)
        lay = QVBoxLayout(self)
        title = QLabel("نظام إدارة معمل الأسنان")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:20pt;font-weight:700;color:#23315a;margin:12px")
        lay.addWidget(title)
        f = QFormLayout(); lay.addLayout(f)
        self.username = QLineEdit("admin")
        self.password = QLineEdit("admin123"); self.password.setEchoMode(QLineEdit.EchoMode.Password)
        f.addRow("اسم المستخدم", self.username); f.addRow("كلمة المرور", self.password)
        hint = QLabel("أول تشغيل: admin / admin123")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter); hint.setStyleSheet("color:#667085")
        lay.addWidget(hint)
        btn = QPushButton("دخول"); btn.clicked.connect(self.try_login); lay.addWidget(btn)
        self.password.returnPressed.connect(self.try_login)

    def try_login(self):
        self.user = self.db.authenticate(self.username.text(), self.password.text())
        if self.user: self.accept()
        else: QMessageBox.warning(self, "رفض الدخول", "اسم المستخدم أو كلمة المرور غير صحيحة")


class BasePage(QWidget):
    def __init__(self, service: DentalLabService, title: str):
        super().__init__()
        self.service = service
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(22, 18, 22, 18)
        h = QLabel(title); h.setObjectName("pageTitle"); self.outer.addWidget(h)

    def make_table(self, headers):
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.verticalHeader().setVisible(False)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.outer.addWidget(t, 1)
        return t

    def row(self, *widgets):
        w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(0,0,0,0)
        for x in widgets: l.addWidget(x)
        l.addStretch(1)
        self.outer.addWidget(w)
        return w


class DashboardPage(BasePage):
    def __init__(self, service):
        super().__init__(service, "لوحة التحكم")
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.container = QWidget(); self.v = QVBoxLayout(self.container); self.v.setContentsMargins(0,0,0,0)
        self.outer.addWidget(self.scroll,1); self.scroll.setWidget(self.container)
        self.kpi_grid = QGridLayout(); self.v.addLayout(self.kpi_grid)
        self.chart_grid = QGridLayout(); self.v.addLayout(self.chart_grid)
        self.recent = QTableWidget(0,5); self.recent.setHorizontalHeaderLabels(["رقم الحالة","المريض","الطبيب","الحالة","موعد التسليم"])
        self.recent.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); self.recent.verticalHeader().hide(); self.recent.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.v.addWidget(QLabel("أحدث الحالات")); self.v.addWidget(self.recent)
        self.refresh()

    def card(self, title, value):
        f = QFrame(); f.setObjectName("card"); l=QVBoxLayout(f)
        a=QLabel(title); a.setObjectName("kpiTitle"); b=QLabel(value); b.setObjectName("kpiValue")
        l.addWidget(a); l.addWidget(b); return f

    def bar_chart(self, title, data):
        chart = QChart(); chart.setTitle(title); chart.legend().hide(); chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        series=QBarSeries(); s=QBarSet(title); cats=[]
        for x in data: cats.append(str(x["label"])); s.append(float(x["value"] or 0))
        series.append(s); chart.addSeries(series)
        ax=QBarCategoryAxis(); ax.append(cats); chart.addAxis(ax, Qt.AlignmentFlag.AlignBottom); series.attachAxis(ax)
        ay=QValueAxis(); ay.setLabelFormat("%.0f"); chart.addAxis(ay,Qt.AlignmentFlag.AlignLeft); series.attachAxis(ay)
        view=QChartView(chart); view.setRenderHint(QPainter.RenderHint.Antialiasing); view.setMinimumHeight(260); return view

    def pie_chart(self, title, data):
        chart=QChart(); chart.setTitle(title); series=QPieSeries()
        for x in data: series.append(str(x["label"]), float(x["value"] or 0))
        for sl in series.slices(): sl.setLabelVisible(True); sl.setLabel(f"{sl.label()} {sl.value():.0f}")
        chart.addSeries(series); chart.legend().setVisible(False)
        view=QChartView(chart); view.setRenderHint(QPainter.RenderHint.Antialiasing); view.setMinimumHeight(260); return view

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
            ("مديونيات الأطباء",money(d['outstanding'])),("قيمة المخزون",money(d['inventory_value'])),
            ("عمولات الفنيين",money(d['technician_commissions'])),("تنبيهات المخزون",str(d['low_stock'])),
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
        edit=QPushButton("تعديل"); edit.clicked.connect(self.edit); arch=QPushButton("أرشفة"); arch.clicked.connect(self.archive); stmt=QPushButton("كشف حساب PDF"); stmt.clicked.connect(self.statement)
        self.row(self.search,add,edit,arch,stmt)
        self.table=self.make_table(["ID","الاسم","الهاتف","العيادة","إجمالي الحالات","إجمالي الفواتير","المدفوع","المتبقي","فاشلة"])
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
        d=SimpleDialog("بيانات الطبيب",self); x=x or {}
        a=d.add_line("اسم الطبيب",x.get('name','')); b=d.add_line("الهاتف",x.get('phone','')); c=d.add_line("اسم العيادة",x.get('clinic_name','')); e=d.add_line("العنوان",x.get('address','')); f=d.add_text("ملاحظات",x.get('notes',''))
        if d.exec(): return dict(name=a.text(),phone=b.text(),clinic_name=c.text(),address=e.text(),notes=f.toPlainText())
    def add(self):
        try:
            v=self.form();
            if v: self.service.add_doctor(**v); self.refresh()
        except Exception as e: error(self,e)
    def edit(self):
        i=selected_id(self.table)
        if not i:return
        x=next(r for r in self.rows if r['id']==i)
        try:
            v=self.form(x)
            if v:self.service.update_doctor(i,**v);self.refresh()
        except Exception as e:error(self,e)
    def archive(self):
        i=selected_id(self.table)
        if i and QMessageBox.question(self,"تأكيد","أرشفة الطبيب؟")==QMessageBox.StandardButton.Yes:
            self.service.update_doctor(i,archived=1);self.refresh()
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
        a=QPushButton("إضافة منتج");a.clicked.connect(self.add); e=QPushButton("تعديل");e.clicked.connect(self.edit); s=QPushButton("حركة مخزون");s.clicked.connect(self.stock)
        self.row(self.search,a,e,s)
        self.table=self.make_table(["ID","المنتج","الفئة","تكلفة الشراء","سعر البيع","المتاح","حد التنبيه","الوحدة","المورد","تنبيه"])
        self.rows=[];self.refresh()
    def refresh(self):
        self.rows=self.service.list_products(self.search.text() if hasattr(self,'search') else '')
        self.table.setRowCount(len(self.rows))
        for r,x in enumerate(self.rows):
            vals=[x['id'],x['name'],x['category'] or '',money(x['purchase_cost']),money(x['selling_price']),f"{x['stock_qty']:g}",f"{x['min_stock']:g}",x['unit'],x['supplier'] or '',"منخفض" if x['low_stock'] else '']
            for c,v in enumerate(vals):
                it=QTableWidgetItem(str(v));
                if c==0: it.setData(Qt.ItemDataRole.UserRole,x['id'])
                if x['low_stock']: it.setBackground(QColor('#fff1f0'))
                self.table.setItem(r,c,it)
    def form(self,x=None,new=False):
        d=SimpleDialog("بيانات المنتج",self);x=x or {}
        n=d.add_line("اسم المنتج",x.get('name',''));cat=d.add_line("الفئة",x.get('category',''));desc=d.add_text("الوصف",x.get('description',''))
        cost=d.add_number("تكلفة الشراء",x.get('purchase_cost',0));price=d.add_number("سعر البيع",x.get('selling_price',0));
        stock=d.add_number("الرصيد الافتتاحي",x.get('stock_qty',0),decimals=3) if new else None
        minimum=d.add_number("حد التنبيه",x.get('min_stock',0),decimals=3);unit=d.add_line("الوحدة",x.get('unit','وحدة'));sup=d.add_line("المورد",x.get('supplier',''))
        if d.exec():
            ret=dict(name=n.text(),category=cat.text(),description=desc.toPlainText(),purchase_cost=cost.value(),selling_price=price.value(),min_stock=minimum.value(),unit=unit.text(),supplier=sup.text())
            if new:ret['stock_qty']=stock.value()
            return ret
    def add(self):
        try:
            v=self.form(new=True)
            if v:self.service.add_product(**v);self.refresh()
        except Exception as e:error(self,e)
    def edit(self):
        i=selected_id(self.table)
        if not i:return
        x=next(r for r in self.rows if r['id']==i)
        try:
            v=self.form(x)
            if v:self.service.update_product(i,**v);self.refresh()
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
        b=QPushButton("تحديث");b.clicked.connect(self.refresh);self.row(b)
        self.table=self.make_table(["ID","التاريخ","المنتج","النوع","الكمية","الرصيد بعد الحركة","الحالة المرتبطة","ملاحظات"]);self.refresh()
    def refresh(self):
        rows=self.service.list_stock_movements();self.table.setRowCount(len(rows))
        for r,x in enumerate(rows):
            vals=[x['id'],x['movement_date'],x['product_name'],x['movement_type'],f"{x['quantity']:g}",f"{x['balance_after']:g}",x['case_no'] or '',x['notes'] or '']
            for c,v in enumerate(vals):self.table.setItem(r,c,QTableWidgetItem(str(v)))


class TechniciansPage(BasePage):
    def __init__(self,service):
        super().__init__(service,"الفنيين والعمولات")
        a=QPushButton("إضافة فني");a.clicked.connect(self.add);e=QPushButton("تعديل");e.clicked.connect(self.edit);p=QPushButton("تسجيل دفع عمولة");p.clicked.connect(self.pay)
        self.row(a,e,p);self.table=self.make_table(["ID","الاسم","الهاتف","طريقة العمولة","النسبة %","الثابت","الحالات","مكتملة","فاشلة","إجمالي العمولة","المدفوع","المتبقي"]);self.rows=[];self.refresh()
    def refresh(self):
        self.rows=self.service.list_technicians();self.table.setRowCount(len(self.rows))
        for r,x in enumerate(self.rows):
            vals=[x['id'],x['name'],x['phone'] or '',COMMISSION_AR.get(x['commission_method'],x['commission_method']),x['commission_rate'],money(x['fixed_amount']),x['assigned_cases'],x['completed_cases'],x['failed_cases'],money(x['total_commission']),money(x['paid_commission']),money(x['outstanding_commission'])]
            for c,v in enumerate(vals):
                it=QTableWidgetItem(str(v));
                if c==0:it.setData(Qt.ItemDataRole.UserRole,x['id'])
                self.table.setItem(r,c,it)
    def form(self,x=None):
        d=SimpleDialog("بيانات الفني",self);x=x or {};n=d.add_line("الاسم",x.get('name',''));ph=d.add_line("الهاتف",x.get('phone',''));m=d.add_combo("طريقة العمولة",list(COMMISSION_AR.values()),COMMISSION_AR.get(x.get('commission_method','selling_percent')));rate=d.add_number("النسبة %",x.get('commission_rate',0),100);fixed=d.add_number("المبلغ الثابت",x.get('fixed_amount',0))
        if d.exec():return dict(name=n.text(),phone=ph.text(),commission_method=AR_COMMISSION[m.currentText()],commission_rate=rate.value(),fixed_amount=fixed.value())
    def add(self):
        try:
            v=self.form();
            if v:self.service.add_technician(**v);self.refresh()
        except Exception as e:error(self,e)
    def edit(self):
        i=selected_id(self.table)
        if not i:return
        x=next(r for r in self.rows if r['id']==i)
        try:
            v=self.form(x)
            if v:self.service.update_technician(i,**v);self.refresh()
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
        a=QPushButton("تسجيل حالة جديدة");a.clicked.connect(self.add);ap=QPushButton("إضافة منتج للحالة");ap.clicked.connect(self.add_product);merge=QPushButton("ضم لفاتورة أخرى");merge.clicked.connect(self.merge_invoice);e=QPushButton("تعديل الحالة");e.clicked.connect(self.edit_case);s=QPushButton("تغيير الحالة");s.clicked.connect(self.change_status);c=QPushButton("إلغاء الحالة");c.clicked.connect(self.cancel_case)
        self.row(self.search,self.status,a,ap,merge,e,s,c)
        self.table=self.make_table(["ID","رقم الحالة","الفاتورة","المريض","الطبيب","المنتج","الفني","الحالة","الاستلام","التسليم","الإجمالي"]);self.rows=[];self.refresh()
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
        d.form.addRow("الفنيون",lw)
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
        i=selected_id(self.table)
        if not i:return
        try:c,item,inv,techs=self.service.case_detail(i)
        except Exception as e:error(self,e);return
        if not c or not item:return
        d=SimpleDialog("تعديل الحالة",self);patient=d.add_line("اسم المريض",c['patient_name']);qty=d.add_number("الكمية",item['quantity'],decimals=2);disc=d.add_number("الخصم",item['discount']);delivery=d.add_date("تاريخ التسليم",c['delivery_date']);status=d.add_combo("الحالة",[v for k,v in STATUS_AR.items() if k!='Cancelled'],STATUS_AR.get(c['status'],'جديدة'));notes=d.add_text("ملاحظات",c['notes'] or '')
        if d.exec():
            try:self.service.edit_case(i,patient.text(),qty.value(),disc.value(),delivery.date().toString('yyyy-MM-dd'),AR_STATUS[status.currentText()],notes.toPlainText());self.refresh();info(self,"تم تعديل الحالة مع تسجيل تسوية المخزون/المال عند الحاجة")
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


class FailuresPage(BasePage):
    def __init__(self,service):
        super().__init__(service,"التركيبات الفاشلة والخسائر")
        a=QPushButton("تسجيل حالة فاشلة");a.clicked.connect(self.add);self.row(a)
        self.table=self.make_table(["ID","التاريخ","رقم الحالة","المريض","الطبيب","المنتج","الفني","السبب","تكلفة خامات","عمولة","إضافي","إجمالي الخسارة","نوع الإعادة"]);self.refresh()
    def refresh(self):
        rows=self.service.list_failures();self.table.setRowCount(len(rows))
        for r,x in enumerate(rows):
            vals=[x['id'],x['failure_date'],x['case_no'],x['patient_name'],x['doctor_name'],x['product_names'] or '',x['technician_names'] or '',x['reason'],money(x['material_cost']),money(x['technician_commission']),money(x['additional_expenses']),money(x['total_loss']),ORDER_AR.get(x['remake_type'],x['remake_type'])]
            for c,v in enumerate(vals):self.table.setItem(r,c,QTableWidgetItem(str(v)))
    def add(self):
        cases=[x for x in self.service.list_cases() if x['status']!='Cancelled']
        if not cases:error(self,"لا توجد حالات");return
        d=SimpleDialog("تسجيل فشل",self);cb=d.add_combo("الحالة",[f"{x['case_no']} - {x['patient_name']}" for x in cases]);reason=d.add_line("سبب الفشل");m=d.add_number("تكلفة الخامات",0);tc=d.add_number("عمولة الفني",0);extra=d.add_number("مصروفات إضافية",0);kind=d.add_combo("نوع الإعادة",["إعادة مجانية","إعادة مدفوعة"],"إعادة مجانية");notes=d.add_text("ملاحظات")
        if d.exec():
            try:
                case=cases[cb.currentIndex()];self.service.record_failure(case['id'],reason.text(),m.value(),tc.value(),extra.value(),"free_remake" if kind.currentText()=="إعادة مجانية" else "charged_reorder",notes.toPlainText());self.refresh()
            except Exception as e:error(self,e)


class InvoicesPage(BasePage):
    def __init__(self,service):
        super().__init__(service,"الفواتير والتحصيل")
        self.search=QLineEdit();self.search.setPlaceholderText("بحث...");self.search.textChanged.connect(self.refresh);p=QPushButton("تسجيل تحصيل");p.clicked.connect(self.pay);pdf=QPushButton("PDF الفاتورة");pdf.clicked.connect(self.pdf)
        self.row(self.search,p,pdf);self.table=self.make_table(["ID","رقم الفاتورة","التاريخ","الطبيب","المريض","الحالات","الإجمالي","المدفوع","المتبقي","الحالة"]);self.rows=[];self.refresh()
    def refresh(self):
        self.rows=self.service.list_invoices(self.search.text() if hasattr(self,'search') else '');self.table.setRowCount(len(self.rows))
        for r,x in enumerate(self.rows):
            vals=[x['id'],x['invoice_no'],x['invoice_date'],x['doctor_name'],x['patients'] or '',x['case_numbers'] or '',money(x['total']),money(x['paid']),money(x['balance']),x['status']]
            for c,v in enumerate(vals):
                it=QTableWidgetItem(str(v));
                if c==0:it.setData(Qt.ItemDataRole.UserRole,x['id'])
                self.table.setItem(r,c,it)
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
        self.summary=QLabel();self.summary.setStyleSheet("background:white;border:1px solid #e1e5ec;border-radius:8px;padding:14px;font-size:11pt")
        self.outer.addWidget(self.summary)
        a=QPushButton("إضافة مصروف");a.clicked.connect(self.expense);b=QPushButton("إضافة إيراد آخر");b.clicked.connect(self.income);r=QPushButton("تحديث");r.clicked.connect(self.refresh);self.row(a,b,r)
        self.table=self.make_table(["ID","التاريخ","الفئة","الوصف","المبلغ"]);self.refresh()
    def refresh(self):
        s=self.service.financial_summary();self.summary.setText(
            f"الإيراد المفوتر: {money(s['invoiced_revenue'])}    |    النقد المحصل: {money(s['cash_collected'])}    |    المديونيات: {money(s['outstanding'])}\n"
            f"تكلفة الخامات: {money(s['material_cost'])}    |    العمولات: {money(s['technician_commissions'])}    |    خسائر الفشل: {money(s['failed_losses'])}\n"
            f"المصروفات: {money(s['expenses'])}    |    مجمل الربح: {money(s['gross_profit'])}    |    صافي الربح: {money(s['net_profit'])}"
        )
        rows=self.service.list_expenses();self.table.setRowCount(len(rows))
        for r,x in enumerate(rows):
            vals=[x['id'],x['expense_date'],x['category'],x['description'] or '',money(x['amount'])]
            for c,v in enumerate(vals):self.table.setItem(r,c,QTableWidgetItem(str(v)))
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
            h=["المنتج","الفئة","تكلفة الشراء","سعر البيع","الرصيد","حد التنبيه","الوحدة"];r=[[x['name'],x['category'] or '',x['purchase_cost'],x['selling_price'],x['stock_qty'],x['min_stock'],x['unit']] for x in self.service.list_products()]
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
        s=service.settings();form=QFormLayout();self.outer.addLayout(form)
        self.lab=QLineEdit(s.get('lab_name',''));self.phone=QLineEdit(s.get('lab_phone',''));self.addr=QLineEdit(s.get('lab_address',''));self.footer=QLineEdit(s.get('invoice_footer',''))
        form.addRow("اسم المعمل",self.lab);form.addRow("الهاتف",self.phone);form.addRow("العنوان",self.addr);form.addRow("تذييل الفاتورة",self.footer)
        save=QPushButton("حفظ الإعدادات");save.clicked.connect(self.save);backup=QPushButton("إنشاء نسخة احتياطية");backup.clicked.connect(self.backup);restore=QPushButton("استعادة نسخة");restore.clicked.connect(self.restore);demo=QPushButton("تحميل بيانات تجريبية");demo.clicked.connect(self.demo)
        add_user=QPushButton("إضافة مستخدم");add_user.clicked.connect(self.add_user);password=QPushButton("تغيير كلمة مرور");password.clicked.connect(self.change_password);reset=QPushButton("مسح بيانات التشغيل");reset.setProperty("class","danger");reset.clicked.connect(self.reset_data)
        self.row(save,backup,restore,demo);self.row(add_user,password,reset);self.outer.addStretch(1)
    def save(self):
        try:
            for k,v in [('lab_name',self.lab.text()),('lab_phone',self.phone.text()),('lab_address',self.addr.text()),('invoice_footer',self.footer.text())]:self.service.set_setting(k,v)
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
        self.service=service
        self.setWindowTitle("نظام إدارة معمل الأسنان - Elite Dental Lab")
        self.resize(1500,900)
        root=QWidget();root.setObjectName('root');self.setCentralWidget(root);main=QHBoxLayout(root);main.setContentsMargins(0,0,0,0);main.setSpacing(0)
        sidebar=QFrame();sidebar.setObjectName('sidebar');sidebar.setFixedWidth(235);sl=QVBoxLayout(sidebar);sl.setContentsMargins(10,8,10,12)
        brand=QLabel("Elite Dental Lab");brand.setObjectName('brand');brand.setAlignment(Qt.AlignmentFlag.AlignCenter);sl.addWidget(brand)
        self.stack=QStackedWidget();main.addWidget(self.stack,1);main.addWidget(sidebar)
        self.pages=[];self.nav=[]
        defs=[
            ("لوحة التحكم",DashboardPage),("إدارة الأطباء",DoctorsPage),("إدارة الحالات",CasesPage),("المنتجات",ProductsPage),
            ("المخزون والجرد",InventoryPage),("الفنيين والعمولات",TechniciansPage),("التركيبات الفاشلة",FailuresPage),
            ("الفواتير",InvoicesPage)
        ]
        if service.user.get('role') == 'owner':
            defs += [("الإيرادات والمصروفات",FinancePage),("التقارير والإحصائيات",ReportsPage),("الإعدادات والنسخ الاحتياطي",SettingsPage)]
        for idx,(name,cls) in enumerate(defs):
            page=cls(service);self.stack.addWidget(page);self.pages.append(page)
            b=QPushButton(name);b.setObjectName('nav');b.setCheckable(True);b.clicked.connect(lambda _,i=idx:self.goto(i));sl.addWidget(b);self.nav.append(b)
        sl.addStretch(1)
        u=QLabel(f"المستخدم: {service.user.get('username','')}\nالصلاحية: {service.user.get('role','')}");u.setStyleSheet('color:#aeb7cc;padding:8px');sl.addWidget(u)
        self.goto(0)

    def goto(self,index):
        self.stack.setCurrentIndex(index)
        for i,b in enumerate(self.nav):b.setChecked(i==index)
        page=self.pages[index]
        if hasattr(page,'refresh'):
            try:page.refresh()
            except Exception as e:error(self,e)

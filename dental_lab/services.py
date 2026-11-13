from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import json
import shutil

from .database import Database
from .paths import backups_dir


class BusinessError(Exception):
    pass


class DentalLabService:
    def __init__(self, db: Database, user: dict | None = None):
        self.db = db
        self.user = user or {}

    @property
    def user_id(self):
        return self.user.get("id")

    @staticmethod
    def today():
        return date.today().isoformat()

    # ---------- generic helpers ----------
    def settings(self):
        with self.db.connect() as con:
            return {r["key"]: r["value"] for r in con.execute("SELECT key,value FROM settings")}

    def set_setting(self, key, value):
        with self.db.connect() as con:
            con.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, str(value)))
        self.db.audit("UPDATE", "setting", key, f"{key}={value}", self.user_id)


    # ---------- users / permissions ----------
    def _require_owner(self):
        if self.user.get("role") != "owner":
            raise BusinessError("هذه العملية متاحة لمالك النظام فقط")

    def list_users(self):
        self._require_owner()
        with self.db.connect() as con:
            return [dict(r) for r in con.execute("SELECT id,username,role,active,created_at FROM users ORDER BY id")]

    def add_user(self, username, password, role="employee"):
        self._require_owner()
        username = username.strip()
        if not username or len(password) < 6:
            raise BusinessError("اسم المستخدم مطلوب وكلمة المرور يجب ألا تقل عن 6 أحرف")
        if role not in {"owner","employee"}:
            raise BusinessError("الصلاحية غير صالحة")
        h, salt = self.db.hash_password(password)
        try:
            with self.db.connect() as con:
                cur = con.execute("INSERT INTO users(username,password_hash,salt,role,active,created_at) VALUES(?,?,?,?,1,?)", (username,h,salt,role,self.db.now()))
                uid = cur.lastrowid
        except Exception as e:
            if "UNIQUE" in str(e).upper():
                raise BusinessError("اسم المستخدم مستخدم بالفعل") from e
            raise
        self.db.audit("CREATE","user",uid,f"{username}:{role}",self.user_id)
        return uid

    def change_password(self, user_id, new_password):
        self._require_owner()
        if len(new_password) < 6:
            raise BusinessError("كلمة المرور يجب ألا تقل عن 6 أحرف")
        h, salt = self.db.hash_password(new_password)
        with self.db.connect() as con:
            con.execute("UPDATE users SET password_hash=?,salt=? WHERE id=?", (h,salt,user_id))
        self.db.audit("PASSWORD","user",user_id,"password changed",self.user_id)

    def set_user_active(self, user_id, active):
        self._require_owner()
        if int(user_id) == int(self.user_id or -1) and not active:
            raise BusinessError("لا يمكن تعطيل المستخدم الحالي")
        with self.db.connect() as con:
            con.execute("UPDATE users SET active=? WHERE id=?", (1 if active else 0,user_id))
        self.db.audit("UPDATE","user",user_id,f"active={bool(active)}",self.user_id)

    # ---------- doctors ----------
    def list_doctors(self, search="", include_archived=False):
        sql = """
            SELECT d.*,
                   COALESCE((SELECT COUNT(*) FROM cases c WHERE c.doctor_id=d.id AND c.status!='Cancelled'),0)
                     + COALESCE(a.total_cases_delta,0) AS total_cases,
                   COALESCE((SELECT SUM(i.total) FROM invoices i WHERE i.doctor_id=d.id AND i.status!='cancelled'),0)
                     + COALESCE(a.total_invoices_delta,0) AS total_invoices,
                   COALESCE((SELECT SUM(p.amount) FROM payments p JOIN invoices ix ON ix.id=p.invoice_id WHERE ix.doctor_id=d.id),0)
                     + COALESCE(a.total_payments_delta,0) AS total_payments,
                   (COALESCE((SELECT SUM(i.total) FROM invoices i WHERE i.doctor_id=d.id AND i.status!='cancelled'),0)
                     + COALESCE(a.total_invoices_delta,0))
                   - (COALESCE((SELECT SUM(p.amount) FROM payments p JOIN invoices ix ON ix.id=p.invoice_id WHERE ix.doctor_id=d.id),0)
                     + COALESCE(a.total_payments_delta,0)) AS remaining_balance,
                   COALESCE((SELECT COUNT(*) FROM cases cx WHERE cx.doctor_id=d.id AND cx.failure_status=1),0)
                     + COALESCE(a.failed_cases_delta,0) AS failed_cases
            FROM doctors d
            LEFT JOIN doctor_manual_adjustments a ON a.doctor_id=d.id
            WHERE (?=1 OR d.archived=0)
              AND (d.name LIKE ? OR COALESCE(d.phone,'') LIKE ? OR COALESCE(d.clinic_name,'') LIKE ?)
            ORDER BY d.name
        """
        pat = f"%{search.strip()}%"
        with self.db.connect() as con:
            return [dict(r) for r in con.execute(sql, (1 if include_archived else 0, pat, pat, pat))]

    def owner_set_doctor_summary(self, doctor_id, *, total_cases, total_invoices, total_payments, remaining_balance, failed_cases):
        self._require_owner()
        total_cases=float(total_cases); total_invoices=float(total_invoices); total_payments=float(total_payments); remaining_balance=float(remaining_balance); failed_cases=float(failed_cases)
        if min(total_cases,total_invoices,total_payments,remaining_balance,failed_cases) < -1e-9:
            raise BusinessError("القيم الملخصة لا يمكن أن تكون سالبة")
        if abs((total_payments + remaining_balance) - total_invoices) > 0.02:
            raise BusinessError("إجمالي الفواتير يجب أن يساوي المدفوع + المتبقي")
        with self.db.connect() as con:
            if not con.execute("SELECT id FROM doctors WHERE id=?",(doctor_id,)).fetchone():
                raise BusinessError("الطبيب غير موجود")
            raw_cases=float(con.execute("SELECT COUNT(*) FROM cases WHERE doctor_id=? AND status!='Cancelled'",(doctor_id,)).fetchone()[0])
            raw_invoices=float(con.execute("SELECT COALESCE(SUM(total),0) FROM invoices WHERE doctor_id=? AND status!='cancelled'",(doctor_id,)).fetchone()[0])
            raw_payments=float(con.execute("SELECT COALESCE(SUM(p.amount),0) FROM payments p JOIN invoices i ON i.id=p.invoice_id WHERE i.doctor_id=?",(doctor_id,)).fetchone()[0])
            raw_failed=float(con.execute("SELECT COUNT(*) FROM cases WHERE doctor_id=? AND failure_status=1",(doctor_id,)).fetchone()[0])
            con.execute("""INSERT INTO doctor_manual_adjustments(doctor_id,total_cases_delta,total_invoices_delta,total_payments_delta,failed_cases_delta,updated_at)
                           VALUES(?,?,?,?,?,?)
                           ON CONFLICT(doctor_id) DO UPDATE SET total_cases_delta=excluded.total_cases_delta,total_invoices_delta=excluded.total_invoices_delta,
                           total_payments_delta=excluded.total_payments_delta,failed_cases_delta=excluded.failed_cases_delta,updated_at=excluded.updated_at""",
                        (doctor_id,total_cases-raw_cases,total_invoices-raw_invoices,total_payments-raw_payments,failed_cases-raw_failed,self.db.now()))
        self.db.audit("OWNER_CORRECTION","doctor_summary",doctor_id,f"cases={total_cases}; invoices={total_invoices}; paid={total_payments}; remaining={remaining_balance}; failed={failed_cases}",self.user_id)

    def add_doctor(self, name, phone="", clinic_name="", address="", notes=""):
        if not name.strip():
            raise BusinessError("اسم الطبيب مطلوب")
        now = self.db.now()
        with self.db.connect() as con:
            cur = con.execute(
                "INSERT INTO doctors(name,phone,clinic_name,address,notes,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                (name.strip(), phone.strip(), clinic_name.strip(), address.strip(), notes.strip(), now, now),
            )
            rid = cur.lastrowid
        self.db.audit("CREATE", "doctor", rid, name, self.user_id)
        return rid

    def update_doctor(self, doctor_id, **fields):
        self._require_owner()
        allowed = {"name", "phone", "clinic_name", "address", "notes", "archived"}
        fields = {k: v for k, v in fields.items() if k in allowed}
        if not fields:
            return
        fields["updated_at"] = self.db.now()
        sql = "UPDATE doctors SET " + ",".join(f"{k}=?" for k in fields) + " WHERE id=?"
        with self.db.connect() as con:
            con.execute(sql, tuple(fields.values()) + (doctor_id,))
        self.db.audit("UPDATE", "doctor", doctor_id, json.dumps(fields, ensure_ascii=False), self.user_id)


    def delete_doctor(self, doctor_id):
        """Delete an unused doctor; archive doctors that already have financial/case history."""
        self._require_owner()
        with self.db.connect() as con:
            row = con.execute("SELECT * FROM doctors WHERE id=?", (doctor_id,)).fetchone()
            if not row:
                raise BusinessError("الطبيب غير موجود")
            linked = con.execute("SELECT COUNT(*) FROM cases WHERE doctor_id=?", (doctor_id,)).fetchone()[0]
            linked += con.execute("SELECT COUNT(*) FROM invoices WHERE doctor_id=?", (doctor_id,)).fetchone()[0]
            if linked:
                con.execute("UPDATE doctors SET archived=1,updated_at=? WHERE id=?", (self.db.now(), doctor_id))
                result = "archived"
                action = "ARCHIVE"
            else:
                con.execute("DELETE FROM doctors WHERE id=?", (doctor_id,))
                result = "deleted"
                action = "DELETE"
        self.db.audit(action, "doctor", doctor_id, row["name"], self.user_id)
        return result

    def doctor_invoices(self, doctor_id):
        with self.db.connect() as con:
            return [dict(r) for r in con.execute(
                "SELECT * FROM invoices WHERE doctor_id=? ORDER BY invoice_date,id", (doctor_id,)
            )]

    def product_sales_report(self):
        with self.db.connect() as con:
            return [dict(r) for r in con.execute(
                """SELECT p.name, p.category,
                          COALESCE(SUM(CASE WHEN i.status!='cancelled' THEN ii.quantity ELSE 0 END),0) quantity,
                          COALESCE(SUM(CASE WHEN i.status!='cancelled' THEN ii.line_total ELSE 0 END),0) revenue
                   FROM products p LEFT JOIN invoice_items ii ON ii.product_id=p.id
                   LEFT JOIN invoices i ON i.id=ii.invoice_id
                   GROUP BY p.id ORDER BY revenue DESC"""
            )]

    def technician_commission_report(self):
        return self.list_technicians(True)

    def outstanding_report(self):
        with self.db.connect() as con:
            return [dict(r) for r in con.execute(
                """SELECT i.invoice_no,i.invoice_date,d.name doctor_name,i.total,i.paid,i.balance,i.status
                   FROM invoices i JOIN doctors d ON d.id=i.doctor_id
                   WHERE i.balance>0 AND i.status!='cancelled' ORDER BY i.invoice_date,i.id"""
            )]

    def reset_operational_data(self):
        self._require_owner()
        safety = self.create_backup()
        tables = [
            "commission_payments","failures","payments","invoice_items","invoice_cases","invoices",
            "case_technicians","case_items","stock_movements","cases","technician_product_rates",
            "expenses","other_income","technician_manual_adjustments","doctor_manual_adjustments","technicians","products","doctors","audit_log"
        ]
        with self.db.connect() as con:
            for table in tables:
                con.execute(f"DELETE FROM {table}")
            placeholders = ','.join('?' for _ in tables)
            con.execute(f"DELETE FROM sqlite_sequence WHERE name IN ({placeholders})", tables)
        self.db.audit("RESET","database",None,"operational data reset",self.user_id)
        return safety

    # ---------- products ----------
    def list_products(self, search="", include_archived=False):
        pat = f"%{search.strip()}%"
        with self.db.connect() as con:
            rows = con.execute(
                """
                SELECT *,
                       CASE WHEN yield_units>0 THEN purchase_cost/yield_units ELSE purchase_cost END AS unit_material_cost,
                       CASE WHEN stock_qty<=min_stock THEN 1 ELSE 0 END AS low_stock
                FROM products
                WHERE (?=1 OR archived=0)
                  AND (name LIKE ? OR COALESCE(category,'') LIKE ? OR COALESCE(supplier,'') LIKE ?)
                ORDER BY name
                """,
                (1 if include_archived else 0, pat, pat, pat),
            )
            return [dict(r) for r in rows]

    def add_product(self, name, category="", description="", purchase_cost=0, yield_units=1, selling_price=0,
                    stock_qty=0, min_stock=0, unit="وحدة", supplier=""):
        if not name.strip():
            raise BusinessError("اسم المنتج مطلوب")
        vals = [float(x or 0) for x in (purchase_cost, selling_price, stock_qty, min_stock)]
        yield_units = float(yield_units or 0)
        if any(v < 0 for v in vals):
            raise BusinessError("القيم المالية والمخزون لا يمكن أن تكون سالبة")
        if yield_units <= 0:
            raise BusinessError("عدد الوحدات الناتجة من العبوة/البلوك يجب أن يكون أكبر من صفر")
        now = self.db.now()
        with self.db.connect() as con:
            cur = con.execute(
                """INSERT INTO products(name,category,description,purchase_cost,yield_units,selling_price,stock_qty,min_stock,unit,supplier,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (name.strip(), category.strip(), description.strip(), vals[0], yield_units, vals[1], vals[2], vals[3], unit.strip() or "وحدة", supplier.strip(), now, now),
            )
            pid = cur.lastrowid
            if vals[2] > 0:
                con.execute(
                    "INSERT INTO stock_movements(product_id,movement_type,quantity,balance_after,movement_date,notes,created_at) VALUES(?,?,?,?,?,?,?)",
                    (pid, "IN", vals[2], vals[2], self.today(), "رصيد افتتاحي", now),
                )
        self.db.audit("CREATE", "product", pid, name, self.user_id)
        return pid

    def update_product(self, product_id, **fields):
        self._require_owner()
        allowed = {"name", "category", "description", "purchase_cost", "yield_units", "selling_price", "min_stock", "unit", "supplier", "archived"}
        fields = {k: v for k, v in fields.items() if k in allowed}
        if "yield_units" in fields and float(fields["yield_units"] or 0) <= 0:
            raise BusinessError("عدد الوحدات الناتجة من العبوة/البلوك يجب أن يكون أكبر من صفر")
        if "purchase_cost" in fields and float(fields["purchase_cost"] or 0) < 0:
            raise BusinessError("تكلفة الشراء لا يمكن أن تكون سالبة")
        if not fields:
            return
        fields["updated_at"] = self.db.now()
        sql = "UPDATE products SET " + ",".join(f"{k}=?" for k in fields) + " WHERE id=?"
        with self.db.connect() as con:
            con.execute(sql, tuple(fields.values()) + (product_id,))
        self.db.audit("UPDATE", "product", product_id, json.dumps(fields, ensure_ascii=False), self.user_id)

    def delete_product(self, product_id):
        """Delete an unused product; archive products referenced by operational history."""
        self._require_owner()
        with self.db.connect() as con:
            row = con.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
            if not row:
                raise BusinessError("المنتج غير موجود")
            linked = con.execute("SELECT COUNT(*) FROM case_items WHERE product_id=?", (product_id,)).fetchone()[0]
            linked += con.execute("SELECT COUNT(*) FROM invoice_items WHERE product_id=?", (product_id,)).fetchone()[0]
            linked += con.execute("SELECT COUNT(*) FROM case_technicians WHERE product_id=?", (product_id,)).fetchone()[0]
            linked += con.execute("SELECT COUNT(*) FROM stock_movements WHERE product_id=? AND related_case_id IS NOT NULL", (product_id,)).fetchone()[0]
            if linked:
                con.execute("UPDATE products SET archived=1,updated_at=? WHERE id=?", (self.db.now(), product_id))
                result = "archived"
                action = "ARCHIVE"
            else:
                con.execute("DELETE FROM technician_product_rates WHERE product_id=?", (product_id,))
                con.execute("DELETE FROM stock_movements WHERE product_id=?", (product_id,))
                con.execute("DELETE FROM products WHERE id=?", (product_id,))
                result = "deleted"
                action = "DELETE"
        self.db.audit(action, "product", product_id, row["name"], self.user_id)
        return result

    def stock_movement(self, product_id, movement_type, quantity, notes="", related_case_id=None):
        movement_type = movement_type.upper()
        if movement_type not in {"IN", "OUT", "ADJUSTMENT", "WASTE", "RETURN"}:
            raise BusinessError("نوع حركة المخزون غير صالح")
        quantity = float(quantity)
        if quantity == 0:
            raise BusinessError("الكمية يجب ألا تساوي صفر")
        now = self.db.now()
        with self.db.connect() as con:
            p = con.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
            if not p:
                raise BusinessError("المنتج غير موجود")
            current = float(p["stock_qty"])
            if movement_type in {"IN", "RETURN"}:
                delta = abs(quantity)
            elif movement_type in {"OUT", "WASTE"}:
                delta = -abs(quantity)
            else:  # ADJUSTMENT is signed
                delta = quantity
            new_balance = current + delta
            if new_balance < -1e-9:
                raise BusinessError(f"المخزون غير كافٍ. الرصيد الحالي: {current:g}")
            con.execute("UPDATE products SET stock_qty=?,updated_at=? WHERE id=?", (new_balance, now, product_id))
            con.execute(
                "INSERT INTO stock_movements(product_id,movement_type,quantity,balance_after,movement_date,related_case_id,notes,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (product_id, movement_type, delta, new_balance, self.today(), related_case_id, notes, now),
            )
        self.db.audit("STOCK", "product", product_id, f"{movement_type} {quantity}", self.user_id)
        return new_balance

    def list_stock_movements(self, product_id=None):
        sql = """
            SELECT sm.*, p.name AS product_name, c.case_no
            FROM stock_movements sm
            JOIN products p ON p.id=sm.product_id
            LEFT JOIN cases c ON c.id=sm.related_case_id
            WHERE (? IS NULL OR sm.product_id=?)
            ORDER BY sm.id DESC
        """
        with self.db.connect() as con:
            return [dict(r) for r in con.execute(sql, (product_id, product_id))]

    def delete_stock_movement(self, movement_id):
        self._require_owner()
        with self.db.connect() as con:
            row=con.execute("SELECT * FROM stock_movements WHERE id=?",(movement_id,)).fetchone()
            if not row: raise BusinessError("حركة المخزون غير موجودة")
            pid=row["product_id"]
            con.execute("DELETE FROM stock_movements WHERE id=?",(movement_id,))
            movements=con.execute("SELECT id,quantity FROM stock_movements WHERE product_id=? ORDER BY id",(pid,)).fetchall()
            balance=0.0
            for m in movements:
                balance += float(m["quantity"])
                if balance < -1e-9:
                    raise BusinessError("لا يمكن حذف هذه الحركة لأنها ستجعل الرصيد التاريخي سالباً")
                con.execute("UPDATE stock_movements SET balance_after=? WHERE id=?",(balance,m["id"]))
            con.execute("UPDATE products SET stock_qty=?,updated_at=? WHERE id=?",(balance,self.db.now(),pid))
        self.db.audit("OWNER_DELETE","stock_movement",movement_id,f"product={pid}; qty={row['quantity']}",self.user_id)

    # ---------- technicians ----------
    def list_technicians(self, include_archived=False):
        with self.db.connect() as con:
            rows = con.execute(
                """
                SELECT t.*,
                       COALESCE((SELECT COUNT(DISTINCT ct.case_id) FROM case_technicians ct WHERE ct.technician_id=t.id),0)
                         + COALESCE(a.assigned_cases_delta,0) assigned_cases,
                       COALESCE((SELECT COUNT(*) FROM case_technicians ct JOIN cases c ON c.id=ct.case_id WHERE ct.technician_id=t.id AND c.status IN ('Completed','Delivered')),0)
                         + COALESCE(a.completed_cases_delta,0) completed_cases,
                       COALESCE((SELECT COUNT(*) FROM case_technicians ct JOIN cases c ON c.id=ct.case_id WHERE ct.technician_id=t.id AND c.failure_status=1),0)
                         + COALESCE(a.failed_cases_delta,0) failed_cases,
                       COALESCE((SELECT SUM(ct.commission_amount) FROM case_technicians ct WHERE ct.technician_id=t.id),0)
                         + COALESCE(a.total_commission_delta,0) total_commission,
                       COALESCE((SELECT SUM(cp.amount) FROM commission_payments cp WHERE cp.technician_id=t.id),0)
                         + COALESCE(a.paid_commission_delta,0) paid_commission
                FROM technicians t
                LEFT JOIN technician_manual_adjustments a ON a.technician_id=t.id
                WHERE (?=1 OR t.archived=0)
                ORDER BY t.name
                """,
                (1 if include_archived else 0,),
            )
            data = []
            for r in rows:
                d = dict(r)
                d["outstanding_commission"] = float(d["total_commission"]) - float(d["paid_commission"])
                data.append(d)
            return data

    def owner_set_technician_summary(self, technician_id, *, assigned_cases, completed_cases, failed_cases, total_commission, paid_commission, outstanding_commission):
        self._require_owner()
        vals=list(map(float,[assigned_cases,completed_cases,failed_cases,total_commission,paid_commission,outstanding_commission]))
        if min(vals) < -1e-9:
            raise BusinessError("القيم الملخصة لا يمكن أن تكون سالبة")
        if abs((paid_commission + outstanding_commission) - total_commission) > 0.02:
            raise BusinessError("إجمالي العمولة يجب أن يساوي المدفوع + المتبقي")
        with self.db.connect() as con:
            if not con.execute("SELECT id FROM technicians WHERE id=?",(technician_id,)).fetchone(): raise BusinessError("الفني غير موجود")
            raw_assigned=float(con.execute("SELECT COUNT(DISTINCT case_id) FROM case_technicians WHERE technician_id=?",(technician_id,)).fetchone()[0])
            raw_completed=float(con.execute("SELECT COUNT(*) FROM case_technicians ct JOIN cases c ON c.id=ct.case_id WHERE ct.technician_id=? AND c.status IN ('Completed','Delivered')",(technician_id,)).fetchone()[0])
            raw_failed=float(con.execute("SELECT COUNT(*) FROM case_technicians ct JOIN cases c ON c.id=ct.case_id WHERE ct.technician_id=? AND c.failure_status=1",(technician_id,)).fetchone()[0])
            raw_total=float(con.execute("SELECT COALESCE(SUM(commission_amount),0) FROM case_technicians WHERE technician_id=?",(technician_id,)).fetchone()[0])
            raw_paid=float(con.execute("SELECT COALESCE(SUM(amount),0) FROM commission_payments WHERE technician_id=?",(technician_id,)).fetchone()[0])
            con.execute("""INSERT INTO technician_manual_adjustments(technician_id,assigned_cases_delta,completed_cases_delta,failed_cases_delta,total_commission_delta,paid_commission_delta,updated_at)
                           VALUES(?,?,?,?,?,?,?)
                           ON CONFLICT(technician_id) DO UPDATE SET assigned_cases_delta=excluded.assigned_cases_delta,completed_cases_delta=excluded.completed_cases_delta,
                           failed_cases_delta=excluded.failed_cases_delta,total_commission_delta=excluded.total_commission_delta,paid_commission_delta=excluded.paid_commission_delta,updated_at=excluded.updated_at""",
                        (technician_id,assigned_cases-raw_assigned,completed_cases-raw_completed,failed_cases-raw_failed,total_commission-raw_total,paid_commission-raw_paid,self.db.now()))
        self.db.audit("OWNER_CORRECTION","technician_summary",technician_id,f"assigned={assigned_cases}; completed={completed_cases}; failed={failed_cases}; total={total_commission}; paid={paid_commission}",self.user_id)

    def add_technician(self, name, phone="", commission_rate=0, commission_method="selling_percent", fixed_amount=0):
        if not name.strip():
            raise BusinessError("اسم الفني مطلوب")
        if commission_method not in {"selling_percent", "profit_percent", "fixed", "custom"}:
            raise BusinessError("طريقة العمولة غير صالحة")
        now = self.db.now()
        with self.db.connect() as con:
            cur = con.execute(
                "INSERT INTO technicians(name,phone,commission_rate,commission_method,fixed_amount,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                (name.strip(), phone.strip(), float(commission_rate or 0), commission_method, float(fixed_amount or 0), now, now),
            )
            tid = cur.lastrowid
        self.db.audit("CREATE", "technician", tid, name, self.user_id)
        return tid

    def update_technician(self, technician_id, **fields):
        self._require_owner()
        allowed = {"name", "phone", "commission_rate", "commission_method", "fixed_amount", "archived"}
        fields = {k: v for k, v in fields.items() if k in allowed}
        if not fields:
            return
        fields["updated_at"] = self.db.now()
        with self.db.connect() as con:
            con.execute("UPDATE technicians SET " + ",".join(f"{k}=?" for k in fields) + " WHERE id=?", tuple(fields.values()) + (technician_id,))
        self.db.audit("UPDATE", "technician", technician_id, json.dumps(fields, ensure_ascii=False), self.user_id)

    def delete_technician(self, technician_id):
        """Delete an unused technician; archive technicians with commission/case history."""
        self._require_owner()
        with self.db.connect() as con:
            row = con.execute("SELECT * FROM technicians WHERE id=?", (technician_id,)).fetchone()
            if not row:
                raise BusinessError("الفني غير موجود")
            linked = con.execute("SELECT COUNT(*) FROM case_technicians WHERE technician_id=?", (technician_id,)).fetchone()[0]
            linked += con.execute("SELECT COUNT(*) FROM commission_payments WHERE technician_id=?", (technician_id,)).fetchone()[0]
            if linked:
                con.execute("UPDATE technicians SET archived=1,updated_at=? WHERE id=?", (self.db.now(), technician_id))
                result = "archived"
                action = "ARCHIVE"
            else:
                con.execute("DELETE FROM technician_product_rates WHERE technician_id=?", (technician_id,))
                con.execute("DELETE FROM technicians WHERE id=?", (technician_id,))
                result = "deleted"
                action = "DELETE"
        self.db.audit(action, "technician", technician_id, row["name"], self.user_id)
        return result

    def record_commission_payment(self, technician_id, amount, notes="", payment_date=None):
        amount = float(amount)
        if amount <= 0:
            raise BusinessError("قيمة الدفعة يجب أن تكون أكبر من صفر")
        tech = next((x for x in self.list_technicians(True) if x["id"] == technician_id), None)
        if not tech:
            raise BusinessError("الفني غير موجود")
        if amount > tech["outstanding_commission"] + 1e-9:
            raise BusinessError("الدفعة أكبر من العمولة المستحقة")
        with self.db.connect() as con:
            con.execute(
                "INSERT INTO commission_payments(technician_id,amount,payment_date,notes,created_at) VALUES(?,?,?,?,?)",
                (technician_id, amount, payment_date or self.today(), notes, self.db.now()),
            )
        self.db.audit("PAY", "technician", technician_id, f"commission {amount}", self.user_id)

    # ---------- cases / invoice creation ----------
    def next_case_no(self):
        prefix = datetime.now().strftime("C%Y%m")
        with self.db.connect() as con:
            n = con.execute("SELECT COUNT(*) FROM cases WHERE case_no LIKE ?", (prefix + "%",)).fetchone()[0] + 1
        return f"{prefix}-{n:04d}"

    def next_invoice_no(self):
        prefix = datetime.now().strftime("INV%Y%m")
        with self.db.connect() as con:
            n = con.execute("SELECT COUNT(*) FROM invoices WHERE invoice_no LIKE ?", (prefix + "%",)).fetchone()[0] + 1
        return f"{prefix}-{n:04d}"

    @staticmethod
    def _commission_amount(method, rate, fixed_amount, custom, selling_total, cost_total, qty):
        if method == "selling_percent":
            return max(0.0, selling_total * rate / 100.0)
        if method == "profit_percent":
            return max(0.0, (selling_total - cost_total) * rate / 100.0)
        if method == "fixed":
            return max(0.0, fixed_amount * qty)
        return max(0.0, custom)

    def create_case(self, doctor_id: int, patient_name: str, product_id: int, quantity: float,
                    tooth_numbers="", technician_ids=None, received_date=None, delivery_date=None,
                    discount=0, status="New", notes="", order_kind="original", custom_commission=0):
        technician_ids = technician_ids or []
        if not patient_name.strip():
            raise BusinessError("اسم المريض مطلوب")
        quantity = float(quantity)
        discount = float(discount or 0)
        if quantity <= 0:
            raise BusinessError("الكمية يجب أن تكون أكبر من صفر")
        if discount < 0:
            raise BusinessError("الخصم لا يمكن أن يكون سالباً")
        if order_kind not in {"original", "free_remake", "charged_reorder"}:
            raise BusinessError("نوع الطلب غير صالح")
        now = self.db.now()
        case_no = self.next_case_no()
        invoice_no = self.next_invoice_no()
        with self.db.connect() as con:
            doctor = con.execute("SELECT * FROM doctors WHERE id=? AND archived=0", (doctor_id,)).fetchone()
            product = con.execute("SELECT * FROM products WHERE id=? AND archived=0", (product_id,)).fetchone()
            if not doctor or not product:
                raise BusinessError("الطبيب أو المنتج غير صالح")
            if float(product["stock_qty"]) < quantity:
                raise BusinessError(f"المخزون غير كافٍ للمنتج {product['name']}. المتاح {product['stock_qty']:g}")

            unit_price = 0.0 if order_kind == "free_remake" else float(product["selling_price"])
            raw_total = unit_price * quantity
            actual_discount = min(discount, raw_total)
            line_total = max(0.0, raw_total - actual_discount)
            unit_material_cost = float(product["purchase_cost"]) / max(float(product["yield_units"] or 1), 1e-9)
            cost_total = unit_material_cost * quantity

            cur = con.execute(
                """INSERT INTO cases(case_no,received_date,delivery_date,doctor_id,patient_name,status,notes,failure_status,order_kind,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (case_no, received_date or self.today(), delivery_date or None, doctor_id, patient_name.strip(), status, notes.strip(), 0, order_kind, now, now),
            )
            case_id = cur.lastrowid
            con.execute(
                """INSERT INTO case_items(case_id,product_id,tooth_numbers,quantity,unit_price_snapshot,purchase_cost_snapshot,discount,line_total)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (case_id, product_id, tooth_numbers.strip(), quantity, unit_price, unit_material_cost, actual_discount, line_total),
            )

            # Always record the stock deduction as a movement.
            new_balance = float(product["stock_qty"]) - quantity
            con.execute("UPDATE products SET stock_qty=?,updated_at=? WHERE id=?", (new_balance, now, product_id))
            con.execute(
                """INSERT INTO stock_movements(product_id,movement_type,quantity,balance_after,movement_date,related_case_id,notes,created_at)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (product_id, "OUT", -quantity, new_balance, received_date or self.today(), case_id, f"استخدام في الحالة {case_no}", now),
            )

            # Snapshot commission terms at registration time.
            if technician_ids:
                share = line_total / len(technician_ids)
                cost_share = cost_total / len(technician_ids)
                qty_share = quantity / len(technician_ids)
                for tid in technician_ids:
                    tech = con.execute("SELECT * FROM technicians WHERE id=? AND archived=0", (tid,)).fetchone()
                    if not tech:
                        raise BusinessError("أحد الفنيين المحددين غير صالح")
                    override = con.execute(
                        "SELECT * FROM technician_product_rates WHERE technician_id=? AND product_id=?", (tid, product_id)
                    ).fetchone()
                    rate = float(override["commission_rate"] if override and override["commission_rate"] is not None else tech["commission_rate"])
                    fixed = float(override["fixed_amount"] if override and override["fixed_amount"] is not None else tech["fixed_amount"])
                    method = tech["commission_method"]
                    # Percentage commissions use the technician's allocated revenue/profit share.
                    # Fixed-per-unit commission is NOT divided by technician count: each selected
                    # technician receives their configured fixed amount for every unit handled.
                    commission_qty = quantity if method == "fixed" else qty_share
                    commission = self._commission_amount(method, rate, fixed, float(custom_commission or 0), share, cost_share, commission_qty)
                    con.execute(
                        """INSERT INTO case_technicians(case_id,technician_id,product_id,commission_method_snapshot,commission_rate_snapshot,fixed_amount_snapshot,custom_commission,commission_amount)
                           VALUES(?,?,?,?,?,?,?,?)""",
                        (case_id, tid, product_id, method, rate, fixed, float(custom_commission or 0), commission),
                    )

            # Every case has a traceable invoice. Free remake => zero revenue invoice.
            cur = con.execute(
                """INSERT INTO invoices(invoice_no,doctor_id,invoice_date,subtotal,discount,total,paid,balance,status,notes,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (invoice_no, doctor_id, received_date or self.today(), raw_total, actual_discount, line_total, 0, line_total, "paid" if line_total == 0 else "unpaid", notes.strip(), now, now),
            )
            invoice_id = cur.lastrowid
            con.execute("INSERT INTO invoice_cases(invoice_id,case_id) VALUES(?,?)", (invoice_id, case_id))
            con.execute(
                """INSERT INTO invoice_items(invoice_id,case_id,product_id,description,quantity,unit_price,discount,line_total)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (invoice_id, case_id, product_id, product["name"], quantity, unit_price, actual_discount, line_total),
            )

        self.db.audit("CREATE", "case", case_id, f"{case_no}; invoice={invoice_no}", self.user_id)
        return case_id, case_no, invoice_id, invoice_no

    def list_cases(self, search="", status=""):
        pat = f"%{search.strip()}%"
        with self.db.connect() as con:
            rows = con.execute(
                """
                SELECT c.*, d.name doctor_name,
                       GROUP_CONCAT(DISTINCT p.name) product_names,
                       GROUP_CONCAT(DISTINCT t.name) technician_names,
                       COALESCE(SUM(DISTINCT ci.line_total),0) total,
                       i.invoice_no
                FROM cases c
                JOIN doctors d ON d.id=c.doctor_id
                LEFT JOIN case_items ci ON ci.case_id=c.id
                LEFT JOIN products p ON p.id=ci.product_id
                LEFT JOIN case_technicians ct ON ct.case_id=c.id
                LEFT JOIN technicians t ON t.id=ct.technician_id
                LEFT JOIN invoice_cases ic ON ic.case_id=c.id
                LEFT JOIN invoices i ON i.id=ic.invoice_id
                WHERE (c.case_no LIKE ? OR c.patient_name LIKE ? OR d.name LIKE ? OR COALESCE(i.invoice_no,'') LIKE ?)
                  AND (?='' OR c.status=?)
                GROUP BY c.id
                ORDER BY c.id DESC
                """,
                (pat, pat, pat, pat, status, status),
            )
            return [dict(r) for r in rows]



    def add_product_to_case(self, case_id, product_id, quantity, tooth_numbers="", discount=0):
        quantity=float(quantity); discount=float(discount or 0)
        if quantity<=0 or discount<0:
            raise BusinessError("بيانات المنتج الإضافي غير صالحة")
        now=self.db.now()
        with self.db.connect() as con:
            c=con.execute("SELECT * FROM cases WHERE id=?",(case_id,)).fetchone()
            inv=con.execute("SELECT i.* FROM invoices i JOIN invoice_cases ic ON ic.invoice_id=i.id WHERE ic.case_id=?",(case_id,)).fetchone()
            p=con.execute("SELECT * FROM products WHERE id=? AND archived=0",(product_id,)).fetchone()
            if not c or not inv or not p: raise BusinessError("الحالة أو المنتج غير صالح")
            if c["status"]=="Cancelled": raise BusinessError("لا يمكن تعديل حالة ملغاة")
            if float(p["stock_qty"])<quantity: raise BusinessError(f"المخزون غير كافٍ. المتاح {p['stock_qty']:g}")
            unit_price=0.0 if c["order_kind"]=="free_remake" else float(p["selling_price"])
            raw=unit_price*quantity; actual_discount=min(discount,raw); total=max(0.0,raw-actual_discount)
            unit_material_cost=float(p["purchase_cost"])/max(float(p["yield_units"] or 1),1e-9); cost=unit_material_cost*quantity
            cur=con.execute("INSERT INTO case_items(case_id,product_id,tooth_numbers,quantity,unit_price_snapshot,purchase_cost_snapshot,discount,line_total) VALUES(?,?,?,?,?,?,?,?)",
                            (case_id,product_id,tooth_numbers.strip(),quantity,unit_price,unit_material_cost,actual_discount,total))
            new_balance=float(p["stock_qty"])-quantity
            con.execute("UPDATE products SET stock_qty=?,updated_at=? WHERE id=?",(new_balance,now,product_id))
            con.execute("INSERT INTO stock_movements(product_id,movement_type,quantity,balance_after,movement_date,related_case_id,notes,created_at) VALUES(?,?,?,?,?,?,?,?)",
                        (product_id,"OUT",-quantity,new_balance,self.today(),case_id,f"إضافة منتج للحالة {c['case_no']}",now))
            con.execute("INSERT INTO invoice_items(invoice_id,case_id,product_id,description,quantity,unit_price,discount,line_total) VALUES(?,?,?,?,?,?,?,?)",
                        (inv["id"],case_id,product_id,p["name"],quantity,unit_price,actual_discount,total))
            new_sub=float(inv["subtotal"])+raw; new_disc=float(inv["discount"])+actual_discount; new_total=float(inv["total"])+total; new_balance_inv=max(0.0,new_total-float(inv["paid"])); status="paid" if new_balance_inv<=1e-9 else ("partial" if float(inv["paid"])>0 else "unpaid")
            con.execute("UPDATE invoices SET subtotal=?,discount=?,total=?,balance=?,status=?,updated_at=? WHERE id=?",(new_sub,new_disc,new_total,new_balance_inv,status,now,inv["id"]))
            tech_ids=[r[0] for r in con.execute("SELECT DISTINCT technician_id FROM case_technicians WHERE case_id=?",(case_id,)).fetchall()]
            if tech_ids:
                share=total/len(tech_ids); cost_share=cost/len(tech_ids); qty_share=quantity/len(tech_ids)
                for tid in tech_ids:
                    tech=con.execute("SELECT * FROM technicians WHERE id=?",(tid,)).fetchone()
                    override=con.execute("SELECT * FROM technician_product_rates WHERE technician_id=? AND product_id=?",(tid,product_id)).fetchone()
                    rate=float(override["commission_rate"] if override and override["commission_rate"] is not None else tech["commission_rate"]); fixed=float(override["fixed_amount"] if override and override["fixed_amount"] is not None else tech["fixed_amount"]); method=tech["commission_method"]
                    commission_qty=quantity if method=="fixed" else qty_share
                    amount=self._commission_amount(method,rate,fixed,0,share,cost_share,commission_qty)
                    con.execute("INSERT OR REPLACE INTO case_technicians(case_id,technician_id,product_id,commission_method_snapshot,commission_rate_snapshot,fixed_amount_snapshot,custom_commission,commission_amount,paid_amount) VALUES(?,?,?,?,?,?,?,?,COALESCE((SELECT paid_amount FROM case_technicians WHERE case_id=? AND technician_id=? AND product_id=?),0))",
                                (case_id,tid,product_id,method,rate,fixed,0,amount,case_id,tid,product_id))
        self.db.audit("UPDATE","case",case_id,f"add product {product_id} qty={quantity}",self.user_id)

    def case_detail(self, case_id):
        with self.db.connect() as con:
            c = con.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
            item = con.execute("SELECT * FROM case_items WHERE case_id=? ORDER BY id LIMIT 1", (case_id,)).fetchone()
            inv = con.execute("SELECT i.* FROM invoices i JOIN invoice_cases ic ON ic.invoice_id=i.id WHERE ic.case_id=?", (case_id,)).fetchone()
            techs = [dict(r) for r in con.execute("SELECT * FROM case_technicians WHERE case_id=?", (case_id,))]
            return (dict(c) if c else None, dict(item) if item else None, dict(inv) if inv else None, techs)

    def edit_case(self, case_id, patient_name, quantity, discount, delivery_date=None, status=None, notes=""):
        self._require_owner()
        quantity = float(quantity); discount = float(discount or 0)
        if quantity <= 0 or discount < 0 or not patient_name.strip():
            raise BusinessError("بيانات الحالة غير صالحة")
        now = self.db.now()
        with self.db.connect() as con:
            c = con.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
            item = con.execute("SELECT * FROM case_items WHERE case_id=? ORDER BY id LIMIT 1", (case_id,)).fetchone()
            inv = con.execute("SELECT i.* FROM invoices i JOIN invoice_cases ic ON ic.invoice_id=i.id WHERE ic.case_id=?", (case_id,)).fetchone()
            if not c or not item or not inv:
                raise BusinessError("الحالة غير مكتملة البيانات")
            old_qty = float(item["quantity"]); unit_price = float(item["unit_price_snapshot"]); cost_unit = float(item["purchase_cost_snapshot"])
            raw_total = unit_price * quantity; new_discount = min(discount, raw_total); new_total = max(0.0, raw_total-new_discount)
            if abs(new_total-float(inv["total"])) > 1e-9 and float(inv["paid"]) > 0:
                raise BusinessError("لا يمكن تغيير الكمية/الخصم بعد وجود تحصيلات على الفاتورة. سجّل تسوية مالية أولاً.")
            p = con.execute("SELECT * FROM products WHERE id=?", (item["product_id"],)).fetchone()
            delta = quantity-old_qty
            if delta > 0 and float(p["stock_qty"]) < delta:
                raise BusinessError(f"المخزون غير كافٍ للزيادة المطلوبة. المتاح {p['stock_qty']:g}")
            if abs(delta) > 1e-9:
                new_balance = float(p["stock_qty"]) - delta
                movement_type = "OUT" if delta > 0 else "RETURN"
                movement_qty = -delta if delta > 0 else abs(delta)
                con.execute("UPDATE products SET stock_qty=?,updated_at=? WHERE id=?", (new_balance,now,p["id"]))
                con.execute("INSERT INTO stock_movements(product_id,movement_type,quantity,balance_after,movement_date,related_case_id,notes,created_at) VALUES(?,?,?,?,?,?,?,?)",
                            (p["id"],movement_type,movement_qty,new_balance,self.today(),case_id,"تسوية تعديل الحالة",now))
            con.execute("UPDATE case_items SET quantity=?,discount=?,line_total=? WHERE id=?", (quantity,new_discount,new_total,item["id"]))
            con.execute("UPDATE cases SET patient_name=?,delivery_date=?,status=COALESCE(?,status),notes=?,updated_at=? WHERE id=?",
                        (patient_name.strip(),delivery_date or None,status,notes,now,case_id))
            balance = max(0.0,new_total-float(inv["paid"])); inv_status = "paid" if balance<=1e-9 else ("partial" if float(inv["paid"])>0 else "unpaid")
            con.execute("UPDATE invoices SET subtotal=?,discount=?,total=?,balance=?,status=?,updated_at=? WHERE id=?", (raw_total,new_discount,new_total,balance,inv_status,now,inv["id"]))
            con.execute("UPDATE invoice_items SET quantity=?,discount=?,line_total=? WHERE invoice_id=? AND case_id=?", (quantity,new_discount,new_total,inv["id"],case_id))
            # Recalculate only technician snapshots for the edited product. Additional
            # products on the same case keep their own commission snapshots unchanged.
            tech_rows = con.execute(
                "SELECT * FROM case_technicians WHERE case_id=? AND (product_id=? OR product_id IS NULL)",
                (case_id, item["product_id"]),
            ).fetchall()
            if tech_rows:
                share=new_total/len(tech_rows); cost_share=(cost_unit*quantity)/len(tech_rows); qty_share=quantity/len(tech_rows)
                for tr in tech_rows:
                    method=tr["commission_method_snapshot"]
                    commission_qty=quantity if method=="fixed" else qty_share
                    amount=self._commission_amount(method,float(tr["commission_rate_snapshot"]),float(tr["fixed_amount_snapshot"]),float(tr["custom_commission"]),share,cost_share,commission_qty)
                    con.execute("UPDATE case_technicians SET commission_amount=? WHERE id=?", (amount,tr["id"]))
        self.db.audit("UPDATE","case",case_id,f"qty={quantity}; discount={discount}",self.user_id)

    def case_full_detail(self, case_id):
        with self.db.connect() as con:
            c = con.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
            inv = con.execute("SELECT i.* FROM invoices i JOIN invoice_cases ic ON ic.invoice_id=i.id WHERE ic.case_id=?", (case_id,)).fetchone()
            items = [dict(r) for r in con.execute("SELECT * FROM case_items WHERE case_id=? ORDER BY id", (case_id,))]
            tech_ids = [r[0] for r in con.execute("SELECT DISTINCT technician_id FROM case_technicians WHERE case_id=? ORDER BY technician_id", (case_id,)).fetchall()]
            return (dict(c) if c else None, items, dict(inv) if inv else None, tech_ids)

    def owner_update_product_full(self, product_id, stock_qty=None, **fields):
        self._require_owner()
        if stock_qty is not None:
            stock_qty = float(stock_qty)
            if stock_qty < 0:
                raise BusinessError("الرصيد لا يمكن أن يكون سالباً")
        now = self.db.now()
        with self.db.connect() as con:
            row = con.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
            if not row:
                raise BusinessError("المنتج غير موجود")
        # normal fields first so validation stays centralized
        self.update_product(product_id, **fields)
        if stock_qty is not None:
            with self.db.connect() as con:
                row = con.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
                current = float(row["stock_qty"])
                delta = stock_qty - current
                if abs(delta) > 1e-9:
                    con.execute("UPDATE products SET stock_qty=?,updated_at=? WHERE id=?", (stock_qty, now, product_id))
                    con.execute(
                        "INSERT INTO stock_movements(product_id,movement_type,quantity,balance_after,movement_date,related_case_id,notes,created_at) VALUES(?,?,?,?,?,?,?,?)",
                        (product_id, "ADJUSTMENT", delta, stock_qty, self.today(), None, "تعديل المالك للرصيد من شاشة المنتج", now),
                    )
            if abs(delta) > 1e-9:
                self.db.audit("OWNER_EDIT", "product_stock", product_id, f"stock={stock_qty}", self.user_id)

    def owner_edit_case_full(self, case_id, *, case_no, invoice_no, doctor_id, patient_name,
                             received_date, delivery_date, status, order_kind, notes,
                             technician_ids, items):
        """Owner-only full case editor. Derived totals/stock remain consistent automatically."""
        self._require_owner()
        if status not in {"New", "In Progress", "Waiting for Doctor", "Completed", "Delivered", "Failed", "Rework", "Cancelled"}:
            raise BusinessError("حالة غير صالحة")
        if order_kind not in {"original", "free_remake", "charged_reorder"}:
            raise BusinessError("نوع الطلب غير صالح")
        if not patient_name.strip() or not case_no.strip() or not invoice_no.strip():
            raise BusinessError("رقم الحالة والفاتورة واسم المريض مطلوبة")
        if not items:
            raise BusinessError("الحالة يجب أن تحتوي على منتج واحد على الأقل")
        technician_ids = list(dict.fromkeys(int(x) for x in technician_ids))
        now = self.db.now()
        with self.db.connect() as con:
            c = con.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
            inv = con.execute("SELECT i.* FROM invoices i JOIN invoice_cases ic ON ic.invoice_id=i.id WHERE ic.case_id=?", (case_id,)).fetchone()
            if not c or not inv:
                raise BusinessError("الحالة أو الفاتورة غير موجودة")
            if not con.execute("SELECT id FROM doctors WHERE id=?", (doctor_id,)).fetchone():
                raise BusinessError("الطبيب غير موجود")
            if con.execute("SELECT id FROM cases WHERE case_no=? AND id<>?", (case_no.strip(), case_id)).fetchone():
                raise BusinessError("رقم الحالة مستخدم بالفعل")
            if con.execute("SELECT id FROM invoices WHERE invoice_no=? AND id<>?", (invoice_no.strip(), inv["id"])).fetchone():
                raise BusinessError("رقم الفاتورة مستخدم بالفعل")
            invoice_case_count = con.execute("SELECT COUNT(*) FROM invoice_cases WHERE invoice_id=?", (inv["id"],)).fetchone()[0]
            if int(doctor_id) != int(c["doctor_id"]) and invoice_case_count > 1:
                raise BusinessError("لا يمكن تغيير الطبيب لحالة داخل فاتورة مدمجة. افصلها أولاً أو عدّل الحالات المرتبطة معاً.")

            old_items = [dict(r) for r in con.execute("SELECT * FROM case_items WHERE case_id=? ORDER BY id", (case_id,))]
            old_qty = {}
            for it in old_items:
                old_qty[it["product_id"]] = old_qty.get(it["product_id"], 0.0) + float(it["quantity"])

            cleaned=[]; new_qty={}
            for raw in items:
                pid=int(raw["product_id"]); qty=float(raw["quantity"]); unit_price=float(raw["unit_price_snapshot"]); unit_cost=float(raw["purchase_cost_snapshot"]); discount=float(raw.get("discount",0) or 0)
                if qty<=0 or unit_price<0 or unit_cost<0 or discount<0:
                    raise BusinessError("قيم المنتج داخل الحالة غير صالحة")
                p=con.execute("SELECT * FROM products WHERE id=?",(pid,)).fetchone()
                if not p: raise BusinessError("أحد المنتجات غير موجود")
                if order_kind=="free_remake": unit_price=0.0
                raw_total=unit_price*qty; discount=min(discount,raw_total); line_total=max(0.0,raw_total-discount)
                cleaned.append(dict(product_id=pid,tooth_numbers=str(raw.get("tooth_numbers","") or ""),quantity=qty,unit_price_snapshot=unit_price,purchase_cost_snapshot=unit_cost,discount=discount,line_total=line_total,description=p["name"]))
                new_qty[pid]=new_qty.get(pid,0.0)+qty

            old_active = c["status"] != "Cancelled"
            new_active = status != "Cancelled"
            for pid in set(old_qty)|set(new_qty):
                old_used = old_qty.get(pid,0.0) if old_active else 0.0
                new_used = new_qty.get(pid,0.0) if new_active else 0.0
                delta = new_used-old_used  # positive => consume more
                if abs(delta)<=1e-9: continue
                p=con.execute("SELECT * FROM products WHERE id=?",(pid,)).fetchone()
                if delta>0 and float(p["stock_qty"])<delta-1e-9:
                    raise BusinessError(f"المخزون غير كافٍ للمنتج {p['name']}. المتاح {p['stock_qty']:g}")
                balance=float(p["stock_qty"])-delta
                con.execute("UPDATE products SET stock_qty=?,updated_at=? WHERE id=?",(balance,now,pid))
                con.execute("INSERT INTO stock_movements(product_id,movement_type,quantity,balance_after,movement_date,related_case_id,notes,created_at) VALUES(?,?,?,?,?,?,?,?)",
                            (pid,"OUT" if delta>0 else "RETURN",-delta if delta>0 else abs(delta),balance,received_date or self.today(),case_id,"تسوية تعديل شامل بواسطة المالك",now))

            con.execute("UPDATE cases SET case_no=?,received_date=?,delivery_date=?,doctor_id=?,patient_name=?,status=?,notes=?,order_kind=?,updated_at=? WHERE id=?",
                        (case_no.strip(),received_date or self.today(),delivery_date or None,doctor_id,patient_name.strip(),status,notes or "",order_kind,now,case_id))
            con.execute("DELETE FROM case_items WHERE case_id=?",(case_id,))
            for it in cleaned:
                con.execute("INSERT INTO case_items(case_id,product_id,tooth_numbers,quantity,unit_price_snapshot,purchase_cost_snapshot,discount,line_total) VALUES(?,?,?,?,?,?,?,?)",
                            (case_id,it["product_id"],it["tooth_numbers"],it["quantity"],it["unit_price_snapshot"],it["purchase_cost_snapshot"],it["discount"],it["line_total"]))

            # Replace invoice lines for this case, then recalculate the entire target invoice.
            con.execute("DELETE FROM invoice_items WHERE invoice_id=? AND case_id=?",(inv["id"],case_id))
            for it in cleaned:
                con.execute("INSERT INTO invoice_items(invoice_id,case_id,product_id,description,quantity,unit_price,discount,line_total) VALUES(?,?,?,?,?,?,?,?)",
                            (inv["id"],case_id,it["product_id"],it["description"],it["quantity"],it["unit_price_snapshot"],it["discount"],it["line_total"]))
            sums=con.execute("SELECT COALESCE(SUM(quantity*unit_price),0),COALESCE(SUM(discount),0),COALESCE(SUM(line_total),0) FROM invoice_items WHERE invoice_id=?",(inv["id"],)).fetchone()
            subtotal,discount_total,total=map(float,sums)
            if not new_active:
                # A standalone cancelled invoice is zeroed; merged invoices keep other cases.
                if invoice_case_count==1: subtotal=discount_total=total=0.0
            paid=float(inv["paid"] or 0)
            if paid>total+1e-9:
                raise BusinessError("التعديل سيجعل إجمالي الفاتورة أقل من المبلغ المحصل. عدّل/سوِّ التحصيلات أولاً.")
            balance=max(0.0,total-paid)
            inv_status="cancelled" if (not new_active and invoice_case_count==1) else ("paid" if balance<=1e-9 else ("partial" if paid>0 else "unpaid"))
            con.execute("UPDATE invoices SET invoice_no=?,doctor_id=?,invoice_date=?,subtotal=?,discount=?,total=?,balance=?,status=?,notes=?,updated_at=? WHERE id=?",
                        (invoice_no.strip(),doctor_id,received_date or self.today(),subtotal,discount_total,total,balance,inv_status,notes or "",now,inv["id"]))

            # Rebuild technician assignments per product. Existing snapshot terms are preserved where possible.
            old_terms={(r["technician_id"],r["product_id"]):dict(r) for r in con.execute("SELECT * FROM case_technicians WHERE case_id=?",(case_id,)).fetchall()}
            con.execute("DELETE FROM case_technicians WHERE case_id=?",(case_id,))
            for it in cleaned:
                if not technician_ids: continue
                share=it["line_total"]/len(technician_ids); cost_share=(it["purchase_cost_snapshot"]*it["quantity"])/len(technician_ids); qty_share=it["quantity"]/len(technician_ids)
                for tid in technician_ids:
                    tech=con.execute("SELECT * FROM technicians WHERE id=?",(tid,)).fetchone()
                    if not tech: raise BusinessError("أحد الفنيين غير موجود")
                    old=old_terms.get((tid,it["product_id"]))
                    if old:
                        method=old["commission_method_snapshot"];rate=float(old["commission_rate_snapshot"]);fixed=float(old["fixed_amount_snapshot"]);custom=float(old["custom_commission"])
                    else:
                        ov=con.execute("SELECT * FROM technician_product_rates WHERE technician_id=? AND product_id=?",(tid,it["product_id"])).fetchone()
                        method=tech["commission_method"];rate=float(ov["commission_rate"] if ov and ov["commission_rate"] is not None else tech["commission_rate"]);fixed=float(ov["fixed_amount"] if ov and ov["fixed_amount"] is not None else tech["fixed_amount"]);custom=0.0
                    commission_qty=it["quantity"] if method=="fixed" else qty_share
                    amount=self._commission_amount(method,rate,fixed,custom,share,cost_share,commission_qty)
                    con.execute("INSERT INTO case_technicians(case_id,technician_id,product_id,commission_method_snapshot,commission_rate_snapshot,fixed_amount_snapshot,custom_commission,commission_amount,paid_amount) VALUES(?,?,?,?,?,?,?,?,0)",
                                (case_id,tid,it["product_id"],method,rate,fixed,custom,amount))
            for tid in technician_ids:
                paid_total=float(con.execute("SELECT COALESCE(SUM(amount),0) FROM commission_payments WHERE technician_id=?",(tid,)).fetchone()[0])
                earned=float(con.execute("SELECT COALESCE(SUM(ct.commission_amount),0) FROM case_technicians ct JOIN cases cc ON cc.id=ct.case_id WHERE ct.technician_id=? AND cc.status!='Cancelled'",(tid,)).fetchone()[0])
                if paid_total>earned+1e-9:
                    raise BusinessError("التعديل سيجعل عمولات فني مدفوعة أكبر من المستحقة. سوِّ دفعات العمولة أولاً.")
        self.db.audit("OWNER_EDIT", "case", case_id, "full owner edit", self.user_id)

    def update_case_status(self, case_id, status):
        allowed = {"New", "In Progress", "Waiting for Doctor", "Completed", "Delivered", "Failed", "Rework"}
        if status not in allowed:
            raise BusinessError("حالة غير صالحة")
        with self.db.connect() as con:
            con.execute("UPDATE cases SET status=?,updated_at=? WHERE id=?", (status, self.db.now(), case_id))
        self.db.audit("STATUS", "case", case_id, status, self.user_id)

    def cancel_case(self, case_id, reason="إلغاء الحالة"):
        """Cancels by reversing stock and zeroing invoice; keeps traceability."""
        now = self.db.now()
        with self.db.connect() as con:
            c = con.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
            if not c:
                raise BusinessError("الحالة غير موجودة")
            items = con.execute("SELECT * FROM case_items WHERE case_id=?", (case_id,)).fetchall()
            for item in items:
                p = con.execute("SELECT * FROM products WHERE id=?", (item["product_id"],)).fetchone()
                new_balance = float(p["stock_qty"]) + float(item["quantity"])
                con.execute("UPDATE products SET stock_qty=?,updated_at=? WHERE id=?", (new_balance, now, p["id"]))
                con.execute(
                    "INSERT INTO stock_movements(product_id,movement_type,quantity,balance_after,movement_date,related_case_id,notes,created_at) VALUES(?,?,?,?,?,?,?,?)",
                    (p["id"], "RETURN", float(item["quantity"]), new_balance, self.today(), case_id, reason, now),
                )
            invoice = con.execute("SELECT i.* FROM invoices i JOIN invoice_cases ic ON ic.invoice_id=i.id WHERE ic.case_id=?", (case_id,)).fetchone()
            if invoice and float(invoice["paid"]) > 0:
                raise BusinessError("لا يمكن إلغاء حالة لها تحصيلات. سجّل تسوية/رد مالي أولاً.")
            if invoice:
                con.execute("UPDATE invoices SET total=0,balance=0,status='cancelled',notes=?,updated_at=? WHERE id=?", (reason, now, invoice["id"]))
            con.execute("UPDATE cases SET status='Cancelled',notes=COALESCE(notes,'') || ?,updated_at=? WHERE id=?", (f"\n{reason}", now, case_id))
        self.db.audit("CANCEL", "case", case_id, reason, self.user_id)


    def delete_case(self, case_id):
        """Hard-delete a mistaken case while rolling back stock, invoice and commission effects.

        Payments are intentionally protected: once money was collected, the case must be
        corrected through a financial reversal rather than silently destroyed.
        """
        self._require_owner()
        now = self.db.now()
        with self.db.connect() as con:
            c = con.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
            if not c:
                raise BusinessError("الحالة غير موجودة")
            invoice = con.execute(
                "SELECT i.* FROM invoices i JOIN invoice_cases ic ON ic.invoice_id=i.id WHERE ic.case_id=?",
                (case_id,),
            ).fetchone()
            if invoice:
                payment_count = con.execute("SELECT COUNT(*) FROM payments WHERE invoice_id=?", (invoice["id"],)).fetchone()[0]
                if payment_count or float(invoice["paid"] or 0) > 1e-9:
                    raise BusinessError("لا يمكن حذف حالة مرتبطة بتحصيلات. اعمل تسوية/رد مالي أولاً.")

            # Do not let a deletion make a technician's already-paid commissions exceed earned commissions.
            tech_ids = [r[0] for r in con.execute("SELECT DISTINCT technician_id FROM case_technicians WHERE case_id=?", (case_id,)).fetchall()]
            for tid in tech_ids:
                paid = float(con.execute("SELECT COALESCE(SUM(amount),0) FROM commission_payments WHERE technician_id=?", (tid,)).fetchone()[0])
                earned_without = float(con.execute(
                    """SELECT COALESCE(SUM(ct.commission_amount),0)
                       FROM case_technicians ct JOIN cases c2 ON c2.id=ct.case_id
                       WHERE ct.technician_id=? AND ct.case_id<>? AND c2.status!='Cancelled'""",
                    (tid, case_id),
                ).fetchone()[0])
                if paid > earned_without + 1e-9:
                    raise BusinessError("لا يمكن حذف الحالة لأن جزءاً من عمولتها تم دفعه بالفعل لأحد الفنيين.")

            items = con.execute("SELECT * FROM case_items WHERE case_id=?", (case_id,)).fetchall()
            if c["status"] != "Cancelled":
                for item in items:
                    product = con.execute("SELECT * FROM products WHERE id=?", (item["product_id"],)).fetchone()
                    if product:
                        new_balance = float(product["stock_qty"]) + float(item["quantity"])
                        con.execute("UPDATE products SET stock_qty=?,updated_at=? WHERE id=?", (new_balance, now, product["id"]))
                        con.execute(
                            """INSERT INTO stock_movements(product_id,movement_type,quantity,balance_after,movement_date,related_case_id,notes,created_at)
                               VALUES(?,?,?,?,?,?,?,?)""",
                            (product["id"], "RETURN", float(item["quantity"]), new_balance, self.today(), None, f"استرجاع مخزون بسبب حذف الحالة {c['case_no']}", now),
                        )

            # Preserve the stock ledger but detach old movements from the soon-to-be-deleted case.
            con.execute(
                "UPDATE stock_movements SET related_case_id=NULL, notes=COALESCE(notes,'') || ? WHERE related_case_id=?",
                (f" | حذفت الحالة {c['case_no']}", case_id),
            )
            con.execute("DELETE FROM failures WHERE case_id=?", (case_id,))

            if invoice:
                con.execute("DELETE FROM invoice_items WHERE invoice_id=? AND case_id=?", (invoice["id"], case_id))
                con.execute("DELETE FROM invoice_cases WHERE invoice_id=? AND case_id=?", (invoice["id"], case_id))
                remaining_cases = con.execute("SELECT COUNT(*) FROM invoice_cases WHERE invoice_id=?", (invoice["id"],)).fetchone()[0]
                if remaining_cases == 0:
                    con.execute("DELETE FROM invoices WHERE id=?", (invoice["id"],))
                else:
                    sums = con.execute(
                        "SELECT COALESCE(SUM(quantity*unit_price),0),COALESCE(SUM(discount),0),COALESCE(SUM(line_total),0) FROM invoice_items WHERE invoice_id=?",
                        (invoice["id"],),
                    ).fetchone()
                    subtotal, discount_total, total = map(float, sums)
                    balance = max(0.0, total - float(invoice["paid"] or 0))
                    status = "paid" if balance <= 1e-9 else ("partial" if float(invoice["paid"] or 0) > 0 else "unpaid")
                    con.execute(
                        "UPDATE invoices SET subtotal=?,discount=?,total=?,balance=?,status=?,updated_at=? WHERE id=?",
                        (subtotal, discount_total, total, balance, status, now, invoice["id"]),
                    )

            con.execute("DELETE FROM cases WHERE id=?", (case_id,))
        self.db.audit("DELETE", "case", case_id, f"hard delete mistaken case {c['case_no']}", self.user_id)


    def merge_case_into_invoice(self, case_id, target_invoice_id):
        now=self.db.now()
        with self.db.connect() as con:
            c=con.execute("SELECT * FROM cases WHERE id=?",(case_id,)).fetchone()
            src=con.execute("SELECT i.* FROM invoices i JOIN invoice_cases ic ON ic.invoice_id=i.id WHERE ic.case_id=?",(case_id,)).fetchone()
            dst=con.execute("SELECT * FROM invoices WHERE id=?",(target_invoice_id,)).fetchone()
            if not c or not src or not dst: raise BusinessError("الحالة أو الفاتورة غير موجودة")
            if src["id"]==dst["id"]: return
            if int(src["doctor_id"])!=int(dst["doctor_id"]): raise BusinessError("لا يمكن دمج حالات لأطباء مختلفين في نفس الفاتورة")
            if float(src["paid"])>0: raise BusinessError("لا يمكن دمج فاتورة المصدر بعد تسجيل تحصيل عليها")
            if dst["status"]=="cancelled": raise BusinessError("فاتورة الهدف ملغاة")
            # Move case/items to target and keep source as a zero-value cancelled audit record.
            con.execute("UPDATE invoice_items SET invoice_id=? WHERE invoice_id=? AND case_id=?",(dst["id"],src["id"],case_id))
            con.execute("DELETE FROM invoice_cases WHERE invoice_id=? AND case_id=?",(src["id"],case_id))
            con.execute("INSERT OR IGNORE INTO invoice_cases(invoice_id,case_id) VALUES(?,?)",(dst["id"],case_id))
            new_sub=float(dst["subtotal"])+float(src["subtotal"]);new_disc=float(dst["discount"])+float(src["discount"]);new_total=float(dst["total"])+float(src["total"]);new_balance=max(0.0,new_total-float(dst["paid"]));status="paid" if new_balance<=1e-9 else ("partial" if float(dst["paid"])>0 else "unpaid")
            con.execute("UPDATE invoices SET subtotal=?,discount=?,total=?,balance=?,status=?,updated_at=? WHERE id=?",(new_sub,new_disc,new_total,new_balance,status,now,dst["id"]))
            con.execute("UPDATE invoices SET subtotal=0,discount=0,total=0,balance=0,status='cancelled',notes=COALESCE(notes,'') || ?,updated_at=? WHERE id=?",(f"\nتم دمج الحالة في الفاتورة {dst['invoice_no']}",now,src["id"]))
        self.db.audit("MERGE","invoice",target_invoice_id,f"case {case_id} from invoice {src['id']}",self.user_id)

    # ---------- invoices / payments ----------
    def list_invoices(self, search=""):
        pat = f"%{search.strip()}%"
        with self.db.connect() as con:
            rows = con.execute(
                """
                SELECT i.*, d.name doctor_name,
                       GROUP_CONCAT(DISTINCT c.patient_name) patients,
                       GROUP_CONCAT(DISTINCT c.case_no) case_numbers
                FROM invoices i
                JOIN doctors d ON d.id=i.doctor_id
                LEFT JOIN invoice_cases ic ON ic.invoice_id=i.id
                LEFT JOIN cases c ON c.id=ic.case_id
                WHERE i.invoice_no LIKE ? OR d.name LIKE ? OR COALESCE(c.patient_name,'') LIKE ?
                GROUP BY i.id
                ORDER BY i.id DESC
                """,
                (pat, pat, pat),
            )
            return [dict(r) for r in rows]

    def invoice_detail(self, invoice_id):
        with self.db.connect() as con:
            inv = con.execute("SELECT i.*,d.name doctor_name,d.phone doctor_phone,d.clinic_name FROM invoices i JOIN doctors d ON d.id=i.doctor_id WHERE i.id=?", (invoice_id,)).fetchone()
            if not inv:
                raise BusinessError("الفاتورة غير موجودة")
            items = [dict(r) for r in con.execute("SELECT * FROM invoice_items WHERE invoice_id=?", (invoice_id,))]
            payments = [dict(r) for r in con.execute("SELECT * FROM payments WHERE invoice_id=? ORDER BY id", (invoice_id,))]
            return dict(inv), items, payments

    def owner_update_invoice_full(self, invoice_id, *, invoice_no, invoice_date, doctor_id, total, paid, status, notes=""):
        self._require_owner()
        invoice_no=invoice_no.strip(); total=float(total); paid=float(paid)
        if not invoice_no: raise BusinessError("رقم الفاتورة مطلوب")
        if total < 0 or paid < 0 or paid > total + 1e-9: raise BusinessError("قيم الفاتورة غير صالحة")
        if status not in {"unpaid","partial","paid","cancelled"}: raise BusinessError("حالة الفاتورة غير صالحة")
        balance=max(0.0,total-paid)
        expected = "paid" if balance<=1e-9 else ("partial" if paid>0 else "unpaid")
        if status=="cancelled":
            if total>1e-9 or paid>1e-9: raise BusinessError("الفاتورة الملغاة يجب أن يكون إجماليها ومدفوعها صفراً")
        elif status != expected:
            raise BusinessError(f"حالة السداد لا تطابق الأرقام. الحالة الصحيحة: {expected}")
        now=self.db.now()
        with self.db.connect() as con:
            inv=con.execute("SELECT * FROM invoices WHERE id=?",(invoice_id,)).fetchone()
            if not inv: raise BusinessError("الفاتورة غير موجودة")
            if not con.execute("SELECT id FROM doctors WHERE id=?",(doctor_id,)).fetchone(): raise BusinessError("الطبيب غير موجود")
            if con.execute("SELECT id FROM invoices WHERE invoice_no=? AND id<>?",(invoice_no,invoice_id)).fetchone(): raise BusinessError("رقم الفاتورة مستخدم بالفعل")

            # Keep invoice lines traceable by maintaining one owner-adjustment line.
            adj=con.execute("SELECT * FROM invoice_items WHERE invoice_id=? AND case_id IS NULL AND product_id IS NULL AND description='OWNER_CORRECTION'",(invoice_id,)).fetchone()
            base=float(con.execute("SELECT COALESCE(SUM(line_total),0) FROM invoice_items WHERE invoice_id=? AND NOT (case_id IS NULL AND product_id IS NULL AND description='OWNER_CORRECTION')",(invoice_id,)).fetchone()[0])
            delta=total-base
            if abs(delta)<=1e-9:
                if adj: con.execute("DELETE FROM invoice_items WHERE id=?",(adj["id"],))
            elif adj:
                con.execute("UPDATE invoice_items SET quantity=1,unit_price=?,discount=0,line_total=? WHERE id=?",(delta,delta,adj["id"]))
            else:
                con.execute("INSERT INTO invoice_items(invoice_id,case_id,product_id,description,quantity,unit_price,discount,line_total) VALUES(?,NULL,NULL,'OWNER_CORRECTION',1,?,0,?)",(invoice_id,delta,delta))

            # Reconcile payment rows to the owner's corrected paid total.
            payment_rows=[dict(r) for r in con.execute("SELECT * FROM payments WHERE invoice_id=? ORDER BY id DESC",(invoice_id,)).fetchall()]
            current=sum(float(r["amount"]) for r in payment_rows)
            diff=paid-current
            if diff>1e-9:
                con.execute("INSERT INTO payments(invoice_id,amount,payment_date,method,notes,created_at) VALUES(?,?,?,?,?,?)",(invoice_id,diff,invoice_date or self.today(),"OWNER_CORRECTION","تسوية يدوية بواسطة المالك",now))
            elif diff < -1e-9:
                need=-diff
                for r in payment_rows:
                    if need<=1e-9: break
                    amt=float(r["amount"])
                    if amt<=need+1e-9:
                        con.execute("DELETE FROM payments WHERE id=?",(r["id"],)); need-=amt
                    else:
                        con.execute("UPDATE payments SET amount=? WHERE id=?",(amt-need,r["id"])); need=0
                if need>1e-6: raise BusinessError("تعذر تسوية المدفوع")

            # Doctor is a property of the invoice and all directly linked cases.
            con.execute("UPDATE invoices SET invoice_no=?,doctor_id=?,invoice_date=?,subtotal=?,discount=0,total=?,paid=?,balance=?,status=?,notes=?,updated_at=? WHERE id=?",
                        (invoice_no,doctor_id,invoice_date or self.today(),total,total,paid,balance,status,notes or "",now,invoice_id))
            con.execute("UPDATE cases SET doctor_id=?,updated_at=? WHERE id IN (SELECT case_id FROM invoice_cases WHERE invoice_id=?)",(doctor_id,now,invoice_id))
        self.db.audit("OWNER_CORRECTION","invoice",invoice_id,f"total={total}; paid={paid}; status={status}",self.user_id)

    def record_payment(self, invoice_id, amount, method="نقدي", notes="", payment_date=None):
        amount = float(amount)
        if amount <= 0:
            raise BusinessError("قيمة التحصيل يجب أن تكون أكبر من صفر")
        now = self.db.now()
        with self.db.connect() as con:
            inv = con.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
            if not inv:
                raise BusinessError("الفاتورة غير موجودة")
            balance = float(inv["balance"])
            if amount > balance + 1e-9:
                raise BusinessError(f"التحصيل أكبر من الرصيد المتبقي ({balance:.2f})")
            new_paid = float(inv["paid"]) + amount
            new_balance = max(0.0, float(inv["total"]) - new_paid)
            status = "paid" if new_balance <= 1e-9 else "partial"
            con.execute(
                "INSERT INTO payments(invoice_id,amount,payment_date,method,notes,created_at) VALUES(?,?,?,?,?,?)",
                (invoice_id, amount, payment_date or self.today(), method, notes, now),
            )
            con.execute("UPDATE invoices SET paid=?,balance=?,status=?,updated_at=? WHERE id=?", (new_paid, new_balance, status, now, invoice_id))
        self.db.audit("PAYMENT", "invoice", invoice_id, f"{amount}", self.user_id)

    # ---------- failures ----------
    def record_failure(self, case_id, reason, material_cost=0, technician_commission=0,
                       additional_expenses=0, remake_type="free_remake", notes="", failure_date=None):
        if not reason.strip():
            raise BusinessError("سبب الفشل مطلوب")
        values = [float(material_cost or 0), float(technician_commission or 0), float(additional_expenses or 0)]
        if any(v < 0 for v in values):
            raise BusinessError("قيم الخسائر لا يمكن أن تكون سالبة")
        total = sum(values)
        now = self.db.now()
        with self.db.connect() as con:
            c = con.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
            if not c:
                raise BusinessError("الحالة غير موجودة")
            con.execute(
                "INSERT INTO failures(case_id,failure_date,reason,material_cost,technician_commission,additional_expenses,total_loss,remake_type,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (case_id, failure_date or self.today(), reason.strip(), values[0], values[1], values[2], total, remake_type, notes, now),
            )
            con.execute("UPDATE cases SET failure_status=1,status='Failed',updated_at=? WHERE id=?", (now, case_id))
        self.db.audit("FAILURE", "case", case_id, f"{reason}; loss={total}", self.user_id)
        return total

    def list_failures(self):
        with self.db.connect() as con:
            return [dict(r) for r in con.execute(
                """SELECT f.*, c.case_no,c.patient_name,d.name doctor_name,
                          GROUP_CONCAT(DISTINCT p.name) product_names,
                          GROUP_CONCAT(DISTINCT t.name) technician_names
                   FROM failures f
                   JOIN cases c ON c.id=f.case_id
                   JOIN doctors d ON d.id=c.doctor_id
                   LEFT JOIN case_items ci ON ci.case_id=c.id
                   LEFT JOIN products p ON p.id=ci.product_id
                   LEFT JOIN case_technicians ct ON ct.case_id=c.id
                   LEFT JOIN technicians t ON t.id=ct.technician_id
                   GROUP BY f.id ORDER BY f.id DESC""")]

    # ---------- finance ----------
    def add_expense(self, category, amount, description="", expense_date=None):
        amount = float(amount)
        if amount < 0 or not category.strip():
            raise BusinessError("بيانات المصروف غير صالحة")
        with self.db.connect() as con:
            cur = con.execute(
                "INSERT INTO expenses(expense_date,category,description,amount,created_at) VALUES(?,?,?,?,?)",
                (expense_date or self.today(), category.strip(), description.strip(), amount, self.db.now()),
            )
            rid = cur.lastrowid
        self.db.audit("CREATE", "expense", rid, f"{category}:{amount}", self.user_id)
        return rid

    def add_other_income(self, category, amount, description="", income_date=None):
        amount = float(amount)
        if amount < 0 or not category.strip():
            raise BusinessError("بيانات الإيراد غير صالحة")
        with self.db.connect() as con:
            cur = con.execute(
                "INSERT INTO other_income(income_date,category,description,amount,created_at) VALUES(?,?,?,?,?)",
                (income_date or self.today(), category.strip(), description.strip(), amount, self.db.now()),
            )
            rid = cur.lastrowid
        self.db.audit("CREATE", "other_income", rid, f"{category}:{amount}", self.user_id)
        return rid

    def list_expenses(self):
        with self.db.connect() as con:
            return [dict(r) for r in con.execute("SELECT * FROM expenses ORDER BY expense_date DESC,id DESC")]

    def delete_expense(self, expense_id):
        self._require_owner()
        with self.db.connect() as con:
            row = con.execute("SELECT * FROM expenses WHERE id=?", (expense_id,)).fetchone()
            if not row:
                raise BusinessError("المصروف غير موجود")
            con.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
        self.db.audit("DELETE", "expense", expense_id, f"{row['category']}:{row['amount']}", self.user_id)

    def delete_failure(self, failure_id):
        self._require_owner()
        with self.db.connect() as con:
            row=con.execute("SELECT * FROM failures WHERE id=?",(failure_id,)).fetchone()
            if not row: raise BusinessError("سجل الفشل غير موجود")
            case_id=row["case_id"]
            con.execute("DELETE FROM failures WHERE id=?",(failure_id,))
            remaining=con.execute("SELECT COUNT(*) FROM failures WHERE case_id=?",(case_id,)).fetchone()[0]
            if remaining==0:
                c=con.execute("SELECT status FROM cases WHERE id=?",(case_id,)).fetchone()
                if c:
                    new_status="In Progress" if c["status"]=="Failed" else c["status"]
                    con.execute("UPDATE cases SET failure_status=0,status=?,updated_at=? WHERE id=?",(new_status,self.db.now(),case_id))
        self.db.audit("OWNER_DELETE","failure",failure_id,f"case={case_id}",self.user_id)

    def update_failure(self, failure_id, *, failure_date, reason, material_cost, technician_commission, additional_expenses, remake_type, notes):
        self._require_owner()
        vals=[float(material_cost or 0),float(technician_commission or 0),float(additional_expenses or 0)]
        if not reason.strip() or any(v<0 for v in vals): raise BusinessError("بيانات الفشل غير صالحة")
        if remake_type not in {"free_remake","charged_reorder"}: raise BusinessError("نوع الإعادة غير صالح")
        total=sum(vals)
        with self.db.connect() as con:
            row=con.execute("SELECT * FROM failures WHERE id=?",(failure_id,)).fetchone()
            if not row: raise BusinessError("سجل الفشل غير موجود")
            con.execute("UPDATE failures SET failure_date=?,reason=?,material_cost=?,technician_commission=?,additional_expenses=?,total_loss=?,remake_type=?,notes=? WHERE id=?",
                        (failure_date or self.today(),reason.strip(),vals[0],vals[1],vals[2],total,remake_type,notes or "",failure_id))
        self.db.audit("OWNER_EDIT","failure",failure_id,f"loss={total}",self.user_id)

    def update_expense(self, expense_id, *, expense_date, category, description, amount):
        self._require_owner(); amount=float(amount)
        if amount<0 or not category.strip(): raise BusinessError("بيانات المصروف غير صالحة")
        with self.db.connect() as con:
            if not con.execute("SELECT id FROM expenses WHERE id=?",(expense_id,)).fetchone(): raise BusinessError("المصروف غير موجود")
            con.execute("UPDATE expenses SET expense_date=?,category=?,description=?,amount=? WHERE id=?",(expense_date or self.today(),category.strip(),description or "",amount,expense_id))
        self.db.audit("OWNER_EDIT","expense",expense_id,f"{category}:{amount}",self.user_id)

    def list_other_income(self):
        with self.db.connect() as con:
            return [dict(r) for r in con.execute("SELECT * FROM other_income ORDER BY income_date DESC,id DESC")]

    def update_other_income(self, income_id, *, income_date, category, description, amount):
        self._require_owner(); amount=float(amount)
        if amount<0 or not category.strip(): raise BusinessError("بيانات الإيراد غير صالحة")
        with self.db.connect() as con:
            if not con.execute("SELECT id FROM other_income WHERE id=?",(income_id,)).fetchone(): raise BusinessError("الإيراد غير موجود")
            con.execute("UPDATE other_income SET income_date=?,category=?,description=?,amount=? WHERE id=?",(income_date or self.today(),category.strip(),description or "",amount,income_id))
        self.db.audit("OWNER_EDIT","other_income",income_id,f"{category}:{amount}",self.user_id)

    def update_invoice_metadata(self, invoice_id, *, invoice_no, invoice_date, notes):
        self._require_owner()
        if not invoice_no.strip(): raise BusinessError("رقم الفاتورة مطلوب")
        with self.db.connect() as con:
            if con.execute("SELECT id FROM invoices WHERE invoice_no=? AND id<>?",(invoice_no.strip(),invoice_id)).fetchone(): raise BusinessError("رقم الفاتورة مستخدم بالفعل")
            if not con.execute("SELECT id FROM invoices WHERE id=?",(invoice_id,)).fetchone(): raise BusinessError("الفاتورة غير موجودة")
            con.execute("UPDATE invoices SET invoice_no=?,invoice_date=?,notes=?,updated_at=? WHERE id=?",(invoice_no.strip(),invoice_date or self.today(),notes or "",self.db.now(),invoice_id))
        self.db.audit("OWNER_EDIT","invoice",invoice_id,invoice_no,self.user_id)

    def update_manual_stock_movement(self, movement_id, *, movement_date, notes):
        self._require_owner()
        with self.db.connect() as con:
            row=con.execute("SELECT * FROM stock_movements WHERE id=?",(movement_id,)).fetchone()
            if not row: raise BusinessError("حركة المخزون غير موجودة")
            # Quantities/product/type of case-linked ledger entries are intentionally edited via the case editor.
            con.execute("UPDATE stock_movements SET movement_date=?,notes=? WHERE id=?",(movement_date or self.today(),notes or "",movement_id))
        self.db.audit("OWNER_EDIT","stock_movement",movement_id,"date/notes",self.user_id)

    def financial_summary(self, start_date=None, end_date=None):
        start_date = start_date or "0001-01-01"
        end_date = end_date or "9999-12-31"
        with self.db.connect() as con:
            invoiced = con.execute("SELECT COALESCE(SUM(total),0) FROM invoices WHERE invoice_date BETWEEN ? AND ? AND status!='cancelled'", (start_date, end_date)).fetchone()[0]
            collected = con.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE payment_date BETWEEN ? AND ?", (start_date, end_date)).fetchone()[0]
            other_income = con.execute("SELECT COALESCE(SUM(amount),0) FROM other_income WHERE income_date BETWEEN ? AND ?", (start_date, end_date)).fetchone()[0]
            expenses = con.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_date BETWEEN ? AND ?", (start_date, end_date)).fetchone()[0]
            material_cost = con.execute(
                """SELECT COALESCE(SUM(ci.purchase_cost_snapshot*ci.quantity),0)
                   FROM case_items ci JOIN cases c ON c.id=ci.case_id
                   WHERE c.received_date BETWEEN ? AND ? AND c.status!='Cancelled'""", (start_date, end_date)
            ).fetchone()[0]
            commissions = con.execute(
                """SELECT COALESCE(SUM(ct.commission_amount),0)
                   FROM case_technicians ct JOIN cases c ON c.id=ct.case_id
                   WHERE c.received_date BETWEEN ? AND ? AND c.status!='Cancelled'""", (start_date, end_date)
            ).fetchone()[0]
            failed_losses = con.execute("SELECT COALESCE(SUM(total_loss),0) FROM failures WHERE failure_date BETWEEN ? AND ?", (start_date, end_date)).fetchone()[0]
            # Material cost and technician commission for failed cases are already present in the normal
            # cost/commission totals above. Only extra failure expenses are an incremental deduction.
            failure_incremental = con.execute("SELECT COALESCE(SUM(additional_expenses),0) FROM failures WHERE failure_date BETWEEN ? AND ?", (start_date, end_date)).fetchone()[0]
            outstanding = con.execute("SELECT COALESCE(SUM(balance),0) FROM invoices WHERE status NOT IN ('cancelled','paid')").fetchone()[0]
        # Profit basis: invoiced revenue, not cash collection. Avoid double-counting failure material/commission.
        gross_profit = float(invoiced) - float(material_cost) - float(commissions)
        net_profit = gross_profit + float(other_income) - float(expenses) - float(failure_incremental)
        return {
            "invoiced_revenue": float(invoiced),
            "cash_collected": float(collected),
            "other_income": float(other_income),
            "expenses": float(expenses),
            "material_cost": float(material_cost),
            "technician_commissions": float(commissions),
            "failed_losses": float(failed_losses),
            "outstanding": float(outstanding),
            "gross_profit": gross_profit,
            "net_profit": net_profit,
        }

    # ---------- dashboard ----------
    def dashboard(self):
        today = date.today()
        month_start = today.replace(day=1).isoformat()
        year_start = today.replace(month=1, day=1).isoformat()
        today_s = today.isoformat()
        month = self.financial_summary(month_start, today_s)
        year = self.financial_summary(year_start, today_s)
        with self.db.connect() as con:
            total_cases = con.execute("SELECT COUNT(*) FROM cases WHERE status!='Cancelled'").fetchone()[0]
            completed = con.execute("SELECT COUNT(*) FROM cases WHERE status IN ('Completed','Delivered')").fetchone()[0]
            pending = con.execute("SELECT COUNT(*) FROM cases WHERE status IN ('New','In Progress','Waiting for Doctor','Rework')").fetchone()[0]
            failed = con.execute("SELECT COUNT(*) FROM cases WHERE failure_status=1").fetchone()[0]
            monthly_tech_commissions = month["technician_commissions"]
            tech_commissions = con.execute(
                """SELECT COALESCE(SUM(ct.commission_amount),0)
                   FROM case_technicians ct JOIN cases c ON c.id=ct.case_id
                   WHERE c.status!='Cancelled'"""
            ).fetchone()[0]
            low_stock = con.execute("SELECT COUNT(*) FROM products WHERE archived=0 AND stock_qty<=min_stock").fetchone()[0]
            recent = [dict(r) for r in con.execute(
                "SELECT c.case_no,c.patient_name,c.status,d.name doctor_name,c.delivery_date FROM cases c JOIN doctors d ON d.id=c.doctor_id ORDER BY c.id DESC LIMIT 8"
            )]
        return {
            "monthly_revenue": month["invoiced_revenue"],
            "yearly_revenue": year["invoiced_revenue"],
            "monthly_expenses": month["expenses"],
            "yearly_expenses": year["expenses"],
            "monthly_profit": month["net_profit"],
            "yearly_profit": year["net_profit"],
            "total_cases": total_cases,
            "completed_cases": completed,
            "pending_cases": pending,
            "failed_cases": failed,
            "outstanding": year["outstanding"],
            "monthly_technician_commissions": float(monthly_tech_commissions),
            "technician_commissions": float(tech_commissions),
            "low_stock": low_stock,
            "recent_cases": recent,
        }

    # ---------- report data ----------
    def report_monthly_revenue(self, year=None):
        year = year or date.today().year
        with self.db.connect() as con:
            rows = con.execute(
                """SELECT substr(invoice_date,1,7) month, SUM(total) total
                   FROM invoices WHERE invoice_date LIKE ? AND status!='cancelled'
                   GROUP BY substr(invoice_date,1,7) ORDER BY month""",
                (f"{year}-%",),
            ).fetchall()
        return [dict(r) for r in rows]

    def report_doctor_balances(self):
        return self.list_doctors()

    def report_inventory(self):
        return self.list_products()

    # ---------- backup / restore ----------
    def create_backup(self):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = backups_dir() / f"DentalLab_{stamp}.sqlite3"
        with self.db.connect() as src:
            dst = __import__('sqlite3').connect(target)
            try:
                src.backup(dst)
            finally:
                dst.close()
        self.db.audit("BACKUP", "database", target.name, str(target), self.user_id)
        return target

    def restore_backup(self, backup_path: str | Path):
        backup_path = Path(backup_path)
        if not backup_path.exists():
            raise BusinessError("ملف النسخة الاحتياطية غير موجود")
        # Validate source as SQLite before overwrite.
        import sqlite3
        test = sqlite3.connect(backup_path)
        try:
            test.execute("SELECT name FROM sqlite_master LIMIT 1").fetchone()
        finally:
            test.close()
        safety = self.create_backup()
        shutil.copy2(backup_path, self.db.path)
        for suffix in ("-wal", "-shm"):
            sidecar = Path(str(self.db.path) + suffix)
            if sidecar.exists():
                sidecar.unlink()
        # Re-open once to validate the restored schema/database.
        with self.db.connect() as con:
            con.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        return safety


    def automatic_backup_if_due(self):
        today = self.today()
        settings = self.settings()
        if settings.get("last_auto_backup") == today:
            return None
        target = self.create_backup()
        self.set_setting("last_auto_backup", today)
        return target

    # ---------- demo data ----------
    def seed_demo_data(self):
        with self.db.connect() as con:
            count = con.execute("SELECT COUNT(*) FROM doctors").fetchone()[0]
        if count:
            raise BusinessError("يوجد بيانات بالفعل. لن يتم إدخال البيانات التجريبية فوق بيانات حالية.")
        d1 = self.add_doctor("د. أحمد سمير", "01000000001", "عيادة سمايل", "الجيزة")
        d2 = self.add_doctor("د. منى خالد", "01000000002", "مركز برايت", "القاهرة")
        p1 = self.add_product("Zirconia Crown", "Crowns", "", 450, 900, 30, 5, "وحدة", "Supplier A")
        p2 = self.add_product("E-Max Crown", "Crowns", "", 600, 1200, 20, 4, "وحدة", "Supplier B")
        t1 = self.add_technician("محمد", "", 10, "selling_percent", 0)
        t2 = self.add_technician("أحمد", "", 12, "profit_percent", 0)
        self.create_case(d1, "مريض تجريبي 1", p1, 2, "11,12", [t1], status="In Progress")
        self.create_case(d2, "مريض تجريبي 2", p2, 1, "21", [t2], status="Completed")
        self.add_expense("إيجار", 5000, "مصروف تجريبي")

    def dashboard_charts(self):
        with self.db.connect() as con:
            monthly = [dict(r) for r in con.execute(
                "SELECT substr(invoice_date,1,7) label, ROUND(SUM(total),2) value FROM invoices WHERE status!='cancelled' GROUP BY label ORDER BY label DESC LIMIT 12"
            )][::-1]
            yearly = [dict(r) for r in con.execute(
                "SELECT substr(invoice_date,1,4) label, ROUND(SUM(total),2) value FROM invoices WHERE status!='cancelled' GROUP BY label ORDER BY label"
            )]
            rev = con.execute("SELECT COALESCE(SUM(total),0) FROM invoices WHERE status!='cancelled'").fetchone()[0]
            exp = con.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()[0]
            success = con.execute("SELECT COUNT(*) FROM cases WHERE status IN ('Completed','Delivered')").fetchone()[0]
            failed = con.execute("SELECT COUNT(*) FROM cases WHERE failure_status=1").fetchone()[0]
            products = [dict(r) for r in con.execute(
                """SELECT p.name label, COALESCE(SUM(ci.quantity),0) value
                   FROM case_items ci JOIN products p ON p.id=ci.product_id JOIN cases c ON c.id=ci.case_id
                   WHERE c.status!='Cancelled' GROUP BY p.id ORDER BY value DESC LIMIT 6"""
            )]
            doctors = [dict(r) for r in con.execute(
                """SELECT d.name label, COALESCE(SUM(i.total),0) value
                   FROM invoices i JOIN doctors d ON d.id=i.doctor_id WHERE i.status!='cancelled'
                   GROUP BY d.id ORDER BY value DESC LIMIT 6"""
            )]
            technicians = [dict(r) for r in con.execute(
                """SELECT t.name label, COALESCE(SUM(ct.commission_amount),0) value
                   FROM case_technicians ct JOIN technicians t ON t.id=ct.technician_id
                   GROUP BY t.id ORDER BY value DESC LIMIT 6"""
            )]
        return {
            "monthly_revenue": monthly,
            "yearly_revenue": yearly,
            "revenue_expense": [{"label": "الإيرادات", "value": float(rev)}, {"label": "المصروفات", "value": float(exp)}],
            "success_failed": [{"label": "ناجحة", "value": int(success)}, {"label": "فاشلة", "value": int(failed)}],
            "products": products,
            "doctors": doctors,
            "technicians": technicians,
        }

import tempfile
import unittest
from pathlib import Path

from dental_lab.database import Database
from dental_lab.services import DentalLabService, BusinessError


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "test.sqlite3")
        self.s = DentalLabService(self.db, {"id": 1, "username": "admin", "role": "owner"})
        self.d = self.s.add_doctor("Doctor A", "010")
        self.p = self.s.add_product("Zirconia", "Crown", purchase_cost=100, selling_price=300, stock_qty=20, min_stock=2)
        self.t = self.s.add_technician("Tech A", commission_rate=10, commission_method="selling_percent")

    def tearDown(self):
        self.tmp.cleanup()

    def test_case_creates_invoice_and_stock_movement(self):
        cid, case_no, iid, inv_no = self.s.create_case(self.d, "Patient", self.p, 2, technician_ids=[self.t])
        inv, items, _ = self.s.invoice_detail(iid)
        self.assertEqual(inv["total"], 600)
        self.assertEqual(inv["balance"], 600)
        products = self.s.list_products()
        self.assertEqual(products[0]["stock_qty"], 18)
        moves = self.s.list_stock_movements(self.p)
        self.assertEqual(moves[0]["movement_type"], "OUT")
        self.assertEqual(moves[0]["related_case_id"], cid)

    def test_free_remake_has_zero_revenue(self):
        _, _, iid, _ = self.s.create_case(self.d, "Patient", self.p, 1, technician_ids=[self.t], order_kind="free_remake")
        inv, _, _ = self.s.invoice_detail(iid)
        self.assertEqual(inv["total"], 0)
        self.assertEqual(inv["balance"], 0)
        self.assertEqual(inv["status"], "paid")

    def test_commission_snapshot_does_not_change(self):
        cid, *_ = self.s.create_case(self.d, "Patient", self.p, 1, technician_ids=[self.t])
        with self.db.connect() as con:
            before = con.execute("SELECT commission_amount,commission_rate_snapshot FROM case_technicians WHERE case_id=?", (cid,)).fetchone()
        self.s.update_technician(self.t, commission_rate=50)
        with self.db.connect() as con:
            after = con.execute("SELECT commission_amount,commission_rate_snapshot FROM case_technicians WHERE case_id=?", (cid,)).fetchone()
        self.assertEqual(before["commission_amount"], 30)
        self.assertEqual(after["commission_amount"], 30)
        self.assertEqual(after["commission_rate_snapshot"], 10)

    def test_partial_payments_update_balance(self):
        _, _, iid, _ = self.s.create_case(self.d, "Patient", self.p, 1)
        self.s.record_payment(iid, 100)
        inv, _, payments = self.s.invoice_detail(iid)
        self.assertEqual(inv["paid"], 100)
        self.assertEqual(inv["balance"], 200)
        self.assertEqual(inv["status"], "partial")
        self.assertEqual(len(payments), 1)
        self.s.record_payment(iid, 200)
        inv, _, _ = self.s.invoice_detail(iid)
        self.assertEqual(inv["balance"], 0)
        self.assertEqual(inv["status"], "paid")

    def test_overpayment_rejected(self):
        _, _, iid, _ = self.s.create_case(self.d, "Patient", self.p, 1)
        with self.assertRaises(BusinessError):
            self.s.record_payment(iid, 301)

    def test_insufficient_stock_rejected_without_partial_case(self):
        with self.assertRaises(BusinessError):
            self.s.create_case(self.d, "Patient", self.p, 100)
        self.assertEqual(self.s.list_cases(), [])

    def test_failed_case_loss(self):
        cid, *_ = self.s.create_case(self.d, "Patient", self.p, 1)
        total = self.s.record_failure(cid, "Broken", 100, 20, 30)
        self.assertEqual(total, 150)
        f = self.s.list_failures()[0]
        self.assertEqual(f["total_loss"], 150)

    def test_inventory_adjustments_are_logged(self):
        new = self.s.stock_movement(self.p, "WASTE", 2, "damaged")
        self.assertEqual(new, 18)
        moves = self.s.list_stock_movements(self.p)
        self.assertEqual(moves[0]["movement_type"], "WASTE")
        self.assertEqual(moves[0]["quantity"], -2)

    def test_case_edit_adjusts_stock_invoice_and_commission(self):
        cid, _, iid, _ = self.s.create_case(self.d, "Patient", self.p, 2, technician_ids=[self.t])
        self.s.edit_case(cid, "Patient 2", 3, 0, status="In Progress")
        inv, _, _ = self.s.invoice_detail(iid)
        self.assertEqual(inv["total"], 900)
        self.assertEqual(self.s.list_products()[0]["stock_qty"], 17)
        with self.db.connect() as con:
            comm = con.execute("SELECT commission_amount FROM case_technicians WHERE case_id=?", (cid,)).fetchone()[0]
        self.assertEqual(comm, 90)

    def test_cancel_case_returns_stock_and_zeroes_invoice(self):
        cid, _, iid, _ = self.s.create_case(self.d, "Patient", self.p, 2)
        self.s.cancel_case(cid)
        self.assertEqual(self.s.list_products()[0]["stock_qty"], 20)
        inv, _, _ = self.s.invoice_detail(iid)
        self.assertEqual(inv["total"], 0)
        self.assertEqual(inv["status"], "cancelled")

    def test_failed_loss_not_double_counted_in_net_profit(self):
        cid, *_ = self.s.create_case(self.d, "Patient", self.p, 1, technician_ids=[self.t])
        self.s.record_failure(cid, "Broken", material_cost=100, technician_commission=30, additional_expenses=20)
        summary = self.s.financial_summary()
        self.assertEqual(summary["failed_losses"], 150)
        # 300 revenue - 100 material - 30 commission - 20 extra failure cost = 150 net
        self.assertEqual(summary["net_profit"], 150)

    def test_multiple_products_share_same_case_invoice(self):
        cid, _, iid, _ = self.s.create_case(self.d, "Patient", self.p, 1, technician_ids=[self.t])
        p2 = self.s.add_product("Emax", "Crown", purchase_cost=200, selling_price=500, stock_qty=10)
        self.s.add_product_to_case(cid, p2, 2, "11,12", 50)
        inv, items, _ = self.s.invoice_detail(iid)
        self.assertEqual(len(items), 2)
        self.assertEqual(inv["total"], 300 + 950)
        self.assertEqual(next(x for x in self.s.list_products() if x["id"]==p2)["stock_qty"], 8)

    def test_multiple_cases_can_be_merged_into_one_invoice(self):
        c1, _, i1, _ = self.s.create_case(self.d, "P1", self.p, 1)
        c2, _, i2, _ = self.s.create_case(self.d, "P2", self.p, 2)
        self.s.merge_case_into_invoice(c2, i1)
        inv, items, _ = self.s.invoice_detail(i1)
        self.assertEqual(inv["total"], 900)
        self.assertEqual(len(items), 2)
        src, _, _ = self.s.invoice_detail(i2)
        self.assertEqual(src["status"], "cancelled")
        self.assertEqual(src["total"], 0)

    def test_fixed_per_unit_commission_is_not_split_between_technicians(self):
        t1 = self.s.add_technician("Fixed 1", commission_method="fixed", fixed_amount=100)
        t2 = self.s.add_technician("Fixed 2", commission_method="fixed", fixed_amount=100)
        t3 = self.s.add_technician("Fixed 3", commission_method="fixed", fixed_amount=100)
        cid, *_ = self.s.create_case(self.d, "Patient Fixed", self.p, 1, technician_ids=[t1,t2,t3])
        with self.db.connect() as con:
            rows = con.execute("SELECT technician_id,commission_amount FROM case_technicians WHERE case_id=? ORDER BY technician_id", (cid,)).fetchall()
        self.assertEqual(len(rows), 3)
        self.assertEqual([r["commission_amount"] for r in rows], [100,100,100])

    def test_fixed_per_unit_commission_scales_with_quantity(self):
        tid = self.s.add_technician("Fixed Tech", commission_method="fixed", fixed_amount=100)
        cid, *_ = self.s.create_case(self.d, "Patient Fixed Qty", self.p, 3, technician_ids=[tid])
        with self.db.connect() as con:
            amount = con.execute("SELECT commission_amount FROM case_technicians WHERE case_id=? AND technician_id=?", (cid,tid)).fetchone()[0]
        self.assertEqual(amount, 300)

    def test_unused_master_records_can_be_deleted(self):
        d2=self.s.add_doctor("Delete Doctor")
        p2=self.s.add_product("Delete Product", stock_qty=5)
        t2=self.s.add_technician("Delete Tech")
        self.assertEqual(self.s.delete_doctor(d2), "deleted")
        self.assertEqual(self.s.delete_product(p2), "deleted")
        self.assertEqual(self.s.delete_technician(t2), "deleted")
        self.assertFalse(any(x["id"]==d2 for x in self.s.list_doctors(include_archived=True)))
        self.assertFalse(any(x["id"]==p2 for x in self.s.list_products(include_archived=True)))
        self.assertFalse(any(x["id"]==t2 for x in self.s.list_technicians(include_archived=True)))

    def test_linked_master_records_are_archived_not_destroyed(self):
        cid, *_ = self.s.create_case(self.d, "History", self.p, 1, technician_ids=[self.t])
        self.assertEqual(self.s.delete_doctor(self.d), "archived")
        self.assertEqual(self.s.delete_product(self.p), "archived")
        self.assertEqual(self.s.delete_technician(self.t), "archived")
        with self.db.connect() as con:
            self.assertEqual(con.execute("SELECT archived FROM doctors WHERE id=?",(self.d,)).fetchone()[0],1)
            self.assertEqual(con.execute("SELECT archived FROM products WHERE id=?",(self.p,)).fetchone()[0],1)
            self.assertEqual(con.execute("SELECT archived FROM technicians WHERE id=?",(self.t,)).fetchone()[0],1)
            self.assertIsNotNone(con.execute("SELECT id FROM cases WHERE id=?",(cid,)).fetchone())

    def test_expense_can_be_deleted(self):
        eid=self.s.add_expense("Test",125,"mistake")
        self.s.delete_expense(eid)
        self.assertFalse(any(x["id"]==eid for x in self.s.list_expenses()))

    def test_package_cost_yield_sets_true_unit_material_cost(self):
        p2 = self.s.add_product("Block Product", purchase_cost=1500, yield_units=20, selling_price=600, stock_qty=10)
        cid, _, _, _ = self.s.create_case(self.d, "Yield Patient", p2, 1)
        with self.db.connect() as con:
            snap = con.execute("SELECT purchase_cost_snapshot FROM case_items WHERE case_id=?", (cid,)).fetchone()[0]
        self.assertEqual(snap, 75)
        summary = self.s.financial_summary()
        # Existing setUp data has no cases; this case contributes 600 - 75 = 525 gross/net.
        self.assertEqual(summary["material_cost"], 75)
        self.assertEqual(summary["net_profit"], 525)

    def test_material_cost_snapshot_remains_historical(self):
        p2 = self.s.add_product("Historic Block", purchase_cost=1500, yield_units=20, selling_price=600, stock_qty=10)
        c1, *_ = self.s.create_case(self.d, "Old", p2, 1)
        self.s.update_product(p2, purchase_cost=2000, yield_units=20)
        c2, *_ = self.s.create_case(self.d, "New", p2, 1)
        with self.db.connect() as con:
            old_cost = con.execute("SELECT purchase_cost_snapshot FROM case_items WHERE case_id=?", (c1,)).fetchone()[0]
            new_cost = con.execute("SELECT purchase_cost_snapshot FROM case_items WHERE case_id=?", (c2,)).fetchone()[0]
        self.assertEqual(old_cost, 75)
        self.assertEqual(new_cost, 100)

    def test_hard_delete_case_rolls_back_stock_invoice_and_commission(self):
        cid, _, iid, _ = self.s.create_case(self.d, "Mistake", self.p, 2, technician_ids=[self.t])
        self.assertEqual(self.s.list_products()[0]["stock_qty"], 18)
        self.s.delete_case(cid)
        self.assertEqual(self.s.list_products()[0]["stock_qty"], 20)
        self.assertFalse(any(x["id"] == cid for x in self.s.list_cases()))
        with self.db.connect() as con:
            self.assertIsNone(con.execute("SELECT id FROM invoices WHERE id=?", (iid,)).fetchone())
            self.assertEqual(con.execute("SELECT COUNT(*) FROM case_technicians WHERE case_id=?", (cid,)).fetchone()[0], 0)

    def test_hard_delete_case_from_merged_invoice_preserves_other_case(self):
        c1, _, i1, _ = self.s.create_case(self.d, "Keep", self.p, 1)
        c2, _, i2, _ = self.s.create_case(self.d, "Delete", self.p, 2)
        self.s.merge_case_into_invoice(c2, i1)
        self.s.delete_case(c2)
        inv, items, _ = self.s.invoice_detail(i1)
        self.assertEqual(inv["total"], 300)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["case_id"], c1)

    def test_hard_delete_case_with_payment_is_blocked(self):
        cid, _, iid, _ = self.s.create_case(self.d, "Paid", self.p, 1)
        self.s.record_payment(iid, 50)
        with self.assertRaises(BusinessError):
            self.s.delete_case(cid)
        self.assertTrue(any(x["id"] == cid for x in self.s.list_cases()))

    def test_dashboard_has_monthly_technician_commissions(self):
        self.s.create_case(self.d, "Commission", self.p, 1, technician_ids=[self.t])
        d = self.s.dashboard()
        self.assertEqual(d["monthly_technician_commissions"], 30)
        self.assertNotIn("inventory_value", d)


    def test_employee_cannot_use_owner_edit_methods(self):
        employee = DentalLabService(self.db, {"id": 2, "username": "emp", "role": "employee"})
        with self.assertRaises(BusinessError): employee.update_doctor(self.d, name="Changed")
        with self.assertRaises(BusinessError): employee.update_product(self.p, selling_price=999)
        with self.assertRaises(BusinessError): employee.update_technician(self.t, phone="1")
        cid, *_ = self.s.create_case(self.d, "Patient", self.p, 1)
        with self.assertRaises(BusinessError): employee.edit_case(cid, "No", 1, 0)

    def test_owner_product_full_edit_records_stock_adjustment(self):
        self.s.owner_update_product_full(self.p, stock_qty=25, name="Zirconia X", purchase_cost=120, yield_units=2, selling_price=350, min_stock=3, unit="tooth", supplier="S", archived=0)
        p = next(x for x in self.s.list_products(include_archived=True) if x["id"] == self.p)
        self.assertEqual(p["stock_qty"], 25)
        self.assertEqual(p["name"], "Zirconia X")
        mv = self.s.list_stock_movements(self.p)[0]
        self.assertEqual(mv["movement_type"], "ADJUSTMENT")
        self.assertEqual(mv["quantity"], 5)

    def test_owner_full_case_edit_updates_doctor_product_stock_invoice_and_technician(self):
        d2 = self.s.add_doctor("Doctor B")
        p2 = self.s.add_product("Emax Owner", purchase_cost=200, yield_units=2, selling_price=500, stock_qty=10)
        t2 = self.s.add_technician("Tech B", commission_method="fixed", fixed_amount=50)
        cid, _, iid, _ = self.s.create_case(self.d, "Old Patient", self.p, 1, technician_ids=[self.t])
        self.s.owner_edit_case_full(
            cid, case_no="CUSTOM-CASE", invoice_no="CUSTOM-INV", doctor_id=d2, patient_name="New Patient",
            received_date="2026-11-01", delivery_date="2026-11-10", status="In Progress", order_kind="original", notes="owner edit",
            technician_ids=[t2], items=[dict(product_id=p2,tooth_numbers="11",quantity=2,unit_price_snapshot=450,purchase_cost_snapshot=100,discount=50)]
        )
        c, items, inv, tids = self.s.case_full_detail(cid)
        self.assertEqual(c["case_no"], "CUSTOM-CASE")
        self.assertEqual(c["doctor_id"], d2)
        self.assertEqual(c["patient_name"], "New Patient")
        self.assertEqual(items[0]["product_id"], p2)
        self.assertEqual(items[0]["quantity"], 2)
        self.assertEqual(inv["invoice_no"], "CUSTOM-INV")
        self.assertEqual(inv["total"], 850)
        self.assertEqual(tids, [t2])
        self.assertEqual(next(x for x in self.s.list_products() if x["id"]==self.p)["stock_qty"], 20)
        self.assertEqual(next(x for x in self.s.list_products() if x["id"]==p2)["stock_qty"], 8)

    def test_owner_can_edit_failure_expense_income_and_invoice_metadata(self):
        cid, _, iid, _ = self.s.create_case(self.d, "P", self.p, 1)
        self.s.record_failure(cid, "Old", 1, 2, 3)
        fid = self.s.list_failures()[0]["id"]
        self.s.update_failure(fid, failure_date="2026-11-02", reason="New", material_cost=10, technician_commission=20, additional_expenses=30, remake_type="charged_reorder", notes="x")
        self.assertEqual(self.s.list_failures()[0]["total_loss"], 60)
        eid = self.s.add_expense("A", 5)
        self.s.update_expense(eid, expense_date="2026-11-03", category="B", description="d", amount=7)
        self.assertEqual(self.s.list_expenses()[0]["amount"], 7)
        oid = self.s.add_other_income("I", 9)
        self.s.update_other_income(oid, income_date="2026-11-04", category="J", description="q", amount=11)
        self.assertEqual(self.s.list_other_income()[0]["amount"], 11)
        self.s.update_invoice_metadata(iid, invoice_no="INV-OWNER", invoice_date="2026-11-05", notes="n")
        inv, _, _ = self.s.invoice_detail(iid)
        self.assertEqual(inv["invoice_no"], "INV-OWNER")
        self.assertEqual(inv["invoice_date"], "2026-11-05")

    def test_owner_can_correct_doctor_summary_visible_values(self):
        self.s.owner_set_doctor_summary(self.d,total_cases=7,total_invoices=1000,total_payments=400,remaining_balance=600,failed_cases=2)
        d=next(x for x in self.s.list_doctors() if x["id"]==self.d)
        self.assertEqual(d["total_cases"],7)
        self.assertEqual(d["total_invoices"],1000)
        self.assertEqual(d["total_payments"],400)
        self.assertEqual(d["remaining_balance"],600)
        self.assertEqual(d["failed_cases"],2)

    def test_owner_can_correct_technician_summary_visible_values(self):
        self.s.owner_set_technician_summary(self.t,assigned_cases=5,completed_cases=3,failed_cases=1,total_commission=900,paid_commission=250,outstanding_commission=650)
        t=next(x for x in self.s.list_technicians() if x["id"]==self.t)
        self.assertEqual(t["assigned_cases"],5)
        self.assertEqual(t["completed_cases"],3)
        self.assertEqual(t["failed_cases"],1)
        self.assertEqual(t["total_commission"],900)
        self.assertEqual(t["paid_commission"],250)
        self.assertEqual(t["outstanding_commission"],650)

    def test_owner_full_invoice_correction_updates_visible_totals_and_doctor(self):
        d2=self.s.add_doctor("Doctor Corrected")
        cid,_,iid,_=self.s.create_case(self.d,"P",self.p,1)
        self.s.owner_update_invoice_full(iid,invoice_no="INV-CORRECT",invoice_date="2026-11-13",doctor_id=d2,total=455,paid=100,status="partial",notes="owner correction")
        inv,items,payments=self.s.invoice_detail(iid)
        self.assertEqual(inv["invoice_no"],"INV-CORRECT")
        self.assertEqual(inv["doctor_id"],d2)
        self.assertEqual(inv["total"],455)
        self.assertEqual(inv["paid"],100)
        self.assertEqual(inv["balance"],355)
        self.assertEqual(inv["status"],"partial")
        self.assertEqual(sum(x["amount"] for x in payments),100)
        with self.db.connect() as con:
            self.assertEqual(con.execute("SELECT doctor_id FROM cases WHERE id=?",(cid,)).fetchone()[0],d2)

    def test_owner_can_delete_stock_movement_and_recalculate_balance(self):
        self.s.stock_movement(self.p,"IN",5,"extra")
        self.s.stock_movement(self.p,"OUT",2,"used")
        moves=self.s.list_stock_movements(self.p)
        out=next(x for x in moves if x["movement_type"]=="OUT" and x["notes"]=="used")
        self.s.delete_stock_movement(out["id"])
        prod=next(x for x in self.s.list_products() if x["id"]==self.p)
        self.assertEqual(prod["stock_qty"],25)
        self.assertFalse(any(x["id"]==out["id"] for x in self.s.list_stock_movements(self.p)))

    def test_owner_can_delete_failure_record(self):
        cid,*_=self.s.create_case(self.d,"P",self.p,1)
        self.s.record_failure(cid,"mistake",10,0,0)
        fid=self.s.list_failures()[0]["id"]
        self.s.delete_failure(fid)
        self.assertEqual(self.s.list_failures(),[])
        with self.db.connect() as con:
            c=con.execute("SELECT failure_status,status FROM cases WHERE id=?",(cid,)).fetchone()
        self.assertEqual(c["failure_status"],0)
        self.assertEqual(c["status"],"In Progress")

    def test_employee_cannot_use_new_owner_corrections_or_deletes(self):
        cid,_,iid,_=self.s.create_case(self.d,"P",self.p,1)
        self.s.record_failure(cid,"x",1,0,0)
        fid=self.s.list_failures()[0]["id"]
        mid=self.s.list_stock_movements(self.p)[0]["id"]
        employee=DentalLabService(self.db,{"id":2,"username":"emp","role":"employee"})
        with self.assertRaises(BusinessError): employee.owner_set_doctor_summary(self.d,total_cases=1,total_invoices=0,total_payments=0,remaining_balance=0,failed_cases=0)
        with self.assertRaises(BusinessError): employee.owner_set_technician_summary(self.t,assigned_cases=0,completed_cases=0,failed_cases=0,total_commission=0,paid_commission=0,outstanding_commission=0)
        with self.assertRaises(BusinessError): employee.owner_update_invoice_full(iid,invoice_no="X",invoice_date="2026-11-13",doctor_id=self.d,total=300,paid=0,status="unpaid",notes="")
        with self.assertRaises(BusinessError): employee.delete_stock_movement(mid)
        with self.assertRaises(BusinessError): employee.delete_failure(fid)


if __name__ == "__main__":
    unittest.main()

import hashlib
import hmac
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from .paths import db_path

SCHEMA_VERSION = 3


class Database:
    def __init__(self, path: Path | None = None):
        self.path = Path(path or db_path())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        con.execute("PRAGMA journal_mode = WAL")
        con.execute("PRAGMA synchronous = NORMAL")
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def initialize(self):
        with self.connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('owner','employee')),
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS doctors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT,
                    clinic_name TEXT,
                    address TEXT,
                    notes TEXT,
                    archived INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    category TEXT,
                    description TEXT,
                    purchase_cost REAL NOT NULL DEFAULT 0,
                    yield_units REAL NOT NULL DEFAULT 1,
                    selling_price REAL NOT NULL DEFAULT 0,
                    stock_qty REAL NOT NULL DEFAULT 0,
                    min_stock REAL NOT NULL DEFAULT 0,
                    unit TEXT NOT NULL DEFAULT 'وحدة',
                    supplier TEXT,
                    archived INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS technicians (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT,
                    commission_rate REAL NOT NULL DEFAULT 0,
                    commission_method TEXT NOT NULL DEFAULT 'selling_percent',
                    fixed_amount REAL NOT NULL DEFAULT 0,
                    archived INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS technician_product_rates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    technician_id INTEGER NOT NULL REFERENCES technicians(id) ON DELETE CASCADE,
                    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                    commission_rate REAL,
                    fixed_amount REAL,
                    UNIQUE(technician_id, product_id)
                );

                CREATE TABLE IF NOT EXISTS doctor_manual_adjustments (
                    doctor_id INTEGER PRIMARY KEY REFERENCES doctors(id) ON DELETE CASCADE,
                    total_cases_delta REAL NOT NULL DEFAULT 0,
                    total_invoices_delta REAL NOT NULL DEFAULT 0,
                    total_payments_delta REAL NOT NULL DEFAULT 0,
                    failed_cases_delta REAL NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS technician_manual_adjustments (
                    technician_id INTEGER PRIMARY KEY REFERENCES technicians(id) ON DELETE CASCADE,
                    assigned_cases_delta REAL NOT NULL DEFAULT 0,
                    completed_cases_delta REAL NOT NULL DEFAULT 0,
                    failed_cases_delta REAL NOT NULL DEFAULT 0,
                    total_commission_delta REAL NOT NULL DEFAULT 0,
                    paid_commission_delta REAL NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_no TEXT NOT NULL UNIQUE,
                    received_date TEXT NOT NULL,
                    delivery_date TEXT,
                    doctor_id INTEGER NOT NULL REFERENCES doctors(id),
                    patient_name TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'New',
                    notes TEXT,
                    failure_status INTEGER NOT NULL DEFAULT 0,
                    order_kind TEXT NOT NULL DEFAULT 'original' CHECK(order_kind IN ('original','free_remake','charged_reorder')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS case_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
                    product_id INTEGER NOT NULL REFERENCES products(id),
                    tooth_numbers TEXT,
                    quantity REAL NOT NULL,
                    unit_price_snapshot REAL NOT NULL,
                    purchase_cost_snapshot REAL NOT NULL,
                    discount REAL NOT NULL DEFAULT 0,
                    line_total REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS case_technicians (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
                    technician_id INTEGER NOT NULL REFERENCES technicians(id),
                    product_id INTEGER REFERENCES products(id),
                    commission_method_snapshot TEXT NOT NULL,
                    commission_rate_snapshot REAL NOT NULL DEFAULT 0,
                    fixed_amount_snapshot REAL NOT NULL DEFAULT 0,
                    custom_commission REAL NOT NULL DEFAULT 0,
                    commission_amount REAL NOT NULL DEFAULT 0,
                    paid_amount REAL NOT NULL DEFAULT 0,
                    UNIQUE(case_id, technician_id, product_id)
                );

                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_no TEXT NOT NULL UNIQUE,
                    doctor_id INTEGER NOT NULL REFERENCES doctors(id),
                    invoice_date TEXT NOT NULL,
                    subtotal REAL NOT NULL DEFAULT 0,
                    discount REAL NOT NULL DEFAULT 0,
                    total REAL NOT NULL DEFAULT 0,
                    paid REAL NOT NULL DEFAULT 0,
                    balance REAL NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'unpaid',
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS invoice_cases (
                    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
                    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
                    PRIMARY KEY(invoice_id, case_id)
                );

                CREATE TABLE IF NOT EXISTS invoice_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
                    case_id INTEGER REFERENCES cases(id),
                    product_id INTEGER REFERENCES products(id),
                    description TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    unit_price REAL NOT NULL,
                    discount REAL NOT NULL DEFAULT 0,
                    line_total REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
                    amount REAL NOT NULL CHECK(amount > 0),
                    payment_date TEXT NOT NULL,
                    method TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS stock_movements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL REFERENCES products(id),
                    movement_type TEXT NOT NULL CHECK(movement_type IN ('IN','OUT','ADJUSTMENT','WASTE','RETURN')),
                    quantity REAL NOT NULL,
                    balance_after REAL NOT NULL,
                    movement_date TEXT NOT NULL,
                    related_case_id INTEGER REFERENCES cases(id),
                    notes TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS failures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id INTEGER NOT NULL REFERENCES cases(id),
                    failure_date TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    material_cost REAL NOT NULL DEFAULT 0,
                    technician_commission REAL NOT NULL DEFAULT 0,
                    additional_expenses REAL NOT NULL DEFAULT 0,
                    total_loss REAL NOT NULL DEFAULT 0,
                    remake_type TEXT NOT NULL DEFAULT 'free_remake',
                    notes TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    expense_date TEXT NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT,
                    amount REAL NOT NULL CHECK(amount >= 0),
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS other_income (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    income_date TEXT NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT,
                    amount REAL NOT NULL CHECK(amount >= 0),
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS commission_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    technician_id INTEGER NOT NULL REFERENCES technicians(id),
                    amount REAL NOT NULL CHECK(amount > 0),
                    payment_date TEXT NOT NULL,
                    notes TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );

                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER REFERENCES users(id),
                    action TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT,
                    details TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_cases_doctor ON cases(doctor_id);
                CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
                CREATE INDEX IF NOT EXISTS idx_cases_dates ON cases(received_date, delivery_date);
                CREATE INDEX IF NOT EXISTS idx_invoices_doctor ON invoices(doctor_id);
                CREATE INDEX IF NOT EXISTS idx_payments_invoice ON payments(invoice_id);
                CREATE INDEX IF NOT EXISTS idx_stock_product ON stock_movements(product_id);
                """
            )
            # v2 migration: package/block purchase cost can yield multiple sale units.
            product_columns = {r[1] for r in con.execute("PRAGMA table_info(products)").fetchall()}
            if "yield_units" not in product_columns:
                con.execute("ALTER TABLE products ADD COLUMN yield_units REAL NOT NULL DEFAULT 1")
            con.execute("UPDATE products SET yield_units=1 WHERE yield_units IS NULL OR yield_units<=0")

            con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version',?)", (str(SCHEMA_VERSION),))
            self._ensure_default_settings(con)
            self._ensure_default_owner(con)

    @staticmethod
    def now() -> str:
        return datetime.now().isoformat(timespec="seconds")

    @staticmethod
    def hash_password(password: str, salt_hex: str | None = None):
        salt = bytes.fromhex(salt_hex) if salt_hex else os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
        return digest.hex(), salt.hex()

    def _ensure_default_owner(self, con):
        exists = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if exists == 0:
            password_hash, salt = self.hash_password("admin123")
            con.execute(
                "INSERT INTO users(username,password_hash,salt,role,active,created_at) VALUES(?,?,?,?,1,?)",
                ("admin", password_hash, salt, "owner", self.now()),
            )

    def _ensure_default_settings(self, con):
        defaults = {
            "lab_name": "Elite Dental Lab",
            "lab_phone": "",
            "lab_address": "",
            "currency": "EGP",
            "date_format": "yyyy-MM-dd",
            "invoice_footer": "شكراً لتعاملكم معنا",
        }
        for k, v in defaults.items():
            con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))

    def authenticate(self, username: str, password: str):
        with self.connect() as con:
            row = con.execute(
                "SELECT * FROM users WHERE username=? AND active=1", (username.strip(),)
            ).fetchone()
            if not row:
                return None
            calc, _ = self.hash_password(password, row["salt"])
            if hmac.compare_digest(calc, row["password_hash"]):
                return dict(row)
            return None

    def audit(self, action: str, entity_type: str, entity_id=None, details="", user_id=None):
        with self.connect() as con:
            con.execute(
                "INSERT INTO audit_log(user_id,action,entity_type,entity_id,details,created_at) VALUES(?,?,?,?,?,?)",
                (user_id, action, entity_type, None if entity_id is None else str(entity_id), details, self.now()),
            )

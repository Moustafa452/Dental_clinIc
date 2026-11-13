# Architecture and Business Logic

## Application layers

1. `app.py` — application startup, RTL setup, login, daily backup, main window.
2. `dental_lab/database.py` — SQLite schema, migrations/bootstrap, authentication and audit writes.
3. `dental_lab/services.py` — all business rules and transactional database operations.
4. `dental_lab/ui.py` — PySide6 desktop pages/dialogs.
5. `dental_lab/exporters.py` — Arabic PDF and Excel exports.
6. `dental_lab/paths.py` — persistent Windows data paths outside the executable/build tree.
7. `tests/test_core.py` — business-rule regression tests.

## Main database relationships

- Doctor -> many Cases
- Doctor -> many Invoices
- Case -> many Case Items
- Case -> many Technician assignments
- Case -> many Failure records
- Invoice -> many Cases through `invoice_cases`
- Invoice -> many Invoice Items
- Invoice -> many Payments
- Product -> many Case Items
- Product -> many Stock Movements
- Technician -> many Case Technician snapshots
- Technician -> many Commission Payments

## Financial formulas

Invoice line:

`line_total = max(0, unit_price_snapshot * quantity - discount)`

Invoice remaining balance:

`balance = total - paid`

Gross profit:

`gross_profit = invoiced_revenue - material_cost - technician_commissions`

Net profit:

`net_profit = gross_profit + other_income - ordinary_expenses - incremental_failure_expenses`

Failed-case total loss is still reported as:

`total_failure_loss = failed_material_cost + failed_technician_commission + additional_failure_expenses`

Material and technician costs are not subtracted twice from net profit because they are already present in the normal case cost/commission totals.

## Technician commission snapshot

When a product is assigned to a technician, the application saves the exact commission method/rate/fixed amount used at that moment. Future edits to the technician profile do not modify historical cases.

Supported methods:
- percentage of selling price
- percentage of product net profit
- fixed amount per unit
- custom amount per case

## Inventory integrity

Stock cannot be changed directly without a `stock_movements` record. Case creation automatically writes an OUT movement. Quantity decreases/cancellation write RETURN movements. Manual operations use IN / OUT / ADJUSTMENT / WASTE / RETURN.

## Free remakes

A case marked `free_remake` uses a zero selling-price snapshot. It still consumes inventory and can still create cost/commission/loss records, but it contributes zero additional invoice revenue.

## Backups

A manual backup uses SQLite's backup API. A daily automatic backup is attempted at application startup once per calendar day. Restoring a backup first creates a safety backup of the current database.

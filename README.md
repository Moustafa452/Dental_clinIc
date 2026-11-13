# Dental Lab Management System — Windows Desktop

This is the actual from-scratch desktop project built from the supplied PRD.

## Stack
- Python 3.12+
- PySide6 desktop UI (Arabic RTL)
- SQLite persistent database
- openpyxl for Excel exports
- Qt PDF writer for Arabic PDF invoices/reports
- PyInstaller for the portable Windows build
- Inno Setup 6 for the normal Windows installer

## First run (no installation)
Double-click:

`Launch_Windows.bat`

It creates a project-local `.venv`, installs dependencies into it, then launches `app.py`.

Default first-login credentials:
- Username: `admin`
- Password: `admin123`

Change the password from Settings after the first login.

## Build portable EXE + Windows installer
Double-click:

`Build_Installer_Windows.bat`

The script runs the automated tests first. If any test fails, packaging stops.

Outputs:
- Portable: `dist\DentalLab\DentalLab.exe`
- Installer: `release\DentalLab_Setup.exe`

Inno Setup 6 is only required for the installer. The portable EXE is still produced if Inno Setup is missing.

## Data safety
Real app data is NOT kept inside the project/build folder. It is stored under:

`%LOCALAPPDATA%\DentalLabSystem\`

Subfolders include:
- `data` — SQLite database
- `backups` — manual/daily backups
- `exports` — invoices and reports
- `logs` — reserved for application logs

Deleting `build`, `dist`, `release`, `.venv`, or `.build-env` will not delete the real laboratory database.

## Implemented functional modules
- Dashboard with KPI cards and seven database-driven charts
- Doctors database, search, edit/archive, balances, PDF account statements
- Cases with unique numbers, statuses, technicians, tooth numbers, discounts and deadlines
- Multiple products in one case/invoice
- Ability to merge multiple same-doctor cases into one invoice
- Product/pricing management
- Inventory movements with IN / OUT / ADJUSTMENT / WASTE / RETURN history
- Technician commission methods and historical rate snapshots
- Commission payments
- Failed-case/loss recording
- Free remake = zero additional revenue
- Invoices and partial/full payments
- Arabic PDF invoices
- Income/expenses and profit calculations
- Ten exportable report categories (PDF / Excel)
- Owner/employee login roles
- Owner-only financial/report/settings pages
- Audit log in the database
- Manual backup, daily automatic backup at startup, restore
- Demo-data seeding and safe operational-data reset (backup first)

## Business rules protected by automated tests
The project contains `tests/test_core.py`. The build BAT runs these tests before creating any EXE.

Covered rules include:
- stock deduction and movement history
- no case creation when stock is insufficient
- free-remake zero revenue
- technician commission snapshot preservation
- partial payments and overpayment rejection
- failed-case loss calculation without double-counting in net profit
- case quantity edits creating inventory/financial adjustments
- cancellation returning inventory and zeroing unpaid invoice revenue
- multiple products on one case/invoice
- multiple cases merged into one invoice


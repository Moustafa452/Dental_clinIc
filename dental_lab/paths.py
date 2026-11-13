from pathlib import Path
import os

APP_NAME = "DentalLabSystem"


def app_data_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    root = base / APP_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def data_dir() -> Path:
    p = app_data_dir() / "data"
    p.mkdir(parents=True, exist_ok=True)
    return p


def backups_dir() -> Path:
    p = app_data_dir() / "backups"
    p.mkdir(parents=True, exist_ok=True)
    return p


def exports_dir() -> Path:
    p = app_data_dir() / "exports"
    p.mkdir(parents=True, exist_ok=True)
    return p


def logs_dir() -> Path:
    p = app_data_dir() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def db_path() -> Path:
    return data_dir() / "dental_lab.sqlite3"

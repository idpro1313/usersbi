# -*- coding: utf-8 -*-
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'app.db'}")

# Маппинг колонок источников (как в config_columns)
AD_COLUMNS = {
    "login": "SamAccountName",
    "domain": "Domain",
    "enabled": "Enabled",
    "password_last_set": "PasswordLastSet",
    "account_expires": "AccountExpirationDate",
    "email": "Mail",
    "phone": "telephoneNumber",
    "display_name": "DisplayName",
    "staff_uuid": "extensionAttribute1",
}
MFA_COLUMNS = {
    "identity": "Identity",
    "email": "Email",
    "name": "Name",
    "phones": "Phones",
    "last_login": "LastLoginDate",
    "created_at": "CreatedAt",
    "status": "Status",
    "is_enrolled": "IsEnrolled",
    "authenticators": "Authenticators",
}
PEOPLE_COLUMNS = {
    "staff_uuid": "StaffUUID",
    "fio": "FIO",
    "email": "Email",
    "phone": "Phone",
}

PEOPLE_EXTRA_COLUMNS = {"ФИО": "fio", "Телефон": "phone", "Мобильный": "phone"}

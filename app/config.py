# -*- coding: utf-8 -*-
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'app.db'}")

# ======================================================================
# Домены AD (ключ → город, DN-суффикс для справки)
# ======================================================================
AD_DOMAINS = {
    "izhevsk":  "Ижевск",     # DC=local,DC=htc-cs,DC=com
    "kostroma": "Кострома",    # DC=ad,DC=local
    "moscow":   "Москва",      # DC=aplana,DC=com
}

# ======================================================================
# Маппинг колонок источников
# Ключ = внутреннее имя поля, значение = имя колонки в файле (основное)
# ======================================================================

# AD: файл All_Uers_all_domain_AD.xlsx
# Фактические колонки: DisplayName, mail, samaccountname, title, manager,
#   enabled, distinguishedName, company, department, mobile, l,
#   telephoneNumber, employeeNumber, StaffUUID, info, PasswordLastSet,
#   groups, expiryDate
AD_COLUMNS = {
    "login": "samaccountname",
    "domain": "",                          # домен извлекается из distinguishedName
    "enabled": "enabled",
    "password_last_set": "PasswordLastSet",
    "account_expires": "expiryDate",
    "email": "mail",
    "phone": "telephoneNumber",
    "display_name": "DisplayName",
    "staff_uuid": "StaffUUID",
}

# MFA: файл multifactor user.csv (разделитель ;)
# Фактические колонки: Identity, Email, Name, Phones, LastLoginDate,
#   CreatedAt, Status, Groups, IsEnrolled, Authenticators, IsSpammer, Id, Ldap
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

# Кадры: файл «Сотрудники с телефонами V1 13.02.2026.xlsx», лист Develonica.People
# Фактические колонки: UUID, Employee, Телефон, Unit, Hub,
#   Employment Status, Unit Manager (RM), Work Format, HR BP, E-mail
PEOPLE_COLUMNS = {
    "staff_uuid": "UUID",
    "fio": "Employee",
    "email": "E-mail",
    "phone": "Телефон",
}

# Русские/альтернативные имена колонок кадров (для совместимости с другими выгрузками)
PEOPLE_EXTRA_COLUMNS = {
    "ФИО": "fio",
    "Мобильный": "phone",
    "Phone": "phone",
    "Email": "email",
    "FIO": "fio",
    "StaffUUID": "staff_uuid",
}

# Альтернативные имена колонок для автоопределения
AD_COLUMN_ALTERNATIVES = {
    "login": ["samaccountname"],
    "staff_uuid": ["StaffUUID"],
    "display_name": ["DisplayName", "Name", "ФИО", "Display name"],
    "email": ["mail", "Mail", "Email", "EmailAddress", "E-mail"],
    "phone": ["telephoneNumber", "mobile", "Phone", "Телефон", "Мобильный"],
    "domain": ["Domain", "Домен", "DomainName"],
    "account_expires": ["expiryDate", "AccountExpirationDate", "AccountExpires"],
    "password_last_set": ["PasswordLastSet", "passwordLastSet"],
    "enabled": ["enabled", "Enabled"],
}
PEOPLE_COLUMN_ALTERNATIVES = {
    "staff_uuid": ["UUID"],
    "fio": ["Employee", "FIO", "ФИО", "Name", "ФИО сотрудника"],
    "email": ["E-mail", "Email", "Mail"],
    "phone": ["Телефон", "Phone", "Мобильный", "mobile"],
}

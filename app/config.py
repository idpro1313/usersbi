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
    "mobile": "mobile",
    "display_name": "DisplayName",
    "staff_uuid": "StaffUUID",
    # --- все остальные поля из файла ---
    "title": "title",
    "manager": "manager",
    "distinguished_name": "distinguishedName",
    "company": "company",
    "department": "department",
    "location": "l",
    "employee_number": "employeeNumber",
    "info": "info",
    "groups": "groups",
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
    # --- все остальные поля из файла ---
    "mfa_groups": "Groups",
    "is_spammer": "IsSpammer",
    "mfa_id": "Id",
    "ldap": "Ldap",
}

# Кадры: файл «Сотрудники с телефонами V1 13.02.2026.xlsx», лист Develonica.People
# Фактические колонки: UUID, Employee, Мобильный, Unit, Hub,
#   Employment Status, Unit Manager (RM), Work Format, HR BP, E-mail
PEOPLE_COLUMNS = {
    "staff_uuid": "UUID",
    "fio": "Employee",
    "email": "E-mail",
    "phone": "Мобильный",
    # --- все остальные поля из файла ---
    "unit": "Unit",
    "hub": "Hub",
    "employment_status": "Employment Status",
    "unit_manager": "Unit Manager (RM)",
    "work_format": "Work Format",
    "hr_bp": "HR BP",
}

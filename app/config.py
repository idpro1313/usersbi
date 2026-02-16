# -*- coding: utf-8 -*-
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'app.db'}")

# Максимальный размер загружаемого файла (по умолчанию 50 МБ)
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", str(50 * 1024 * 1024)))

# Опциональная Basic Auth (активна, только если заданы обе переменные)
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "")

# ======================================================================
# Домены AD (ключ → город, DN-суффикс для справки)
# ======================================================================
AD_DOMAINS = {
    "izhevsk":  "Ижевск",
    "kostroma": "Кострома",
    "moscow":   "Москва",
}

# Короткие метки AD-доменов для сводной таблицы
AD_SOURCE_LABELS = {
    "izhevsk":  "AD izh",
    "kostroma": "AD kst",
    "moscow":   "AD msk",
}

# Полные метки AD-доменов для карточки пользователя
AD_LABELS = {
    "izhevsk":  "AD Ижевск",
    "kostroma": "AD Кострома",
    "moscow":   "AD Москва",
}

# DN-суффиксы для валидации принадлежности УЗ к домену
AD_DOMAIN_DN = {
    "izhevsk":  "DC=local,DC=htc-cs,DC=com",
    "kostroma": "DC=ad,DC=local",
    "moscow":   "DC=aplana,DC=com",
}

# Правила определения типа УЗ по distinguishedName.
# Для каждого домена — упорядоченный список (паттерн DN, тип УЗ).
# Проверяется по порядку, первое совпадение (case-insensitive подстрока) побеждает.
# Если ни одно правило не сработало — тип "Service".
AD_ACCOUNT_TYPE_RULES: dict[str, list[tuple[str, str]]] = {
    "izhevsk": [
        ("OU=HTC,OU=Staff",                       "User"),
        ("OU=Уволенные сотрудники,OU=Staff",       "User"),
        ("OU=OutStaff,OU=Staff",                   "Contractor"),
    ],
    "moscow": [
        ("OU=Departments,OU=Develonica Group",     "User"),
        ("OU=Disabled Users,OU=Develonica Group",  "User"),
        ("OU=Contractor,OU=Develonica Group",      "Contractor"),
    ],
    "kostroma": [
        ("OU=Users,OU=MyBusiness",                 "User"),
        ("OU=Disabled_user,OU=MyBusiness",         "User"),
    ],
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
    "must_change_password": "MustChangePassword",
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

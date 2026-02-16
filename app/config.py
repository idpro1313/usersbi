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
# LDAP-подключение к AD (опциональная синхронизация напрямую)
# Активно, только если заданы AD_LDAP_USER и AD_LDAP_PASSWORD.
# Серверы задаются per-domain через переменные окружения.
# ======================================================================
AD_LDAP = {
    "izhevsk": {
        "server": os.getenv("AD_LDAP_SERVER_IZHEVSK", ""),
        "search_base": "DC=local,DC=htc-cs,DC=com",
    },
    "kostroma": {
        "server": os.getenv("AD_LDAP_SERVER_KOSTROMA", ""),
        "search_base": "DC=ad,DC=local",
    },
    "moscow": {
        "server": os.getenv("AD_LDAP_SERVER_MOSCOW", ""),
        "search_base": "DC=aplana,DC=com",
    },
}
AD_LDAP_USER = os.getenv("AD_LDAP_USER", "")
AD_LDAP_PASSWORD = os.getenv("AD_LDAP_PASSWORD", "")
AD_LDAP_USE_SSL = os.getenv("AD_LDAP_USE_SSL", "false").lower() in ("true", "1", "yes")

# ======================================================================
# Маппинг колонок источников
# Ключ = внутреннее имя поля, значение = имя колонки в файле (основное)
# ======================================================================

# AD: CSV-выгрузка Export-ADUsers.ps1 (разделитель «;», UTF-8 с BOM)
AD_COLUMNS = {
    # --- Основные ---
    "login": "samaccountname",
    "domain": "",                          # домен извлекается из distinguishedName
    "enabled": "Enabled",
    "display_name": "DisplayName",
    "given_name": "GivenName",
    "surname_ad": "Surname",
    "email": "mail",
    "upn": "UserPrincipalName",
    "phone": "telephoneNumber",
    "mobile": "mobile",
    "title": "title",
    "manager": "manager",
    "distinguished_name": "distinguishedName",
    "company": "company",
    "department": "department",
    "description": "Description",
    "employee_type": "employeeType",
    "employee_number": "employeeNumber",
    "location": "l",
    "street_address": "StreetAddress",
    "staff_uuid": "StaffUUID",
    "info": "info",
    # --- Пароль и сроки ---
    "password_last_set": "PasswordLastSet",
    "pwd_last_set": "pwdLastSet",
    "password_expired": "PasswordExpired",
    "password_never_expires": "PasswordNeverExpires",
    "password_not_required": "PasswordNotRequired",
    "cannot_change_password": "CannotChangePassword",
    "account_expiration_date": "AccountExpirationDate",
    "account_expires": "accountExpires",
    # --- Аудит активности ---
    "last_logon_date": "LastLogonDate",
    "last_logon_timestamp": "lastLogonTimestamp",
    "logon_count": "logonCount",
    "last_bad_password_attempt": "LastBadPasswordAttempt",
    "bad_logon_count": "BadLogonCount",
    "locked_out": "LockedOut",
    # --- Жизненный цикл ---
    "created_date": "Created",
    "modified_date": "Modified",
    "when_created": "whenCreated",
    "when_changed": "whenChanged",
    "exported_at": "ExportedAt",
    # --- Безопасность ---
    "trusted_for_delegation": "TrustedForDelegation",
    "trusted_to_auth_for_delegation": "TrustedToAuthForDelegation",
    "account_not_delegated": "AccountNotDelegated",
    "does_not_require_preauth": "DoesNotRequirePreAuth",
    "allow_reversible_password_encryption": "AllowReversiblePasswordEncryption",
    "smartcard_logon_required": "SmartcardLogonRequired",
    "protected_from_accidental_deletion": "ProtectedFromAccidentalDeletion",
    "user_account_control": "userAccountControl",
    "service_principal_names": "ServicePrincipalNames",
    "account_lockout_time": "AccountLockoutTime",
    # --- Идентификаторы ---
    "object_guid": "ObjectGUID",
    "sid": "SID",
    "canonical_name": "CanonicalName",
    # --- Профиль и ограничения ---
    "logon_workstations": "LogonWorkstations",
    "home_drive": "HomeDrive",
    "home_directory": "HomeDirectory",
    "profile_path": "ProfilePath",
    "script_path": "ScriptPath",
    # --- Связи ---
    "groups": "memberOf",
    "direct_reports": "directReports",
    "managed_objects": "managedObjects",
    "primary_group": "PrimaryGroup",
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

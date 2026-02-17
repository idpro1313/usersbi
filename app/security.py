# -*- coding: utf-8 -*-
"""Модуль аналитики безопасности учётных записей AD."""
import re
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db, ADRecord
from app.config import AD_LABELS
from app.consolidation import load_ou_rules, compute_account_type
from app.utils import norm, enabled_str

router = APIRouter(prefix="/api/security", tags=["security"])

# Пороги (дни)
INACTIVE_DAYS = 90
STALE_PASSWORD_DAYS = 180

def _to_dt(val) -> datetime | None:
    """Извлекает datetime из значения поля. Поддерживает datetime и строки."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    s = norm(val)
    if not s:
        return None
    for fmt in ("%d.%m.%Y %H:%M:%S", "%d.%m.%Y", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    return None


def _is_true(val: str) -> bool:
    return norm(val).lower() in ("true", "1", "да", "yes")


def _is_enabled(r: ADRecord) -> bool:
    return enabled_str(r.enabled) == "Да"


def _user_link(r: ADRecord, ou_rules: dict | None = None) -> dict:
    """Минимальный словарь для отображения в таблице."""
    uuid = norm(r.staff_uuid)
    login = norm(r.login)
    key = uuid.lower() if uuid else f"_login_{login.lower()}" if login else ""
    at = compute_account_type(r.ad_source or "", norm(r.distinguished_name), ou_rules) if ou_rules else ""
    return {
        "key": key,
        "login": login,
        "display_name": norm(r.display_name),
        "domain": AD_LABELS.get(r.ad_source, r.ad_source or ""),
        "enabled": enabled_str(r.enabled),
        "account_type": at,
        "distinguished_name": norm(r.distinguished_name),
    }


# ─── Категории проверок ──────────────────────────────────────

def _check_password_never_expires(records: list[ADRecord], ou_rules: dict) -> list[dict]:
    return [_user_link(r, ou_rules) for r in records
            if _is_enabled(r) and _is_true(getattr(r, "password_never_expires", ""))]


def _check_password_not_required(records: list[ADRecord], ou_rules: dict) -> list[dict]:
    return [_user_link(r, ou_rules) for r in records
            if _is_enabled(r) and _is_true(getattr(r, "password_not_required", ""))]


def _check_reversible_encryption(records: list[ADRecord], ou_rules: dict) -> list[dict]:
    return [_user_link(r, ou_rules) for r in records
            if _is_true(getattr(r, "allow_reversible_password_encryption", ""))]


def _check_no_preauth(records: list[ADRecord], ou_rules: dict) -> list[dict]:
    return [_user_link(r, ou_rules) for r in records
            if _is_enabled(r) and _is_true(getattr(r, "does_not_require_preauth", ""))]


def _check_unconstrained_delegation(records: list[ADRecord], ou_rules: dict) -> list[dict]:
    return [_user_link(r, ou_rules) for r in records
            if _is_true(getattr(r, "trusted_for_delegation", ""))]


def _check_protocol_transition(records: list[ADRecord], ou_rules: dict) -> list[dict]:
    return [_user_link(r, ou_rules) for r in records
            if _is_true(getattr(r, "trusted_to_auth_for_delegation", ""))]


def _check_spn_kerberoasting(records: list[ADRecord], ou_rules: dict) -> list[dict]:
    """Пользовательские УЗ с SPN (потенциальный Kerberoasting)."""
    result = []
    for r in records:
        if not _is_enabled(r):
            continue
        spn = norm(getattr(r, "service_principal_names", ""))
        if spn:
            item = _user_link(r, ou_rules)
            item["spn"] = spn
            result.append(item)
    return result


def _check_locked_out(records: list[ADRecord], ou_rules: dict) -> list[dict]:
    return [_user_link(r, ou_rules) for r in records
            if _is_true(getattr(r, "locked_out", ""))]


def _check_must_change_password(records: list[ADRecord], ou_rules: dict) -> list[dict]:
    return [_user_link(r, ou_rules) for r in records
            if _is_enabled(r) and norm(r.must_change_password).lower() in ("да", "true", "yes", "1")]


def _check_password_expired(records: list[ADRecord], ou_rules: dict) -> list[dict]:
    return [_user_link(r, ou_rules) for r in records
            if _is_enabled(r) and _is_true(getattr(r, "password_expired", ""))]


def _check_inactive_accounts(records: list[ADRecord], days: int, ou_rules: dict) -> list[dict]:
    """Активные УЗ, последний вход которых был более N дней назад."""
    cutoff = datetime.now() - timedelta(days=days)
    result = []
    for r in records:
        if not _is_enabled(r):
            continue
        dt = _to_dt(getattr(r, "last_logon_date", None))
        if dt is None:
            dt = _to_dt(getattr(r, "last_logon_timestamp", None))
        if dt is None:
            item = _user_link(r, ou_rules)
            item["last_logon"] = "никогда"
            item["days_ago"] = "∞"
            result.append(item)
        elif dt < cutoff:
            item = _user_link(r, ou_rules)
            item["last_logon"] = dt.strftime("%d.%m.%Y")
            item["days_ago"] = str((datetime.now() - dt).days)
            result.append(item)
    return result


def _check_stale_passwords(records: list[ADRecord], days: int, ou_rules: dict) -> list[dict]:
    """Активные УЗ, пароль которых не менялся более N дней."""
    cutoff = datetime.now() - timedelta(days=days)
    result = []
    for r in records:
        if not _is_enabled(r):
            continue
        dt = _to_dt(r.password_last_set)
        if dt is None:
            dt = _to_dt(getattr(r, "pwd_last_set", None))
        if dt is None:
            continue
        if dt < cutoff:
            item = _user_link(r, ou_rules)
            item["password_last_set"] = dt.strftime("%d.%m.%Y")
            item["days_ago"] = str((datetime.now() - dt).days)
            result.append(item)
    return result


def _check_disabled_with_groups(records: list[ADRecord], ou_rules: dict) -> list[dict]:
    """Отключённые УЗ, всё ещё состоящие в группах безопасности."""
    result = []
    for r in records:
        if _is_enabled(r):
            continue
        groups = norm(r.groups)
        if not groups:
            continue
        count = len([g for g in groups.split(";") if g.strip()])
        if count > 1:
            item = _user_link(r, ou_rules)
            item["group_count"] = count
            result.append(item)
    return result


# ─── API ─────────────────────────────────────────────────────

CATEGORIES = [
    {
        "id": "pwd_never_expires",
        "title": "Бессрочный пароль",
        "severity": "high",
        "description": "Активные УЗ с флагом PasswordNeverExpires. Нарушают политику ротации паролей.",
        "columns": [],
    },
    {
        "id": "pwd_not_required",
        "title": "Пароль не требуется",
        "severity": "critical",
        "description": "Активные УЗ с флагом PasswordNotRequired. Могут быть использованы без аутентификации.",
        "columns": [],
    },
    {
        "id": "reversible_encryption",
        "title": "Обратимое шифрование",
        "severity": "critical",
        "description": "УЗ с AllowReversiblePasswordEncryption. Пароль хранится в обратимом виде — легко извлечь.",
        "columns": [],
    },
    {
        "id": "no_preauth",
        "title": "Без Kerberos Pre-Auth",
        "severity": "critical",
        "description": "Активные УЗ с DoesNotRequirePreAuth. Уязвимы для AS-REP Roasting — офлайн-перебор пароля.",
        "columns": [],
    },
    {
        "id": "unconstrained_delegation",
        "title": "Неограниченное делегирование",
        "severity": "high",
        "description": "УЗ с TrustedForDelegation. Могут олицетворять любого пользователя домена.",
        "columns": [],
    },
    {
        "id": "protocol_transition",
        "title": "Протокольный переход (S4U)",
        "severity": "medium",
        "description": "УЗ с TrustedToAuthForDelegation. Могут запрашивать билеты от имени других пользователей.",
        "columns": [],
    },
    {
        "id": "spn_kerberoasting",
        "title": "SPN (Kerberoasting)",
        "severity": "high",
        "description": "Пользовательские УЗ с ServicePrincipalName. Уязвимы для Kerberoasting — офлайн-перебор пароля сервисной УЗ.",
        "columns": [{"key": "spn", "label": "SPN"}],
    },
    {
        "id": "locked_out",
        "title": "Заблокированные УЗ",
        "severity": "info",
        "description": "УЗ в статусе LockedOut. Возможна brute-force атака или проблема с паролем.",
        "columns": [],
    },
    {
        "id": "must_change_password",
        "title": "Требуется смена пароля",
        "severity": "info",
        "description": "Активные УЗ с установленным флагом «Требовать смену пароля при следующем входе».",
        "columns": [],
    },
    {
        "id": "password_expired",
        "title": "Просроченный пароль",
        "severity": "medium",
        "description": "Активные УЗ с просроченным паролем.",
        "columns": [],
    },
    {
        "id": "inactive_accounts",
        "title": f"Неактивные УЗ (>{INACTIVE_DAYS} дней)",
        "severity": "medium",
        "description": f"Активные УЗ без входа более {INACTIVE_DAYS} дней. Кандидаты на отключение.",
        "columns": [
            {"key": "last_logon", "label": "Последний вход"},
            {"key": "days_ago", "label": "Дней назад"},
        ],
    },
    {
        "id": "stale_passwords",
        "title": f"Старые пароли (>{STALE_PASSWORD_DAYS} дней)",
        "severity": "medium",
        "description": f"Активные УЗ, пароль которых не менялся более {STALE_PASSWORD_DAYS} дней.",
        "columns": [
            {"key": "password_last_set", "label": "Пароль изменён"},
            {"key": "days_ago", "label": "Дней назад"},
        ],
    },
    {
        "id": "disabled_with_groups",
        "title": "Отключённые УЗ в группах",
        "severity": "medium",
        "description": "Отключённые УЗ, всё ещё состоящие в нескольких группах безопасности. Рекомендуется удалить из групп.",
        "columns": [{"key": "group_count", "label": "Групп"}],
    },
]

_CHECK_FN = {
    "pwd_never_expires": _check_password_never_expires,
    "pwd_not_required": _check_password_not_required,
    "reversible_encryption": _check_reversible_encryption,
    "no_preauth": _check_no_preauth,
    "unconstrained_delegation": _check_unconstrained_delegation,
    "protocol_transition": _check_protocol_transition,
    "spn_kerberoasting": _check_spn_kerberoasting,
    "locked_out": _check_locked_out,
    "must_change_password": _check_must_change_password,
    "password_expired": _check_password_expired,
    "inactive_accounts": lambda recs, rules: _check_inactive_accounts(recs, INACTIVE_DAYS, rules),
    "stale_passwords": lambda recs, rules: _check_stale_passwords(recs, STALE_PASSWORD_DAYS, rules),
    "disabled_with_groups": _check_disabled_with_groups,
}


@router.get("/findings")
def security_findings(db: Session = Depends(get_db)):
    """Полный отчёт по всем категориям безопасности."""
    records = db.query(ADRecord).all()
    ou_rules = load_ou_rules(db)
    total_accounts = len(records)
    total_enabled = sum(1 for r in records if _is_enabled(r))

    findings = []
    total_issues = 0
    critical_count = 0
    high_count = 0

    for cat in CATEGORIES:
        fn = _CHECK_FN[cat["id"]]
        items = fn(records, ou_rules)
        count = len(items)
        total_issues += count
        if cat["severity"] == "critical":
            critical_count += count
        elif cat["severity"] == "high":
            high_count += count
        findings.append({
            "id": cat["id"],
            "title": cat["title"],
            "severity": cat["severity"],
            "description": cat["description"],
            "extra_columns": cat["columns"],
            "count": count,
            "items": items,
        })

    return {
        "total_accounts": total_accounts,
        "total_enabled": total_enabled,
        "total_issues": total_issues,
        "critical_count": critical_count,
        "high_count": high_count,
        "findings": findings,
    }

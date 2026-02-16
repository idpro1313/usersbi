# -*- coding: utf-8 -*-
import io
import logging
import re
import threading

import pandas as pd
from app.config import AD_COLUMNS, MFA_COLUMNS, PEOPLE_COLUMNS
from app.utils import norm, norm_phone, safe_datetime

logger = logging.getLogger(__name__)


def _extract_domain_from_dn(dn: str) -> str:
    """Извлекает доменное имя из distinguishedName (DC=aplana,DC=com -> aplana.com)."""
    if not dn:
        return ""
    parts = re.findall(r"DC=([^,]+)", str(dn), re.IGNORECASE)
    return ".".join(parts) if parts else ""


def _map_columns(df: pd.DataFrame, primary: dict) -> pd.DataFrame:
    """Маппинг колонок DataFrame по именам из config (case-insensitive)."""
    rename_map = {}
    col_lower = {c.lower(): c for c in df.columns}
    for target, expected in primary.items():
        if not expected:
            continue
        real_col = col_lower.get(expected.lower())
        if real_col is not None:
            rename_map[real_col] = target
    if rename_map:
        df = df.rename(columns=rename_map)
    return df


def _read_file(content: bytes, filename: str) -> pd.DataFrame:
    """Читает CSV или Excel файл в DataFrame.

    CSV: автоматически определяет разделитель (; или ,) по первой строке.
    Поддержка UTF-8 с BOM (utf-8-sig).
    """
    ext = (filename or "").lower().split(".")[-1]
    if ext in ("xlsx", "xls"):
        return pd.read_excel(io.BytesIO(content), sheet_name=0)
    first_line = content.decode("utf-8-sig", errors="replace").split("\n", 1)[0]
    sep = ";" if first_line.count(";") > first_line.count(",") else ","
    return pd.read_csv(io.BytesIO(content), encoding="utf-8-sig", sep=sep, on_bad_lines="skip")


# Хранит информацию о последнем парсинге для диагностики
_last_parse_info = {}
_parse_info_lock = threading.Lock()


def get_last_parse_info() -> dict:
    with _parse_info_lock:
        return dict(_last_parse_info)


def parse_ad(content: bytes, filename: str, override_domain: str = "",
             expected_dn_suffix: str = "") -> tuple[list[dict], str | None, int]:
    """
    Парсит CSV или Excel выгрузку AD.
    Возвращает (rows, error, skipped_count).
    """
    try:
        df = _read_file(content, filename)
        original_cols = list(df.columns)
        df = _map_columns(df, AD_COLUMNS)
        mapped_cols = list(df.columns)

        # Найти колонку distinguishedName
        dn_col = None
        for c in df.columns:
            if str(c).strip().lower() in ("distinguishedname", "distinguished_name"):
                dn_col = c
                break

        # Домен: извлечь из distinguishedName
        if "domain" not in df.columns:
            if dn_col:
                df["domain"] = df[dn_col].apply(
                    lambda x: _extract_domain_from_dn(str(x) if pd.notna(x) else "")
                )
            else:
                df["domain"] = ""

        # Фильтрация по DN-суффиксу
        total_before = len(df)
        dn_suffix_lower = expected_dn_suffix.lower().replace(" ", "") if expected_dn_suffix else ""
        if dn_suffix_lower and dn_col:
            df = df[df[dn_col].apply(
                lambda x: dn_suffix_lower in str(x).lower().replace(" ", "") if pd.notna(x) else False
            )]
        skipped = total_before - len(df)

        # Диагностика
        with _parse_info_lock:
            _last_parse_info["ad"] = {
                "original_columns": original_cols,
                "mapped_columns": mapped_cols,
                "domain_source": "distinguishedName" if "domain" not in mapped_cols else "column",
                "sample_login": norm(df["login"].iloc[0]) if "login" in df.columns and len(df) > 0 else "NOT FOUND",
                "sample_domain": norm(df["domain"].iloc[0]) if "domain" in df.columns and len(df) > 0 else "NOT FOUND",
                "rows": len(df),
                "skipped_wrong_domain": skipped,
            }
        logger.info("[AD] Original columns: %s", original_cols)
        logger.info("[AD] Mapped columns:   %s", mapped_cols)
        logger.info("[AD] Total in file: %d, accepted: %d, skipped: %d", total_before, len(df), skipped)

        # Используем to_dict вместо iterrows для скорости
        records = df.to_dict("records")
        rows = []
        for r in records:
            domain_val = override_domain if override_domain else norm(r.get("domain", ""))
            pwd_ts = norm(r.get("pwd_last_set", ""))
            rows.append({
                "domain": domain_val,
                # --- основные ---
                "login": norm(r.get("login", "")),
                "enabled": norm(r.get("enabled", "")),
                "display_name": norm(r.get("display_name", "")),
                "given_name": norm(r.get("given_name", "")),
                "surname_ad": norm(r.get("surname_ad", "")),
                "email": norm(r.get("email", "")),
                "upn": norm(r.get("upn", "")),
                "phone": norm_phone(r.get("phone", "")),
                "mobile": norm_phone(r.get("mobile", "")),
                "title": norm(r.get("title", "")),
                "manager": norm(r.get("manager", "")),
                "distinguished_name": norm(r.get("distinguished_name", "")),
                "company": norm(r.get("company", "")),
                "department": norm(r.get("department", "")),
                "description": norm(r.get("description", "")),
                "employee_type": norm(r.get("employee_type", "")),
                "employee_number": norm(r.get("employee_number", "")),
                "location": norm(r.get("location", "")),
                "street_address": norm(r.get("street_address", "")),
                "staff_uuid": norm(r.get("staff_uuid", "")),
                "info": norm(r.get("info", "")),
                # --- пароль и сроки ---
                "password_last_set": safe_datetime(r.get("password_last_set")),
                "pwd_last_set": pwd_ts,
                "must_change_password": "Да" if not pwd_ts else "Нет",
                "password_expired": norm(r.get("password_expired", "")),
                "password_never_expires": norm(r.get("password_never_expires", "")),
                "password_not_required": norm(r.get("password_not_required", "")),
                "cannot_change_password": norm(r.get("cannot_change_password", "")),
                "account_expiration_date": safe_datetime(r.get("account_expiration_date")),
                "account_expires": norm(r.get("account_expires", "")),
                # --- аудит активности ---
                "last_logon_date": safe_datetime(r.get("last_logon_date")),
                "last_logon_timestamp": norm(r.get("last_logon_timestamp", "")),
                "logon_count": norm(r.get("logon_count", "")),
                "last_bad_password_attempt": safe_datetime(r.get("last_bad_password_attempt")),
                "bad_logon_count": norm(r.get("bad_logon_count", "")),
                "locked_out": norm(r.get("locked_out", "")),
                # --- жизненный цикл ---
                "created_date": safe_datetime(r.get("created_date")),
                "modified_date": safe_datetime(r.get("modified_date")),
                "when_created": safe_datetime(r.get("when_created")),
                "when_changed": safe_datetime(r.get("when_changed")),
                "exported_at": safe_datetime(r.get("exported_at")),
                # --- безопасность ---
                "trusted_for_delegation": norm(r.get("trusted_for_delegation", "")),
                "trusted_to_auth_for_delegation": norm(r.get("trusted_to_auth_for_delegation", "")),
                "account_not_delegated": norm(r.get("account_not_delegated", "")),
                "does_not_require_preauth": norm(r.get("does_not_require_preauth", "")),
                "allow_reversible_password_encryption": norm(r.get("allow_reversible_password_encryption", "")),
                "smartcard_logon_required": norm(r.get("smartcard_logon_required", "")),
                "protected_from_accidental_deletion": norm(r.get("protected_from_accidental_deletion", "")),
                "user_account_control": norm(r.get("user_account_control", "")),
                "service_principal_names": norm(r.get("service_principal_names", "")),
                "account_lockout_time": safe_datetime(r.get("account_lockout_time")),
                # --- идентификаторы ---
                "object_guid": norm(r.get("object_guid", "")),
                "sid": norm(r.get("sid", "")),
                "canonical_name": norm(r.get("canonical_name", "")),
                # --- профиль ---
                "logon_workstations": norm(r.get("logon_workstations", "")),
                "home_drive": norm(r.get("home_drive", "")),
                "home_directory": norm(r.get("home_directory", "")),
                "profile_path": norm(r.get("profile_path", "")),
                "script_path": norm(r.get("script_path", "")),
                # --- связи ---
                "groups": norm(r.get("groups", "")),
                "direct_reports": norm(r.get("direct_reports", "")),
                "managed_objects": norm(r.get("managed_objects", "")),
                "primary_group": norm(r.get("primary_group", "")),
            })
        return rows, None, skipped
    except Exception as e:
        logger.error("Ошибка парсинга AD: %s", e, exc_info=True)
        return [], str(e), 0


def parse_mfa(content: bytes, filename: str) -> tuple[list[dict], str | None]:
    try:
        df = pd.read_csv(io.BytesIO(content), encoding="utf-8", sep=";", on_bad_lines="skip")
        original_cols = list(df.columns)
        df = _map_columns(df, MFA_COLUMNS)
        with _parse_info_lock:
            _last_parse_info["mfa"] = {"original_columns": original_cols, "mapped_columns": list(df.columns), "rows": len(df)}
        logger.info("[MFA] Original columns: %s", original_cols)

        rows = []
        for r in df.to_dict("records"):
            rows.append({
                "identity": norm(r.get("identity", "")),
                "email": norm(r.get("email", "")),
                "name": norm(r.get("name", "")),
                "phones": norm_phone(r.get("phones", "")),
                "last_login": safe_datetime(r.get("last_login")),
                "created_at": safe_datetime(r.get("created_at")),
                "status": norm(r.get("status", "")),
                "is_enrolled": norm(r.get("is_enrolled", "")),
                "authenticators": norm(r.get("authenticators", "")),
                "mfa_groups": norm(r.get("mfa_groups", "")),
                "is_spammer": norm(r.get("is_spammer", "")),
                "mfa_id": norm(r.get("mfa_id", "")),
                "ldap": norm(r.get("ldap", "")),
            })
        return rows, None
    except Exception as e:
        logger.error("Ошибка парсинга MFA: %s", e, exc_info=True)
        return [], str(e)


def parse_people(content: bytes, filename: str) -> tuple[list[dict], str | None]:
    try:
        df = pd.read_excel(io.BytesIO(content), sheet_name=0)
        original_cols = list(df.columns)
        df = _map_columns(df, PEOPLE_COLUMNS)
        with _parse_info_lock:
            _last_parse_info["people"] = {"original_columns": original_cols, "mapped_columns": list(df.columns), "rows": len(df)}
        logger.info("[People] Original columns: %s", original_cols)

        rows = []
        for r in df.to_dict("records"):
            rows.append({
                "staff_uuid": norm(r.get("staff_uuid", "")),
                "fio": norm(r.get("fio", "")),
                "email": norm(r.get("email", "")),
                "phone": norm_phone(r.get("phone", "")),
                "unit": norm(r.get("unit", "")),
                "hub": norm(r.get("hub", "")),
                "employment_status": norm(r.get("employment_status", "")),
                "unit_manager": norm(r.get("unit_manager", "")),
                "work_format": norm(r.get("work_format", "")),
                "hr_bp": norm(r.get("hr_bp", "")),
            })
        return rows, None
    except Exception as e:
        logger.error("Ошибка парсинга People: %s", e, exc_info=True)
        return [], str(e)

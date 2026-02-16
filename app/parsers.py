# -*- coding: utf-8 -*-
import io
import logging
import re
import threading

import pandas as pd
from app.config import AD_COLUMNS, MFA_COLUMNS, PEOPLE_COLUMNS
from app.utils import norm, norm_phone, safe_date

logger = logging.getLogger(__name__)


def _extract_domain_from_dn(dn: str) -> str:
    """Извлекает доменное имя из distinguishedName (DC=aplana,DC=com -> aplana.com)."""
    if not dn:
        return ""
    parts = re.findall(r"DC=([^,]+)", str(dn), re.IGNORECASE)
    return ".".join(parts) if parts else ""


def _map_columns(df: pd.DataFrame, primary: dict) -> pd.DataFrame:
    """Прямой маппинг колонок DataFrame по точным именам из config."""
    rename_map = {}
    for target, expected in primary.items():
        if not expected:
            continue
        if expected in df.columns:
            rename_map[expected] = target
    if rename_map:
        df = df.rename(columns=rename_map)
    return df


def _read_file(content: bytes, filename: str) -> pd.DataFrame:
    """Читает CSV или Excel файл в DataFrame."""
    ext = (filename or "").lower().split(".")[-1]
    if ext in ("xlsx", "xls"):
        return pd.read_excel(io.BytesIO(content), sheet_name=0)
    df = pd.read_csv(io.BytesIO(content), encoding="utf-8", sep=",", on_bad_lines="skip")
    if df.shape[1] == 1:
        df = pd.read_csv(io.BytesIO(content), encoding="utf-8", sep=";", on_bad_lines="skip")
    return df


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
            rows.append({
                "domain": domain_val,
                "login": norm(r.get("login", "")),
                "enabled": norm(r.get("enabled", "")),
                "password_last_set": safe_date(r.get("password_last_set")),
                "account_expires": safe_date(r.get("account_expires")),
                "email": norm(r.get("email", "")),
                "phone": norm_phone(r.get("phone", "")),
                "mobile": norm_phone(r.get("mobile", "")),
                "display_name": norm(r.get("display_name", "")),
                "staff_uuid": norm(r.get("staff_uuid", "")),
                "title": norm(r.get("title", "")),
                "manager": norm(r.get("manager", "")),
                "distinguished_name": norm(r.get("distinguished_name", "")),
                "company": norm(r.get("company", "")),
                "department": norm(r.get("department", "")),
                "location": norm(r.get("location", "")),
                "employee_number": norm(r.get("employee_number", "")),
                "info": norm(r.get("info", "")),
                "groups": norm(r.get("groups", "")),
            })
        return rows, None, skipped
    except Exception as e:
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
                "last_login": norm(r.get("last_login", "")),
                "created_at": norm(r.get("created_at", "")),
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
        return [], str(e)

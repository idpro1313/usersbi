# -*- coding: utf-8 -*-
import io
import re
import pandas as pd
from app.config import (
    AD_COLUMNS,
    MFA_COLUMNS,
    PEOPLE_COLUMNS,
    PEOPLE_EXTRA_COLUMNS,
    AD_COLUMN_ALTERNATIVES,
    PEOPLE_COLUMN_ALTERNATIVES,
)


def _norm(s):
    if pd.isna(s) or s is None:
        return ""
    s = str(s).strip()
    return "" if s in ("nan", "None", "#N/A") else s


def _safe_date(x):
    if pd.isna(x):
        return ""
    if hasattr(x, "strftime"):
        return x.strftime("%d.%m.%Y")
    s = str(x).strip()
    if not s or s.lower() in ("nat", "nan", "none", "never"):
        return s if s.lower() == "never" else ""
    # Убираем время из любого формата "дата пробел время"
    s = re.split(r"\s+", s)[0]
    return s


def _extract_domain_from_dn(dn: str) -> str:
    """Извлекает доменное имя из distinguishedName (DC=aplana,DC=com -> aplana.com)."""
    if not dn:
        return ""
    parts = re.findall(r"DC=([^,]+)", str(dn), re.IGNORECASE)
    return ".".join(parts) if parts else ""


def parse_ad(content: bytes, filename: str) -> tuple[list[dict], str | None]:
    """Парсит CSV или Excel выгрузку AD. Возвращает (список dict для вставки в БД, ошибка)."""
    try:
        ext = (filename or "").lower().split(".")[-1]
        if ext == "xlsx" or ext == "xls":
            df = pd.read_excel(io.BytesIO(content), sheet_name=0)
        else:
            df = pd.read_csv(io.BytesIO(content), encoding="utf-8", sep=",", on_bad_lines="skip")
            if df.shape[1] == 1:
                df = pd.read_csv(io.BytesIO(content), encoding="utf-8", sep=";", on_bad_lines="skip")
        # Маппинг: сначала точное совпадение, потом case-insensitive
        inv = {v: k for k, v in AD_COLUMNS.items() if v}
        df = df.rename(columns=lambda c: inv.get(str(c).strip(), c))
        # Case-insensitive fallback
        col_lower = {str(c).strip().lower(): c for c in df.columns}
        for target, alternatives in AD_COLUMN_ALTERNATIVES.items():
            if target not in df.columns:
                for alt in alternatives:
                    real = col_lower.get(alt.lower())
                    if real and real in df.columns:
                        df = df.rename(columns={real: target})
                        col_lower = {str(c).strip().lower(): c for c in df.columns}
                        break
        if "domain" not in df.columns:
            # Извлекаем домен из distinguishedName, если он есть
            dn_col = None
            for c in df.columns:
                if str(c).strip().lower() == "distinguishedname":
                    dn_col = c
                    break
            if dn_col:
                df["domain"] = df[dn_col].apply(lambda x: _extract_domain_from_dn(str(x) if pd.notna(x) else ""))
            else:
                df["domain"] = ""
        rows = []
        for _, r in df.iterrows():
            rows.append({
                "domain": _norm(r.get("domain", "")),
                "login": _norm(r.get("login", "")),
                "enabled": str(r.get("enabled", "")),
                "password_last_set": _safe_date(r.get("password_last_set")),
                "account_expires": _safe_date(r.get("account_expires")),
                "email": _norm(r.get("email", "")),
                "phone": _norm(r.get("phone", "")),
                "display_name": _norm(r.get("display_name", "")),
                "staff_uuid": _norm(r.get("staff_uuid", "")),
            })
        return rows, None
    except Exception as e:
        return [], str(e)


def parse_mfa(content: bytes, filename: str) -> tuple[list[dict], str | None]:
    try:
        df = pd.read_csv(io.BytesIO(content), encoding="utf-8", sep=";", on_bad_lines="skip")
        inv = {v: k for k, v in MFA_COLUMNS.items() if v}
        df = df.rename(columns=lambda c: inv.get(str(c).strip(), c))
        rows = []
        for _, r in df.iterrows():
            rows.append({
                "identity": _norm(r.get("identity", "")),
                "email": _norm(r.get("email", "")),
                "name": _norm(r.get("name", "")),
                "phones": _norm(r.get("phones", "")),
                "last_login": _norm(r.get("last_login", "")),
                "created_at": _norm(r.get("created_at", "")),
                "status": _norm(r.get("status", "")),
                "is_enrolled": _norm(r.get("is_enrolled", "")),
                "authenticators": _norm(r.get("authenticators", "")),
            })
        return rows, None
    except Exception as e:
        return [], str(e)


def parse_people(content: bytes, filename: str) -> tuple[list[dict], str | None]:
    try:
        df = pd.read_excel(io.BytesIO(content), sheet_name=0)
        inv = {v: k for k, v in PEOPLE_COLUMNS.items() if v}
        df = df.rename(columns=lambda c: inv.get(str(c).strip(), c))
        for k, v in PEOPLE_EXTRA_COLUMNS.items():
            if k in df.columns and v not in df.columns:
                df = df.rename(columns={k: v})
        # Case-insensitive fallback
        col_lower = {str(c).strip().lower(): c for c in df.columns}
        for target, alternatives in PEOPLE_COLUMN_ALTERNATIVES.items():
            if target not in df.columns:
                for alt in alternatives:
                    real = col_lower.get(alt.lower())
                    if real and real in df.columns:
                        df = df.rename(columns={real: target})
                        col_lower = {str(c).strip().lower(): c for c in df.columns}
                        break
        rows = []
        for _, r in df.iterrows():
            rows.append({
                "staff_uuid": _norm(r.get("staff_uuid", "")),
                "fio": _norm(r.get("fio", "")),
                "email": _norm(r.get("email", "")),
                "phone": _norm(r.get("phone", "")),
            })
        return rows, None
    except Exception as e:
        return [], str(e)

# -*- coding: utf-8 -*-
import io
import re
import pandas as pd
from app.config import (
    AD_COLUMNS,
    MFA_COLUMNS,
    PEOPLE_COLUMNS,
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
    if not s or s.lower() in ("nat", "nan", "none"):
        return ""
    if s.lower() == "never":
        return "never"
    # Убираем время из любого формата "дата пробел время"
    s = re.split(r"\s+", s)[0]
    return s


def _extract_domain_from_dn(dn: str) -> str:
    """Извлекает доменное имя из distinguishedName (DC=aplana,DC=com -> aplana.com)."""
    if not dn:
        return ""
    parts = re.findall(r"DC=([^,]+)", str(dn), re.IGNORECASE)
    return ".".join(parts) if parts else ""


def _map_columns(df: pd.DataFrame, primary: dict) -> pd.DataFrame:
    """
    Прямой маппинг колонок DataFrame по точным именам из config.
    primary: {внутреннее_имя: имя_колонки_в_файле}
    """
    rename_map = {}
    for target, expected in primary.items():
        if not expected:
            continue
        if expected in df.columns:
            rename_map[expected] = target

    if rename_map:
        df = df.rename(columns=rename_map)

    return df


# Хранит информацию о последнем парсинге для диагностики
_last_parse_info = {}


def get_last_parse_info() -> dict:
    return dict(_last_parse_info)


def parse_ad(content: bytes, filename: str, override_domain: str = "") -> tuple[list[dict], str | None]:
    """Парсит CSV или Excel выгрузку AD. override_domain — если задан, подставляется в поле domain."""
    try:
        ext = (filename or "").lower().split(".")[-1]
        if ext in ("xlsx", "xls"):
            df = pd.read_excel(io.BytesIO(content), sheet_name=0)
        else:
            df = pd.read_csv(io.BytesIO(content), encoding="utf-8", sep=",", on_bad_lines="skip")
            if df.shape[1] == 1:
                df = pd.read_csv(io.BytesIO(content), encoding="utf-8", sep=";", on_bad_lines="skip")

        original_cols = list(df.columns)
        df = _map_columns(df, AD_COLUMNS)
        mapped_cols = list(df.columns)

        # Домен: извлечь из distinguishedName, если колонки domain нет
        if "domain" not in df.columns:
            dn_col = None
            for c in df.columns:
                if str(c).strip().lower() == "distinguishedname":
                    dn_col = c
                    break
            if dn_col:
                df["domain"] = df[dn_col].apply(
                    lambda x: _extract_domain_from_dn(str(x) if pd.notna(x) else "")
                )
            else:
                df["domain"] = ""

        # Диагностика
        _last_parse_info["ad"] = {
            "original_columns": original_cols,
            "mapped_columns": mapped_cols,
            "domain_source": "distinguishedName" if "domain" not in mapped_cols else "column",
            "sample_login": _norm(df["login"].iloc[0]) if "login" in df.columns and len(df) > 0 else "NOT FOUND",
            "sample_domain": _norm(df["domain"].iloc[0]) if "domain" in df.columns and len(df) > 0 else "NOT FOUND",
            "rows": len(df),
        }
        print(f"[AD] Original columns: {original_cols}")
        print(f"[AD] Mapped columns:   {mapped_cols}")
        print(f"[AD] Sample login: {_last_parse_info['ad']['sample_login']}")
        print(f"[AD] Sample domain: {_last_parse_info['ad']['sample_domain']}")

        rows = []
        for _, r in df.iterrows():
            domain_val = override_domain if override_domain else _norm(r.get("domain", ""))
            rows.append({
                "domain": domain_val,
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
        original_cols = list(df.columns)
        df = _map_columns(df, MFA_COLUMNS)
        _last_parse_info["mfa"] = {"original_columns": original_cols, "mapped_columns": list(df.columns), "rows": len(df)}
        print(f"[MFA] Original columns: {original_cols}")

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
        original_cols = list(df.columns)
        df = _map_columns(df, PEOPLE_COLUMNS)
        _last_parse_info["people"] = {"original_columns": original_cols, "mapped_columns": list(df.columns), "rows": len(df)}
        print(f"[People] Original columns: {original_cols}")
        print(f"[People] Mapped columns:   {list(df.columns)}")

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

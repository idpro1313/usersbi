# -*- coding: utf-8 -*-
"""Общие утилиты, используемые во всех модулях бэкенда."""
import re
from datetime import datetime

import pandas as pd

# Форматы дат, распознаваемые парсером
_DATE_FORMATS = [
    "%d.%m.%Y %H:%M:%S",   # 13.02.2026 15:53:29
    "%d.%m.%Y %H:%M",      # 13.02.2026 15:53
    "%d.%m.%Y",             # 13.02.2026
    "%m/%d/%Y %H:%M:%S",   # 02/13/2026 15:53:29
    "%m/%d/%Y",             # 02/13/2026
    "%Y-%m-%d %H:%M:%S",   # 2026-02-13 15:53:29
    "%Y-%m-%d",             # 2026-02-13
]


def norm(s):
    """Нормализация значения в строку. Обрабатывает None, NaN, pandas-типы."""
    if s is None:
        return ""
    if isinstance(s, float):
        if pd.isna(s):
            return ""
        if s == int(s):
            return str(int(s))
        return str(s)
    if isinstance(s, pd.Timestamp):
        return str(s)
    s = str(s).strip()
    return "" if s in ("None", "#N/A") else s


def norm_phone(raw) -> str:
    """
    Универсальный парсер номера телефона.
    Возвращает: +<цифры> или "" если не похоже на номер.
    """
    if pd.isna(raw) or raw is None:
        return ""
    if isinstance(raw, float):
        if raw != raw:  # NaN
            return ""
        raw = str(int(raw))
    else:
        raw = str(raw).strip()
    if not raw or raw.lower() in ("nan", "none", "#n/a", ""):
        return ""
    if raw.endswith(".0"):
        raw = raw[:-2]
    digits = re.sub(r"\D", "", raw)
    if not digits or digits == "0":
        return ""
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    return "+" + digits


def norm_email(s) -> str:
    """Нормализация email в нижний регистр."""
    return norm(s).lower()


def norm_key_login(s) -> str:
    """Нормализация логина/identity для сопоставления (без учёта регистра, без префикса домена)."""
    k = norm(s)
    if not k:
        return ""
    if "\\" in k:
        k = k.split("\\")[-1]
    return k.lower()


def norm_key_uuid(s) -> str:
    """Нормализация StaffUUID для сопоставления."""
    k = norm(s)
    return k.lower() if k else ""


def enabled_str(val) -> str:
    """Преобразование значения enabled в 'Да'/'Нет'."""
    if isinstance(val, bool):
        return "Да" if val else "Нет"
    en_low = norm(val).lower()
    if en_low in ("true", "1", "да", "yes"):
        return "Да"
    if en_low in ("false", "0", "нет", "no"):
        return "Нет"
    return norm(val)


def safe_datetime(x) -> datetime | None:
    """Парсит значение даты в datetime. Возвращает None если не удалось."""
    if x is None:
        return None
    if isinstance(x, datetime):
        return x
    if isinstance(x, pd.Timestamp):
        return x.to_pydatetime()
    if pd.isna(x):
        return None
    s = str(x).strip()
    if not s or s.lower() in ("nat", "nan", "none", "", "never"):
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def fmt_date(dt) -> str:
    """Форматирует datetime → 'DD.MM.YYYY' или '' если None."""
    if dt is None:
        return ""
    if isinstance(dt, datetime):
        return dt.strftime("%d.%m.%Y")
    if isinstance(dt, pd.Timestamp):
        return dt.strftime("%d.%m.%Y")
    return norm(dt)


def fmt_datetime(dt) -> str:
    """Форматирует datetime → 'DD.MM.YYYY HH:MM:SS' или '' если None."""
    if dt is None:
        return ""
    if isinstance(dt, datetime):
        if dt.hour == 0 and dt.minute == 0 and dt.second == 0:
            return dt.strftime("%d.%m.%Y")
        return dt.strftime("%d.%m.%Y %H:%M:%S")
    if isinstance(dt, pd.Timestamp):
        return dt.strftime("%d.%m.%Y %H:%M:%S")
    return norm(dt)


def build_member_dict(r, *, include_location: bool = False, include_domain_label: str = "",
                      account_type: str = "") -> dict:
    """
    Общая функция формирования словаря участника из ADRecord.
    Используется в groups, structure, org для единообразия.
    """
    d = {
        "login": norm(r.login),
        "display_name": norm(r.display_name),
        "email": norm(r.email),
        "enabled": enabled_str(r.enabled),
        "account_type": account_type,
        "password_last_set": fmt_date(r.password_last_set),
        "title": norm(r.title),
        "department": norm(r.department),
        "company": norm(r.company),
        "staff_uuid": norm(r.staff_uuid),
    }
    if include_location:
        d["location"] = norm(r.location)
    if include_domain_label:
        d["domain"] = include_domain_label
    return d


def sort_members(members: list[dict]) -> None:
    """Сортировка списка участников по ФИО/логину (in-place)."""
    members.sort(key=lambda m: (m.get("display_name") or m.get("login") or "").lower())

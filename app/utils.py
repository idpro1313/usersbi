# -*- coding: utf-8 -*-
"""Общие утилиты, используемые во всех модулях бэкенда."""
import re
import pandas as pd


def norm(s):
    """Нормализация значения в строку. Обрабатывает None, NaN, pandas-типы."""
    if pd.isna(s) or s is None:
        return ""
    if isinstance(s, float) and s == int(s):
        s = str(int(s))
    else:
        s = str(s).strip()
    return "" if s in ("nan", "None", "#N/A") else s


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


def safe_date(x) -> str:
    """Нормализация значения даты в строку DD.MM.YYYY."""
    if pd.isna(x):
        return ""
    if hasattr(x, "strftime"):
        return x.strftime("%d.%m.%Y")
    s = str(x).strip()
    if not s or s.lower() in ("nat", "nan", "none"):
        return ""
    if s.lower() == "never":
        return "never"
    s = re.split(r"\s+", s)[0]
    return s

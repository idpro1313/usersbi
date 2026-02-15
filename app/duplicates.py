# -*- coding: utf-8 -*-
"""Модуль анализа дублей логинов между доменами AD."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db, ADRecord
from app.config import AD_SOURCE_LABELS
from app.utils import norm, enabled_str, norm_key_login

router = APIRouter(prefix="/api/duplicates", tags=["duplicates"])


@router.get("")
def get_duplicates(db: Session = Depends(get_db)):
    """
    Находит логины, которые встречаются более чем в одном домене AD.
    Возвращает список записей с подробной информацией по каждому дублю.
    """
    all_recs = db.query(ADRecord).all()

    # Группируем по нормализованному логину → {login: [records]}
    login_map: dict[str, list] = {}
    for r in all_recs:
        login = norm_key_login(r.login)
        if not login:
            continue
        login_map.setdefault(login, []).append(r)

    # Оставляем только те, что встречаются в >1 доменах
    rows = []
    for login, recs in login_map.items():
        domains = set(r.ad_source for r in recs)
        if len(domains) < 2:
            continue

        for r in recs:
            rows.append({
                "login":             norm(r.login),
                "domain":            AD_SOURCE_LABELS.get(r.ad_source, r.ad_source or ""),
                "ad_source":         r.ad_source or "",
                "display_name":      norm(r.display_name),
                "email":             norm(r.email),
                "phone":             norm(r.phone),
                "mobile":            norm(r.mobile),
                "enabled":           enabled_str(r.enabled),
                "password_last_set": norm(r.password_last_set),
                "account_expires":   norm(r.account_expires),
                "staff_uuid":        norm(r.staff_uuid),
                "title":             norm(r.title),
                "department":        norm(r.department),
                "company":           norm(r.company),
                "distinguished_name": norm(r.distinguished_name),
                "domains_count":     len(domains),
            })

    # Сортируем: сначала по логину, потом по домену
    rows.sort(key=lambda x: (x["login"].lower(), x["domain"]))

    # Считаем статистику
    unique_logins = set()
    for r in rows:
        unique_logins.add(r["login"].lower())

    return {
        "rows": rows,
        "total_records": len(rows),
        "unique_logins": len(unique_logins),
    }

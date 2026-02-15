# -*- coding: utf-8 -*-
"""API-эндпоинты для анализа пользователей по StaffUUID."""
from collections import defaultdict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db, ADRecord, MFARecord, PeopleRecord
from app.config import AD_DOMAINS

router = APIRouter(prefix="/api/users", tags=["users"])

_AD_LABELS = {
    "izhevsk": "AD Ижевск",
    "kostroma": "AD Кострома",
    "moscow": "AD Москва",
}


def _norm(s):
    if s is None:
        return ""
    s = str(s).strip()
    return "" if s in ("nan", "None", "#N/A") else s


def _enabled_str(val):
    en = _norm(val).lower()
    if en in ("true", "1", "да", "yes"):
        return "Да"
    if en in ("false", "0", "нет", "no"):
        return "Нет"
    return _norm(val)


@router.get("/list")
def users_list(db: Session = Depends(get_db)):
    """
    Список уникальных пользователей.
    Объединяем по StaffUUID (AD + People) и по login/identity (MFA).
    Возвращаем краткую информацию для дерева/списка.
    """
    users: dict[str, dict] = {}

    # 1) AD-записи: ключ — StaffUUID (если есть) или login
    ad_all = db.query(ADRecord).all()
    for r in ad_all:
        uuid = _norm(r.staff_uuid)
        login = _norm(r.login)
        key = uuid.lower() if uuid else f"_login_{login.lower()}" if login else None
        if not key:
            continue
        if key not in users:
            users[key] = {
                "staff_uuid": uuid,
                "fio": "",
                "logins": [],
                "sources": set(),
                "has_mfa": False,
                "has_people": False,
            }
        u = users[key]
        if not u["staff_uuid"] and uuid:
            u["staff_uuid"] = uuid
        if not u["fio"] and _norm(r.display_name):
            u["fio"] = _norm(r.display_name)
        ad_label = _AD_LABELS.get(r.ad_source, "AD")
        if login and login not in u["logins"]:
            u["logins"].append(login)
        u["sources"].add(ad_label)

    # 2) People-записи
    people_all = db.query(PeopleRecord).all()
    for r in people_all:
        uuid = _norm(r.staff_uuid)
        if not uuid:
            continue
        key = uuid.lower()
        if key not in users:
            users[key] = {
                "staff_uuid": uuid,
                "fio": "",
                "logins": [],
                "sources": set(),
                "has_mfa": False,
                "has_people": False,
            }
        u = users[key]
        if not u["staff_uuid"]:
            u["staff_uuid"] = uuid
        if not u["fio"] and _norm(r.fio):
            u["fio"] = _norm(r.fio)
        u["has_people"] = True
        u["sources"].add("Кадры")

    # 3) MFA-записи: привязка через login = identity
    login_to_key = {}
    for key, u in users.items():
        for login in u["logins"]:
            login_to_key[login.lower()] = key

    mfa_all = db.query(MFARecord).all()
    for r in mfa_all:
        identity = _norm(r.identity)
        if not identity:
            continue
        ident_lower = identity.lower()
        if "\\" in ident_lower:
            ident_lower = ident_lower.split("\\")[-1]

        matched_key = login_to_key.get(ident_lower)
        if matched_key:
            users[matched_key]["has_mfa"] = True
            users[matched_key]["sources"].add("MFA")
        else:
            key = f"_mfa_{ident_lower}"
            if key not in users:
                users[key] = {
                    "staff_uuid": "",
                    "fio": _norm(r.name) or identity,
                    "logins": [identity],
                    "sources": {"MFA"},
                    "has_mfa": True,
                    "has_people": False,
                }
            else:
                users[key]["has_mfa"] = True
                users[key]["sources"].add("MFA")

    # Формируем список
    result = []
    for key, u in users.items():
        result.append({
            "key": key,
            "staff_uuid": u["staff_uuid"],
            "fio": u["fio"],
            "logins": u["logins"],
            "sources": sorted(u["sources"]),
            "has_mfa": u["has_mfa"],
            "has_people": u["has_people"],
        })

    result.sort(key=lambda x: (x["fio"] or x["staff_uuid"] or "".join(x["logins"])).lower())

    return {"users": result, "total": len(result)}


@router.get("/card")
def user_card(
    key: str = Query(..., description="Ключ пользователя (staff_uuid или internal key)"),
    db: Session = Depends(get_db),
):
    """Полная карточка пользователя: все данные из AD, MFA, People."""
    # Определяем, это UUID или внутренний ключ
    staff_uuid = ""
    logins: list[str] = []

    if key.startswith("_login_"):
        login_val = key[7:]
        logins = [login_val]
        ad_recs = db.query(ADRecord).filter(
            ADRecord.login.ilike(login_val)
        ).all()
        if ad_recs and _norm(ad_recs[0].staff_uuid):
            staff_uuid = _norm(ad_recs[0].staff_uuid)
    elif key.startswith("_mfa_"):
        identity_val = key[5:]
        logins = [identity_val]
        ad_recs = []
    else:
        staff_uuid = key
        ad_recs = db.query(ADRecord).filter(
            ADRecord.staff_uuid.ilike(staff_uuid)
        ).all()
        logins = list({_norm(r.login).lower() for r in ad_recs if _norm(r.login)})

    # Если нашли UUID из login-ключа, дополнить AD-записи
    if staff_uuid and key.startswith("_login_"):
        ad_recs = db.query(ADRecord).filter(
            ADRecord.staff_uuid.ilike(staff_uuid)
        ).all()
        logins = list({_norm(r.login).lower() for r in ad_recs if _norm(r.login)})

    # --- AD ---
    ad_cards = []
    for r in ad_recs:
        login = _norm(r.login)
        if login.lower() not in [l.lower() for l in logins]:
            logins.append(login.lower())
        ad_cards.append({
            "ad_source": r.ad_source or "",
            "domain": _AD_LABELS.get(r.ad_source, r.ad_source or ""),
            "login": login,
            "display_name": _norm(r.display_name),
            "email": _norm(r.email),
            "phone": _norm(r.phone),
            "mobile": _norm(r.mobile),
            "enabled": _enabled_str(r.enabled),
            "password_last_set": _norm(r.password_last_set),
            "account_expires": _norm(r.account_expires),
            "title": _norm(r.title),
            "department": _norm(r.department),
            "company": _norm(r.company),
            "location": _norm(r.location),
            "manager": _norm(r.manager),
            "employee_number": _norm(r.employee_number),
            "distinguished_name": _norm(r.distinguished_name),
            "groups": _norm(r.groups),
            "info": _norm(r.info),
            "staff_uuid": _norm(r.staff_uuid),
        })

    # --- MFA ---
    mfa_cards = []
    for login in logins:
        recs = db.query(MFARecord).filter(
            MFARecord.identity.ilike(f"%{login}%")
        ).all()
        for r in recs:
            if r.id in [m.get("_id") for m in mfa_cards]:
                continue
            mfa_cards.append({
                "_id": r.id,
                "identity": _norm(r.identity),
                "name": _norm(r.name),
                "email": _norm(r.email),
                "phones": _norm(r.phones),
                "status": _norm(r.status),
                "is_enrolled": _norm(r.is_enrolled),
                "authenticators": _norm(r.authenticators),
                "last_login": _norm(r.last_login),
                "created_at": _norm(r.created_at),
                "mfa_groups": _norm(r.mfa_groups),
                "ldap": _norm(r.ldap),
            })
    # Убираем _id
    for m in mfa_cards:
        m.pop("_id", None)

    # --- People ---
    people_card = None
    if staff_uuid:
        prec = db.query(PeopleRecord).filter(
            PeopleRecord.staff_uuid.ilike(staff_uuid)
        ).first()
        if prec:
            people_card = {
                "staff_uuid": _norm(prec.staff_uuid),
                "fio": _norm(prec.fio),
                "email": _norm(prec.email),
                "phone": _norm(prec.phone),
                "unit": _norm(prec.unit),
                "hub": _norm(prec.hub),
                "employment_status": _norm(prec.employment_status),
                "unit_manager": _norm(prec.unit_manager),
                "work_format": _norm(prec.work_format),
                "hr_bp": _norm(prec.hr_bp),
            }

    # ФИО: приоритет People → AD → MFA
    fio = ""
    if people_card and people_card["fio"]:
        fio = people_card["fio"]
    elif ad_cards and ad_cards[0]["display_name"]:
        fio = ad_cards[0]["display_name"]
    elif mfa_cards and mfa_cards[0]["name"]:
        fio = mfa_cards[0]["name"]

    return {
        "staff_uuid": staff_uuid,
        "fio": fio,
        "logins": logins,
        "ad": ad_cards,
        "mfa": mfa_cards,
        "people": people_card,
    }

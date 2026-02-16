# -*- coding: utf-8 -*-
"""API-эндпоинты для анализа пользователей по StaffUUID."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from app.database import get_db, ADRecord, MFARecord, PeopleRecord
from app.config import AD_LABELS, AD_SOURCE_LABELS
from app.utils import norm, norm_email, enabled_str

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/list")
def users_list(db: Session = Depends(get_db)):
    """
    Список уникальных пользователей.
    Объединяем по StaffUUID (AD + People) и по login/identity (MFA).
    """
    users: dict[str, dict] = {}

    # 1) AD-записи
    for r in db.query(ADRecord).all():
        uuid = norm(r.staff_uuid)
        login = norm(r.login)
        key = uuid.lower() if uuid else f"_login_{login.lower()}" if login else None
        if not key:
            continue
        if key not in users:
            users[key] = {
                "staff_uuid": uuid, "fio": "", "logins": [],
                "sources": set(), "has_mfa": False, "has_people": False,
                "all_disabled": True,  # все УЗ неактивны?
            }
        u = users[key]
        if not u["staff_uuid"] and uuid:
            u["staff_uuid"] = uuid
        if not u["fio"] and norm(r.display_name):
            u["fio"] = norm(r.display_name)
        ad_label = AD_LABELS.get(r.ad_source, "AD")
        if login and login not in u["logins"]:
            u["logins"].append(login)
        u["sources"].add(ad_label)
        # Если хотя бы одна УЗ активна — пользователь не «полностью отключён»
        if enabled_str(r.enabled) == "Да":
            u["all_disabled"] = False

    # 2) People-записи
    for r in db.query(PeopleRecord).all():
        uuid = norm(r.staff_uuid)
        if not uuid:
            continue
        key = uuid.lower()
        if key not in users:
            users[key] = {
                "staff_uuid": uuid, "fio": "", "logins": [],
                "sources": set(), "has_mfa": False, "has_people": False,
                "all_disabled": False,  # нет AD — не считаем «отключённым»
            }
        u = users[key]
        if not u["staff_uuid"]:
            u["staff_uuid"] = uuid
        if not u["fio"] and norm(r.fio):
            u["fio"] = norm(r.fio)
        u["has_people"] = True
        u["sources"].add("Кадры")

    # 3) MFA-записи
    login_to_key = {}
    for key, u in users.items():
        for login in u["logins"]:
            login_to_key[login.lower()] = key

    for r in db.query(MFARecord).all():
        identity = norm(r.identity)
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
                    "staff_uuid": "", "fio": norm(r.name) or identity,
                    "logins": [identity], "sources": {"MFA"},
                    "has_mfa": True, "has_people": False,
                    "all_disabled": False,
                }
            else:
                users[key]["has_mfa"] = True
                users[key]["sources"].add("MFA")

    # Формируем список
    result = [
        {
            "key": key,
            "staff_uuid": u["staff_uuid"],
            "fio": u["fio"],
            "logins": u["logins"],
            "sources": sorted(u["sources"]),
            "has_mfa": u["has_mfa"],
            "has_people": u["has_people"],
            "all_disabled": u.get("all_disabled", False),
        }
        for key, u in users.items()
    ]
    result.sort(key=lambda x: (x["fio"] or x["staff_uuid"] or "".join(x["logins"])).lower())

    return {"users": result, "total": len(result)}


def _resolve_key(key: str, db: Session):
    """Определяет staff_uuid и logins по ключу пользователя."""
    staff_uuid = ""
    logins: list[str] = []
    ad_recs = []

    if key.startswith("_login_"):
        login_val = key[7:]
        logins = [login_val]
        ad_recs = db.query(ADRecord).filter(ADRecord.login.ilike(login_val)).all()
        if ad_recs and norm(ad_recs[0].staff_uuid):
            staff_uuid = norm(ad_recs[0].staff_uuid)
            # Дополнить все AD-записи по UUID
            ad_recs = db.query(ADRecord).filter(ADRecord.staff_uuid.ilike(staff_uuid)).all()
            logins = list({norm(r.login).lower() for r in ad_recs if norm(r.login)})
    elif key.startswith("_mfa_"):
        logins = [key[5:]]
    else:
        staff_uuid = key
        ad_recs = db.query(ADRecord).filter(ADRecord.staff_uuid.ilike(staff_uuid)).all()
        logins = list({norm(r.login).lower() for r in ad_recs if norm(r.login)})

    return staff_uuid, logins, ad_recs


def _resolve_managers(ad_cards: list[dict], db: Session):
    """
    Для каждой AD-карточки с полем manager (DN руководителя)
    находит запись руководителя в БД и добавляет manager_key + manager_name.
    """
    # Собираем уникальные DN руководителей
    mgr_dns = set()
    for c in ad_cards:
        mgr = c.get("manager", "")
        if mgr:
            mgr_dns.add(mgr.lower())

    if not mgr_dns:
        for c in ad_cards:
            c["manager_key"] = ""
            c["manager_name"] = ""
        return

    # Один запрос: только AD-записи, чей DN совпадает с одним из manager DN
    conditions = [ADRecord.distinguished_name.ilike(dn) for dn in mgr_dns]
    mgr_recs = db.query(ADRecord).filter(or_(*conditions)).all()

    dn_to_info: dict[str, dict] = {}
    for r in mgr_recs:
        dn = norm(r.distinguished_name).lower()
        if not dn:
            continue
        uuid = norm(r.staff_uuid)
        login = norm(r.login)
        key = uuid.lower() if uuid else f"_login_{login.lower()}" if login else ""
        cn = ""
        dn_orig = norm(r.distinguished_name)
        if dn_orig.upper().startswith("CN="):
            cn = dn_orig.split(",")[0][3:]
        dn_to_info[dn] = {
            "key": key,
            "name": norm(r.display_name) or cn or login,
        }

    for c in ad_cards:
        mgr = c.get("manager", "")
        info = dn_to_info.get(mgr.lower(), {}) if mgr else {}
        c["manager_key"] = info.get("key", "")
        c["manager_name"] = info.get("name", "")


def _build_ad_cards(ad_recs, logins):
    """Строит список карточек AD-записей."""
    logins_set = {l.lower() for l in logins}
    cards = []
    for r in ad_recs:
        login = norm(r.login)
        if login.lower() not in logins_set:
            logins.append(login.lower())
            logins_set.add(login.lower())
        cards.append({
            "ad_source": r.ad_source or "",
            "domain": AD_LABELS.get(r.ad_source, r.ad_source or ""),
            "login": login,
            # --- основные ---
            "display_name": norm(r.display_name),
            "given_name": norm(getattr(r, "given_name", "") or ""),
            "surname_ad": norm(getattr(r, "surname_ad", "") or ""),
            "email": norm(r.email),
            "upn": norm(getattr(r, "upn", "") or ""),
            "phone": norm(r.phone),
            "mobile": norm(r.mobile),
            "title": norm(r.title),
            "department": norm(r.department),
            "company": norm(r.company),
            "description": norm(getattr(r, "description", "") or ""),
            "employee_type": norm(getattr(r, "employee_type", "") or ""),
            "employee_number": norm(r.employee_number),
            "location": norm(r.location),
            "street_address": norm(getattr(r, "street_address", "") or ""),
            "manager": norm(r.manager),
            "distinguished_name": norm(r.distinguished_name),
            "staff_uuid": norm(r.staff_uuid),
            "info": norm(r.info),
            "enabled": enabled_str(r.enabled),
            # --- пароль ---
            "password_last_set": norm(r.password_last_set),
            "pwd_last_set": norm(getattr(r, "pwd_last_set", "") or ""),
            "must_change_password": norm(r.must_change_password),
            "password_expired": norm(getattr(r, "password_expired", "") or ""),
            "password_never_expires": norm(getattr(r, "password_never_expires", "") or ""),
            "password_not_required": norm(getattr(r, "password_not_required", "") or ""),
            "cannot_change_password": norm(getattr(r, "cannot_change_password", "") or ""),
            # --- сроки ---
            "account_expiration_date": norm(getattr(r, "account_expiration_date", "") or ""),
            "account_expires": norm(r.account_expires),
            # --- аудит активности ---
            "last_logon_date": norm(getattr(r, "last_logon_date", "") or ""),
            "last_logon_timestamp": norm(getattr(r, "last_logon_timestamp", "") or ""),
            "logon_count": norm(getattr(r, "logon_count", "") or ""),
            "last_bad_password_attempt": norm(getattr(r, "last_bad_password_attempt", "") or ""),
            "bad_logon_count": norm(getattr(r, "bad_logon_count", "") or ""),
            "locked_out": norm(getattr(r, "locked_out", "") or ""),
            # --- жизненный цикл ---
            "created_date": norm(getattr(r, "created_date", "") or ""),
            "modified_date": norm(getattr(r, "modified_date", "") or ""),
            "when_created": norm(getattr(r, "when_created", "") or ""),
            "when_changed": norm(getattr(r, "when_changed", "") or ""),
            "exported_at": norm(getattr(r, "exported_at", "") or ""),
            # --- безопасность ---
            "trusted_for_delegation": norm(getattr(r, "trusted_for_delegation", "") or ""),
            "trusted_to_auth_for_delegation": norm(getattr(r, "trusted_to_auth_for_delegation", "") or ""),
            "account_not_delegated": norm(getattr(r, "account_not_delegated", "") or ""),
            "does_not_require_preauth": norm(getattr(r, "does_not_require_preauth", "") or ""),
            "allow_reversible_password_encryption": norm(getattr(r, "allow_reversible_password_encryption", "") or ""),
            "smartcard_logon_required": norm(getattr(r, "smartcard_logon_required", "") or ""),
            "protected_from_accidental_deletion": norm(getattr(r, "protected_from_accidental_deletion", "") or ""),
            "user_account_control": norm(getattr(r, "user_account_control", "") or ""),
            "service_principal_names": norm(getattr(r, "service_principal_names", "") or ""),
            "account_lockout_time": norm(getattr(r, "account_lockout_time", "") or ""),
            # --- идентификаторы ---
            "object_guid": norm(getattr(r, "object_guid", "") or ""),
            "sid": norm(getattr(r, "sid", "") or ""),
            "canonical_name": norm(getattr(r, "canonical_name", "") or ""),
            # --- профиль ---
            "logon_workstations": norm(getattr(r, "logon_workstations", "") or ""),
            "home_drive": norm(getattr(r, "home_drive", "") or ""),
            "home_directory": norm(getattr(r, "home_directory", "") or ""),
            "profile_path": norm(getattr(r, "profile_path", "") or ""),
            "script_path": norm(getattr(r, "script_path", "") or ""),
            # --- связи ---
            "groups": norm(r.groups),
            "direct_reports": norm(getattr(r, "direct_reports", "") or ""),
            "managed_objects": norm(getattr(r, "managed_objects", "") or ""),
            "primary_group": norm(getattr(r, "primary_group", "") or ""),
        })
    return cards, logins


def _fetch_mfa_cards(logins: list[str], db: Session):
    """Загружает MFA-карточки одним запросом. Точное совпадение логина (с учётом домена)."""
    if not logins:
        return []
    # Точное совпадение: identity = 'login' ИЛИ identity заканчивается на '\login'
    conditions = []
    for login in logins:
        conditions.append(MFARecord.identity.ilike(login))           # exact
        conditions.append(MFARecord.identity.ilike(f"%\\{login}"))   # DOMAIN\login
    recs = db.query(MFARecord).filter(or_(*conditions)).all()
    seen_ids = set()
    logins_lower = {l.lower() for l in logins}
    cards = []
    for r in recs:
        if r.id in seen_ids:
            continue
        # Дополнительная проверка: identity (без домена) должен точно совпадать с одним из логинов
        ident = norm(r.identity)
        ident_clean = ident.split("\\")[-1].lower() if "\\" in ident else ident.lower()
        if ident_clean not in logins_lower:
            continue
        seen_ids.add(r.id)
        cards.append({
            "identity": norm(r.identity),
            "name": norm(r.name),
            "email": norm(r.email),
            "phones": norm(r.phones),
            "status": norm(r.status),
            "is_enrolled": norm(r.is_enrolled),
            "authenticators": norm(r.authenticators),
            "last_login": norm(r.last_login),
            "created_at": norm(r.created_at),
            "mfa_groups": norm(r.mfa_groups),
            "ldap": norm(r.ldap),
        })
    return cards


@router.get("/card")
def user_card(
    key: str = Query(..., description="Ключ пользователя (staff_uuid или internal key)"),
    db: Session = Depends(get_db),
):
    """Полная карточка пользователя: все данные из AD, MFA, People."""
    staff_uuid, logins, ad_recs = _resolve_key(key, db)

    # --- AD ---
    ad_cards, logins = _build_ad_cards(ad_recs, logins)

    # --- Резолв руководителей ---
    _resolve_managers(ad_cards, db)

    # --- MFA (один запрос вместо N) ---
    mfa_cards = _fetch_mfa_cards(logins, db)

    # --- People ---
    people_card = None
    if staff_uuid:
        prec = db.query(PeopleRecord).filter(PeopleRecord.staff_uuid.ilike(staff_uuid)).first()
        if prec:
            people_card = {
                "staff_uuid": norm(prec.staff_uuid),
                "fio": norm(prec.fio),
                "email": norm(prec.email),
                "phone": norm(prec.phone),
                "unit": norm(prec.unit),
                "hub": norm(prec.hub),
                "employment_status": norm(prec.employment_status),
                "unit_manager": norm(prec.unit_manager),
                "work_format": norm(prec.work_format),
                "hr_bp": norm(prec.hr_bp),
            }

    # ФИО: приоритет People → AD → MFA
    fio = ""
    if people_card and people_card["fio"]:
        fio = people_card["fio"]
    elif ad_cards and ad_cards[0]["display_name"]:
        fio = ad_cards[0]["display_name"]
    elif mfa_cards and mfa_cards[0]["name"]:
        fio = mfa_cards[0]["name"]

    # Сводные поля для шапки карточки
    city = ""
    for c in ad_cards:
        if c.get("location"):
            city = c["location"]
            break
    hub = people_card["hub"] if people_card else ""
    dp_unit = people_card["unit"] if people_card else ""
    rm = people_card["unit_manager"] if people_card else ""

    # --- Возможные совпадения ---
    matches = _find_matches(
        key, staff_uuid, logins, fio,
        [c["email"] for c in ad_cards if c.get("email")] +
        ([people_card["email"]] if people_card and people_card.get("email") else []) +
        [c["email"] for c in mfa_cards if c.get("email")],
        db,
    )

    return {
        "staff_uuid": staff_uuid,
        "fio": fio,
        "logins": logins,
        "city": city,
        "hub": hub,
        "dp_unit": dp_unit,
        "rm": rm,
        "ad": ad_cards,
        "mfa": mfa_cards,
        "people": people_card,
        "matches": matches,
    }


def _find_matches(
    own_key: str,
    own_uuid: str,
    own_logins: list[str],
    fio: str,
    emails: list[str],
    db: Session,
) -> list[dict]:
    """
    Ищет «возможные совпадения» — записи из AD, People, MFA,
    у которых совпадает ФИО (точно) или email с текущим пользователем,
    но они НЕ принадлежат ему напрямую (другой StaffUUID / логин).
    Фильтрация кандидатов выполняется на уровне SQL для производительности.
    """
    if not fio and not emails:
        return []

    fio_low = fio.strip().lower() if fio else ""
    email_set = {norm_email(e) for e in emails if norm_email(e)}
    own_uuid_low = own_uuid.lower() if own_uuid else ""
    own_logins_low = {l.lower() for l in own_logins if l}

    matches: list[dict] = []
    seen_keys: set[str] = set()

    # --- AD: фильтрация кандидатов на уровне SQL ---
    ad_conditions = []
    if fio_low:
        ad_conditions.append(func.lower(ADRecord.display_name) == fio_low)
    if email_set:
        ad_conditions.append(func.lower(ADRecord.email).in_(email_set))
    if ad_conditions:
        for r in db.query(ADRecord).filter(or_(*ad_conditions)).all():
            r_uuid = norm(r.staff_uuid).lower()
            r_login = norm(r.login).lower()
            if own_uuid_low and r_uuid and r_uuid == own_uuid_low:
                continue
            if r_login and r_login in own_logins_low:
                continue
            r_fio = norm(r.display_name).strip().lower()
            r_email = norm_email(r.email)
            reason = []
            if fio_low and r_fio and r_fio == fio_low:
                reason.append("ФИО")
            if r_email and r_email in email_set:
                reason.append("Email")
            if not reason:
                continue
            mkey = f"ad_{r.id}"
            if mkey in seen_keys:
                continue
            seen_keys.add(mkey)
            matches.append({
                "source": AD_SOURCE_LABELS.get(r.ad_source, "AD"),
                "fio": norm(r.display_name),
                "email": norm(r.email),
                "login": norm(r.login),
                "staff_uuid": norm(r.staff_uuid),
                "enabled": enabled_str(r.enabled),
                "reason": ", ".join(reason),
            })

    # --- People: фильтрация кандидатов на уровне SQL ---
    people_conditions = []
    if fio_low:
        people_conditions.append(func.lower(PeopleRecord.fio) == fio_low)
    if email_set:
        people_conditions.append(func.lower(PeopleRecord.email).in_(email_set))
    if people_conditions:
        for r in db.query(PeopleRecord).filter(or_(*people_conditions)).all():
            r_uuid = norm(r.staff_uuid).lower()
            if own_uuid_low and r_uuid and r_uuid == own_uuid_low:
                continue
            r_fio = norm(r.fio).strip().lower()
            r_email = norm_email(r.email)
            reason = []
            if fio_low and r_fio and r_fio == fio_low:
                reason.append("ФИО")
            if r_email and r_email in email_set:
                reason.append("Email")
            if not reason:
                continue
            mkey = f"people_{r.id}"
            if mkey in seen_keys:
                continue
            seen_keys.add(mkey)
            matches.append({
                "source": "Кадры",
                "fio": norm(r.fio),
                "email": norm(r.email),
                "login": "",
                "staff_uuid": norm(r.staff_uuid),
                "enabled": "",
                "reason": ", ".join(reason),
            })

    # --- MFA: фильтрация кандидатов на уровне SQL ---
    mfa_conditions = []
    if fio_low:
        mfa_conditions.append(func.lower(MFARecord.name) == fio_low)
    if email_set:
        mfa_conditions.append(func.lower(MFARecord.email).in_(email_set))
    if mfa_conditions:
        for r in db.query(MFARecord).filter(or_(*mfa_conditions)).all():
            r_identity = norm(r.identity)
            r_ident_clean = r_identity.split("\\")[-1].lower() if "\\" in r_identity else r_identity.lower()
            if r_ident_clean and r_ident_clean in own_logins_low:
                continue
            r_fio = norm(r.name).strip().lower()
            r_email = norm_email(r.email)
            reason = []
            if fio_low and r_fio and r_fio == fio_low:
                reason.append("ФИО")
            if r_email and r_email in email_set:
                reason.append("Email")
            if not reason:
                continue
            mkey = f"mfa_{r.id}"
            if mkey in seen_keys:
                continue
            seen_keys.add(mkey)
            matches.append({
                "source": "MFA",
                "fio": norm(r.name),
                "email": norm(r.email),
                "login": r_identity,
                "staff_uuid": "",
                "enabled": "",
                "reason": ", ".join(reason),
            })

    matches.sort(key=lambda m: (m.get("reason", ""), m.get("fio", "").lower()))
    return matches

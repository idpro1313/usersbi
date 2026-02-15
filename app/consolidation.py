# -*- coding: utf-8 -*-
import re
from sqlalchemy.orm import Session
from app.database import ADRecord, MFARecord, PeopleRecord

# Короткие метки AD-доменов для поля "Источник"
_AD_SOURCE_LABELS = {
    "izhevsk":  "AD izh",
    "kostroma": "AD kst",
    "moscow":   "AD msk",
}


def _norm(s):
    if s is None:
        return ""
    s = str(s).strip()
    return "" if s in ("nan", "None", "#N/A") else s


def _norm_key_login(s):
    """Нормализация логина/identity для сопоставления (без учёта регистра, без префикса домена)."""
    k = _norm(s)
    if not k:
        return ""
    if "\\" in k:
        k = k.split("\\")[-1]
    return k.lower()


def _norm_key_uuid(s):
    """Нормализация StaffUUID для сопоставления."""
    k = _norm(s)
    return k.lower() if k else ""


def _norm_phone(s):
    """Телефоны уже нормализованы при загрузке, здесь только trim."""
    return _norm(s)


def _norm_email(s):
    return _norm(s).lower()


def build_consolidated(db: Session) -> list[dict]:
    """Строит сводную таблицу из записей в БД: AD + MFA + кадры."""
    ad_rows = db.query(ADRecord).all()
    mfa_rows = db.query(MFARecord).all()
    people_rows = db.query(PeopleRecord).all()

    def to_ad(r):
        return {
            "ad_source": _norm(r.ad_source),
            "domain": _norm(r.domain),
            "login": _norm(r.login),
            "enabled": _norm(r.enabled),
            "password_last_set": _norm(r.password_last_set),
            "account_expires": _norm(r.account_expires),
            "email_ad": _norm_email(r.email),
            "phone_ad": _norm_phone(r.phone),
            "mobile_ad": _norm_phone(r.mobile),
            "fio_ad": _norm(r.display_name),
            "staff_uuid": _norm(r.staff_uuid),
        }

    def to_mfa(r):
        return {
            "identity": _norm(r.identity),
            "email_mfa": _norm_email(r.email),
            "phone_mfa": _norm_phone(r.phones),
            "fio_mfa": _norm(r.name),
            "last_login_mfa": _norm(r.last_login),
            "created_at_mfa": _norm(r.created_at),
            "is_enrolled": _norm(r.is_enrolled),
            "authenticators": _norm(r.authenticators),
        }

    def to_people(r):
        return {
            "staff_uuid": _norm(r.staff_uuid),
            "email_people": _norm_email(r.email),
            "phone_people": _norm_phone(r.phone),
            "fio_people": _norm(r.fio),
        }

    rows_ad = [to_ad(r) for r in ad_rows]
    rows_mfa = [to_mfa(r) for r in mfa_rows]
    rows_people = [to_people(r) for r in people_rows]

    # Словари по нормализованным ключам, чтобы связывать данные между источниками
    mfa_by_identity = {_norm_key_login(r["identity"]): r for r in rows_mfa if r["identity"]}
    people_by_uuid = {_norm_key_uuid(r["staff_uuid"]): r for r in rows_people if r["staff_uuid"]}
    ad_logins = {_norm_key_login(r["login"]) for r in rows_ad if r["login"]}
    ad_uuids = {_norm_key_uuid(r["staff_uuid"]) for r in rows_ad if r["staff_uuid"]}

    result = []

    for r in rows_ad:
        login = r["login"]
        uuid = r["staff_uuid"]
        mfa = mfa_by_identity.get(_norm_key_login(login), {})
        people = people_by_uuid.get(_norm_key_uuid(uuid), {})

        email_ad = r.get("email_ad", "")
        email_mfa = mfa.get("email_mfa", "")
        email_people = people.get("email_people", "")
        phone_ad = r.get("phone_ad", "")
        mobile_ad = r.get("mobile_ad", "")
        phone_mfa = mfa.get("phone_mfa", "")
        phone_people = people.get("phone_people", "")
        # Множество AD-телефонов для сверки (оба поля)
        ad_phones = {p for p in (phone_ad, mobile_ad) if p}
        fio_ad = r.get("fio_ad", "")
        fio_mfa = mfa.get("fio_mfa", "")
        fio_people = people.get("fio_people", "")

        has_mfa = bool(mfa)
        has_people = bool(people)

        remarks = []
        if not has_people:
            remarks.append("Нет в кадрах")
        if email_ad and email_mfa and email_ad != email_mfa:
            remarks.append("Email AD≠MFA")
        if email_ad and email_people and email_ad != email_people:
            remarks.append("Email AD≠Кадры")
        if email_mfa and email_people and email_mfa != email_people:
            remarks.append("Email MFA≠Кадры")
        # Телефон: MFA/Кадры совпадает хотя бы с одним из AD-телефонов?
        if phone_mfa and ad_phones and phone_mfa not in ad_phones:
            remarks.append("Тел. MFA≠AD")
        if phone_people and ad_phones and phone_people not in ad_phones:
            remarks.append("Тел. Кадры≠AD")
        if phone_mfa and phone_people and phone_mfa != phone_people:
            remarks.append("Тел. MFA≠Кадры")
        if fio_ad and fio_mfa and fio_ad != fio_mfa:
            remarks.append("ФИО AD≠MFA")
        if fio_ad and fio_people and fio_ad != fio_people:
            remarks.append("ФИО AD≠Кадры")
        if fio_mfa and fio_people and fio_mfa != fio_people:
            remarks.append("ФИО MFA≠Кадры")

        en = r["enabled"]
        if isinstance(en, bool):
            en_str = "Да" if en else "Нет"
        else:
            en_low = str(en).strip().lower()
            if en_low in ("true", "1", "да", "yes"):
                en_str = "Да"
            elif en_low in ("false", "0", "нет", "no"):
                en_str = "Нет"
            else:
                en_str = str(en).strip() if str(en).strip() else ""

        result.append({
            "source": _AD_SOURCE_LABELS.get(r.get("ad_source", ""), "AD"),
            "domain": r["domain"],
            "login": login,
            "uz_active": en_str,
            "password_last_set": r["password_last_set"],
            "account_expires": r["account_expires"],
            "staff_uuid": uuid,
            "mfa_enabled": "Да" if has_mfa and str(mfa.get("is_enrolled", "")).lower() in ("true", "1", "да", "yes") else "Нет",
            "mfa_created_at": mfa.get("created_at_mfa", "") if has_mfa else "НЕТ MFA",
            "mfa_last_login": mfa.get("last_login_mfa", "") if has_mfa else "НЕТ MFA",
            "mfa_authenticators": mfa.get("authenticators", "") if has_mfa else "НЕТ MFA",
            "fio_ad": fio_ad,
            "fio_mfa": "НЕТ MFA" if not has_mfa else (fio_mfa if fio_mfa else "НЕТ ФИО"),
            "fio_people": fio_people if has_people else "НЕТ в DP",
            "email_ad": email_ad,
            "email_mfa": "НЕТ MFA" if not has_mfa else (email_mfa if email_mfa else "НЕТ EMAIL"),
            "email_people": "НЕТ в DP" if not has_people else (email_people if email_people else "НЕТ EMAIL"),
            "phone_ad": phone_ad,
            "mobile_ad": mobile_ad,
            "phone_mfa": "НЕТ MFA" if not has_mfa else (phone_mfa if phone_mfa else "НЕТ ТЕЛ"),
            "phone_people": "НЕТ в DP" if not has_people else (phone_people if phone_people else "НЕТ ТЕЛ"),
            "discrepancies": "; ".join(remarks) if remarks else "",
        })

    for r in rows_mfa:
        if _norm_key_login(r["identity"]) in ad_logins:
            continue
        mfa_remarks = ["Нет УЗ в AD"]
        # Попробуем найти в кадрах по email
        has_people = False
        fio_people = ""
        email_people = ""
        phone_people = ""
        for p in rows_people:
            if p.get("email_people") and r.get("email_mfa") and p["email_people"] == r["email_mfa"]:
                has_people = True
                fio_people = p.get("fio_people", "")
                email_people = p.get("email_people", "")
                phone_people = p.get("phone_people", "")
                break
        if not has_people:
            mfa_remarks.append("Нет в кадрах")
        result.append({
            "source": "MFA",
            "domain": "НЕТ УЗ",
            "login": r["identity"],
            "uz_active": "НЕТ УЗ",
            "password_last_set": "НЕТ УЗ",
            "account_expires": "НЕТ УЗ",
            "staff_uuid": "",
            "mfa_enabled": "Да",
            "mfa_created_at": r.get("created_at_mfa", ""),
            "mfa_last_login": r.get("last_login_mfa", ""),
            "mfa_authenticators": r.get("authenticators", ""),
            "fio_ad": "НЕТ УЗ",
            "fio_mfa": r.get("fio_mfa", ""),
            "fio_people": fio_people if has_people else "НЕТ в DP",
            "email_ad": "НЕТ УЗ",
            "email_mfa": r.get("email_mfa", ""),
            "email_people": email_people if has_people else "НЕТ в DP",
            "phone_ad": "НЕТ УЗ",
            "mobile_ad": "НЕТ УЗ",
            "phone_mfa": r.get("phone_mfa", ""),
            "phone_people": phone_people if has_people else "НЕТ в DP",
            "discrepancies": "; ".join(mfa_remarks),
        })

    for r in rows_people:
        if _norm_key_uuid(r["staff_uuid"]) in ad_uuids:
            continue
        result.append({
            "source": "Кадры",
            "domain": "НЕТ УЗ",
            "login": "НЕТ УЗ",
            "uz_active": "НЕТ УЗ",
            "password_last_set": "НЕТ УЗ",
            "account_expires": "НЕТ УЗ",
            "staff_uuid": r["staff_uuid"],
            "mfa_enabled": "",
            "mfa_created_at": "",
            "mfa_last_login": "",
            "mfa_authenticators": "",
            "fio_ad": "НЕТ УЗ",
            "fio_mfa": "",
            "fio_people": r.get("fio_people", ""),
            "email_ad": "НЕТ УЗ",
            "email_mfa": "",
            "email_people": r.get("email_people", ""),
            "phone_ad": "НЕТ УЗ",
            "mobile_ad": "НЕТ УЗ",
            "phone_mfa": "",
            "phone_people": r.get("phone_people", ""),
            "discrepancies": "Нет УЗ в AD",
        })

    return result

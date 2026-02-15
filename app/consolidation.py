# -*- coding: utf-8 -*-
from sqlalchemy.orm import Session
from app.database import ADRecord, MFARecord, PeopleRecord
from app.config import AD_SOURCE_LABELS
from app.utils import norm, norm_phone, norm_email, norm_key_login, norm_key_uuid, enabled_str


def _to_ad(r):
    return {
        "ad_source": norm(r.ad_source),
        "domain": norm(r.domain),
        "login": norm(r.login),
        "enabled": norm(r.enabled),
        "password_last_set": norm(r.password_last_set),
        "account_expires": norm(r.account_expires),
        "email_ad": norm_email(r.email),
        "phone_ad": norm_phone(r.phone),
        "mobile_ad": norm_phone(r.mobile),
        "fio_ad": norm(r.display_name),
        "staff_uuid": norm(r.staff_uuid),
    }


def _to_mfa(r):
    return {
        "identity": norm(r.identity),
        "email_mfa": norm_email(r.email),
        "phone_mfa": norm_phone(r.phones),
        "fio_mfa": norm(r.name),
        "last_login_mfa": norm(r.last_login),
        "created_at_mfa": norm(r.created_at),
        "is_enrolled": norm(r.is_enrolled),
        "authenticators": norm(r.authenticators),
    }


def _to_people(r):
    return {
        "staff_uuid": norm(r.staff_uuid),
        "email_people": norm_email(r.email),
        "phone_people": norm_phone(r.phone),
        "fio_people": norm(r.fio),
    }


def _detect_remarks(r, mfa, people, has_mfa, has_people):
    """Определяет расхождения между данными из AD, MFA и кадров."""
    email_ad = r.get("email_ad", "")
    email_mfa = mfa.get("email_mfa", "")
    email_people = people.get("email_people", "")
    phone_ad = r.get("phone_ad", "")
    mobile_ad = r.get("mobile_ad", "")
    phone_mfa = mfa.get("phone_mfa", "")
    phone_people = people.get("phone_people", "")
    ad_phones = {p for p in (phone_ad, mobile_ad) if p}
    fio_ad = r.get("fio_ad", "")
    fio_mfa = mfa.get("fio_mfa", "")
    fio_people = people.get("fio_people", "")

    remarks = []
    if not has_people:
        remarks.append("Нет в кадрах")
    if email_ad and email_mfa and email_ad != email_mfa:
        remarks.append("Email AD≠MFA")
    if email_ad and email_people and email_ad != email_people:
        remarks.append("Email AD≠Кадры")
    if email_mfa and email_people and email_mfa != email_people:
        remarks.append("Email MFA≠Кадры")
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
    return remarks


def _build_result_row(r, mfa, people, has_mfa, has_people, remarks):
    """Формирует одну строку сводной таблицы для записи AD."""
    fio_mfa = mfa.get("fio_mfa", "")
    email_mfa = mfa.get("email_mfa", "")
    phone_mfa = mfa.get("phone_mfa", "")
    fio_people = people.get("fio_people", "")
    email_people = people.get("email_people", "")
    phone_people = people.get("phone_people", "")

    return {
        "source": AD_SOURCE_LABELS.get(r.get("ad_source", ""), "AD"),
        "domain": r["domain"],
        "login": r["login"],
        "uz_active": enabled_str(r["enabled"]),
        "password_last_set": r["password_last_set"],
        "account_expires": r["account_expires"],
        "staff_uuid": r["staff_uuid"],
        "mfa_enabled": "Да" if has_mfa and str(mfa.get("is_enrolled", "")).lower() in ("true", "1", "да", "yes") else "Нет",
        "mfa_created_at": mfa.get("created_at_mfa", "") if has_mfa else "НЕТ MFA",
        "mfa_last_login": mfa.get("last_login_mfa", "") if has_mfa else "НЕТ MFA",
        "mfa_authenticators": mfa.get("authenticators", "") if has_mfa else "НЕТ MFA",
        "fio_ad": r.get("fio_ad", ""),
        "fio_mfa": "НЕТ MFA" if not has_mfa else (fio_mfa if fio_mfa else "НЕТ ФИО"),
        "fio_people": fio_people if has_people else "НЕТ в DP",
        "email_ad": r.get("email_ad", ""),
        "email_mfa": "НЕТ MFA" if not has_mfa else (email_mfa if email_mfa else "НЕТ EMAIL"),
        "email_people": "НЕТ в DP" if not has_people else (email_people if email_people else "НЕТ EMAIL"),
        "phone_ad": r.get("phone_ad", ""),
        "mobile_ad": r.get("mobile_ad", ""),
        "phone_mfa": "НЕТ MFA" if not has_mfa else (phone_mfa if phone_mfa else "НЕТ ТЕЛ"),
        "phone_people": "НЕТ в DP" if not has_people else (phone_people if phone_people else "НЕТ ТЕЛ"),
        "discrepancies": "; ".join(remarks) if remarks else "",
    }


def build_consolidated(db: Session) -> list[dict]:
    """Строит сводную таблицу из записей в БД: AD + MFA + кадры."""
    rows_ad = [_to_ad(r) for r in db.query(ADRecord).all()]
    rows_mfa = [_to_mfa(r) for r in db.query(MFARecord).all()]
    rows_people = [_to_people(r) for r in db.query(PeopleRecord).all()]

    # Словари для быстрого поиска
    mfa_by_identity = {norm_key_login(r["identity"]): r for r in rows_mfa if r["identity"]}
    people_by_uuid = {norm_key_uuid(r["staff_uuid"]): r for r in rows_people if r["staff_uuid"]}
    people_by_email = {r["email_people"]: r for r in rows_people if r["email_people"]}
    ad_logins = {norm_key_login(r["login"]) for r in rows_ad if r["login"]}
    ad_uuids = {norm_key_uuid(r["staff_uuid"]) for r in rows_ad if r["staff_uuid"]}

    result = []

    # 1) Записи из AD
    for r in rows_ad:
        mfa = mfa_by_identity.get(norm_key_login(r["login"]), {})
        people = people_by_uuid.get(norm_key_uuid(r["staff_uuid"]), {})
        has_mfa = bool(mfa)
        has_people = bool(people)
        remarks = _detect_remarks(r, mfa, people, has_mfa, has_people)
        result.append(_build_result_row(r, mfa, people, has_mfa, has_people, remarks))

    # 2) Записи MFA, не найденные в AD
    for r in rows_mfa:
        if norm_key_login(r["identity"]) in ad_logins:
            continue
        mfa_remarks = ["Нет УЗ в AD"]
        # Поиск в кадрах по email — через dict-индекс O(1)
        people = people_by_email.get(r.get("email_mfa", ""), {}) if r.get("email_mfa") else {}
        has_people = bool(people)
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
            "fio_mfa": r.get("fio_mfa", "") or "НЕТ ФИО",
            "fio_people": people.get("fio_people", "") if has_people else "НЕТ в DP",
            "email_ad": "НЕТ УЗ",
            "email_mfa": r.get("email_mfa", "") or "НЕТ EMAIL",
            "email_people": people.get("email_people", "") if has_people else "НЕТ в DP",
            "phone_ad": "НЕТ УЗ",
            "mobile_ad": "НЕТ УЗ",
            "phone_mfa": r.get("phone_mfa", "") or "НЕТ ТЕЛ",
            "phone_people": people.get("phone_people", "") if has_people else "НЕТ в DP",
            "discrepancies": "; ".join(mfa_remarks),
        })

    # 3) Записи кадров, не найденные в AD
    for r in rows_people:
        if norm_key_uuid(r["staff_uuid"]) in ad_uuids:
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

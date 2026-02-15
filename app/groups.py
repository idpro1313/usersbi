# -*- coding: utf-8 -*-
"""API-эндпоинты для анализа групп AD."""
from collections import defaultdict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db, ADRecord
from app.config import AD_DOMAINS

router = APIRouter(prefix="/api/groups", tags=["groups"])


def _parse_groups(raw: str) -> list[str]:
    """Разбирает строку групп (разделитель ';') в список уникальных имён."""
    if not raw or raw.strip() in ("", "nan", "None"):
        return []
    return [g.strip() for g in raw.split(";") if g.strip()]


@router.get("/tree")
def groups_tree(db: Session = Depends(get_db)):
    """Дерево: домен → список групп с количеством участников."""
    records = db.query(
        ADRecord.ad_source, ADRecord.groups
    ).filter(ADRecord.groups != "", ADRecord.groups.isnot(None)).all()

    # domain_key → { group_name → count }
    tree: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for ad_source, groups_str in records:
        domain_key = ad_source or "unknown"
        for g in _parse_groups(groups_str):
            tree[domain_key][g] += 1

    # Формируем ответ в порядке AD_DOMAINS
    domains = []
    for key in AD_DOMAINS:
        if key not in tree:
            domains.append({"key": key, "city": AD_DOMAINS[key], "groups": [], "total_users": 0})
            continue
        groups_map = tree[key]
        groups_list = sorted(
            [{"name": name, "count": cnt} for name, cnt in groups_map.items()],
            key=lambda x: x["name"].lower(),
        )
        total_users = db.query(ADRecord).filter(ADRecord.ad_source == key).count()
        domains.append({
            "key": key,
            "city": AD_DOMAINS[key],
            "groups": groups_list,
            "total_users": total_users,
        })

    # Если есть записи без домена
    if "unknown" in tree:
        groups_map = tree["unknown"]
        groups_list = sorted(
            [{"name": name, "count": cnt} for name, cnt in groups_map.items()],
            key=lambda x: x["name"].lower(),
        )
        domains.append({
            "key": "unknown",
            "city": "Без домена",
            "groups": groups_list,
            "total_users": 0,
        })

    return {"domains": domains}


@router.get("/members")
def group_members(
    group: str = Query(..., description="Имя группы"),
    domain: str = Query(..., description="Ключ домена (izhevsk, kostroma, moscow)"),
    db: Session = Depends(get_db),
):
    """Список участников конкретной группы в указанном домене."""
    city = AD_DOMAINS.get(domain, domain)

    # Берём все записи домена, у которых непустое поле groups
    records = db.query(ADRecord).filter(
        ADRecord.ad_source == domain,
        ADRecord.groups != "",
        ADRecord.groups.isnot(None),
    ).all()

    members = []
    for r in records:
        user_groups = _parse_groups(r.groups or "")
        if group in user_groups:
            # enabled → Да/Нет
            en = (r.enabled or "").strip().lower()
            if en in ("true", "1", "да", "yes"):
                enabled_str = "Да"
            elif en in ("false", "0", "нет", "no"):
                enabled_str = "Нет"
            else:
                enabled_str = r.enabled or ""

            members.append({
                "login": r.login or "",
                "display_name": r.display_name or "",
                "email": r.email or "",
                "enabled": enabled_str,
                "password_last_set": r.password_last_set or "",
                "title": r.title or "",
                "department": r.department or "",
                "company": r.company or "",
                "staff_uuid": r.staff_uuid or "",
            })

    members.sort(key=lambda m: (m["display_name"] or m["login"]).lower())

    return {
        "group": group,
        "domain": domain,
        "city": city,
        "members": members,
        "count": len(members),
    }

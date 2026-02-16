# -*- coding: utf-8 -*-
"""API-эндпоинты для анализа групп AD."""
from collections import defaultdict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db, ADRecord
from app.config import AD_DOMAINS
from app.utils import build_member_dict, sort_members

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

    tree: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for ad_source, groups_str in records:
        domain_key = ad_source or "unknown"
        for g in _parse_groups(groups_str):
            tree[domain_key][g] += 1

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
            "key": key, "city": AD_DOMAINS[key],
            "groups": groups_list, "total_users": total_users,
        })

    if "unknown" in tree:
        groups_map = tree["unknown"]
        groups_list = sorted(
            [{"name": name, "count": cnt} for name, cnt in groups_map.items()],
            key=lambda x: x["name"].lower(),
        )
        domains.append({"key": "unknown", "city": "Без домена", "groups": groups_list, "total_users": 0})

    return {"domains": domains}


@router.get("/members")
def group_members(
    group: str = Query(..., description="Имя группы"),
    domain: str = Query(..., description="Ключ домена"),
    db: Session = Depends(get_db),
):
    """Список участников конкретной группы в указанном домене."""
    city = AD_DOMAINS.get(domain, domain)
    records = db.query(ADRecord).filter(
        ADRecord.ad_source == domain,
        ADRecord.groups != "",
        ADRecord.groups.isnot(None),
    ).all()

    members = [build_member_dict(r) for r in records if group in _parse_groups(r.groups or "")]
    sort_members(members)
    return {"group": group, "domain": domain, "city": city, "members": members, "count": len(members)}

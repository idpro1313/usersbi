# -*- coding: utf-8 -*-
"""API-эндпоинты для анализа структуры OU Active Directory."""
import re
from collections import defaultdict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db, ADRecord
from app.config import AD_DOMAINS

router = APIRouter(prefix="/api/structure", tags=["structure"])


def _parse_ou_path(dn: str) -> list[str]:
    """
    Извлекает путь OU из distinguishedName (от корня к листу).
    CN=Иванов Иван,OU=Отдел,OU=Департамент,OU=Departments,DC=aplana,DC=com
    → ["Departments", "Департамент", "Отдел"]
    """
    if not dn or dn.strip() in ("", "nan", "None"):
        return []
    # Извлечь все OU=... значения
    ous = re.findall(r"OU=([^,]+)", dn, re.IGNORECASE)
    if not ous:
        return []
    # В DN порядок от листа к корню — переворачиваем
    ous.reverse()
    return ous


def _build_tree(records: list[tuple[str]]) -> dict:
    """
    Строит вложенное дерево OU из списка distinguishedName.
    Возвращает: { "children": { "OU_name": { "count": N, "children": {...} } } }
    """
    root: dict = {"count": 0, "children": {}}

    for (dn_str,) in records:
        path = _parse_ou_path(dn_str or "")
        if not path:
            continue
        node = root
        for part in path:
            if part not in node["children"]:
                node["children"][part] = {"count": 0, "children": {}}
            node = node["children"][part]
        node["count"] += 1

    return root


def _tree_to_list(node: dict, depth: int = 0) -> list[dict]:
    """Рекурсивно преобразует дерево в список для JSON-ответа."""
    result = []
    for name in sorted(node["children"].keys(), key=str.lower):
        child = node["children"][name]
        total = _count_total(child)
        result.append({
            "name": name,
            "count": child["count"],       # непосредственно в этом OU
            "total": total,                 # всего с вложенными
            "children": _tree_to_list(child, depth + 1),
        })
    return result


def _count_total(node: dict) -> int:
    """Считает общее количество записей в узле и всех вложенных."""
    total = node["count"]
    for child in node["children"].values():
        total += _count_total(child)
    return total


@router.get("/tree")
def structure_tree(db: Session = Depends(get_db)):
    """Дерево OU по каждому домену AD."""
    domains = []

    for key, city in AD_DOMAINS.items():
        records = db.query(ADRecord.distinguished_name).filter(
            ADRecord.ad_source == key,
            ADRecord.distinguished_name != "",
            ADRecord.distinguished_name.isnot(None),
        ).all()

        tree = _build_tree(records)
        total_users = db.query(ADRecord).filter(ADRecord.ad_source == key).count()

        domains.append({
            "key": key,
            "city": city,
            "total_users": total_users,
            "tree": _tree_to_list(tree),
        })

    return {"domains": domains}


@router.get("/members")
def structure_members(
    path: str = Query(..., description="Путь OU через '/' (например Departments/Отдел)"),
    domain: str = Query(..., description="Ключ домена"),
    db: Session = Depends(get_db),
):
    """Список пользователей, находящихся непосредственно в указанном OU."""
    city = AD_DOMAINS.get(domain, domain)
    target_parts = [p.strip() for p in path.split("/") if p.strip()]

    records = db.query(ADRecord).filter(
        ADRecord.ad_source == domain,
        ADRecord.distinguished_name != "",
        ADRecord.distinguished_name.isnot(None),
    ).all()

    members = []
    for r in records:
        ou_path = _parse_ou_path(r.distinguished_name or "")
        if ou_path == target_parts:
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
        "path": "/".join(target_parts),
        "ou_name": target_parts[-1] if target_parts else "",
        "domain": domain,
        "city": city,
        "members": members,
        "count": len(members),
    }

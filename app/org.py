# -*- coding: utf-8 -*-
"""API-эндпоинты для модуля «Организация» (Company → Department → пользователи)."""
from collections import defaultdict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db, ADRecord
from app.config import AD_SOURCE_LABELS
from app.consolidation import load_ou_rules, compute_account_type
from app.utils import norm, enabled_str, build_member_dict, sort_members

router = APIRouter(prefix="/api/org", tags=["org"])


@router.get("/tree")
def org_tree(db: Session = Depends(get_db)):
    """
    Дерево: company → department (со всех доменов, без группировки по домену).
    Возвращает count (всего) и enabled_count (активных) для каждого узла.
    """
    records = db.query(
        ADRecord.ad_source, ADRecord.company, ADRecord.department, ADRecord.enabled
    ).all()

    # company → department → {count, enabled_count}
    tree: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: {"count": 0, "enabled_count": 0})
    )

    for ad_source, company, department, enabled_val in records:
        comp = norm(company) or "(без компании)"
        dept = norm(department) or "(без отдела)"
        tree[comp][dept]["count"] += 1
        if enabled_str(enabled_val) == "Да":
            tree[comp][dept]["enabled_count"] += 1

    companies = []
    for comp_name in sorted(tree.keys(), key=str.lower):
        depts = tree[comp_name]
        dept_list = sorted(
            [
                {
                    "name": d,
                    "count": info["count"],
                    "enabled_count": info["enabled_count"],
                }
                for d, info in depts.items()
            ],
            key=lambda x: x["name"].lower(),
        )
        companies.append({
            "name": comp_name,
            "departments": dept_list,
            "count": sum(d["count"] for d in dept_list),
            "enabled_count": sum(d["enabled_count"] for d in dept_list),
        })

    total = db.query(ADRecord).count()
    return {"companies": companies, "total_users": total}


@router.get("/members")
def org_members(
    company: str = Query("", description="Компания"),
    department: str = Query("", description="Отдел"),
    db: Session = Depends(get_db),
):
    """Список пользователей по компании и/или отделу."""
    q = db.query(ADRecord)

    if company:
        if company == "(без компании)":
            q = q.filter((ADRecord.company == "") | (ADRecord.company.is_(None)))
        else:
            q = q.filter(ADRecord.company == company)

    if department:
        if department == "(без отдела)":
            q = q.filter((ADRecord.department == "") | (ADRecord.department.is_(None)))
        else:
            q = q.filter(ADRecord.department == department)

    records = q.all()

    ou_rules = load_ou_rules(db)
    members = [
        build_member_dict(r, include_location=True,
                          include_domain_label=AD_SOURCE_LABELS.get(r.ad_source, r.ad_source or ""),
                          account_type=compute_account_type(r.ad_source or "", norm(r.distinguished_name), ou_rules))
        for r in records
    ]
    sort_members(members)
    return {
        "company": company, "department": department,
        "members": members, "count": len(members),
    }

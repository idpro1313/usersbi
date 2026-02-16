# -*- coding: utf-8 -*-
"""API-эндпоинты для модуля «Организация» (Company → Department → пользователи)."""
from collections import defaultdict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db, ADRecord
from app.config import AD_DOMAINS, AD_SOURCE_LABELS
from app.utils import norm, enabled_str

router = APIRouter(prefix="/api/org", tags=["org"])


@router.get("/tree")
def org_tree(db: Session = Depends(get_db)):
    """
    Дерево: company → department (со всех доменов, без группировки по домену).
    """
    records = db.query(
        ADRecord.ad_source, ADRecord.company, ADRecord.department
    ).all()

    # company → department → count
    tree: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for ad_source, company, department in records:
        comp = norm(company) or "(без компании)"
        dept = norm(department) or "(без отдела)"
        tree[comp][dept] += 1

    companies = []
    for comp_name in sorted(tree.keys(), key=str.lower):
        depts = tree[comp_name]
        dept_list = sorted(
            [{"name": d, "count": c} for d, c in depts.items()],
            key=lambda x: x["name"].lower(),
        )
        companies.append({
            "name": comp_name,
            "departments": dept_list,
            "count": sum(d["count"] for d in dept_list),
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

    members = []
    for r in records:
        members.append({
            "login": norm(r.login),
            "display_name": norm(r.display_name),
            "email": norm(r.email),
            "enabled": enabled_str(r.enabled),
            "password_last_set": norm(r.password_last_set),
            "title": norm(r.title),
            "department": norm(r.department),
            "company": norm(r.company),
            "location": norm(r.location),
            "domain": AD_SOURCE_LABELS.get(r.ad_source, r.ad_source or ""),
            "staff_uuid": norm(r.staff_uuid),
        })

    members.sort(key=lambda m: (m["display_name"] or m["login"]).lower())
    return {
        "company": company, "department": department,
        "members": members, "count": len(members),
    }

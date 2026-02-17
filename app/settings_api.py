# -*- coding: utf-8 -*-
"""API настроек приложения: LDAP-подключения, пользователи."""
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.database import get_db, get_setting, set_setting, AppSetting, AppUser
from app.auth import require_admin, encrypt_value, decrypt_value, hash_password
import json
from app.config import AD_DOMAINS, AD_ACCOUNT_TYPE_RULES, ACCOUNT_TYPES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])

_LDAP_DOMAINS = list(AD_DOMAINS.keys())


# ── LDAP settings ──────────────────────────────────────────

@router.get("/ldap")
async def get_ldap_settings(
    _user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Текущие LDAP-настройки всех доменов."""
    domains = {}
    for key in _LDAP_DOMAINS:
        domains[key] = {
            "city": AD_DOMAINS[key],
            "server": get_setting(db, f"ldap.{key}.server"),
            "search_base": get_setting(db, f"ldap.{key}.search_base"),
            "enabled": get_setting(db, f"ldap.{key}.enabled", "false"),
        }
    return {
        "domains": domains,
        "user": get_setting(db, "ldap.user"),
        "password": "********" if get_setting(db, "ldap.password") else "",
        "use_ssl": get_setting(db, "ldap.use_ssl", "false"),
        "auth_domain": get_setting(db, "ldap.auth_domain", "izhevsk"),
        "bind_user_format": get_setting(db, "ldap.bind_user_format", "{username}"),
        "jwt_expire_hours": get_setting(db, "jwt.expire_hours", "12"),
    }


@router.put("/ldap")
async def update_ldap_settings(
    payload: dict[str, Any] = Body(...),
    _user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Обновить настройки LDAP."""
    domains_data = payload.get("domains", {})
    for key in _LDAP_DOMAINS:
        d = domains_data.get(key, {})
        if "server" in d:
            set_setting(db, f"ldap.{key}.server", d["server"])
        if "search_base" in d:
            set_setting(db, f"ldap.{key}.search_base", d["search_base"])
        if "enabled" in d:
            set_setting(db, f"ldap.{key}.enabled", str(d["enabled"]).lower())

    if "user" in payload:
        set_setting(db, "ldap.user", payload["user"])
    if "password" in payload and payload["password"] != "********":
        encrypted = encrypt_value(payload["password"])
        set_setting(db, "ldap.password", encrypted)
    if "use_ssl" in payload:
        set_setting(db, "ldap.use_ssl", str(payload["use_ssl"]).lower())
    if "auth_domain" in payload:
        set_setting(db, "ldap.auth_domain", payload["auth_domain"])
    if "bind_user_format" in payload:
        set_setting(db, "ldap.bind_user_format", payload["bind_user_format"])
    if "jwt_expire_hours" in payload:
        set_setting(db, "jwt.expire_hours", str(payload["jwt_expire_hours"]))

    db.commit()
    return {"ok": True}


@router.post("/ldap/test")
async def test_ldap_connection(
    payload: dict[str, Any] = Body(...),
    _user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Проверить подключение к LDAP-серверу."""
    try:
        from ldap3 import Server, Connection, ALL as LDAP_ALL
    except ImportError:
        raise HTTPException(500, "ldap3 не установлена")

    domain_key = payload.get("domain", "")
    server_addr = payload.get("server", "") or get_setting(db, f"ldap.{domain_key}.server")
    user = payload.get("user", "") or get_setting(db, "ldap.user")
    password = payload.get("password", "")
    if password == "********" or not password:
        password = decrypt_value(get_setting(db, "ldap.password"))

    use_ssl_str = payload.get("use_ssl", get_setting(db, "ldap.use_ssl", "false"))
    use_ssl = str(use_ssl_str).lower() in ("true", "1")

    if not server_addr:
        raise HTTPException(400, "Не указан адрес сервера")
    if not user or not password:
        raise HTTPException(400, "Не указаны учётные данные")

    port = 636 if use_ssl else 389
    try:
        server = Server(server_addr, port=port, use_ssl=use_ssl, get_info=LDAP_ALL)
        conn = Connection(server, user=user, password=password, auto_bind=True)
        conn.unbind()
        return {"ok": True, "message": f"Подключение к {server_addr}:{port} успешно"}
    except Exception as e:
        return {"ok": False, "message": f"Ошибка: {e}"}


# ── Users CRUD ─────────────────────────────────────────────

@router.get("/users")
async def list_users(
    _user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    users = db.query(AppUser).order_by(AppUser.created_at).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "display_name": u.display_name,
            "role": u.role,
            "domain": u.domain,
            "is_active": u.is_active,
            "is_local": bool(u.password_hash),
            "last_login": u.last_login.isoformat() if u.last_login else None,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.post("/users")
async def add_user(
    payload: dict[str, Any] = Body(...),
    current: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    username = (payload.get("username") or "").strip().lower()
    if not username:
        raise HTTPException(400, "Логин обязателен")
    if db.query(AppUser).filter_by(username=username).first():
        raise HTTPException(409, f"Пользователь {username} уже существует")
    role = payload.get("role", "viewer")
    if role not in ("admin", "viewer"):
        role = "viewer"
    pwd = (payload.get("password") or "").strip()
    user = AppUser(
        username=username,
        display_name=payload.get("display_name", ""),
        password_hash=hash_password(pwd) if pwd else "",
        role=role,
        domain=payload.get("domain", ""),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"ok": True, "id": user.id}


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    payload: dict[str, Any] = Body(...),
    current: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(AppUser).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    if user.username == current["username"] and payload.get("role") == "viewer":
        raise HTTPException(400, "Нельзя понизить себя")

    if "role" in payload and payload["role"] in ("admin", "viewer"):
        user.role = payload["role"]
    if "display_name" in payload:
        user.display_name = payload["display_name"]
    if "domain" in payload:
        user.domain = payload["domain"]
    if "password" in payload:
        pwd = (payload["password"] or "").strip()
        user.password_hash = hash_password(pwd) if pwd else ""
    if "is_active" in payload:
        if user.username == current["username"] and not payload["is_active"]:
            raise HTTPException(400, "Нельзя заблокировать себя")
        user.is_active = payload["is_active"]
    db.commit()
    return {"ok": True}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(AppUser).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    if user.username == current["username"]:
        raise HTTPException(400, "Нельзя удалить себя")
    db.delete(user)
    db.commit()
    return {"ok": True}


# ── OU → Account Type mapping ─────────────────────────────

def _get_ou_rules(db) -> dict:
    """Возвращает правила из БД или дефолтные из config."""
    raw = get_setting(db, "ou_type_rules")
    if raw:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            pass
    return {k: [list(t) for t in v] for k, v in AD_ACCOUNT_TYPE_RULES.items()}


@router.get("/ou-rules")
async def get_ou_rules(
    _user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Текущие правила маппинга OU→тип УЗ."""
    rules = _get_ou_rules(db)
    return {
        "rules": rules,
        "domains": {k: v for k, v in AD_DOMAINS.items()},
        "account_types": ACCOUNT_TYPES,
    }


@router.put("/ou-rules")
async def update_ou_rules(
    payload: dict[str, Any] = Body(...),
    _user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Обновить правила маппинга OU→тип УЗ."""
    rules = payload.get("rules", {})
    for domain_key, domain_rules in rules.items():
        if domain_key not in AD_DOMAINS:
            raise HTTPException(400, f"Неизвестный домен: {domain_key}")
        if not isinstance(domain_rules, list):
            raise HTTPException(400, f"Правила для {domain_key} должны быть списком")
        for rule in domain_rules:
            if not isinstance(rule, list) or len(rule) != 2:
                raise HTTPException(400, "Каждое правило — [паттерн, тип]")
            if rule[1] not in ACCOUNT_TYPES:
                raise HTTPException(400, f"Недопустимый тип: {rule[1]}")
    set_setting(db, "ou_type_rules", json.dumps(rules, ensure_ascii=False))
    db.commit()
    return {"ok": True}


@router.post("/ou-rules/reset")
async def reset_ou_rules(
    _user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Сбросить правила к значениям по умолчанию."""
    defaults = {k: [list(t) for t in v] for k, v in AD_ACCOUNT_TYPE_RULES.items()}
    set_setting(db, "ou_type_rules", json.dumps(defaults, ensure_ascii=False))
    db.commit()
    return {"ok": True, "rules": defaults}

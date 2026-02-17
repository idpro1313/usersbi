# -*- coding: utf-8 -*-
"""Модуль авторизации: LDAP bind + JWT + FastAPI dependencies."""
import logging
from datetime import datetime, timezone, timedelta

import jwt
from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db, get_setting, SessionLocal, AppUser, is_auth_configured
from app.config import APP_SECRET_KEY

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)

try:
    from ldap3 import Server, Connection, ALL as LDAP_ALL
    _LDAP3_OK = True
except ImportError:
    _LDAP3_OK = False


# ── Fernet шифрование паролей ──────────────────────────────

def _fernet():
    """Возвращает Fernet-объект для шифрования/расшифровки."""
    if not APP_SECRET_KEY:
        return None
    try:
        return Fernet(APP_SECRET_KEY)
    except Exception:
        return None


def encrypt_value(plain: str) -> str:
    f = _fernet()
    if not f or not plain:
        return plain
    return f.encrypt(plain.encode()).decode()


def decrypt_value(encrypted: str) -> str:
    f = _fernet()
    if not f or not encrypted:
        return encrypted
    try:
        return f.decrypt(encrypted.encode()).decode()
    except InvalidToken:
        return encrypted


# ── LDAP bind ──────────────────────────────────────────────

def authenticate_ad(username: str, password: str, domain: str) -> dict | None:
    """
    Выполняет LDAP bind и возвращает информацию о пользователе.
    Возвращает dict {display_name, groups} при успехе, None при ошибке.
    """
    if not _LDAP3_OK:
        raise HTTPException(500, "Библиотека ldap3 не установлена")

    db = SessionLocal()
    try:
        auth_domain = get_setting(db, "ldap.auth_domain", domain)
        server_addr = get_setting(db, f"ldap.{auth_domain}.server")
        search_base = get_setting(db, f"ldap.{auth_domain}.search_base")
        use_ssl = get_setting(db, "ldap.use_ssl", "false").lower() in ("true", "1")
        ldap_user_fmt = get_setting(db, "ldap.bind_user_format", "{username}")
    finally:
        db.close()

    if not server_addr:
        raise HTTPException(503, f"LDAP-сервер для домена {auth_domain} не настроен")

    bind_dn = ldap_user_fmt.replace("{username}", username)
    port = 636 if use_ssl else 389

    try:
        server = Server(server_addr, port=port, use_ssl=use_ssl, get_info=LDAP_ALL)
        conn = Connection(server, user=bind_dn, password=password, auto_bind=True)
    except Exception as e:
        logger.warning("LDAP bind failed for %s@%s: %s", username, auth_domain, e)
        return None

    display_name = username
    try:
        conn.search(
            search_base=search_base,
            search_filter=f"(&(objectClass=user)(sAMAccountName={username}))",
            attributes=["displayName", "memberOf"],
        )
        if conn.entries:
            entry = conn.entries[0]
            dn = getattr(entry, "displayName", None)
            if dn and dn.value:
                display_name = str(dn.value)
    except Exception:
        pass
    finally:
        try:
            conn.unbind()
        except Exception:
            pass

    return {"display_name": display_name}


# ── JWT ────────────────────────────────────────────────────

def _jwt_secret() -> str:
    db = SessionLocal()
    try:
        return get_setting(db, "jwt.secret", "fallback-insecure-key")
    finally:
        db.close()


def _jwt_expire_hours() -> int:
    db = SessionLocal()
    try:
        val = get_setting(db, "jwt.expire_hours", "12")
        return int(val) if val.isdigit() else 12
    finally:
        db.close()


def create_jwt(username: str, display_name: str, role: str, domain: str = "") -> str:
    secret = _jwt_secret()
    expire = datetime.now(timezone.utc) + timedelta(hours=_jwt_expire_hours())
    payload = {
        "sub": username,
        "name": display_name,
        "role": role,
        "domain": domain,
        "exp": expire,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_jwt(token: str) -> dict | None:
    secret = _jwt_secret()
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ── FastAPI dependencies ───────────────────────────────────

async def get_current_user_optional(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> dict | None:
    """Возвращает текущего пользователя или None (для маршрутов без обязательной авторизации)."""
    if not is_auth_configured(db):
        return {"username": "__setup__", "name": "Setup", "role": "admin", "domain": ""}
    if not creds:
        return None
    data = verify_jwt(creds.credentials)
    if not data:
        return None
    user = db.query(AppUser).filter_by(username=data["sub"], is_active=True).first()
    if not user:
        return None
    return {"username": user.username, "name": user.display_name, "role": user.role, "domain": user.domain}


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> dict:
    """Возвращает текущего пользователя или 401."""
    if not is_auth_configured(db):
        return {"username": "__setup__", "name": "Setup", "role": "admin", "domain": ""}
    if not creds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Требуется авторизация")
    data = verify_jwt(creds.credentials)
    if not data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Токен недействителен")
    user = db.query(AppUser).filter_by(username=data["sub"], is_active=True).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Пользователь не найден или заблокирован")
    return {"username": user.username, "name": user.display_name, "role": user.role, "domain": user.domain}


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Проверяет role == admin, иначе 403."""
    if user.get("role") != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Требуются права администратора")
    return user

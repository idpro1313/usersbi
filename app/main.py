# -*- coding: utf-8 -*-
import base64
import io
import logging
import secrets
from contextlib import asynccontextmanager
from typing import Dict, Any

import pandas as pd
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Body
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response as StarletteResponse
from pathlib import Path

from app.database import init_db, get_db, Upload, ADRecord, MFARecord, PeopleRecord
from app.parsers import parse_ad, parse_mfa, parse_people, get_last_parse_info
from app.consolidation import build_consolidated
from app.ldap_sync import sync_domain as ldap_sync_domain, is_available as ldap_is_available
from app.config import AD_DOMAINS, AD_DOMAIN_DN, MAX_UPLOAD_SIZE, AUTH_USERNAME, AUTH_PASSWORD
from app.groups import router as groups_router
from app.structure import router as structure_router
from app.users import router as users_router
from app.duplicates import router as duplicates_router
from app.org import router as org_router
from app.security import router as security_router

logger = logging.getLogger(__name__)


# ─── Хелперы ────────────────────────────────────────────────

STATIC_DIR = Path(__file__).resolve().parent / "static"


async def _read_upload(file: UploadFile) -> bytes:
    """Читает загруженный файл с проверкой размера."""
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        size_mb = len(content) / (1024 * 1024)
        limit_mb = MAX_UPLOAD_SIZE / (1024 * 1024)
        raise HTTPException(
            413,
            f"Файл слишком большой ({size_mb:.1f} МБ). Максимум: {limit_mb:.0f} МБ",
        )
    return content


# ─── Basic Auth (опциональная) ───────────────────────────────

class _BasicAuthMiddleware(BaseHTTPMiddleware):
    """HTTP Basic Auth. Активна только при заданных AUTH_USERNAME и AUTH_PASSWORD."""

    async def dispatch(self, request: Request, call_next):
        if not AUTH_USERNAME or not AUTH_PASSWORD:
            return await call_next(request)
        # Пропускаем healthcheck для Docker
        if request.url.path == "/api/stats":
            return await call_next(request)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
                username, password = decoded.split(":", 1)
                if (secrets.compare_digest(username, AUTH_USERNAME)
                        and secrets.compare_digest(password, AUTH_PASSWORD)):
                    return await call_next(request)
            except Exception:
                pass
        return StarletteResponse(
            content="Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="UsersBI"'},
        )


# ─── Приложение ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Девелоника Пользователи", lifespan=lifespan)
app.add_middleware(_BasicAuthMiddleware)
app.include_router(groups_router)
app.include_router(structure_router)
app.include_router(users_router)
app.include_router(duplicates_router)
app.include_router(org_router)
app.include_router(security_router)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ─── Favicon ─────────────────────────────────────────────────

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    ico = STATIC_DIR / "favicon.ico"
    if ico.exists():
        return FileResponse(str(ico), media_type="image/x-icon")
    return HTMLResponse("", status_code=204)


# ─── Загрузка файлов ────────────────────────────────────────

@app.post("/api/upload/ad/{domain_key}")
async def upload_ad(domain_key: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if domain_key not in AD_DOMAINS:
        raise HTTPException(400, f"Неизвестный домен: {domain_key}")
    city_name = AD_DOMAINS[domain_key]
    if not file.filename:
        raise HTTPException(400, "Нет имени файла")
    content = await _read_upload(file)
    dn_suffix = AD_DOMAIN_DN.get(domain_key, "")
    rows, err, skipped = parse_ad(content, file.filename, override_domain=city_name, expected_dn_suffix=dn_suffix)
    if err:
        raise HTTPException(400, f"Ошибка разбора файла: {err}")
    if not rows and skipped > 0:
        raise HTTPException(400, f"В файле нет записей для домена {city_name} (отфильтровано {skipped} записей других доменов)")

    # Удаляем только записи этого домена
    try:
        db.query(ADRecord).filter(ADRecord.ad_source == domain_key).delete()
        db.query(Upload).filter(Upload.source == f"ad_{domain_key}").delete()
        upload = Upload(source=f"ad_{domain_key}", filename=file.filename, row_count=len(rows))
        db.add(upload)
        db.flush()
        for r in rows:
            r["upload_id"] = upload.id
            r["ad_source"] = domain_key
        db.bulk_insert_mappings(ADRecord, rows)
        db.commit()
    except Exception:
        db.rollback()
        raise

    result = {"ok": True, "rows": len(rows), "filename": file.filename, "domain": city_name}
    if skipped > 0:
        result["skipped"] = skipped
        result["message"] = f"Загружено {len(rows)} записей {city_name}, пропущено {skipped} записей других доменов"
    return result


@app.post("/api/upload/mfa")
async def upload_mfa(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(400, "Нет имени файла")
    content = await _read_upload(file)
    rows, err = parse_mfa(content, file.filename)
    if err:
        raise HTTPException(400, f"Ошибка разбора файла: {err}")
    try:
        db.query(MFARecord).delete()
        db.query(Upload).filter(Upload.source == "mfa").delete()
        upload = Upload(source="mfa", filename=file.filename, row_count=len(rows))
        db.add(upload)
        db.flush()
        for r in rows:
            r["upload_id"] = upload.id
        db.bulk_insert_mappings(MFARecord, rows)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"ok": True, "rows": len(rows), "filename": file.filename}


@app.post("/api/upload/people")
async def upload_people(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(400, "Нет имени файла")
    content = await _read_upload(file)
    rows, err = parse_people(content, file.filename)
    if err:
        raise HTTPException(400, f"Ошибка разбора файла: {err}")
    try:
        db.query(PeopleRecord).delete()
        db.query(Upload).filter(Upload.source == "people").delete()
        upload = Upload(source="people", filename=file.filename, row_count=len(rows))
        db.add(upload)
        db.flush()
        for r in rows:
            r["upload_id"] = upload.id
        db.bulk_insert_mappings(PeopleRecord, rows)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"ok": True, "rows": len(rows), "filename": file.filename}


# ─── Синхронизация из AD по LDAP ─────────────────────────────

@app.get("/api/sync/status")
async def sync_status():
    """Проверяет доступность LDAP-синхронизации."""
    return ldap_is_available()


@app.post("/api/sync/ad/{domain_key}")
async def sync_ad_domain(domain_key: str, db: Session = Depends(get_db)):
    """Синхронизирует один домен AD по LDAP."""
    if domain_key not in AD_DOMAINS:
        raise HTTPException(400, f"Неизвестный домен: {domain_key}")
    city_name = AD_DOMAINS[domain_key]

    rows, err = ldap_sync_domain(domain_key)
    if err:
        raise HTTPException(400, f"Ошибка синхронизации {city_name}: {err}")
    if not rows:
        raise HTTPException(400, f"Нет записей для домена {city_name}")

    try:
        db.query(ADRecord).filter(ADRecord.ad_source == domain_key).delete()
        db.query(Upload).filter(Upload.source == f"ad_{domain_key}").delete()
        upload = Upload(source=f"ad_{domain_key}", filename="LDAP sync", row_count=len(rows))
        db.add(upload)
        db.flush()
        for r in rows:
            r["upload_id"] = upload.id
            r["ad_source"] = domain_key
        db.bulk_insert_mappings(ADRecord, rows)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {"ok": True, "rows": len(rows), "domain": city_name, "source": "ldap"}


@app.post("/api/sync/ad")
async def sync_ad_all(db: Session = Depends(get_db)):
    """Синхронизирует все настроенные домены AD по LDAP."""
    results = {}
    errors = []
    for domain_key, city_name in AD_DOMAINS.items():
        cfg = (ldap_is_available()).get("domains", {}).get(domain_key, {})
        if not cfg.get("configured"):
            results[domain_key] = {"city": city_name, "skipped": True, "reason": "Сервер не настроен"}
            continue

        rows, err = ldap_sync_domain(domain_key)
        if err:
            results[domain_key] = {"city": city_name, "error": err}
            errors.append(f"{city_name}: {err}")
            continue

        db.query(ADRecord).filter(ADRecord.ad_source == domain_key).delete()
        db.query(Upload).filter(Upload.source == f"ad_{domain_key}").delete()
        upload = Upload(source=f"ad_{domain_key}", filename="LDAP sync", row_count=len(rows))
        db.add(upload)
        db.flush()
        for r in rows:
            r["upload_id"] = upload.id
            r["ad_source"] = domain_key
        db.bulk_insert_mappings(ADRecord, rows)

        results[domain_key] = {"city": city_name, "rows": len(rows)}

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"ok": not errors, "domains": results, "errors": errors}


# ─── Сводная ────────────────────────────────────────────────

@app.get("/api/consolidated")
async def get_consolidated(db: Session = Depends(get_db)):
    rows = build_consolidated(db)
    return {"rows": rows, "total": len(rows)}


# ─── Статистика ─────────────────────────────────────────────

@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    mfa = db.query(MFARecord).count()
    people = db.query(PeopleRecord).count()
    last_mfa = db.query(Upload).filter(Upload.source == "mfa").order_by(Upload.uploaded_at.desc()).first()
    last_people = db.query(Upload).filter(Upload.source == "people").order_by(Upload.uploaded_at.desc()).first()

    ad_info = {}
    ad_total = 0
    for key, city in AD_DOMAINS.items():
        cnt = db.query(ADRecord).filter(ADRecord.ad_source == key).count()
        ad_total += cnt
        last = db.query(Upload).filter(Upload.source == f"ad_{key}").order_by(Upload.uploaded_at.desc()).first()
        ad_info[key] = {
            "city": city, "rows": cnt,
            "last": {"filename": last.filename, "at": last.uploaded_at.isoformat(), "rows": last.row_count} if last else None,
        }

    return {
        "ad_total": ad_total, "ad_domains": ad_info,
        "mfa_rows": mfa, "people_rows": people,
        "last_upload": {
            "mfa": {"filename": last_mfa.filename, "at": last_mfa.uploaded_at.isoformat(), "rows": last_mfa.row_count} if last_mfa else None,
            "people": {"filename": last_people.filename, "at": last_people.uploaded_at.isoformat(), "rows": last_people.row_count} if last_people else None,
        },
    }


# ─── Очистка БД ─────────────────────────────────────────────

@app.delete("/api/clear/all")
async def clear_all(db: Session = Depends(get_db)):
    ad = db.query(ADRecord).count()
    mfa = db.query(MFARecord).count()
    people = db.query(PeopleRecord).count()
    try:
        db.query(ADRecord).delete()
        db.query(MFARecord).delete()
        db.query(PeopleRecord).delete()
        db.query(Upload).delete()
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"ok": True, "deleted": {"ad": ad, "mfa": mfa, "people": people}}


@app.delete("/api/clear/ad/{domain_key}")
async def clear_ad(domain_key: str, db: Session = Depends(get_db)):
    if domain_key not in AD_DOMAINS:
        raise HTTPException(400, f"Неизвестный домен: {domain_key}")
    count = db.query(ADRecord).filter(ADRecord.ad_source == domain_key).count()
    db.query(ADRecord).filter(ADRecord.ad_source == domain_key).delete()
    db.query(Upload).filter(Upload.source == f"ad_{domain_key}").delete()
    db.commit()
    return {"ok": True, "deleted": count, "domain": AD_DOMAINS[domain_key]}


@app.delete("/api/clear/mfa")
async def clear_mfa(db: Session = Depends(get_db)):
    count = db.query(MFARecord).count()
    db.query(MFARecord).delete()
    db.query(Upload).filter(Upload.source == "mfa").delete()
    db.commit()
    return {"ok": True, "deleted": count}


@app.delete("/api/clear/people")
async def clear_people(db: Session = Depends(get_db)):
    count = db.query(PeopleRecord).count()
    db.query(PeopleRecord).delete()
    db.query(Upload).filter(Upload.source == "people").delete()
    db.commit()
    return {"ok": True, "deleted": count}


# ─── Экспорт ────────────────────────────────────────────────

@app.get("/api/export/xlsx")
async def export_xlsx(db: Session = Depends(get_db)):
    """Выгружает сводную таблицу в Excel (все данные)."""
    rows = build_consolidated(db)
    if not rows:
        raise HTTPException(400, "Нет данных для выгрузки")

    col_map = {
        "source": "Источник", "account_type": "Тип УЗ",
        "login": "Логин", "domain": "Домен",
        "uz_active": "УЗ активна", "password_last_set": "Смена пароля",
        "must_change_password": "Треб. смена пароля",
        "account_expires": "Срок УЗ", "staff_uuid": "StaffUUID",
        "mfa_enabled": "Есть MFA", "mfa_created_at": "MFA подключен",
        "mfa_last_login": "Последний вход MFA", "mfa_authenticators": "Способ MFA",
        "fio_ad": "ФИО (AD)", "fio_mfa": "ФИО (MFA)", "fio_people": "ФИО (Кадры)",
        "email_ad": "Email (AD)", "email_mfa": "Email (MFA)", "email_people": "Email (Кадры)",
        "phone_ad": "Телефон (AD)", "mobile_ad": "Мобильный (AD)",
        "phone_mfa": "Телефон (MFA)", "phone_people": "Телефон (Кадры)",
        "discrepancies": "Расхождения",
    }

    df = pd.DataFrame(rows).rename(columns=col_map)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="Сводная", index=False)
        if "Расхождения" in df.columns:
            diff = df[df["Расхождения"].astype(str).str.len() > 0]
            if not diff.empty:
                diff.to_excel(w, sheet_name="Расхождения", index=False)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Svodka_AD_MFA_People.xlsx"},
    )


@app.post("/api/export/table")
async def export_table(payload: Dict[str, Any] = Body(...)):
    """Универсальная выгрузка таблицы в XLSX."""
    columns = payload.get("columns", [])
    rows = payload.get("rows", [])
    filename = payload.get("filename", "export.xlsx")
    sheet = payload.get("sheet", "Данные")

    if not rows:
        raise HTTPException(400, "Нет данных для выгрузки")

    col_keys = [c["key"] for c in columns]
    col_labels = {c["key"]: c["label"] for c in columns}

    data = [{col_labels.get(k, k): row.get(k, "") for k in col_keys} for row in rows]
    df = pd.DataFrame(data)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, sheet_name=sheet[:31], index=False)
    buf.seek(0)

    safe_filename = filename.replace('"', "'")
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
    )


# ─── Диагностика ────────────────────────────────────────────

@app.get("/api/debug/columns")
async def debug_columns():
    return get_last_parse_info()


# ─── SPA catch-all ────────────────────────────────────────────

@app.get("/{path:path}", response_class=HTMLResponse)
async def spa_catchall(path: str):
    """Отдаёт Vue SPA index.html для всех не-API маршрутов."""
    dist_index = STATIC_DIR / "dist" / "index.html"
    if dist_index.exists():
        return dist_index.read_text(encoding="utf-8")
    return HTMLResponse("Frontend not built. Run: cd frontend && npm run build", status_code=404)

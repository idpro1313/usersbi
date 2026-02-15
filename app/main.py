# -*- coding: utf-8 -*-
import io
import tempfile
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pathlib import Path

from app.database import init_db, get_db, Upload, ADRecord, MFARecord, PeopleRecord
from app.parsers import parse_ad, parse_mfa, parse_people, get_last_parse_info
from app.consolidation import build_consolidated
from app.config import AD_DOMAINS, AD_DOMAIN_DN
from app.groups import router as groups_router
from app.structure import router as structure_router
from app.users import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Сводная AD / MFA / Кадры", lifespan=lifespan)
app.include_router(groups_router)
app.include_router(structure_router)
app.include_router(users_router)

STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    return html


@app.get("/upload", response_class=HTMLResponse)
async def upload_page():
    html = (STATIC_DIR / "upload.html").read_text(encoding="utf-8")
    return html


@app.get("/groups", response_class=HTMLResponse)
async def groups_page():
    html = (STATIC_DIR / "groups.html").read_text(encoding="utf-8")
    return html


@app.get("/structure", response_class=HTMLResponse)
async def structure_page():
    html = (STATIC_DIR / "structure.html").read_text(encoding="utf-8")
    return html


@app.get("/users", response_class=HTMLResponse)
async def users_page():
    html = (STATIC_DIR / "users.html").read_text(encoding="utf-8")
    return html


@app.post("/api/upload/ad/{domain_key}")
async def upload_ad(domain_key: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if domain_key not in AD_DOMAINS:
        raise HTTPException(400, f"Неизвестный домен: {domain_key}")
    city_name = AD_DOMAINS[domain_key]
    if not file.filename:
        raise HTTPException(400, "Нет имени файла")
    content = await file.read()
    dn_suffix = AD_DOMAIN_DN.get(domain_key, "")
    rows, err, skipped = parse_ad(content, file.filename, override_domain=city_name, expected_dn_suffix=dn_suffix)
    if err:
        raise HTTPException(400, f"Ошибка разбора файла: {err}")
    if not rows and skipped > 0:
        raise HTTPException(400, f"В файле нет записей для домена {city_name} (отфильтровано {skipped} записей других доменов)")
    # Удаляем только записи этого домена
    db.query(ADRecord).filter(ADRecord.ad_source == domain_key).delete()
    db.query(Upload).filter(Upload.source == f"ad_{domain_key}").delete()
    upload = Upload(source=f"ad_{domain_key}", filename=file.filename, row_count=len(rows))
    db.add(upload)
    db.flush()
    for r in rows:
        rec = ADRecord(upload_id=upload.id, ad_source=domain_key, **r)
        db.add(rec)
    db.commit()
    result = {"ok": True, "rows": len(rows), "filename": file.filename, "domain": city_name}
    if skipped > 0:
        result["skipped"] = skipped
        result["message"] = f"Загружено {len(rows)} записей {city_name}, пропущено {skipped} записей других доменов"
    return result


@app.post("/api/upload/mfa")
async def upload_mfa(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(400, "Нет имени файла")
    content = await file.read()
    rows, err = parse_mfa(content, file.filename)
    if err:
        raise HTTPException(400, f"Ошибка разбора файла: {err}")
    db.query(MFARecord).delete()
    upload = Upload(source="mfa", filename=file.filename, row_count=len(rows))
    db.add(upload)
    db.flush()
    for r in rows:
        rec = MFARecord(upload_id=upload.id, **r)
        db.add(rec)
    db.commit()
    return {"ok": True, "rows": len(rows), "filename": file.filename}


@app.post("/api/upload/people")
async def upload_people(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(400, "Нет имени файла")
    content = await file.read()
    rows, err = parse_people(content, file.filename)
    if err:
        raise HTTPException(400, f"Ошибка разбора файла: {err}")
    db.query(PeopleRecord).delete()
    upload = Upload(source="people", filename=file.filename, row_count=len(rows))
    db.add(upload)
    db.flush()
    for r in rows:
        rec = PeopleRecord(upload_id=upload.id, **r)
        db.add(rec)
    db.commit()
    return {"ok": True, "rows": len(rows), "filename": file.filename}


@app.get("/api/consolidated")
async def get_consolidated(db: Session = Depends(get_db)):
    rows = build_consolidated(db)
    return {"rows": rows, "total": len(rows)}


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
            "city": city,
            "rows": cnt,
            "last": {"filename": last.filename, "at": last.uploaded_at.isoformat(), "rows": last.row_count} if last else None,
        }

    return {
        "ad_total": ad_total,
        "ad_domains": ad_info,
        "mfa_rows": mfa,
        "people_rows": people,
        "last_upload": {
            "mfa": {"filename": last_mfa.filename, "at": last_mfa.uploaded_at.isoformat(), "rows": last_mfa.row_count} if last_mfa else None,
            "people": {"filename": last_people.filename, "at": last_people.uploaded_at.isoformat(), "rows": last_people.row_count} if last_people else None,
        },
    }


@app.delete("/api/clear/all")
async def clear_all(db: Session = Depends(get_db)):
    ad = db.query(ADRecord).count()
    mfa = db.query(MFARecord).count()
    people = db.query(PeopleRecord).count()
    db.query(ADRecord).delete()
    db.query(MFARecord).delete()
    db.query(PeopleRecord).delete()
    db.query(Upload).delete()
    db.commit()
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


@app.get("/api/export/xlsx")
async def export_xlsx(db: Session = Depends(get_db)):
    """Выгружает сводную таблицу в файл Excel (без фильтров, все данные)."""
    import pandas as pd

    rows = build_consolidated(db)
    if not rows:
        raise HTTPException(400, "Нет данных для выгрузки")

    col_map = {
        "source": "Источник",
        "login": "Логин",
        "domain": "Домен",
        "uz_active": "УЗ активна",
        "password_last_set": "Смена пароля",
        "account_expires": "Срок УЗ",
        "staff_uuid": "StaffUUID",
        "mfa_enabled": "Есть MFA",
        "mfa_created_at": "MFA подключен",
        "mfa_last_login": "Последний вход MFA",
        "mfa_authenticators": "Способ MFA",
        "fio_ad": "ФИО (AD)",
        "fio_mfa": "ФИО (MFA)",
        "fio_people": "ФИО (Кадры)",
        "email_ad": "Email (AD)",
        "email_mfa": "Email (MFA)",
        "email_people": "Email (Кадры)",
        "phone_ad": "Телефон (AD)",
        "mobile_ad": "Мобильный (AD)",
        "phone_mfa": "Телефон (MFA)",
        "phone_people": "Телефон (Кадры)",
        "discrepancies": "Расхождения",
    }

    df = pd.DataFrame(rows)
    df = df.rename(columns=col_map)

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


from fastapi import Body
from typing import List, Dict, Any


@app.post("/api/export/table")
async def export_table(
    payload: Dict[str, Any] = Body(...),
):
    """
    Универсальная выгрузка таблицы в XLSX.
    Body JSON: { "columns": [{"key":"...", "label":"..."}], "rows": [...], "filename": "...", "sheet": "..." }
    """
    import pandas as pd

    columns = payload.get("columns", [])
    rows = payload.get("rows", [])
    filename = payload.get("filename", "export.xlsx")
    sheet = payload.get("sheet", "Данные")

    if not rows:
        raise HTTPException(400, "Нет данных для выгрузки")

    col_keys = [c["key"] for c in columns]
    col_labels = {c["key"]: c["label"] for c in columns}

    data = []
    for row in rows:
        data.append({col_labels.get(k, k): row.get(k, "") for k in col_keys})

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


@app.get("/api/debug/columns")
async def debug_columns():
    """Показывает колонки, прочитанные при последней загрузке каждого файла."""
    return get_last_parse_info()

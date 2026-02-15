# -*- coding: utf-8 -*-
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pathlib import Path

from app.database import init_db, get_db, Upload, ADRecord, MFARecord, PeopleRecord
from app.parsers import parse_ad, parse_mfa, parse_people
from app.consolidation import build_consolidated


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Сводная AD / MFA / Кадры", lifespan=lifespan)

STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    return html


@app.post("/api/upload/ad")
async def upload_ad(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(400, "Нет имени файла")
    content = await file.read()
    rows, err = parse_ad(content, file.filename)
    if err:
        raise HTTPException(400, f"Ошибка разбора файла: {err}")
    db.query(ADRecord).delete()
    upload = Upload(source="ad", filename=file.filename, row_count=len(rows))
    db.add(upload)
    db.flush()
    for r in rows:
        rec = ADRecord(upload_id=upload.id, **r)
        db.add(rec)
    db.commit()
    return {"ok": True, "rows": len(rows), "filename": file.filename}


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
    ad = db.query(ADRecord).count()
    mfa = db.query(MFARecord).count()
    people = db.query(PeopleRecord).count()
    last_ad = db.query(Upload).filter(Upload.source == "ad").order_by(Upload.uploaded_at.desc()).first()
    last_mfa = db.query(Upload).filter(Upload.source == "mfa").order_by(Upload.uploaded_at.desc()).first()
    last_people = db.query(Upload).filter(Upload.source == "people").order_by(Upload.uploaded_at.desc()).first()
    return {
        "ad_rows": ad,
        "mfa_rows": mfa,
        "people_rows": people,
        "last_upload": {
            "ad": {"filename": last_ad.filename, "at": last_ad.uploaded_at.isoformat(), "rows": last_ad.row_count} if last_ad else None,
            "mfa": {"filename": last_mfa.filename, "at": last_mfa.uploaded_at.isoformat(), "rows": last_mfa.row_count} if last_mfa else None,
            "people": {"filename": last_people.filename, "at": last_people.uploaded_at.isoformat(), "rows": last_people.row_count} if last_people else None,
        },
    }

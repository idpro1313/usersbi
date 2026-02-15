# -*- coding: utf-8 -*-
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, text, inspect as sa_inspect
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Upload(Base):
    __tablename__ = "uploads"
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(20), nullable=False)  # ad, mfa, people
    filename = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    row_count = Column(Integer, default=0)


class ADRecord(Base):
    __tablename__ = "ad_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    upload_id = Column(Integer, nullable=True)
    ad_source = Column(String(50), default="", index=True)   # izhevsk / kostroma / moscow
    domain = Column(String(255), default="")
    login = Column(String(255), default="", index=True)
    enabled = Column(String(20), default="")
    password_last_set = Column(String(50), default="")
    account_expires = Column(String(50), default="")
    email = Column(String(255), default="")
    phone = Column(String(100), default="")
    mobile = Column(String(100), default="")
    display_name = Column(String(255), default="")
    staff_uuid = Column(String(100), default="", index=True)


class MFARecord(Base):
    __tablename__ = "mfa_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    upload_id = Column(Integer, nullable=True)
    identity = Column(String(255), default="", index=True)
    email = Column(String(255), default="")
    name = Column(String(255), default="")
    phones = Column(String(255), default="")
    last_login = Column(String(50), default="")
    created_at = Column(String(50), default="")
    status = Column(String(50), default="")
    is_enrolled = Column(String(20), default="")
    authenticators = Column(String(255), default="")


class PeopleRecord(Base):
    __tablename__ = "people_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    upload_id = Column(Integer, nullable=True)
    staff_uuid = Column(String(100), default="", index=True)
    fio = Column(String(255), default="")
    email = Column(String(255), default="")
    phone = Column(String(100), default="")


def init_db():
    Base.metadata.create_all(bind=engine)
    # Миграция: добавить ad_source, если колонки ещё нет
    insp = sa_inspect(engine)
    cols = [c["name"] for c in insp.get_columns("ad_records")]
    if "ad_source" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE ad_records ADD COLUMN ad_source VARCHAR(50) DEFAULT ''"))
    if "mobile" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE ad_records ADD COLUMN mobile VARCHAR(100) DEFAULT ''"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

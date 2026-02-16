# -*- coding: utf-8 -*-
import re
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, text, inspect as sa_inspect
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import DATABASE_URL

_SAFE_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Upload(Base):
    __tablename__ = "uploads"
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(20), nullable=False)  # ad, mfa, people
    filename = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    row_count = Column(Integer, default=0)


class ADRecord(Base):
    __tablename__ = "ad_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    upload_id = Column(Integer, nullable=True)
    ad_source = Column(String(50), default="", index=True)   # izhevsk / kostroma / moscow
    # --- основные поля ---
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
    # --- дополнительные основные ---
    given_name = Column(String(255), default="")
    surname_ad = Column(String(255), default="")
    upn = Column(String(255), default="")
    title = Column(String(255), default="")
    manager = Column(Text, default="")
    distinguished_name = Column(Text, default="")
    company = Column(String(255), default="")
    department = Column(String(255), default="")
    description = Column(Text, default="")
    employee_type = Column(String(100), default="")
    location = Column(String(255), default="")
    street_address = Column(String(500), default="")
    employee_number = Column(String(100), default="")
    info = Column(Text, default="")
    must_change_password = Column(String(20), default="")
    groups = Column(Text, default="")
    # --- пароль и сроки ---
    pwd_last_set = Column(String(50), default="")
    password_expired = Column(String(20), default="")
    password_never_expires = Column(String(20), default="")
    password_not_required = Column(String(20), default="")
    cannot_change_password = Column(String(20), default="")
    account_expiration_date = Column(String(50), default="")
    # --- аудит активности ---
    last_logon_date = Column(String(50), default="")
    last_logon_timestamp = Column(String(50), default="")
    logon_count = Column(String(20), default="")
    last_bad_password_attempt = Column(String(50), default="")
    bad_logon_count = Column(String(20), default="")
    locked_out = Column(String(20), default="")
    # --- жизненный цикл ---
    created_date = Column(String(50), default="")
    modified_date = Column(String(50), default="")
    when_created = Column(String(50), default="")
    when_changed = Column(String(50), default="")
    exported_at = Column(String(50), default="")
    # --- безопасность ---
    trusted_for_delegation = Column(String(20), default="")
    trusted_to_auth_for_delegation = Column(String(20), default="")
    account_not_delegated = Column(String(20), default="")
    does_not_require_preauth = Column(String(20), default="")
    allow_reversible_password_encryption = Column(String(20), default="")
    smartcard_logon_required = Column(String(20), default="")
    protected_from_accidental_deletion = Column(String(20), default="")
    user_account_control = Column(String(20), default="")
    service_principal_names = Column(Text, default="")
    account_lockout_time = Column(String(50), default="")
    # --- идентификаторы ---
    object_guid = Column(String(100), default="")
    sid = Column(String(200), default="")
    canonical_name = Column(Text, default="")
    # --- профиль и ограничения ---
    logon_workstations = Column(Text, default="")
    home_drive = Column(String(20), default="")
    home_directory = Column(Text, default="")
    profile_path = Column(Text, default="")
    script_path = Column(Text, default="")
    # --- связи ---
    direct_reports = Column(Text, default="")
    managed_objects = Column(Text, default="")
    primary_group = Column(Text, default="")


class MFARecord(Base):
    __tablename__ = "mfa_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    upload_id = Column(Integer, nullable=True)
    # --- основные поля ---
    identity = Column(String(255), default="", index=True)
    email = Column(String(255), default="")
    name = Column(String(255), default="")
    phones = Column(String(255), default="")
    last_login = Column(String(50), default="")
    created_at = Column(String(50), default="")
    status = Column(String(50), default="")
    is_enrolled = Column(String(20), default="")
    authenticators = Column(String(255), default="")
    # --- дополнительные поля из файла MFA ---
    mfa_groups = Column(Text, default="")
    is_spammer = Column(String(20), default="")
    mfa_id = Column(String(100), default="")
    ldap = Column(Text, default="")


class PeopleRecord(Base):
    __tablename__ = "people_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    upload_id = Column(Integer, nullable=True)
    # --- основные поля ---
    staff_uuid = Column(String(100), default="", index=True)
    fio = Column(String(255), default="")
    email = Column(String(255), default="")
    phone = Column(String(100), default="")
    # --- дополнительные поля из файла People ---
    unit = Column(String(255), default="")
    hub = Column(String(255), default="")
    employment_status = Column(String(100), default="")
    unit_manager = Column(String(255), default="")
    work_format = Column(String(100), default="")
    hr_bp = Column(String(255), default="")


def _migrate_table(insp, table_name, model_class):
    """Добавляет недостающие колонки в таблицу на основе модели."""
    if not _SAFE_IDENTIFIER.match(table_name):
        raise ValueError(f"Недопустимое имя таблицы: {table_name}")
    existing = {c["name"] for c in insp.get_columns(table_name)}
    for col in model_class.__table__.columns:
        if col.name not in existing:
            if not _SAFE_IDENTIFIER.match(col.name):
                raise ValueError(f"Недопустимое имя колонки: {col.name}")
            col_type = "TEXT"
            if isinstance(col.type, String):
                length = getattr(col.type, "length", None)
                col_type = f"VARCHAR({length})" if length else "TEXT"
            elif isinstance(col.type, Integer):
                col_type = "INTEGER"
            default = "''" if col_type != "INTEGER" else "0"
            with engine.begin() as conn:
                conn.execute(text(
                    f'ALTER TABLE "{table_name}" ADD COLUMN "{col.name}" {col_type} DEFAULT {default}'
                ))


def init_db():
    if "sqlite" in DATABASE_URL:
        with engine.begin() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
    Base.metadata.create_all(bind=engine)
    insp = sa_inspect(engine)
    _migrate_table(insp, "ad_records", ADRecord)
    _migrate_table(insp, "mfa_records", MFARecord)
    _migrate_table(insp, "people_records", PeopleRecord)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

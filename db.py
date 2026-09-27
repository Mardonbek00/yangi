from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

import config

_url = config.DATABASE_URL
# Render Postgres ba'zan "postgres://" beradi, SQLAlchemy "postgresql://" talab qiladi
if _url.startswith("postgres://"):
    _url = _url.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if _url.startswith("sqlite") else {}

engine = create_engine(_url, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()


def get_session():
    return SessionLocal()

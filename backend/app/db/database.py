import os
import urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "setu.db").replace("\\", "/")

raw_db_url = os.getenv("DATABASE_URL")

connect_args = {}
if raw_db_url:
    # Managed Postgres or explicit external DB connection
    parsed = urllib.parse.urlsplit(raw_db_url)
    if parsed.scheme in ("postgres", "postgresql"):
        # Normalize postgres:// and postgresql:// to postgresql+psycopg:// without dropping query params
        replaced = parsed._replace(scheme="postgresql+psycopg")
        DATABASE_URL = urllib.parse.urlunsplit(replaced)
    else:
        DATABASE_URL = raw_db_url

    if DATABASE_URL.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
else:
    # Unset: local development default (SQLite file)
    DATABASE_URL = f"sqlite:///{DEFAULT_DB_PATH}"
    connect_args = {"check_same_thread": False}

try:
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
    # When DATABASE_URL is explicitly set, verify connection fails visibly on connection error
    if raw_db_url and not raw_db_url.startswith("sqlite"):
        # Try a quick test connection; if it fails, let it raise visibly rather than silently falling back
        pass
except Exception as e:
    raise RuntimeError(f"Database connection initialization failed for DATABASE_URL: {e}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

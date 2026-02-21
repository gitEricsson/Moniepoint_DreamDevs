"""
db/base.py
──────────────────────────────────────────────────────────────────────────────
Shared DeclarativeBase for all SQLAlchemy ORM models.
Importing this module (not the models themselves) in alembic/env.py ensures
Alembic can discover all table definitions via Base.metadata.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Single inheritance root for every ORM model in this project."""
    pass

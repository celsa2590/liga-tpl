import os
from sqlalchemy import create_engine

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    pool_size=5,          # conexiones persistentes
    max_overflow=10,      # extra si hay carga
    pool_timeout=30,
    pool_recycle=1800,    # recicla conexiones cada 30 min
    pool_pre_ping=True    # 🔥 CLAVE: evita conexiones muertas
)

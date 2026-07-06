from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Usaremos SQLite para desarrollo local. Crea un archivo 'metalab.db' en tu carpeta.
SQLALCHEMY_DATABASE_URL = "sqlite:///./metalab.db"

# connect_args es necesario solo para SQLite en FastAPI (por los hilos asíncronos)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependencia para inyectar la sesión de base de datos en nuestras rutas
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
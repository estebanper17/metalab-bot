from sqlalchemy import Column, String, JSON, Integer, DateTime
from database import Base

class ClienteEstado(Base):
    __tablename__ = "estados_clientes"
    telefono = Column(String, primary_key=True, index=True)
    estado_actual = Column(String, default="INICIO")
    datos_temporales = Column(JSON, default={})

# =========================================================================
# NUEVA TABLA: SISTEMA DE RESERVAS Y BLOQUEOS
# =========================================================================
class CitaTutoria(Base):
    __tablename__ = "citas_tutorias"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    telefono_cliente = Column(String, index=True) # Para saber de quién es la clase
    nombre_alumno = Column(String, nullable=True) # Manual o recogido por el bot
    materia = Column(String)
    nivel = Column(String)
    
    # El corazón del sistema temporal
    fecha_hora_inicio = Column(DateTime, index=True)
    
    # Para saber si la clase está activa, cancelada, o es un bloqueo manual tuyo
    estado = Column(String, default="CONFIRMADA")
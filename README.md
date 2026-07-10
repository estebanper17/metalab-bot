# Ecosistema Automatizado de Reservas e IA Conversacional - MetaLab Analytics

Este repositorio contiene la arquitectura de backend de un sistema inteligente de atención al cliente y gestión de reservas automatizadas a través de WhatsApp, integrado con modelos de lenguaje avanzados (LLM), persistencia de datos relacionales en la nube y un motor de tareas programadas inmortal frente a fallos o reinicios de infraestructura.

La solución está diseñada para optimizar los flujos de conversión de clientes, filtrando agendas en tiempo real según preferencias del usuario y asegurando alertas de preparación con precisión quirúrgica.

##  Arquitectura y Características Clave

* **Procesamiento de Intenciones con LLM:** Integración de la API de Gemini mediante inyección dinámica de contexto (historial conversacional de estados, fecha del sistema en tiempo real y slots disponibles). Clasificación sutil de intenciones en tres canales: `CONVERSAR`, `AGENDAR_TUTORIA` y `ATENCION_MANUAL`.
* **Motor de Calendario con Filtro UX Inteligente:** Algoritmo de extracción de disponibilidad en tiempo real que desacopla la visión del modelo (30 slots de análisis) de la visualización del cliente (10 slots filtrados dinámicamente por preferencia de mañana o tarde), mitigando la fricción y el ruido visual en interfaces móviles.
* **Persistencia Inmortal de Tareas (Job Store Relacional):** Configuración avanzada de `APScheduler` utilizando `SQLAlchemyJobStore` sobre PostgreSQL. Las alertas de seguimiento ya no residen en la memoria volátil (RAM); se escriben directamente en la base de datos de manera encriptada, garantizando resiliencia absoluta frente a reinicios de infraestructura (*Zero-Downtime Deployments*).
* **Alertas Duales y Sincronización Horaria:** Lógica de seguridad para agendas de emergencia y normalización horaria centralizada bajo estándares UTC / UTC-6. Automatización de flujos de salida duales: recordatorios estructurados al cliente final vía Twilio WhatsApp y alertas administrativas inmediatas vía API de Telegram (2 horas y 10 minutos antes de cada sesión).
* **Infraestructura de Alta Disponibilidad:** Implementación de rutas de verificación de estado (*keep-alive /ping*) y monitorización externa constante para prevenir la suspensión de contenedores en la nube, asegurando operatividad continua 24/7.

##  Stack Tecnológico

* **Core Backend:** FastAPI (Asynchronous Server Gateway Interface) & Uvicorn.
* **Inteligencia Artificial:** Gemini API (Modelos Generativos).
* **Persistencia de Datos:** Supabase (PostgreSQL Engine) & SQLAlchemy ORM.
* **Automatización de Tareas:** APScheduler (Advanced Python Scheduler).
* **Canales de Comunicación:** Twilio API (WhatsApp Business Gateway) & Telegram Bot API.

##  Configuración e Instalación Local

### Prerrequisitos
* Python 3.10 o superior instalado.
* Instancia de PostgreSQL activa (o proyecto en Supabase).
* Credenciales de desarrollo de Twilio y Telegram.

### Instalar Dependencias
1. Clona este repositorio:
   ```bash
   git clone [https://github.com/tu-usuario/metalab-bot-api.git](https://github.com/tu-usuario/metalab-bot-api.git)
   cd metalab-bot-api
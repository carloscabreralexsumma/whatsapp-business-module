"""
WhatsApp Business Module — Servidor independiente (white-label).

Este es el punto de entrada del módulo como producto independiente.
Cualquier negocio puede usarlo con su propio número de WhatsApp Business.

Uso:
    uvicorn main:app --host 0.0.0.0 --port 8000

Variables de entorno:
    WHATSAPP_PHONE_NUMBER_ID   - ID del número de WhatsApp Business (Meta)
    WHATSAPP_ACCESS_TOKEN      - Token de acceso de la Cloud API
    WHATSAPP_BUSINESS_ACCOUNT_ID - ID de la cuenta de WhatsApp Business
    WHATSAPP_WEBHOOK_VERIFY_TOKEN - Token para verificar el webhook
    WHATSAPP_ENABLED           - "true" para activar
    WHATSAPP_NOMBRE_NEGOCIO    - Nombre del negocio
    WHATSAPP_NOMBRE_REMITENTE  - Nombre que aparece como remitente
    WHATSAPP_FIRMA             - Firma al final de los mensajes
    ADMIN_PASSWORD             - Contraseña del portal de administración
    DATABASE_URL               - URL de PostgreSQL (opcional, por ahora en memoria)
    ENV                        - "development" o "production"
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from comunicaciones.whatsapp.adaptadores.insolvencia import registrar_plantillas
from comunicaciones.whatsapp.almacen import crear_almacen
from comunicaciones.whatsapp.auth_router import router as auth_router
from comunicaciones.whatsapp.config import CONFIG_DEFAULT
from comunicaciones.whatsapp.database import database_activada, init_db
from comunicaciones.whatsapp.servicio import ServicioWhatsApp
from comunicaciones.whatsapp.webhook import inicializar_servicio
from comunicaciones.whatsapp.webhook import router as whatsapp_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# ─── Configuración ───

ENV = os.getenv("ENV", "development")
DEBUG = ENV == "development"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa el módulo al arrancar."""
    # Crear tablas si hay DATABASE_URL
    db_ok = init_db()
    if db_ok:
        print("Base de datos PostgreSQL inicializada.")
    # Crear almacén (PostgreSQL o memoria)
    almacen = crear_almacen()
    servicio = ServicioWhatsApp(CONFIG_DEFAULT, almacen=almacen)
    try:
        registrar_plantillas(servicio)
    except Exception as e:  # noqa: BLE001
        import logging

        logging.getLogger(__name__).warning("No se pudieron registrar plantillas: %s", e)
    inicializar_servicio(servicio)
    print(f"WhatsApp Module iniciado. Tenant: {CONFIG_DEFAULT.tenant_id}, activado: {CONFIG_DEFAULT.activado()}, DB: {database_activada()}")
    yield
    print("WhatsApp Module detenido.")


app = FastAPI(
    title="WhatsApp Business Module",
    description="Módulo de comunicación por WhatsApp Business Cloud API. White-label, multi-tenant.",
    version="0.1.0",
    debug=DEBUG,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if DEBUG else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router de WhatsApp
app.include_router(whatsapp_router)
app.include_router(auth_router)

# Archivos estáticos del portal de administración
import os as _os

_admin_dir = _os.path.join(_os.path.dirname(__file__), "..", "frontend", "admin")
if _os.path.isdir(_admin_dir):
    app.mount("/admin", StaticFiles(directory=_admin_dir, html=True), name="admin")


@app.get("/", include_in_schema=False)
def root():
    """Redirige al portal de administración."""
    return FileResponse(
        _os.path.join(_admin_dir, "index.html"),
        media_type="text/html",
    )


@app.get("/health")
def health():
    return {"status": "ok", "env": ENV, "modulo": "whatsapp-business"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=DEBUG)

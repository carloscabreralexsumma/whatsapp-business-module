"""
Gestión de conexión a PostgreSQL para el módulo de WhatsApp.

Patrón: igual que insolvencia/config/database.py, pero simplificado.
Si DATABASE_URL no está configurada, el módulo usa almacenamiento en memoria.
"""
from __future__ import annotations

import os
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL", "")


def database_activada() -> bool:
    """True si hay DATABASE_URL configurada."""
    return bool(DATABASE_URL)


def obtener_conexion():
    """Obtiene una conexión a PostgreSQL. Lanza error si no hay DATABASE_URL."""
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL no configurada")
    import psycopg2

    return psycopg2.connect(DATABASE_URL)


@contextmanager
def conexion():
    """Context manager para conexión con commit/rollback automático."""
    conn = obtener_conexion()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> bool:
    """Crea las tablas si no existen. Devuelve True si se crearon/modificaron."""
    if not database_activada():
        return False
    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS wa_tenants (
                id TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                phone_number_id TEXT NOT NULL DEFAULT '',
                access_token TEXT NOT NULL DEFAULT '',
                business_account_id TEXT NOT NULL DEFAULT '',
                webhook_verify_token TEXT NOT NULL DEFAULT '',
                api_version TEXT NOT NULL DEFAULT 'v21.0',
                activo BOOLEAN NOT NULL DEFAULT FALSE,
                nombre_remitente TEXT NOT NULL DEFAULT '',
                firma TEXT NOT NULL DEFAULT '',
                fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS wa_contactos (
                id SERIAL PRIMARY KEY,
                tenant_id TEXT NOT NULL REFERENCES wa_tenants(id),
                telefono TEXT NOT NULL,
                nombre TEXT NOT NULL DEFAULT '',
                opt_in TEXT NOT NULL DEFAULT 'pending',
                fecha_opt_in TIMESTAMP,
                fecha_ultimo_mensaje TIMESTAMP,
                metadatos JSONB NOT NULL DEFAULT '{}',
                UNIQUE(tenant_id, telefono)
            );

            CREATE TABLE IF NOT EXISTS wa_conversaciones (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL REFERENCES wa_tenants(id),
                contacto_telefono TEXT NOT NULL,
                fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
                fecha_ultimo_mensaje TIMESTAMP,
                abierta BOOLEAN NOT NULL DEFAULT TRUE,
                UNIQUE(tenant_id, contacto_telefono)
            );

            CREATE TABLE IF NOT EXISTS wa_mensajes (
                id TEXT PRIMARY KEY,
                conversacion_id TEXT NOT NULL REFERENCES wa_conversaciones(id),
                tenant_id TEXT NOT NULL REFERENCES wa_tenants(id),
                direccion TEXT NOT NULL,
                tipo TEXT NOT NULL,
                contenido TEXT NOT NULL DEFAULT '',
                media_url TEXT NOT NULL DEFAULT '',
                media_id TEXT NOT NULL DEFAULT '',
                plantilla_nombre TEXT NOT NULL DEFAULT '',
                plantilla_idioma TEXT NOT NULL DEFAULT 'es',
                estado TEXT NOT NULL DEFAULT 'pending',
                fecha_envio TIMESTAMP NOT NULL DEFAULT NOW(),
                fecha_entrega TIMESTAMP,
                fecha_lectura TIMESTAMP,
                error_codigo TEXT NOT NULL DEFAULT '',
                error_mensaje TEXT NOT NULL DEFAULT '',
                metadata JSONB NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS wa_plantillas (
                id SERIAL PRIMARY KEY,
                tenant_id TEXT NOT NULL REFERENCES wa_tenants(id),
                nombre TEXT NOT NULL,
                idioma TEXT NOT NULL DEFAULT 'es',
                categoria TEXT NOT NULL DEFAULT 'UTILITY',
                estado TEXT NOT NULL DEFAULT 'PENDING',
                componentes JSONB NOT NULL DEFAULT '[]',
                UNIQUE(tenant_id, nombre)
            );

            CREATE INDEX IF NOT EXISTS idx_wa_mensajes_conv ON wa_mensajes(conversacion_id);
            CREATE INDEX IF NOT EXISTS idx_wa_mensajes_tenant ON wa_mensajes(tenant_id);
            CREATE INDEX IF NOT EXISTS idx_wa_contactos_tenant ON wa_contactos(tenant_id);
            CREATE INDEX IF NOT EXISTS idx_wa_conversaciones_tenant ON wa_conversaciones(tenant_id);
        """)
        conn.commit()
        cur.close()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

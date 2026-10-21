"""
Autenticación simple para el portal de administración.

Patrón: igual que el gate de abogados de insolvencia, pero simplificado.
Cada tenant tiene una contraseña de administración. El portal usa un token
Bearer firmado con SESSION_SECRET.

Para el MVP: un solo administrador por tenant. Multi-tenant real (varios
usuarios por tenant) queda para después.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time

SESSION_SECRET = os.getenv("SESSION_SECRET", "whatsapp-module-dev-secret-change-in-prod")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")


def _firmar(payload: str) -> str:
    return hmac.new(SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


def crear_token(tenant_id: str, usuario: str = "admin") -> str:
    """Crea un token firmado para un tenant."""
    payload = json.dumps({"tenant_id": tenant_id, "usuario": usuario, "exp": int(time.time()) + 86400})
    firma = _firmar(payload)
    return f"{payload}|{firma}"


def validar_token(token: str) -> dict | None:
    """Valida un token. Devuelve el payload si es válido, None si no."""
    if not token or "|" not in token:
        return None
    payload, firma = token.rsplit("|", 1)
    if not hmac.compare_digest(_firmar(payload), firma):
        return None
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if data.get("exp", 0) < time.time():
        return None
    return data


def verificar_password(password: str) -> bool:
    """Verifica la contraseña de administración."""
    return hmac.compare_digest(password, ADMIN_PASSWORD)


def registrar_tenant(
    tenant_id: str,
    nombre: str,
    password: str,
    phone_number_id: str = "",
    access_token: str = "",
    business_account_id: str = "",
    webhook_verify_token: str = "",
    nombre_remitente: str = "",
    firma: str = "",
) -> dict:
    """Registra un nuevo tenant. Devuelve el token de acceso."""
    from comunicaciones.whatsapp.almacen import crear_almacen
    from comunicaciones.whatsapp.config import ConfigWhatsApp
    from comunicaciones.whatsapp.modelos import Tenant
    from comunicaciones.whatsapp.servicio import ServicioWhatsApp

    config = ConfigWhatsApp(
        tenant_id=tenant_id,
        nombre_negocio=nombre,
        phone_number_id=phone_number_id,
        access_token=access_token,
        business_account_id=business_account_id,
        webhook_verify_token=webhook_verify_token,
        activo=bool(phone_number_id and access_token),
        nombre_remitente=nombre_remitente or nombre,
        firma=firma,
    )

    almacen = crear_almacen()
    servicio = ServicioWhatsApp(config, almacen=almacen)

    # Registrar tenant en el almacén
    tenant = Tenant(id=tenant_id, nombre=nombre, config=config, activo=config.activo)
    almacen.registrar_tenant(tenant)

    # Registrar plantillas por defecto
    try:
        from comunicaciones.whatsapp.adaptadores.insolvencia import registrar_plantillas

        registrar_plantillas(servicio)
    except Exception as e:  # noqa: BLE001
        logging.getLogger(__name__).warning("No se pudieron registrar plantillas: %s", e)

    token = crear_token(tenant_id)
    return {
        "tenant_id": tenant_id,
        "nombre": nombre,
        "token": token,
        "activado": config.activado(),
    }


def login_tenant(tenant_id: str, password: str) -> dict | None:
    """Autentica un tenant. Devuelve el token si la contraseña es correcta."""
    if not verificar_password(password):
        return None
    token = crear_token(tenant_id)
    return {"tenant_id": tenant_id, "token": token}

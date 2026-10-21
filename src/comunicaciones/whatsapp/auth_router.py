"""
Router FastAPI para autenticación y onboarding del módulo de WhatsApp.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from comunicaciones.whatsapp.auth import (
    login_tenant,
    registrar_tenant,
    validar_token,
    verificar_password,
)

router = APIRouter(prefix="/api/v1/whatsapp/auth", tags=["whatsapp-auth"])


@router.post("/registrar")
def registrar(
    tenant_id: str,
    nombre: str,
    password: str,
    phone_number_id: str = "",
    access_token: str = "",
    business_account_id: str = "",
    webhook_verify_token: str = "",
    nombre_remitente: str = "",
    firma: str = "",
):
    """Registra un nuevo tenant (negocio)."""
    if not verificar_password(password):
        raise HTTPException(status_code=403, detail="Contraseña de administración incorrecta")
    resultado = registrar_tenant(
        tenant_id=tenant_id,
        nombre=nombre,
        password=password,
        phone_number_id=phone_number_id,
        access_token=access_token,
        business_account_id=business_account_id,
        webhook_verify_token=webhook_verify_token,
        nombre_remitente=nombre_remitente,
        firma=firma,
    )
    return resultado


@router.post("/login")
def login(tenant_id: str, password: str):
    """Autentica un tenant."""
    if not verificar_password(password):
        raise HTTPException(status_code=403, detail="Contraseña incorrecta")
    resultado = login_tenant(tenant_id, password)
    if resultado is None:
        raise HTTPException(status_code=403, detail="Autenticación fallida")
    return resultado


@router.get("/verificar")
def verificar(token: str = Query(...)):
    """Verifica un token de acceso."""
    data = validar_token(token)
    if data is None:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    return {"valido": True, "tenant_id": data["tenant_id"], "usuario": data["usuario"]}

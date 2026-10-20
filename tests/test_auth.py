"""
Pruebas de autenticación y onboarding del módulo de WhatsApp.

Prueban:
- Registro de tenant (correcto e incorrecto).
- Login (contraseña correcta e incorrecta).
- Verificación de token (válido e inválido).
- Flujo de onboarding (registrar → verificar → enviar).
"""
from __future__ import annotations

import os

import pytest

from comunicaciones.whatsapp.auth import (
    crear_token,
    login_tenant,
    registrar_tenant,
    validar_token,
    verificar_password,
)
from comunicaciones.whatsapp.almacen import AlmacenWhatsApp
from comunicaciones.whatsapp.config import ConfigWhatsApp
from comunicaciones.whatsapp.servicio import ServicioWhatsApp


# ── Password ──


def test_verificar_password_correcta():
    os.environ["ADMIN_PASSWORD"] = "secreto123"
    # Re-import to pick up env
    import importlib
    import comunicaciones.whatsapp.auth as auth_mod
    importlib.reload(auth_mod)
    assert auth_mod.verificar_password("secreto123") is True


def test_verificar_password_incorrecta():
    os.environ["ADMIN_PASSWORD"] = "secreto123"
    import importlib
    import comunicaciones.whatsapp.auth as auth_mod
    importlib.reload(auth_mod)
    assert auth_mod.verificar_password("otra") is False


# ── Token ──


def test_crear_y_validar_token():
    token = crear_token("tenant1", "admin")
    assert "|" in token
    data = validar_token(token)
    assert data is not None
    assert data["tenant_id"] == "tenant1"
    assert data["usuario"] == "admin"


def test_token_invalido():
    assert validar_token("basura") is None
    assert validar_token("") is None
    assert validar_token("payload|firma-falsa") is None


def test_token_expirado():
    import json, time, hmac, hashlib
    from comunicaciones.whatsapp.auth import _firmar
    payload = json.dumps({"tenant_id": "t1", "usuario": "admin", "exp": int(time.time()) - 100})
    firma = _firmar(payload)
    token = f"{payload}|{firma}"
    assert validar_token(token) is None


# ── Registro ──


def test_registrar_tenant_sin_credenciales():
    os.environ["ADMIN_PASSWORD"] = "admin123"
    import importlib
    import comunicaciones.whatsapp.auth as auth_mod
    importlib.reload(auth_mod)
    resultado = auth_mod.registrar_tenant(
        tenant_id="test-tenant",
        nombre="Test Negocio",
        password="admin123",
    )
    assert resultado["tenant_id"] == "test-tenant"
    assert resultado["nombre"] == "Test Negocio"
    assert resultado["activado"] is False
    assert "token" in resultado


def test_registrar_tenant_con_credenciales():
    os.environ["ADMIN_PASSWORD"] = "admin123"
    import importlib
    import comunicaciones.whatsapp.auth as auth_mod
    importlib.reload(auth_mod)
    resultado = auth_mod.registrar_tenant(
        tenant_id="test-tenant-2",
        nombre="Test Negocio 2",
        password="admin123",
        phone_number_id="123456",
        access_token="token-secreto",
    )
    assert resultado["activado"] is True


def test_registrar_tenant_password_incorrecta():
    os.environ["ADMIN_PASSWORD"] = "admin123"
    import importlib
    import comunicaciones.whatsapp.auth as auth_mod
    importlib.reload(auth_mod)
    # La función registrar_tenant no verifica password; eso lo hace el endpoint.
    # Aquí solo verificamos que verificar_password funcione.
    assert auth_mod.verificar_password("otra") is False


# ── Login ──


def test_login_correcto():
    os.environ["ADMIN_PASSWORD"] = "admin123"
    import importlib
    import comunicaciones.whatsapp.auth as auth_mod
    importlib.reload(auth_mod)
    resultado = auth_mod.login_tenant("mi-tenant", "admin123")
    assert resultado is not None
    assert resultado["tenant_id"] == "mi-tenant"
    assert "token" in resultado


def test_login_incorrecto():
    os.environ["ADMIN_PASSWORD"] = "admin123"
    import importlib
    import comunicaciones.whatsapp.auth as auth_mod
    importlib.reload(auth_mod)
    resultado = auth_mod.login_tenant("mi-tenant", "otra")
    assert resultado is None


# ── Flujo de onboarding ──


def test_flujo_onboarding_completo():
    """Simula el flujo completo: registrar → verificar token → enviar mensaje (sin creds)."""
    os.environ["ADMIN_PASSWORD"] = "admin123"
    import importlib
    import comunicaciones.whatsapp.auth as auth_mod
    importlib.reload(auth_mod)

    # 1. Registrar
    reg = auth_mod.registrar_tenant(
        tenant_id="onboarding-test",
        nombre="Onboarding Test",
        password="admin123",
    )
    assert reg["activado"] is False

    # 2. Verificar token
    data = auth_mod.validar_token(reg["token"])
    assert data is not None
    assert data["tenant_id"] == "onboarding-test"

    # 3. Enviar mensaje sin creds → no_configurado
    cfg = ConfigWhatsApp(tenant_id="onboarding-test", activo=False)
    svc = ServicioWhatsApp(cfg)
    resultado = svc.enviar_texto("573001234567", "Hola")
    assert resultado["enviado"] is False
    assert resultado["estado"] == "no_configurado"


def test_flujo_onboarding_con_credenciales():
    """Onboarding con credenciales → activado."""
    os.environ["ADMIN_PASSWORD"] = "admin123"
    import importlib
    import comunicaciones.whatsapp.auth as auth_mod
    importlib.reload(auth_mod)

    reg = auth_mod.registrar_tenant(
        tenant_id="onboarding-test-2",
        nombre="Onboarding Test 2",
        password="admin123",
        phone_number_id="123456",
        access_token="token-secreto",
    )
    assert reg["activado"] is True
    data = auth_mod.validar_token(reg["token"])
    assert data is not None

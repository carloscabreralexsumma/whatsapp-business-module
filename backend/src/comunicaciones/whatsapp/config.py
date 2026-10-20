"""
Configuración del módulo de WhatsApp Business Cloud API.

Patrón: igual que email/api.py — sin credenciales el módulo queda desactivado
y devuelve "no_configurado" en vez de fallar. Con credenciales, envía de verdad.

Variables de entorno (por tenant, o globales para el tenant por defecto):
- WHATSAPP_ENABLED: "true"/"false" (default false)
- WHATSAPP_PHONE_NUMBER_ID: ID del número de WhatsApp Business (de Meta)
- WHATSAPP_ACCESS_TOKEN: token de acceso de la Cloud API
- WHATSAPP_BUSINESS_ACCOUNT_ID: ID de la cuenta de WhatsApp Business
- WHATSAPP_WEBHOOK_VERIFY_TOKEN: token para verificar el webhook (lo eliges tú)
- WHATSAPP_API_VERSION: versión de la Graph API (default v21.0)
"""
from __future__ import annotations

import os
from dataclasses import dataclass


def get_env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


@dataclass
class ConfigWhatsApp:
    """Configuración de un tenant (un negocio que usa el módulo)."""

    tenant_id: str = "default"
    nombre_negocio: str = "Mi Negocio"
    phone_number_id: str = ""
    access_token: str = ""
    business_account_id: str = ""
    webhook_verify_token: str = ""
    api_version: str = "v21.0"
    activo: bool = False

    # Marca (para mensajes y plantillas white-label)
    nombre_remitente: str = ""
    firma: str = ""

    # Límites operativos
    max_reintentos: int = 3
    timeout_segundos: int = 30

    @property
    def api_base(self) -> str:
        return f"https://graph.facebook.com/{self.api_version}"

    @property
    def url_mensajes(self) -> str:
        return f"{self.api_base}/{self.phone_number_id}/messages"

    @property
    def url_media(self) -> str:
        return f"{self.api_base}/{self.phone_number_id}/media"

    def activado(self) -> bool:
        return bool(self.activo and self.phone_number_id and self.access_token)


def config_desde_entorno(tenant_id: str = "default") -> ConfigWhatsApp:
    """Construye la configuración leyendo variables de entorno."""
    prefijo = f"WHATSAPP_{tenant_id.upper()}_" if tenant_id != "default" else "WHATSAPP_"
    cfg = ConfigWhatsApp(
        tenant_id=tenant_id,
        nombre_negocio=get_env(f"{prefijo}NOMBRE_NEGOCIO", get_env("WHATSAPP_NOMBRE_NEGOCIO", "Mi Negocio")),
        phone_number_id=get_env(f"{prefijo}PHONE_NUMBER_ID", get_env("WHATSAPP_PHONE_NUMBER_ID")),
        access_token=get_env(f"{prefijo}ACCESS_TOKEN", get_env("WHATSAPP_ACCESS_TOKEN")),
        business_account_id=get_env(f"{prefijo}BUSINESS_ACCOUNT_ID", get_env("WHATSAPP_BUSINESS_ACCOUNT_ID")),
        webhook_verify_token=get_env(f"{prefijo}WEBHOOK_VERIFY_TOKEN", get_env("WHATSAPP_WEBHOOK_VERIFY_TOKEN")),
        api_version=get_env(f"{prefijo}API_VERSION", get_env("WHATSAPP_API_VERSION", "v21.0")),
        activo=get_env(f"{prefijo}ENABLED", get_env("WHATSAPP_ENABLED", "false")).lower() == "true",
        nombre_remitente=get_env(f"{prefijo}NOMBRE_REMITENTE", get_env("WHATSAPP_NOMBRE_REMITENTE", "")),
        firma=get_env(f"{prefijo}FIRMA", get_env("WHATSAPP_FIRMA", "")),
    )
    return cfg


# Configuración global del tenant por defecto (Insolvencia Colombia)
CONFIG_DEFAULT = config_desde_entorno("default")

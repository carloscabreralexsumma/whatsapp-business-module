"""
Comunicaciones por WhatsApp Business Cloud API — módulo genérico y reutilizable.

Diseñado para funcionar como servicio independiente (white-label): cualquier
negocio puede configurar su propio número de WhatsApp Business, sus plantillas
y su marca, sin tocar el código del módulo.

La plataforma de Insolvencia Colombia es el primer consumidor (tenant 0).

Capas:
- config: configuración por tenant (phone_number_id, access_token, etc.)
- cliente: cliente HTTP de la Cloud API de Meta (urllib, sin dependencias).
- modelos: entidades de dominio (Contacto, Conversacion, Mensaje, Plantilla, Tenant).
- almacen: persistencia en memoria (patrón del proyecto; migrar a PostgreSQL después).
- servicio: lógica de negocio (enviar, recibir, opt-in/out, trazabilidad).
- webhook: router FastAPI para verificación e ingreso de mensajes.
- adaptadores: integraciones específicas por negocio (insolvencia, etc.).
"""
from __future__ import annotations

__version__ = "0.1.0"

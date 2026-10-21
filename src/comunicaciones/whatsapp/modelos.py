"""
Modelos de dominio del módulo de WhatsApp.

Entidades:
- Tenant: un negocio que usa el módulo (config + marca).
- Contacto: una persona con la que se conversa (teléfono, nombre, opt-in).
- Conversacion: hilo de mensajes con un contacto.
- Mensaje: un mensaje individual (enviado o recibido).
- Plantilla: plantilla aprobada por Meta (para mensajes proactivos).
- EstadoEntrega: estado de entrega de un mensaje (enviado, entregado, leído, fallido).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from comunicaciones.whatsapp.config import ConfigWhatsApp


class TipoMensaje(StrEnum):
    TEXTO = "text"
    PLANTILLA = "template"
    DOCUMENTO = "document"
    IMAGEN = "image"
    AUDIO = "audio"
    VIDEO = "video"
    UBICACION = "location"
    CONTACTO = "contacts"
    INTERACTIVO = "interactive"


class Direccion(StrEnum):
    ENVIADO = "outbound"
    RECIBIDO = "inbound"


class EstadoEntrega(StrEnum):
    PENDIENTE = "pending"
    ENVIADO = "sent"
    ENTREGADO = "delivered"
    LEIDO = "read"
    FALLIDO = "failed"


class OptIn(StrEnum):
    PENDIENTE = "pending"
    ACEPTADO = "accepted"
    RECHAZADO = "rejected"


@dataclass
class Contacto:
    """Una persona con la que se conversa por WhatsApp."""

    telefono: str  # formato E.164 sin + (ej: 573001234567)
    nombre: str = ""
    tenant_id: str = "default"
    opt_in: OptIn = OptIn.PENDIENTE
    fecha_opt_in: datetime | None = None
    fecha_ultimo_mensaje: datetime | None = None
    metadatos: dict = field(default_factory=dict)

    @property
    def telefono_formateado(self) -> str:
        return f"+{self.telefono}" if not self.telefono.startswith("+") else self.telefono

    def aceptar_opt_in(self) -> None:
        self.opt_in = OptIn.ACEPTADO
        self.fecha_opt_in = datetime.now(UTC)

    def rechazar_opt_in(self) -> None:
        self.opt_in = OptIn.RECHAZADO


@dataclass
class Mensaje:
    """Un mensaje individual (enviado o recibido)."""

    id: str
    conversacion_id: str
    tenant_id: str
    direccion: Direccion
    tipo: TipoMensaje
    contenido: str = ""
    media_url: str = ""
    media_id: str = ""
    plantilla_nombre: str = ""
    plantilla_idioma: str = "es"
    estado: EstadoEntrega = EstadoEntrega.PENDIENTE
    fecha_envio: datetime = field(default_factory=lambda: datetime.now(UTC))
    fecha_entrega: datetime | None = None
    fecha_lectura: datetime | None = None
    error_codigo: str = ""
    error_mensaje: str = ""
    metadata: dict = field(default_factory=dict)

    def marcar_entregado(self) -> None:
        self.estado = EstadoEntrega.ENTREGADO
        self.fecha_entrega = datetime.now(UTC)

    def marcar_leido(self) -> None:
        self.estado = EstadoEntrega.LEIDO
        self.fecha_lectura = datetime.now(UTC)

    def marcar_fallido(self, codigo: str, mensaje: str) -> None:
        self.estado = EstadoEntrega.FALLIDO
        self.error_codigo = codigo
        self.error_mensaje = mensaje


@dataclass
class Conversacion:
    """Hilo de mensajes con un contacto."""

    id: str
    tenant_id: str
    contacto_telefono: str
    mensajes: list[Mensaje] = field(default_factory=list)
    fecha_creacion: datetime = field(default_factory=lambda: datetime.now(UTC))
    fecha_ultimo_mensaje: datetime | None = None
    abierta: bool = True

    def agregar_mensaje(self, mensaje: Mensaje) -> None:
        self.mensajes.append(mensaje)
        self.fecha_ultimo_mensaje = mensaje.fecha_envio

    @property
    def ultimo_mensaje(self) -> Mensaje | None:
        return self.mensajes[-1] if self.mensajes else None

    @property
    def cantidad_mensajes(self) -> int:
        return len(self.mensajes)


@dataclass
class Plantilla:
    """Plantilla aprobada por Meta para mensajes proactivos."""

    nombre: str
    idioma: str = "es"
    categoria: str = "UTILITY"  # UTILITY, MARKETING, AUTHENTICATION
    estado: str = "PENDING"  # PENDING, APPROVED, REJECTED
    componentes: list[dict] = field(default_factory=list)
    tenant_id: str = "default"

    @property
    def aprobada(self) -> bool:
        return self.estado == "APPROVED"


@dataclass
class Tenant:
    """Un negocio que usa el módulo (configuración + marca)."""

    id: str
    nombre: str
    config: ConfigWhatsApp | None = None  # type: ignore[assignment]
    plantillas: list[Plantilla] = field(default_factory=list)
    fecha_creacion: datetime = field(default_factory=lambda: datetime.now(UTC))
    activo: bool = True

    def plantilla_por_nombre(self, nombre: str) -> Plantilla | None:
        for p in self.plantillas:
            if p.nombre == nombre:
                return p
        return None

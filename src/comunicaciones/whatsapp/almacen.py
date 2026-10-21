"""
Almacenamiento en memoria del módulo de WhatsApp.

Patrón: igual que memoria_juridica/servicio.py — diccionarios en memoria,
útil para desarrollo y pruebas. Migrar a PostgreSQL cuando pase a producción
(igual que las 5 capas jurídicas, P20).

Entidades almacenadas:
- tenants: dict[tenant_id, Tenant]
- contactos: dict[(tenant_id, telefono), Contacto]
- conversaciones: dict[(tenant_id, telefono), Conversacion]
- mensajes: dict[mensaje_id, Mensaje]
- plantillas: dict[(tenant_id, nombre), Plantilla]
"""
from __future__ import annotations

import uuid
from datetime import datetime

from comunicaciones.whatsapp.modelos import (
    Contacto,
    Conversacion,
    Mensaje,
    Plantilla,
    Tenant,
)


def crear_almacen():
    """Factory: devuelve AlmacenWhatsAppPostgres si DATABASE_URL está configurada,
    o AlmacenWhatsApp (memoria) si no."""
    from comunicaciones.whatsapp.database import database_activada

    if database_activada():
        from comunicaciones.whatsapp.almacen_postgres import AlmacenWhatsAppPostgres

        return AlmacenWhatsAppPostgres()
    return AlmacenWhatsApp()


class AlmacenWhatsApp:
    """Almacenamiento en memoria para el módulo de WhatsApp."""

    def __init__(self):
        self.tenants: dict[str, Tenant] = {}
        self.contactos: dict[tuple[str, str], Contacto] = {}
        self.conversaciones: dict[tuple[str, str], Conversacion] = {}
        self.mensajes: dict[str, Mensaje] = {}
        self.plantillas: dict[tuple[str, str], Plantilla] = {}

    # ── Tenants ──

    def registrar_tenant(self, tenant: Tenant) -> Tenant:
        self.tenants[tenant.id] = tenant
        return tenant

    def obtener_tenant(self, tenant_id: str) -> Tenant | None:
        return self.tenants.get(tenant_id)

    def listar_tenants(self) -> list[Tenant]:
        return list(self.tenants.values())

    # ── Contactos ──

    def obtener_o_crear_contacto(
        self, tenant_id: str, telefono: str, nombre: str = ""
    ) -> Contacto:
        clave = (tenant_id, telefono)
        if clave not in self.contactos:
            self.contactos[clave] = Contacto(
                telefono=telefono, nombre=nombre, tenant_id=tenant_id
            )
        elif nombre and not self.contactos[clave].nombre:
            self.contactos[clave].nombre = nombre
        return self.contactos[clave]

    def obtener_contacto(self, tenant_id: str, telefono: str) -> Contacto | None:
        return self.contactos.get((tenant_id, telefono))

    def listar_contactos(self, tenant_id: str) -> list[Contacto]:
        return [c for (t, _), c in self.contactos.items() if t == tenant_id]

    # ── Conversaciones ──

    def obtener_o_crear_conversacion(
        self, tenant_id: str, telefono: str
    ) -> Conversacion:
        clave = (tenant_id, telefono)
        if clave not in self.conversaciones:
            self.conversaciones[clave] = Conversacion(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                contacto_telefono=telefono,
            )
        return self.conversaciones[clave]

    def obtener_conversacion(
        self, tenant_id: str, telefono: str
    ) -> Conversacion | None:
        return self.conversaciones.get((tenant_id, telefono))

    def listar_conversaciones(self, tenant_id: str) -> list[Conversacion]:
        return [c for (t, _), c in self.conversaciones.items() if t == tenant_id]

    # ── Mensajes ──

    def guardar_mensaje(self, mensaje: Mensaje) -> Mensaje:
        self.mensajes[mensaje.id] = mensaje
        conv = self.obtener_o_crear_conversacion(mensaje.tenant_id, self._telefono_de_mensaje(mensaje))
        conv.agregar_mensaje(mensaje)
        return mensaje

    def obtener_mensaje(self, mensaje_id: str) -> Mensaje | None:
        return self.mensajes.get(mensaje_id)

    def actualizar_estado_mensaje(
        self, mensaje_id: str, estado: str, fecha: datetime | None = None
    ) -> Mensaje | None:
        msg = self.mensajes.get(mensaje_id)
        if msg is None:
            return None
        if estado == "delivered":
            msg.marcar_entregado()
        elif estado == "read":
            msg.marcar_leido()
        elif estado == "failed":
            msg.marcar_fallido("", "")
        return msg

    def _telefono_de_mensaje(self, mensaje: Mensaje) -> str:
        # El teléfono está en la conversación, no en el mensaje. Buscar por conv_id.
        for conv in self.conversaciones.values():
            if conv.id == mensaje.conversacion_id:
                return conv.contacto_telefono
        return ""

    # ── Plantillas ──

    def registrar_plantilla(self, plantilla: Plantilla) -> Plantilla:
        self.plantillas[(plantilla.tenant_id, plantilla.nombre)] = plantilla
        tenant = self.tenants.get(plantilla.tenant_id)
        if tenant:
            tenant.plantillas.append(plantilla)
        return plantilla

    def obtener_plantilla(self, tenant_id: str, nombre: str) -> Plantilla | None:
        return self.plantillas.get((tenant_id, nombre))

    def listar_plantillas(self, tenant_id: str) -> list[Plantilla]:
        return [p for (t, _), p in self.plantillas.items() if t == tenant_id]

    # ── Utilidades ──

    def limpiar(self) -> None:
        """Limpia todo el almacen (para pruebas)."""
        self.tenants.clear()
        self.contactos.clear()
        self.conversaciones.clear()
        self.mensajes.clear()
        self.plantillas.clear()

    def estadisticas(self, tenant_id: str = "") -> dict:
        """Estadísticas básicas del módulo."""
        if tenant_id:
            convs = self.listar_conversaciones(tenant_id)
            msgs = [m for m in self.mensajes.values() if m.tenant_id == tenant_id]
        else:
            convs = list(self.conversaciones.values())
            msgs = list(self.mensajes.values())
        return {
            "tenants": len(self.tenants),
            "contactos": len(self.contactos) if not tenant_id else len(self.listar_contactos(tenant_id)),
            "conversaciones": len(convs),
            "mensajes": len(msgs),
            "mensajes_enviados": sum(1 for m in msgs if m.direccion.value == "outbound"),
            "mensajes_recibidos": sum(1 for m in msgs if m.direccion.value == "inbound"),
        }

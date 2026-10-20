"""
Almacenamiento en PostgreSQL del módulo de WhatsApp.

Implementa la misma interfaz que AlmacenWhatsApp (memoria) pero persiste
en PostgreSQL. Se usa cuando DATABASE_URL está configurada.

Si DATABASE_URL no está configurada, se usa AlmacenWhatsApp (memoria).
"""
from __future__ import annotations

import json
import uuid

from comunicaciones.whatsapp.database import conexion
from comunicaciones.whatsapp.modelos import (
    Contacto,
    Conversacion,
    Mensaje,
    OptIn,
    Plantilla,
    Tenant,
)


def _row_to_contacto(row) -> Contacto:
    return Contacto(
        telefono=row[1],
        nombre=row[2] or "",
        tenant_id=row[0],
        opt_in=OptIn(row[3]) if row[3] else OptIn.PENDIENTE,
        fecha_opt_in=row[4],
        fecha_ultimo_mensaje=row[5],
        metadatos=row[6] if row[6] else {},
    )


def _row_to_conversacion(row) -> Conversacion:
    return Conversacion(
        id=row[0],
        tenant_id=row[1],
        contacto_telefono=row[2],
        fecha_creacion=row[3],
        fecha_ultimo_mensaje=row[4],
        abierta=row[5] if row[5] is not None else True,
    )


def _row_to_mensaje(row) -> Mensaje:
    from comunicaciones.whatsapp.modelos import Direccion, EstadoEntrega, TipoMensaje

    return Mensaje(
        id=row[0],
        conversacion_id=row[1],
        tenant_id=row[2],
        direccion=Direccion(row[3]),
        tipo=TipoMensaje(row[4]),
        contenido=row[5] or "",
        media_url=row[6] or "",
        media_id=row[7] or "",
        plantilla_nombre=row[8] or "",
        plantilla_idioma=row[9] or "es",
        estado=EstadoEntrega(row[10]) if row[10] else EstadoEntrega.PENDIENTE,
        fecha_envio=row[11],
        fecha_entrega=row[12],
        fecha_lectura=row[13],
        error_codigo=row[14] or "",
        error_mensaje=row[15] or "",
        metadata=row[16] if row[16] else {},
    )


def _row_to_plantilla(row) -> Plantilla:
    return Plantilla(
        nombre=row[1],
        idioma=row[2] or "es",
        categoria=row[3] or "UTILITY",
        estado=row[4] or "PENDING",
        componentes=row[5] if row[5] else [],
        tenant_id=row[0],
    )


def _row_to_tenant(row) -> Tenant:
    from comunicaciones.whatsapp.config import ConfigWhatsApp

    config = ConfigWhatsApp(
        tenant_id=row[0],
        nombre_negocio=row[1],
        phone_number_id=row[2] or "",
        access_token=row[3] or "",
        business_account_id=row[4] or "",
        webhook_verify_token=row[5] or "",
        api_version=row[6] or "v21.0",
        activo=row[7] if row[7] is not None else False,
        nombre_remitente=row[8] or "",
        firma=row[9] or "",
    )
    return Tenant(
        id=row[0],
        nombre=row[1],
        config=config,
        fecha_creacion=row[10],
        activo=row[7] if row[7] is not None else True,
    )


class AlmacenWhatsAppPostgres:
    """Almacenamiento en PostgreSQL del módulo de WhatsApp."""

    # ── Tenants ──

    def registrar_tenant(self, tenant) -> Tenant:
        with conexion() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO wa_tenants (id, nombre, phone_number_id, access_token,
                   business_account_id, webhook_verify_token, api_version, activo,
                   nombre_remitente, firma)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (id) DO UPDATE SET
                     nombre = EXCLUDED.nombre,
                     phone_number_id = EXCLUDED.phone_number_id,
                     access_token = EXCLUDED.access_token,
                     business_account_id = EXCLUDED.business_account_id,
                     webhook_verify_token = EXCLUDED.webhook_verify_token,
                     api_version = EXCLUDED.api_version,
                     activo = EXCLUDED.activo,
                     nombre_remitente = EXCLUDED.nombre_remitente,
                     firma = EXCLUDED.firma""",
                (
                    tenant.id,
                    tenant.nombre,
                    tenant.config.phone_number_id if tenant.config else "",
                    tenant.config.access_token if tenant.config else "",
                    tenant.config.business_account_id if tenant.config else "",
                    tenant.config.webhook_verify_token if tenant.config else "",
                    tenant.config.api_version if tenant.config else "v21.0",
                    tenant.activo,
                    tenant.config.nombre_remitente if tenant.config else "",
                    tenant.config.firma if tenant.config else "",
                ),
            )
            cur.close()
        return tenant

    def obtener_tenant(self, tenant_id: str) -> Tenant | None:
        with conexion() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT id, nombre, phone_number_id, access_token, business_account_id,
                          webhook_verify_token, api_version, activo, nombre_remitente,
                          firma, fecha_creacion
                   FROM wa_tenants WHERE id = %s""",
                (tenant_id,),
            )
            row = cur.fetchone()
            cur.close()
            if row is None:
                return None
            tenant = _row_to_tenant(row)
            # Cargar plantillas
            tenant.plantillas = self.listar_plantillas(tenant_id)
            return tenant

    def listar_tenants(self) -> list[Tenant]:
        with conexion() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, nombre, phone_number_id, access_token, business_account_id, webhook_verify_token, api_version, activo, nombre_remitente, firma, fecha_creacion FROM wa_tenants")
            rows = cur.fetchall()
            cur.close()
            return [_row_to_tenant(r) for r in rows]

    # ── Contactos ──

    def obtener_o_crear_contacto(self, tenant_id: str, telefono: str, nombre: str = "") -> Contacto:
        with conexion() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT tenant_id, telefono, nombre, opt_in, fecha_opt_in,
                          fecha_ultimo_mensaje, metadatos
                   FROM wa_contactos WHERE tenant_id = %s AND telefono = %s""",
                (tenant_id, telefono),
            )
            row = cur.fetchone()
            if row is None:
                cur.execute(
                    """INSERT INTO wa_contactos (tenant_id, telefono, nombre)
                       VALUES (%s, %s, %s) RETURNING tenant_id, telefono, nombre, opt_in,
                       fecha_opt_in, fecha_ultimo_mensaje, metadatos""",
                    (tenant_id, telefono, nombre),
                )
                row = cur.fetchone()
            elif nombre and not row[2]:
                cur.execute(
                    "UPDATE wa_contactos SET nombre = %s WHERE tenant_id = %s AND telefono = %s",
                    (nombre, tenant_id, telefono),
                )
                cur.execute(
                    """SELECT tenant_id, telefono, nombre, opt_in, fecha_opt_in,
                              fecha_ultimo_mensaje, metadatos
                       FROM wa_contactos WHERE tenant_id = %s AND telefono = %s""",
                    (tenant_id, telefono),
                )
                row = cur.fetchone()
            cur.close()
            return _row_to_contacto(row)

    def obtener_contacto(self, tenant_id: str, telefono: str) -> Contacto | None:
        with conexion() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT tenant_id, telefono, nombre, opt_in, fecha_opt_in,
                          fecha_ultimo_mensaje, metadatos
                   FROM wa_contactos WHERE tenant_id = %s AND telefono = %s""",
                (tenant_id, telefono),
            )
            row = cur.fetchone()
            cur.close()
            if row is None:
                return None
            return _row_to_contacto(row)

    def listar_contactos(self, tenant_id: str) -> list[Contacto]:
        with conexion() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT tenant_id, telefono, nombre, opt_in, fecha_opt_in,
                          fecha_ultimo_mensaje, metadatos
                   FROM wa_contactos WHERE tenant_id = %s""",
                (tenant_id,),
            )
            rows = cur.fetchall()
            cur.close()
            return [_row_to_contacto(r) for r in rows]

    # ── Conversaciones ──

    def obtener_o_crear_conversacion(self, tenant_id: str, telefono: str) -> Conversacion:
        with conexion() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, tenant_id, contacto_telefono, fecha_creacion, fecha_ultimo_mensaje, abierta "
                "FROM wa_conversaciones WHERE tenant_id = %s AND contacto_telefono = %s",
                (tenant_id, telefono),
            )
            row = cur.fetchone()
            if row is None:
                conv_id = str(uuid.uuid4())
                cur.execute(
                    """INSERT INTO wa_conversaciones (id, tenant_id, contacto_telefono)
                       VALUES (%s, %s, %s) RETURNING id, tenant_id, contacto_telefono,
                       fecha_creacion, fecha_ultimo_mensaje, abierta""",
                    (conv_id, tenant_id, telefono),
                )
                row = cur.fetchone()
            cur.close()
            conv = _row_to_conversacion(row)
            # Cargar mensajes
            return conv

    def obtener_conversacion(self, tenant_id: str, telefono: str) -> Conversacion | None:
        with conexion() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, tenant_id, contacto_telefono, fecha_creacion, fecha_ultimo_mensaje, abierta "
                "FROM wa_conversaciones WHERE tenant_id = %s AND contacto_telefono = %s",
                (tenant_id, telefono),
            )
            row = cur.fetchone()
            cur.close()
            if row is None:
                return None
            conv = _row_to_conversacion(row)
            # Cargar mensajes
            conv.mensajes = self._cargar_mensajes(conv.id)
            return conv

    def _cargar_mensajes(self, conversacion_id: str) -> list[Mensaje]:
        with conexion() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT id, conversacion_id, tenant_id, direccion, tipo, contenido,
                          media_url, media_id, plantilla_nombre, plantilla_idioma, estado,
                          fecha_envio, fecha_entrega, fecha_lectura, error_codigo,
                          error_mensaje, metadata
                   FROM wa_mensajes WHERE conversacion_id = %s ORDER BY fecha_envio""",
                (conversacion_id,),
            )
            rows = cur.fetchall()
            cur.close()
            return [_row_to_mensaje(r) for r in rows]

    def listar_conversaciones(self, tenant_id: str) -> list[Conversacion]:
        with conexion() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, tenant_id, contacto_telefono, fecha_creacion, fecha_ultimo_mensaje, abierta "
                "FROM wa_conversaciones WHERE tenant_id = %s ORDER BY fecha_ultimo_mensaje DESC NULLS LAST",
                (tenant_id,),
            )
            rows = cur.fetchall()
            cur.close()
            convs = []
            for r in rows:
                conv = _row_to_conversacion(r)
                conv.mensajes = self._cargar_mensajes(conv.id)
                convs.append(conv)
            return convs

    # ── Mensajes ──

    def guardar_mensaje(self, mensaje: Mensaje) -> Mensaje:
        with conexion() as conn:
            cur = conn.cursor()
            # Insertar mensaje
            cur.execute(
                """INSERT INTO wa_mensajes (id, conversacion_id, tenant_id, direccion, tipo,
                   contenido, media_url, media_id, plantilla_nombre, plantilla_idioma, estado,
                   fecha_envio, fecha_entrega, fecha_lectura, error_codigo, error_mensaje, metadata)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (id) DO UPDATE SET
                     estado = EXCLUDED.estado,
                     fecha_entrega = EXCLUDED.fecha_entrega,
                     fecha_lectura = EXCLUDED.fecha_lectura,
                     error_codigo = EXCLUDED.error_codigo,
                     error_mensaje = EXCLUDED.error_mensaje""",
                (
                    mensaje.id,
                    mensaje.conversacion_id,
                    mensaje.tenant_id,
                    mensaje.direccion.value,
                    mensaje.tipo.value,
                    mensaje.contenido,
                    mensaje.media_url,
                    mensaje.media_id,
                    mensaje.plantilla_nombre,
                    mensaje.plantilla_idioma,
                    mensaje.estado.value,
                    mensaje.fecha_envio,
                    mensaje.fecha_entrega,
                    mensaje.fecha_lectura,
                    mensaje.error_codigo,
                    mensaje.error_mensaje,
                    json.dumps(mensaje.metadata),
                ),
            )
            # Actualizar fecha_ultimo_mensaje de la conversación
            cur.execute(
                "UPDATE wa_conversaciones SET fecha_ultimo_mensaje = %s WHERE id = %s",
                (mensaje.fecha_envio, mensaje.conversacion_id),
            )
            cur.close()
        return mensaje

    def obtener_mensaje(self, mensaje_id: str) -> Mensaje | None:
        with conexion() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT id, conversacion_id, tenant_id, direccion, tipo, contenido,
                          media_url, media_id, plantilla_nombre, plantilla_idioma, estado,
                          fecha_envio, fecha_entrega, fecha_lectura, error_codigo,
                          error_mensaje, metadata
                   FROM wa_mensajes WHERE id = %s""",
                (mensaje_id,),
            )
            row = cur.fetchone()
            cur.close()
            if row is None:
                return None
            return _row_to_mensaje(row)

    def actualizar_estado_mensaje(self, mensaje_id: str, estado: str, fecha=None) -> Mensaje | None:
        msg = self.obtener_mensaje(mensaje_id)
        if msg is None:
            return None
        if estado == "delivered":
            msg.marcar_entregado()
        elif estado == "read":
            msg.marcar_leido()
        elif estado == "failed":
            msg.marcar_fallido("", "")
        # Persistir
        with conexion() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE wa_mensajes SET estado = %s, fecha_entrega = %s, fecha_lectura = %s WHERE id = %s",
                (msg.estado.value, msg.fecha_entrega, msg.fecha_lectura, mensaje_id),
            )
            cur.close()
        return msg

    # ── Plantillas ──

    def registrar_plantilla(self, plantilla: Plantilla) -> Plantilla:
        with conexion() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO wa_plantillas (tenant_id, nombre, idioma, categoria, estado, componentes)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (tenant_id, nombre) DO UPDATE SET
                     idioma = EXCLUDED.idioma,
                     categoria = EXCLUDED.categoria,
                     estado = EXCLUDED.estado,
                     componentes = EXCLUDED.componentes""",
                (
                    plantilla.tenant_id,
                    plantilla.nombre,
                    plantilla.idioma,
                    plantilla.categoria,
                    plantilla.estado,
                    json.dumps(plantilla.componentes),
                ),
            )
            cur.close()
        return plantilla

    def obtener_plantilla(self, tenant_id: str, nombre: str) -> Plantilla | None:
        with conexion() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT tenant_id, nombre, idioma, categoria, estado, componentes FROM wa_plantillas WHERE tenant_id = %s AND nombre = %s",
                (tenant_id, nombre),
            )
            row = cur.fetchone()
            cur.close()
            if row is None:
                return None
            return _row_to_plantilla(row)

    def listar_plantillas(self, tenant_id: str) -> list[Plantilla]:
        with conexion() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT tenant_id, nombre, idioma, categoria, estado, componentes FROM wa_plantillas WHERE tenant_id = %s",
                (tenant_id,),
            )
            rows = cur.fetchall()
            cur.close()
            return [_row_to_plantilla(r) for r in rows]

    # ── Utilidades ──

    def limpiar(self) -> None:
        """Limpia todo (para pruebas — solo en memoria, no toca PostgreSQL)."""

    def estadisticas(self, tenant_id: str = "") -> dict:
        with conexion() as conn:
            cur = conn.cursor()
            if tenant_id:
                cur.execute("SELECT COUNT(*) FROM wa_contactos WHERE tenant_id = %s", (tenant_id,))
                contactos = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM wa_conversaciones WHERE tenant_id = %s", (tenant_id,))
                convs = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM wa_mensajes WHERE tenant_id = %s", (tenant_id,))
                msgs = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM wa_mensajes WHERE tenant_id = %s AND direccion = 'outbound'", (tenant_id,))
                enviados = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM wa_mensajes WHERE tenant_id = %s AND direccion = 'inbound'", (tenant_id,))
                recibidos = cur.fetchone()[0]
            else:
                cur.execute("SELECT COUNT(*) FROM wa_contactos")
                contactos = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM wa_conversaciones")
                convs = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM wa_mensajes")
                msgs = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM wa_mensajes WHERE direccion = 'outbound'")
                enviados = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM wa_mensajes WHERE direccion = 'inbound'")
                recibidos = cur.fetchone()[0]
            cur.close()
            return {
                "tenants": len(self.listar_tenants()),
                "contactos": contactos,
                "conversaciones": convs,
                "mensajes": msgs,
                "mensajes_enviados": enviados,
                "mensajes_recibidos": recibidos,
            }

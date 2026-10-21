"""
Servicio de WhatsApp: orquesta el envío, la recepción y el seguimiento
de mensajes. Es la capa que usan los adaptadores (insolvencia, etc.).

Patrón: como email/api.py — sin credenciales devuelve "no_configurado"
en vez de fallar. Con credenciales, envía de verdad.

Funcionalidades:
- enviar_texto: mensaje libre (ventana de 24h).
- enviar_plantilla: mensaje proactivo con plantilla aprobada.
- enviar_documento: envía un PDF/documento por URL.
- enviar_interactivo: botones o lista.
- procesar_webhook: procesa mensajes entrantes y actualizaciones de estado.
- opt_in / opt_out: gestión de consentimiento.
- obtener_conversacion: historial de mensajes con un contacto.
"""
from __future__ import annotations

import contextlib
import uuid
from datetime import UTC, datetime

from comunicaciones.whatsapp.almacen import AlmacenWhatsApp
from comunicaciones.whatsapp.cliente import ClienteWhatsApp, ErrorWhatsApp
from comunicaciones.whatsapp.config import ConfigWhatsApp
from comunicaciones.whatsapp.modelos import (
    Contacto,
    Conversacion,
    Direccion,
    EstadoEntrega,
    Mensaje,
    OptIn,
    TipoMensaje,
)


class ServicioWhatsApp:
    """Servicio principal del módulo de WhatsApp."""

    def __init__(self, config: ConfigWhatsApp, almacen: AlmacenWhatsApp | None = None):
        self.config = config
        self.cliente = ClienteWhatsApp(config)
        self.almacen = almacen or AlmacenWhatsApp()

        # Registrar el tenant en el almacén
        from comunicaciones.whatsapp.modelos import Tenant

        tenant = Tenant(
            id=config.tenant_id,
            nombre=config.nombre_negocio,
            config=config,
        )
        self.almacen.registrar_tenant(tenant)

    def activado(self) -> bool:
        return self.config.activado()

    # ── Envío ──

    def enviar_texto(self, telefono: str, texto: str, nombre_contacto: str = "") -> dict:
        """Envía un mensaje de texto libre."""
        if not self.activado():
            return {"enviado": False, "estado": "no_configurado", "telefono": telefono}

        if not telefono:
            return {"enviado": False, "estado": "sin_telefono", "telefono": ""}

        contacto = self.almacen.obtener_o_crear_contacto(
            self.config.tenant_id, telefono, nombre_contacto
        )

        if contacto.opt_in == OptIn.RECHAZADO:
            return {"enviado": False, "estado": "opt_out", "telefono": telefono}

        conv = self.almacen.obtener_o_crear_conversacion(self.config.tenant_id, telefono)

        mensaje = Mensaje(
            id=str(uuid.uuid4()),
            conversacion_id=conv.id,
            tenant_id=self.config.tenant_id,
            direccion=Direccion.ENVIADO,
            tipo=TipoMensaje.TEXTO,
            contenido=texto,
        )

        try:
            resultado = self.cliente.enviar_texto(telefono, texto)
            wa_id = resultado.get("messages", [{}])[0].get("id", "")
            if wa_id:
                mensaje.id = wa_id
            mensaje.estado = EstadoEntrega.ENVIADO
            self.almacen.guardar_mensaje(mensaje)
            contacto.fecha_ultimo_mensaje = datetime.now(UTC)
            return {
                "enviado": True,
                "estado": "enviado",
                "telefono": telefono,
                "message_id": mensaje.id,
                "resultado_api": resultado,
            }
        except ErrorWhatsApp as e:
            mensaje.marcar_fallido(e.codigo, e.mensaje)
            self.almacen.guardar_mensaje(mensaje)
            return {
                "enviado": False,
                "estado": "error",
                "telefono": telefono,
                "error_codigo": e.codigo,
                "error_mensaje": e.mensaje,
            }

    def enviar_plantilla(
        self,
        telefono: str,
        nombre_plantilla: str,
        componentes: list[dict] | None = None,
        nombre_contacto: str = "",
    ) -> dict:
        """Envía un mensaje con plantilla aprobada (proactivo)."""
        if not self.activado():
            return {"enviado": False, "estado": "no_configurado", "telefono": telefono}

        if not telefono:
            return {"enviado": False, "estado": "sin_telefono", "telefono": ""}

        contacto = self.almacen.obtener_o_crear_contacto(
            self.config.tenant_id, telefono, nombre_contacto
        )

        if contacto.opt_in == OptIn.RECHAZADO:
            return {"enviado": False, "estado": "opt_out", "telefono": telefono}

        conv = self.almacen.obtener_o_crear_conversacion(self.config.tenant_id, telefono)

        mensaje = Mensaje(
            id=str(uuid.uuid4()),
            conversacion_id=conv.id,
            tenant_id=self.config.tenant_id,
            direccion=Direccion.ENVIADO,
            tipo=TipoMensaje.PLANTILLA,
            plantilla_nombre=nombre_plantilla,
        )

        try:
            resultado = self.cliente.enviar_plantilla(
                telefono, nombre_plantilla, "es", componentes
            )
            wa_id = resultado.get("messages", [{}])[0].get("id", "")
            if wa_id:
                mensaje.id = wa_id
            mensaje.estado = EstadoEntrega.ENVIADO
            self.almacen.guardar_mensaje(mensaje)
            contacto.fecha_ultimo_mensaje = datetime.now(UTC)
            return {
                "enviado": True,
                "estado": "enviado",
                "telefono": telefono,
                "message_id": mensaje.id,
                "plantilla": nombre_plantilla,
            }
        except ErrorWhatsApp as e:
            mensaje.marcar_fallido(e.codigo, e.mensaje)
            self.almacen.guardar_mensaje(mensaje)
            return {
                "enviado": False,
                "estado": "error",
                "telefono": telefono,
                "error_codigo": e.codigo,
                "error_mensaje": e.mensaje,
            }

    def enviar_documento(
        self,
        telefono: str,
        url_documento: str,
        nombre_archivo: str = "documento.pdf",
        caption: str = "",
        nombre_contacto: str = "",
    ) -> dict:
        """Envía un documento (PDF) por URL pública."""
        if not self.activado():
            return {"enviado": False, "estado": "no_configurado", "telefono": telefono}

        if not telefono or not url_documento:
            return {"enviado": False, "estado": "sin_datos", "telefono": telefono}

        contacto = self.almacen.obtener_o_crear_contacto(
            self.config.tenant_id, telefono, nombre_contacto
        )

        if contacto.opt_in == OptIn.RECHAZADO:
            return {"enviado": False, "estado": "opt_out", "telefono": telefono}

        conv = self.almacen.obtener_o_crear_conversacion(self.config.tenant_id, telefono)

        mensaje = Mensaje(
            id=str(uuid.uuid4()),
            conversacion_id=conv.id,
            tenant_id=self.config.tenant_id,
            direccion=Direccion.ENVIADO,
            tipo=TipoMensaje.DOCUMENTO,
            contenido=caption,
            media_url=url_documento,
        )

        try:
            resultado = self.cliente.enviar_documento(telefono, url_documento, nombre_archivo, caption)
            wa_id = resultado.get("messages", [{}])[0].get("id", "")
            if wa_id:
                mensaje.id = wa_id
            mensaje.estado = EstadoEntrega.ENVIADO
            self.almacen.guardar_mensaje(mensaje)
            return {
                "enviado": True,
                "estado": "enviado",
                "telefono": telefono,
                "message_id": mensaje.id,
                "archivo": nombre_archivo,
            }
        except ErrorWhatsApp as e:
            mensaje.marcar_fallido(e.codigo, e.mensaje)
            self.almacen.guardar_mensaje(mensaje)
            return {
                "enviado": False,
                "estado": "error",
                "telefono": telefono,
                "error_codigo": e.codigo,
                "error_mensaje": e.mensaje,
            }

    def enviar_interactivo_botones(
        self,
        telefono: str,
        texto: str,
        botones: list[dict],
        nombre_contacto: str = "",
    ) -> dict:
        """Envía un mensaje con botones de respuesta rápida (máx 3)."""
        if not self.activado():
            return {"enviado": False, "estado": "no_configurado", "telefono": telefono}

        if not telefono:
            return {"enviado": False, "estado": "sin_telefono", "telefono": ""}

        contacto = self.almacen.obtener_o_crear_contacto(
            self.config.tenant_id, telefono, nombre_contacto
        )

        if contacto.opt_in == OptIn.RECHAZADO:
            return {"enviado": False, "estado": "opt_out", "telefono": telefono}

        conv = self.almacen.obtener_o_crear_conversacion(self.config.tenant_id, telefono)

        mensaje = Mensaje(
            id=str(uuid.uuid4()),
            conversacion_id=conv.id,
            tenant_id=self.config.tenant_id,
            direccion=Direccion.ENVIADO,
            tipo=TipoMensaje.INTERACTIVO,
            contenido=texto,
        )

        try:
            resultado = self.cliente.enviar_interactivo_botones(telefono, texto, botones)
            wa_id = resultado.get("messages", [{}])[0].get("id", "")
            if wa_id:
                mensaje.id = wa_id
            mensaje.estado = EstadoEntrega.ENVIADO
            self.almacen.guardar_mensaje(mensaje)
            return {
                "enviado": True,
                "estado": "enviado",
                "telefono": telefono,
                "message_id": mensaje.id,
            }
        except ErrorWhatsApp as e:
            mensaje.marcar_fallido(e.codigo, e.mensaje)
            self.almacen.guardar_mensaje(mensaje)
            return {
                "enviado": False,
                "estado": "error",
                "telefono": telefono,
                "error_codigo": e.codigo,
                "error_mensaje": e.mensaje,
            }

    # ── Recepción ──

    def procesar_webhook(self, payload: dict) -> dict:
        """Procesa un webhook entrante de Meta (mensajes + estados).

        Devuelve un resumen de lo procesado.
        """
        resultado = {
            "mensajes_procesados": 0,
            "estados_actualizados": 0,
            "errores": [],
        }

        try:
            entries = payload.get("entry", [])
            for entry in entries:
                changes = entry.get("changes", [])
                for change in changes:
                    value = change.get("value", {})
                    # Mensajes entrantes
                    for msg in value.get("messages", []):
                        self._procesar_mensaje_entrante(msg, value)
                        resultado["mensajes_procesados"] += 1

                    # Actualizaciones de estado
                    for status in value.get("statuses", []):
                        self._procesar_estado(status)
                        resultado["estados_actualizados"] += 1

                    # Contactos (nombres)
                    for contact in value.get("contacts", []):
                        telefono = contact.get("wa_id", "")
                        nombre = contact.get("profile", {}).get("name", "")
                        if telefono:
                            self.almacen.obtener_o_crear_contacto(
                                self.config.tenant_id, telefono, nombre
                            )

        except Exception as e:  # noqa: BLE001
            resultado["errores"].append(str(e))

        return resultado

    def _procesar_mensaje_entrante(self, msg: dict, value: dict) -> None:
        """Procesa un mensaje entrante individual."""
        telefono = msg.get("from", "")
        msg_id = msg.get("id", "")
        msg_type = msg.get("type", "text")
        msg.get("timestamp", "")

        contacto = self.almacen.obtener_o_crear_contacto(self.config.tenant_id, telefono)
        contacto.fecha_ultimo_mensaje = datetime.now(UTC)
        conv = self.almacen.obtener_o_crear_conversacion(self.config.tenant_id, telefono)

        # Extraer contenido según tipo
        contenido = ""
        media_url = ""
        if msg_type == "text":
            contenido = msg.get("text", {}).get("body", "")
        elif msg_type == "image":
            media_url = msg.get("image", {}).get("id", "")
            contenido = msg.get("image", {}).get("caption", "")
        elif msg_type == "document":
            media_url = msg.get("document", {}).get("id", "")
            contenido = msg.get("document", {}).get("filename", "")
        elif msg_type == "audio":
            media_url = msg.get("audio", {}).get("id", "")
        elif msg_type == "video":
            media_url = msg.get("video", {}).get("id", "")
            contenido = msg.get("video", {}).get("caption", "")
        elif msg_type == "location":
            loc = msg.get("location", {})
            contenido = f"{loc.get('latitude')},{loc.get('longitude')}"
        elif msg_type == "interactive":
            inter = msg.get("interactive", {})
            if inter.get("type") == "button_reply":
                contenido = inter.get("button_reply", {}).get("title", "")
            elif inter.get("type") == "list_reply":
                contenido = inter.get("list_reply", {}).get("title", "")

        tipo_map = {
            "text": TipoMensaje.TEXTO,
            "image": TipoMensaje.IMAGEN,
            "document": TipoMensaje.DOCUMENTO,
            "audio": TipoMensaje.AUDIO,
            "video": TipoMensaje.VIDEO,
            "location": TipoMensaje.UBICACION,
            "interactive": TipoMensaje.INTERACTIVO,
        }

        mensaje = Mensaje(
            id=msg_id,
            conversacion_id=conv.id,
            tenant_id=self.config.tenant_id,
            direccion=Direccion.RECIBIDO,
            tipo=tipo_map.get(msg_type, TipoMensaje.TEXTO),
            contenido=contenido,
            media_url=media_url,
            estado=EstadoEntrega.ENTREGADO,
        )
        self.almacen.guardar_mensaje(mensaje)

        # Marcar como leído automáticamente
        with contextlib.suppress(Exception):
            self.cliente.marcar_leido(msg_id)

    def _procesar_estado(self, status: dict) -> None:
        """Procesa una actualización de estado de entrega."""
        msg_id = status.get("id", "")
        estado = status.get("status", "")
        if estado in ("delivered", "read", "failed"):
            self.almacen.actualizar_estado_mensaje(msg_id, estado)

    # ── Opt-in / Opt-out ──

    def registrar_opt_in(self, telefono: str, nombre: str = "") -> Contacto:
        """Registra el consentimiento del ciudadano para recibir mensajes."""
        contacto = self.almacen.obtener_o_crear_contacto(
            self.config.tenant_id, telefono, nombre
        )
        contacto.aceptar_opt_in()
        return contacto

    def registrar_opt_out(self, telefono: str) -> Contacto | None:
        """Registra que el ciudadano no quiere recibir más mensajes."""
        contacto = self.almacen.obtener_o_crear_contacto(self.config.tenant_id, telefono)
        contacto.rechazar_opt_in()
        return contacto

    def tiene_opt_in(self, telefono: str) -> bool:
        contacto = self.almacen.obtener_contacto(self.config.tenant_id, telefono)
        return contacto is not None and contacto.opt_in == OptIn.ACEPTADO

    # ── Consultas ──

    def obtener_conversacion(self, telefono: str) -> Conversacion | None:
        return self.almacen.obtener_conversacion(self.config.tenant_id, telefono)

    def listar_conversaciones(self) -> list[Conversacion]:
        return self.almacen.listar_conversaciones(self.config.tenant_id)

    def obtener_historial(self, telefono: str, limite: int = 50) -> list[Mensaje]:
        conv = self.almacen.obtener_conversacion(self.config.tenant_id, telefono)
        if not conv:
            return []
        return conv.mensajes[-limite:]

    def estadisticas(self) -> dict:
        return self.almacen.estadisticas(self.config.tenant_id)

    # ── Verificación de webhook ──

    def verificar_webhook(self, mode: str, token: str, challenge: str) -> str | None:
        """Verifica el webhook de Meta (GET). Devuelve el challenge si es válido."""
        if mode == "subscribe" and token == self.config.webhook_verify_token:
            return challenge
        return None

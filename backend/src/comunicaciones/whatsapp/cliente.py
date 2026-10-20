"""
Cliente HTTP de la WhatsApp Cloud API de Meta.

Usa urllib (stdlib) siguiendo el patrón del proyecto (email/api.py,
radar_normativo/vigilancia.py). Sin dependencias externas.

Operaciones:
- enviar_texto: mensaje de texto libre (solo dentro de ventana de 24h).
- enviar_plantilla: mensaje con plantilla aprobada (proactivo).
- enviar_documento: envía un documento (PDF, etc.) por URL pública.
- subir_media: sube un archivo a Meta y devuelve media_id.
- marcar_leido: marca un mensaje entrante como leído.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from comunicaciones.whatsapp.config import ConfigWhatsApp


class ErrorWhatsApp(Exception):
    """Error de la API de WhatsApp."""

    def __init__(self, codigo: str, mensaje: str, status_http: int = 0):
        super().__init__(f"[{codigo}] {mensaje}")
        self.codigo = codigo
        self.mensaje = mensaje
        self.status_http = status_http


class ClienteWhatsApp:
    """Cliente de la Cloud API de Meta."""

    def __init__(self, config: ConfigWhatsApp):
        self.config = config

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.access_token}",
            "Content-Type": "application/json",
        }

    def _post(self, url: str, payload: dict) -> dict:
        """POST genérico. Devuelve el JSON de respuesta o lanza ErrorWhatsApp."""
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=self._headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_segundos) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            cuerpo = e.read().decode("utf-8", errors="replace")
            try:
                err = json.loads(cuerpo).get("error", {})
                raise ErrorWhatsApp(
                    codigo=str(err.get("code", e.code)),
                    mensaje=err.get("message", cuerpo),
                    status_http=e.code,
                )
            except (json.JSONDecodeError, AttributeError):
                raise ErrorWhatsApp(codigo=str(e.code), mensaje=cuerpo, status_http=e.code) from None
        except urllib.error.URLError as e:
            raise ErrorWhatsApp(codigo="NETWORK", mensaje=str(e.reason)) from None

    def _get(self, url: str) -> dict:
        req = urllib.request.Request(url, headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_segundos) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            cuerpo = e.read().decode("utf-8", errors="replace")
            raise ErrorWhatsApp(codigo=str(e.code), mensaje=cuerpo, status_http=e.code) from None

    # ── Envío de mensajes ──

    def enviar_texto(self, telefono: str, texto: str) -> dict:
        """Envía un mensaje de texto libre (solo dentro de ventana de 24h)."""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": telefono,
            "type": "text",
            "text": {"body": texto, "preview_url": False},
        }
        return self._post(self.config.url_mensajes, payload)

    def enviar_plantilla(
        self,
        telefono: str,
        nombre_plantilla: str,
        idioma: str = "es",
        componentes: list[dict] | None = None,
    ) -> dict:
        """Envía un mensaje con plantilla aprobada (proactivo, fuera de ventana)."""
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": telefono,
            "type": "template",
            "template": {
                "name": nombre_plantilla,
                "language": {"code": idioma},
            },
        }
        if componentes:
            payload["template"]["components"] = componentes
        return self._post(self.config.url_mensajes, payload)

    def enviar_documento(
        self,
        telefono: str,
        url_documento: str,
        nombre_archivo: str = "documento.pdf",
        caption: str = "",
    ) -> dict:
        """Envía un documento por URL pública (debe ser accesible por Meta)."""
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": telefono,
            "type": "document",
            "document": {
                "link": url_documento,
                "filename": nombre_archivo,
            },
        }
        if caption:
            payload["document"]["caption"] = caption
        return self._post(self.config.url_mensajes, payload)

    def enviar_imagen(self, telefono: str, url_imagen: str, caption: str = "") -> dict:
        """Envía una imagen por URL pública."""
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": telefono,
            "type": "image",
            "image": {"link": url_imagen},
        }
        if caption:
            payload["image"]["caption"] = caption
        return self._post(self.config.url_mensajes, payload)

    def enviar_interactivo_botones(
        self,
        telefono: str,
        texto_cuerpo: str,
        botones: list[dict],
        texto_pie: str = "",
    ) -> dict:
        """Envía un mensaje interactivo con botones de respuesta rápida (máx 3)."""
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": telefono,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": texto_cuerpo},
                "action": {"buttons": botones},
            },
        }
        if texto_pie:
            payload["interactive"]["footer"] = {"text": texto_pie}
        return self._post(self.config.url_mensajes, payload)

    def enviar_interactivo_lista(
        self,
        telefono: str,
        texto_cuerpo: str,
        titulo_boton: str,
        secciones: list[dict],
        texto_pie: str = "",
    ) -> dict:
        """Envía un mensaje interactivo con lista de opciones."""
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": telefono,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": texto_cuerpo},
                "action": {"button": titulo_boton, "sections": secciones},
            },
        }
        if texto_pie:
            payload["interactive"]["footer"] = {"text": texto_pie}
        return self._post(self.config.url_mensajes, payload)

    def marcar_leido(self, message_id: str) -> dict:
        """Marca un mensaje entrante como leído."""
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        return self._post(self.config.url_mensajes, payload)

    def subir_media(self, archivo_bytes: bytes, tipo_mime: str, nombre: str) -> str:
        """Sube un archivo a Meta y devuelve el media_id."""
        boundary = "----WhatsAppBoundary"
        body_parts = []
        body_parts.append(f"--{boundary}")
        body_parts.append(f'Content-Disposition: form-data; name="file"; filename="{nombre}"')
        body_parts.append(f"Content-Type: {tipo_mime}")
        body_parts.append("")
        body_parts.append("")  # placeholder for binary

        # Construir body multipart manualmente
        data = b""
        data += f"--{boundary}\r\n".encode()
        data += f'Content-Disposition: form-data; name="file"; filename="{nombre}"\r\n'.encode()
        data += f"Content-Type: {tipo_mime}\r\n\r\n".encode()
        data += archivo_bytes
        data += f"\r\n--{boundary}\r\n".encode()
        data += b'Content-Disposition: form-data; name="messaging_product"\r\n\r\n'
        data += b"whatsapp\r\n"
        data += f"--{boundary}--\r\n".encode()

        req = urllib.request.Request(
            self.config.url_media,
            data=data,
            headers={
                "Authorization": f"Bearer {self.config.access_token}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_segundos) as resp:
                resultado = json.loads(resp.read().decode("utf-8"))
                return resultado.get("id", "")
        except urllib.error.HTTPError as e:
            cuerpo = e.read().decode("utf-8", errors="replace")
            raise ErrorWhatsApp(codigo=str(e.code), mensaje=cuerpo, status_http=e.code) from None

    def enviar_media_id(
        self,
        telefono: str,
        media_id: str,
        tipo: str = "document",
        nombre_archivo: str = "documento.pdf",
        caption: str = "",
    ) -> dict:
        """Envía un archivo ya subido a Meta (por media_id)."""
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": telefono,
            "type": tipo,
            tipo: {"id": media_id},
        }
        if tipo == "document":
            payload[tipo]["filename"] = nombre_archivo
        if caption:
            payload[tipo]["caption"] = caption
        return self._post(self.config.url_mensajes, payload)

    def obtener_perfil(self, telefono: str) -> dict:
        """Obtiene el perfil público de un número (nombre, foto)."""
        url = f"{self.config.api_base}/{telefono}"
        return self._get(url)

    def listar_plantillas(self) -> list[dict]:
        """Lista las plantillas aprobadas de la cuenta de WhatsApp Business."""
        url = (
            f"{self.config.api_base}/{self.config.business_account_id}"
            "/message_templates?limit=100"
        )
        resultado = self._get(url)
        return resultado.get("data", [])

"""
Router FastAPI para el webhook de WhatsApp.

Endpoints:
- GET  /api/v1/whatsapp/webhook  → verificación de Meta (hub.challenge).
- POST /api/v1/whatsapp/webhook  → recepción de mensajes y estados.
- POST /api/v1/whatsapp/enviar    → envío manual (para pruebas y el portal).
- GET  /api/v1/whatsapp/conversaciones → listado de conversaciones.
- GET  /api/v1/whatsapp/conversacion/{telefono} → historial.
- POST /api/v1/whatsapp/opt-in    → registrar consentimiento.
- POST /api/v1/whatsapp/opt-out   → cancelar suscripción.
- GET  /api/v1/whatsapp/estado    → estado del módulo.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from comunicaciones.whatsapp.servicio import ServicioWhatsApp

# Instancia global del servicio (se inicializa al arrancar la app)
_servicio: ServicioWhatsApp | None = None


def inicializar_servicio(servicio: ServicioWhatsApp) -> None:
    """Inicializa el servicio global del módulo."""
    global _servicio
    _servicio = servicio


def obtener_servicio() -> ServicioWhatsApp:
    if _servicio is None:
        raise HTTPException(status_code=503, detail="Módulo de WhatsApp no inicializado")
    return _servicio


router = APIRouter(prefix="/api/v1/whatsapp", tags=["whatsapp"])


@router.get("/webhook")
async def verificar_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """Verificación del webhook por Meta (GET con hub.challenge)."""
    servicio = obtener_servicio()
    resultado = servicio.verificar_webhook(hub_mode or "", hub_verify_token or "", hub_challenge or "")
    if resultado is None:
        raise HTTPException(status_code=403, detail="Verificación fallida")
    return int(resultado) if resultado.isdigit() else resultado


@router.post("/webhook")
async def recibir_webhook(request: Request):
    """Recepción de mensajes y estados de entrega."""
    servicio = obtener_servicio()
    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Payload inválido") from None
    resultado = servicio.procesar_webhook(payload)
    return {"ok": True, "procesado": resultado}


@router.get("/estado")
def estado_modulo():
    """Estado del módulo (activado, estadísticas)."""
    servicio = obtener_servicio()
    return {
        "activado": servicio.activado(),
        "tenant": servicio.config.tenant_id,
        "nombre_negocio": servicio.config.nombre_negocio,
        "estadisticas": servicio.estadisticas(),
    }


@router.post("/enviar/texto")
def enviar_texto(telefono: str, texto: str, nombre_contacto: str = ""):
    servicio = obtener_servicio()
    return servicio.enviar_texto(telefono, texto, nombre_contacto)


@router.post("/enviar/plantilla")
def enviar_plantilla(
    telefono: str,
    nombre_plantilla: str,
    componentes: str = "",
    nombre_contacto: str = "",
):
    import json as _json

    comps = _json.loads(componentes) if componentes else None
    servicio = obtener_servicio()
    return servicio.enviar_plantilla(telefono, nombre_plantilla, comps, nombre_contacto)


@router.post("/enviar/documento")
def enviar_documento(
    telefono: str,
    url_documento: str,
    nombre_archivo: str = "documento.pdf",
    caption: str = "",
    nombre_contacto: str = "",
):
    servicio = obtener_servicio()
    return servicio.enviar_documento(telefono, url_documento, nombre_archivo, caption, nombre_contacto)


@router.get("/conversaciones")
def listar_conversaciones():
    servicio = obtener_servicio()
    convs = servicio.listar_conversaciones()
    return {
        "conversaciones": [
            {
                "id": c.id,
                "telefono": c.contacto_telefono,
                "mensajes": c.cantidad_mensajes,
                "ultimo_mensaje": c.ultimo_mensaje.contenido if c.ultimo_mensaje else None,
                "fecha_ultimo": c.fecha_ultimo_mensaje.isoformat() if c.fecha_ultimo_mensaje else None,
                "abierta": c.abierta,
            }
            for c in convs
        ]
    }


@router.get("/conversacion/{telefono}")
def obtener_conversacion(telefono: str, limite: int = 50):
    servicio = obtener_servicio()
    mensajes = servicio.obtener_historial(telefono, limite)
    return {
        "telefono": telefono,
        "mensajes": [
            {
                "id": m.id,
                "direccion": m.direccion.value,
                "tipo": m.tipo.value,
                "contenido": m.contenido,
                "estado": m.estado.value,
                "fecha": m.fecha_envio.isoformat(),
            }
            for m in mensajes
        ],
    }


@router.post("/opt-in")
def registrar_opt_in(telefono: str, nombre: str = ""):
    servicio = obtener_servicio()
    contacto = servicio.registrar_opt_in(telefono, nombre)
    return {
        "telefono": telefono,
        "opt_in": contacto.opt_in.value,
        "fecha": contacto.fecha_opt_in.isoformat() if contacto.fecha_opt_in else None,
    }


@router.post("/opt-out")
def registrar_opt_out(telefono: str):
    servicio = obtener_servicio()
    contacto = servicio.registrar_opt_out(telefono)
    if contacto is None:
        return {"telefono": telefono, "estado": "no_encontrado"}
    return {"telefono": telefono, "opt_in": contacto.opt_in.value}

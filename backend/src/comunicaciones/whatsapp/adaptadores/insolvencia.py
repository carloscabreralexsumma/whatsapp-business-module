"""
Adaptador del módulo de WhatsApp para la plataforma de Insolvencia Colombia.

Define las plantillas de mensajes específicas del dominio de insolvencia
y las funciones de disparo (triggers) que envían mensajes cuando el estado
del caso cambia.

Plantillas (deben aprobarse en Meta antes de usarlas en producción):
- insolvencia_bienvenida: cuando el ciudadano califica.
- insolvencia_documento_listo: cuando el documento queda preparado.
- insolvencia_recordatorio_documentos: recordatorio de documentos pendientes.
- insolvencia_cita_centro: fecha de cita en el centro de conciliación.
- insolvencia_acuerdo_logrado: cuando se logra un acuerdo.
- insolvencia_paquete_oferta: oferta del paquete completo ($19.900).
- insolvencia_paquete_entregado: confirmación de entrega del paquete.

Cada plantilla se registra en el almacén al inicializar el adaptador.
"""
from __future__ import annotations

from comunicaciones.whatsapp.modelos import Plantilla
from comunicaciones.whatsapp.servicio import ServicioWhatsApp

PLANTILLAS_INSOLVENCIA = [
    Plantilla(
        nombre="insolvencia_bienvenida",
        idioma="es",
        categoria="UTILITY",
        estado="APPROVED",
        componentes=[
            {"type": "BODY", "text": "Hola {{1}}, gracias por usar Insolvencia Colombia. Tu caso fue registrado y está en clasificación. Te avisaremos cuando tengamos novedades."},
            {"type": "FOOTER", "text": "Insolvencia Colombia — Trámite gratuito en centros de conciliación (art. 535 CGP)"},
        ],
    ),
    Plantilla(
        nombre="insolvencia_documento_listo",
        idioma="es",
        categoria="UTILITY",
        estado="APPROVED",
        componentes=[
            {"type": "BODY", "text": "Hola {{1}}, tu documento de insolvencia está preparado con tus datos. Recuerda: le falta la firma de un abogado para poder radicarlo. Puedes descargarlo aquí: {{2}}"},
            {"type": "FOOTER", "text": "El trámite en el centro de conciliación es gratuito (art. 535 CGP)"},
        ],
    ),
    Plantilla(
        nombre="insolvencia_recordatorio_documentos",
        idioma="es",
        categoria="UTILITY",
        estado="APPROVED",
        componentes=[
            {"type": "BODY", "text": "Hola {{1}}, aún faltan algunos documentos para completar tu solicitud: {{2}}. ¿Necesitas ayuda para conseguirlos?"},
        ],
    ),
    Plantilla(
        nombre="insolvencia_cita_centro",
        idioma="es",
        categoria="UTILITY",
        estado="APPROVED",
        componentes=[
            {"type": "BODY", "text": "Hola {{1}}, tu cita en el centro de conciliación {{2}} está programada para el {{3}}. Lleva tu documento de identidad y los documentos que te indicamos."},
        ],
    ),
    Plantilla(
        nombre="insolvencia_acuerdo_logrado",
        idioma="es",
        categoria="UTILITY",
        estado="APPROVED",
        componentes=[
            {"type": "BODY", "text": "Hola {{1}}, ¡buenas noticias! Se logró un acuerdo en tu proceso de insolvencia. Revisa los detalles: {{2}}"},
        ],
    ),
    Plantilla(
        nombre="insolvencia_paquete_oferta",
        idioma="es",
        categoria="MARKETING",
        estado="APPROVED",
        componentes=[
            {"type": "BODY", "text": "Hola {{1}}, tu documento está preparado. Por $19.900 te enviamos el paquete completo: el documento con tus datos, el paso a paso para conseguir la firma del abogado y radicar, y la orientación para tu caso. ¿Te interesa? Responde SI para más información."},
            {"type": "FOOTER", "text": "El trámite en el centro de conciliación es gratuito (art. 535 CGP)"},
        ],
    ),
    Plantilla(
        nombre="insolvencia_paquete_entregado",
        idioma="es",
        categoria="UTILITY",
        estado="APPROVED",
        componentes=[
            {"type": "BODY", "text": "Hola {{1}}, tu paquete completo fue enviado a tu correo. Incluye: el documento preparado, el paso a paso para conseguir la firma del abogado y radicar, y la orientación para tu caso. ¿Tienes alguna pregunta?"},
        ],
    ),
]


def registrar_plantillas(servicio: ServicioWhatsApp) -> None:
    for plantilla in PLANTILLAS_INSOLVENCIA:
        plantilla.tenant_id = servicio.config.tenant_id
        servicio.almacen.registrar_plantilla(plantilla)


def notificar_bienvenida(servicio, telefono, nombre):
    return servicio.enviar_plantilla(telefono=telefono, nombre_plantilla="insolvencia_bienvenida",
        componentes=[{"type": "body", "parameters": [{"type": "text", "text": nombre}]}], nombre_contacto=nombre)

def notificar_documento_listo(servicio, telefono, nombre, url_pdf):
    return servicio.enviar_plantilla(telefono=telefono, nombre_plantilla="insolvencia_documento_listo",
        componentes=[{"type": "body", "parameters": [{"type": "text", "text": nombre}, {"type": "text", "text": url_pdf}]}], nombre_contacto=nombre)

def notificar_recordatorio_documentos(servicio, telefono, nombre, documentos_faltantes):
    return servicio.enviar_plantilla(telefono=telefono, nombre_plantilla="insolvencia_recordatorio_documentos",
        componentes=[{"type": "body", "parameters": [{"type": "text", "text": nombre}, {"type": "text", "text": documentos_faltantes}]}], nombre_contacto=nombre)

def notificar_cita_centro(servicio, telefono, nombre, centro, fecha):
    return servicio.enviar_plantilla(telefono=telefono, nombre_plantilla="insolvencia_cita_centro",
        componentes=[{"type": "body", "parameters": [{"type": "text", "text": nombre}, {"type": "text", "text": centro}, {"type": "text", "text": fecha}]}], nombre_contacto=nombre)

def notificar_acuerdo_logrado(servicio, telefono, nombre, detalles):
    return servicio.enviar_plantilla(telefono=telefono, nombre_plantilla="insolvencia_acuerdo_logrado",
        componentes=[{"type": "body", "parameters": [{"type": "text", "text": nombre}, {"type": "text", "text": detalles}]}], nombre_contacto=nombre)

def notificar_paquete_oferta(servicio, telefono, nombre):
    return servicio.enviar_plantilla(telefono=telefono, nombre_plantilla="insolvencia_paquete_oferta",
        componentes=[{"type": "body", "parameters": [{"type": "text", "text": nombre}]}], nombre_contacto=nombre)

def notificar_paquete_entregado(servicio, telefono, nombre):
    return servicio.enviar_plantilla(telefono=telefono, nombre_plantilla="insolvencia_paquete_entregado",
        componentes=[{"type": "body", "parameters": [{"type": "text", "text": nombre}]}], nombre_contacto=nombre)

def enviar_paquete_whatsapp(servicio, telefono, nombre, url_pdf):
    return servicio.enviar_documento(telefono=telefono, url_documento=url_pdf, nombre_archivo="solicitud_insolvencia.pdf",
        caption=f"Hola {nombre}, aquí está tu documento preparado.", nombre_contacto=nombre)

def enviar_mensaje_personalizado(servicio, telefono, texto, nombre=""):
    return servicio.enviar_texto(telefono, texto, nombre)

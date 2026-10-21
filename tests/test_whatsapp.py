"""
Pruebas del módulo de WhatsApp Business Cloud API.

Prueban:
- Configuración (activado/desactivado).
- Modelos (contacto, mensaje, conversación, plantilla, tenant).
- Almacén (CRUD en memoria).
- Servicio (envío sin credenciales → no_configurado; procesamiento de webhook).
- Cliente (construcción de payloads — sin red).
- Adaptador de insolvencia (plantillas registradas).
"""
from __future__ import annotations

import pytest

from comunicaciones.whatsapp.adaptadores.insolvencia import (
    PLANTILLAS_INSOLVENCIA,
    registrar_plantillas,
)
from comunicaciones.whatsapp.almacen import AlmacenWhatsApp
from comunicaciones.whatsapp.config import ConfigWhatsApp, config_desde_entorno
from comunicaciones.whatsapp.modelos import (
    Contacto,
    Conversacion,
    Direccion,
    EstadoEntrega,
    Mensaje,
    OptIn,
    Plantilla,
    Tenant,
    TipoMensaje,
)
from comunicaciones.whatsapp.servicio import ServicioWhatsApp

# ── Config ──


def test_config_desactivada_por_defecto():
    cfg = config_desde_entorno("default")
    assert cfg.activado() is False
    assert cfg.phone_number_id == ""
    assert cfg.access_token == ""


def test_config_activada_con_credenciales():
    cfg = ConfigWhatsApp(
        tenant_id="test",
        phone_number_id="123456",
        access_token="token-secreto",
        activo=True,
    )
    assert cfg.activado() is True
    assert "123456" in cfg.url_mensajes
    assert cfg.api_base == "https://graph.facebook.com/v21.0"


def test_config_sin_phone_no_activa():
    cfg = ConfigWhatsApp(access_token="token", activo=True)
    assert cfg.activado() is False


# ── Modelos ──


def test_contacto_opt_in():
    c = Contacto(telefono="573001234567", nombre="Ana")
    assert c.opt_in == OptIn.PENDIENTE
    c.aceptar_opt_in()
    assert c.opt_in == OptIn.ACEPTADO
    assert c.fecha_opt_in is not None
    c.rechazar_opt_in()
    assert c.opt_in == OptIn.RECHAZADO


def test_mensaje_marcar_estados():
    m = Mensaje(
        id="msg1",
        conversacion_id="conv1",
        tenant_id="default",
        direccion=Direccion.ENVIADO,
        tipo=TipoMensaje.TEXTO,
        contenido="hola",
    )
    assert m.estado == EstadoEntrega.PENDIENTE
    m.marcar_entregado()
    assert m.estado == EstadoEntrega.ENTREGADO
    assert m.fecha_entrega is not None
    m.marcar_leido()
    assert m.estado == EstadoEntrega.LEIDO
    assert m.fecha_lectura is not None


def test_mensaje_marcar_fallido():
    m = Mensaje(
        id="msg2",
        conversacion_id="conv1",
        tenant_id="default",
        direccion=Direccion.ENVIADO,
        tipo=TipoMensaje.TEXTO,
    )
    m.marcar_fallido("401", "no autorizado")
    assert m.estado == EstadoEntrega.FALLIDO
    assert m.error_codigo == "401"


def test_conversacion_agregar_mensajes():
    conv = Conversacion(id="c1", tenant_id="default", contacto_telefono="573001234567")
    m1 = Mensaje(id="m1", conversacion_id="c1", tenant_id="default", direccion=Direccion.ENVIADO, tipo=TipoMensaje.TEXTO, contenido="hola")
    m2 = Mensaje(id="m2", conversacion_id="c1", tenant_id="default", direccion=Direccion.RECIBIDO, tipo=TipoMensaje.TEXTO, contenido="qué tal")
    conv.agregar_mensaje(m1)
    conv.agregar_mensaje(m2)
    assert conv.cantidad_mensajes == 2
    assert conv.ultimo_mensaje.id == "m2"
    assert conv.fecha_ultimo_mensaje is not None


def test_plantilla_aprobada():
    p = Plantilla(nombre="test", estado="APPROVED")
    assert p.aprobada is True
    p2 = Plantilla(nombre="test2", estado="PENDING")
    assert p2.aprobada is False


def test_tenant_plantilla_por_nombre():
    t = Tenant(id="t1", nombre="Test")
    p = Plantilla(nombre="bienvenida", tenant_id="t1")
    t.plantillas.append(p)
    assert t.plantilla_por_nombre("bienvenida") is p
    assert t.plantilla_por_nombre("noexiste") is None


# ── Almacén ──


def test_almacen_contacto_crear_y_obtener():
    alm = AlmacenWhatsApp()
    c1 = alm.obtener_o_crear_contacto("t1", "573001234567", "Ana")
    assert c1.nombre == "Ana"
    c2 = alm.obtener_o_crear_contacto("t1", "573001234567", "Ana2")
    assert c2 is c1  # mismo objeto
    assert c2.nombre == "Ana"  # no sobrescribe


def test_almacen_conversacion():
    alm = AlmacenWhatsApp()
    conv1 = alm.obtener_o_crear_conversacion("t1", "573001234567")
    conv2 = alm.obtener_o_crear_conversacion("t1", "573001234567")
    assert conv1 is conv2
    assert conv1.id == conv2.id


def test_almacen_guardar_mensaje():
    alm = AlmacenWhatsApp()
    conv = alm.obtener_o_crear_conversacion("t1", "573001234567")
    msg = Mensaje(id="m1", conversacion_id=conv.id, tenant_id="t1", direccion=Direccion.ENVIADO, tipo=TipoMensaje.TEXTO, contenido="hola")
    alm.guardar_mensaje(msg)
    assert alm.obtener_mensaje("m1") is msg
    assert conv.cantidad_mensajes == 1


def test_almacen_plantillas():
    alm = AlmacenWhatsApp()
    p = Plantilla(nombre="bienvenida", tenant_id="t1")
    alm.registrar_plantilla(p)
    assert alm.obtener_plantilla("t1", "bienvenida") is p
    assert len(alm.listar_plantillas("t1")) == 1


def test_almacen_limpiar():
    alm = AlmacenWhatsApp()
    alm.obtener_o_crear_contacto("t1", "573001234567")
    alm.limpiar()
    assert alm.listar_contactos("t1") == []


def test_almacen_estadisticas():
    alm = AlmacenWhatsApp()
    alm.obtener_o_crear_contacto("t1", "573001234567")
    conv = alm.obtener_o_crear_conversacion("t1", "573001234567")
    msg = Mensaje(id="m1", conversacion_id=conv.id, tenant_id="t1", direccion=Direccion.ENVIADO, tipo=TipoMensaje.TEXTO)
    alm.guardar_mensaje(msg)
    stats = alm.estadisticas("t1")
    assert stats["contactos"] == 1
    assert stats["mensajes"] == 1
    assert stats["mensajes_enviados"] == 1


# ── Servicio ──


def test_servicio_desactivado():
    cfg = ConfigWhatsApp(tenant_id="test", activo=False)
    svc = ServicioWhatsApp(cfg)
    resultado = svc.enviar_texto("573001234567", "hola")
    assert resultado["enviado"] is False
    assert resultado["estado"] == "no_configurado"


def test_servicio_sin_telefono():
    cfg = ConfigWhatsApp(tenant_id="test", phone_number_id="123", access_token="tok", activo=True)
    svc = ServicioWhatsApp(cfg)
    resultado = svc.enviar_texto("", "hola")
    assert resultado["enviado"] is False
    assert resultado["estado"] == "sin_telefono"


def test_servicio_opt_out_bloquea_envio():
    cfg = ConfigWhatsApp(tenant_id="test", phone_number_id="123", access_token="tok", activo=True)
    svc = ServicioWhatsApp(cfg)
    svc.registrar_opt_out("573001234567")
    resultado = svc.enviar_texto("573001234567", "hola")
    assert resultado["enviado"] is False
    assert resultado["estado"] == "opt_out"


def test_servicio_opt_in():
    cfg = ConfigWhatsApp(tenant_id="test", phone_number_id="123", access_token="tok", activo=True)
    svc = ServicioWhatsApp(cfg)
    contacto = svc.registrar_opt_in("573001234567", "Ana")
    assert contacto.opt_in.value == "accepted"
    assert svc.tiene_opt_in("573001234567") is True
    assert svc.tiene_opt_in("579999999999") is False


def test_servicio_webhook_mensaje_entrante():
    cfg = ConfigWhatsApp(tenant_id="test", phone_number_id="123", access_token="tok", activo=True)
    svc = ServicioWhatsApp(cfg)
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "573001234567",
                                    "id": "wamid.123",
                                    "type": "text",
                                    "text": {"body": "Hola, ¿cómo va mi caso?"},
                                }
                            ],
                            "contacts": [
                                {"wa_id": "573001234567", "profile": {"name": "Ana"}}
                            ],
                        }
                    }
                ]
            }
        ]
    }
    resultado = svc.procesar_webhook(payload)
    assert resultado["mensajes_procesados"] == 1
    assert resultado["errores"] == []
    conv = svc.obtener_conversacion("573001234567")
    assert conv is not None
    assert conv.cantidad_mensajes == 1
    assert conv.mensajes[0].contenido == "Hola, ¿cómo va mi caso?"
    assert conv.mensajes[0].direccion.value == "inbound"


def test_servicio_webhook_estado_entrega():
    cfg = ConfigWhatsApp(tenant_id="test", phone_number_id="123", access_token="tok", activo=True)
    svc = ServicioWhatsApp(cfg)
    # Primero enviar un mensaje (simulado)
    conv = svc.almacen.obtener_o_crear_conversacion("test", "573001234567")
    msg = Mensaje(id="wamid.999", conversacion_id=conv.id, tenant_id="test", direccion=Direccion.ENVIADO, tipo=TipoMensaje.TEXTO)
    svc.almacen.guardar_mensaje(msg)

    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "statuses": [
                                {"id": "wamid.999", "status": "delivered"}
                            ]
                        }
                    }
                ]
            }
        ]
    }
    resultado = svc.procesar_webhook(payload)
    assert resultado["estados_actualizados"] == 1
    assert svc.almacen.obtener_mensaje("wamid.999").estado.value == "delivered"


def test_servicio_verificar_webhook():
    cfg = ConfigWhatsApp(tenant_id="test", webhook_verify_token="mi-token-secreto", activo=True)
    svc = ServicioWhatsApp(cfg)
    assert svc.verificar_webhook("subscribe", "mi-token-secreto", "challenge123") == "challenge123"
    assert svc.verificar_webhook("subscribe", "token-incorrecto", "challenge123") is None
    assert svc.verificar_webhook("otro", "mi-token-secreto", "challenge123") is None


def test_servicio_enviar_texto_sin_credenciales():
    cfg = ConfigWhatsApp(tenant_id="test", activo=False)
    svc = ServicioWhatsApp(cfg)
    resultado = svc.enviar_texto("573001234567", "hola")
    assert resultado["enviado"] is False
    assert resultado["estado"] == "no_configurado"


def test_servicio_estadisticas():
    cfg = ConfigWhatsApp(tenant_id="test", phone_number_id="123", access_token="tok", activo=True)
    svc = ServicioWhatsApp(cfg)
    svc.registrar_opt_in("573001234567", "Ana")
    stats = svc.estadisticas()
    assert stats["contactos"] == 1


# ── Adaptador de insolvencia ──


def test_plantillas_insolvencia_registradas():
    cfg = ConfigWhatsApp(tenant_id="test", phone_number_id="123", access_token="tok", activo=True)
    svc = ServicioWhatsApp(cfg)
    registrar_plantillas(svc)
    plantillas = svc.almacen.listar_plantillas("test")
    assert len(plantillas) == len(PLANTILLAS_INSOLVENCIA)
    assert len(plantillas) == 7
    nombres = [p.nombre for p in plantillas]
    assert "insolvencia_bienvenida" in nombres
    assert "insolvencia_paquete_oferta" in nombres


def test_notificar_bienvenida_sin_credenciales():
    from comunicaciones.whatsapp.adaptadores.insolvencia import notificar_bienvenida

    cfg = ConfigWhatsApp(tenant_id="test", activo=False)
    svc = ServicioWhatsApp(cfg)
    resultado = notificar_bienvenida(svc, "573001234567", "Ana")
    assert resultado["enviado"] is False
    assert resultado["estado"] == "no_configurado"


# ── Cliente (payloads sin red) ──


def test_cliente_url_mensajes():
    cfg = ConfigWhatsApp(tenant_id="test", phone_number_id="123456", access_token="tok", activo=True)
    from comunicaciones.whatsapp.cliente import ClienteWhatsApp

    cliente = ClienteWhatsApp(cfg)
    assert "123456" in cliente.config.url_mensajes
    assert cliente.config.url_mensajes.endswith("/messages")


def test_cliente_error_sin_red():
    """Verifica que el cliente lanza ErrorWhatsApp cuando no hay red."""
    from comunicaciones.whatsapp.cliente import ClienteWhatsApp, ErrorWhatsApp

    cfg = ConfigWhatsApp(tenant_id="test", phone_number_id="123456", access_token="tok", activo=True, timeout_segundos=1)
    cliente = ClienteWhatsApp(cfg)
    with pytest.raises(ErrorWhatsApp):
        cliente.enviar_texto("573001234567", "hola")

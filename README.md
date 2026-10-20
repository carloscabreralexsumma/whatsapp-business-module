# WhatsApp Business Module — White-Label

Módulo de comunicación por WhatsApp Business Cloud API. Genérico, multi-tenant,
reutilizable. Cualquier negocio puede usarlo con su propio número de WhatsApp
Business.

## Características

- **Envío de mensajes:** texto, plantillas aprobadas, documentos (PDF), imágenes, interactivos (botones y listas).
- **Recepción:** webhook de Meta para mensajes entrantes y estados de entrega.
- **Gestión de conversaciones:** historial, listado, estadísticas.
- **Opt-in/Opt-out:** consentimiento del ciudadano (Ley 1581).
- **Multi-tenant:** cada negocio tiene su propia configuración, plantillas y marca.
- **Portal de administración:** dashboard web para configurar, enviar y ver conversaciones.
- **Sin dependencias externas:** solo urllib (stdlib de Python) + FastAPI.

## Instalación

### Requisitos

- Python 3.11+
- Cuenta de WhatsApp Business en Meta (developers.facebook.com)
- Número de teléfono para WhatsApp Business

### Instalación local

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/whatsapp-business-module.git
cd whatsapp-business-module

# 2. Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales de Meta

# 5. Arrancar
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Variables de entorno

| Variable | Descripción | Ejemplo |
|---|---|---|
| `WHATSAPP_PHONE_NUMBER_ID` | ID del número de WhatsApp Business (Meta) | `123456789012345` |
| `WHATSAPP_ACCESS_TOKEN` | Token de acceso de la Cloud API | `EAAxxxxxxx...` |
| `WHATSAPP_BUSINESS_ACCOUNT_ID` | ID de la cuenta de WhatsApp Business | `123456789012345` |
| `WHATSAPP_WEBHOOK_VERIFY_TOKEN` | Token para verificar el webhook (lo eliges tú) | `mi-token-secreto` |
| `WHATSAPP_ENABLED` | Activar el módulo | `true` |
| `WHATSAPP_NOMBRE_NEGOCIO` | Nombre del negocio | `Mi Negocio` |
| `WHATSAPP_NOMBRE_REMITENTE` | Nombre que aparece como remitente | `Mi Negocio` |
| `WHATSAPP_FIRMA` | Firma al final de los mensajes | `Mi Negocio — www.minegocio.com` |
| `ENV` | Entorno | `development` o `production` |
| `PORT` | Puerto del servidor | `8000` |

### Configurar el webhook en Meta

1. Ir a developers.facebook.com → tu app → WhatsApp → Configuración.
2. En "Webhook", poner la URL: `https://tu-servidor.com/api/v1/whatsapp/webhook`
3. En "Verify Token", poner el mismo valor de `WHATSAPP_WEBHOOK_VERIFY_TOKEN`.
4. Suscribirse a los eventos: `messages`, `message_deliveries`, `message_reads`.

## Uso de la API

### Enviar texto

```
POST /api/v1/whatsapp/enviar/texto?telefono=573001234567&texto=Hola
```

### Enviar plantilla

```
POST /api/v1/whatsapp/enviar/plantilla?telefono=573001234567&nombre_plantilla=bienvenida&componentes=[{"type":"body","parameters":[{"type":"text","text":"Juan"}]}]
```

### Enviar documento (PDF)

```
POST /api/v1/whatsapp/enviar/documento?telefono=573001234567&url_documento=https://ejemplo.com/doc.pdf&nombre_archivo=documento.pdf
```

### Ver estado del módulo

```
GET /api/v1/whatsapp/estado
```

### Listar conversaciones

```
GET /api/v1/whatsapp/conversaciones
```

### Ver historial de una conversación

```
GET /api/v1/whatsapp/conversacion/573001234567
```

### Registrar consentimiento (opt-in)

```
POST /api/v1/whatsapp/opt-in?telefono=573001234567&nombre=Juan
```

## Portal de administración

Acceder a `http://tu-servidor:8000/admin/` para:
- Ver dashboard con estadísticas
- Configurar credenciales
- Ver plantillas
- Ver conversaciones y responder
- Enviar mensajes manuales
- Registrar consentimientos

## Estructura del proyecto

```
whatsapp-business-module/
├── backend/
│   ├── main.py                          # Punto de entrada
│   └── src/
│       └── comunicaciones/
│           └── whatsapp/
│               ├── __init__.py
│               ├── config.py            # Configuración por tenant
│               ├── cliente.py           # Cliente HTTP de la Cloud API
│               ├── modelos.py           # Entidades de dominio
│               ├── almacen.py           # Almacenamiento (memoria/PostgreSQL)
│               ├── servicio.py          # Lógica de negocio
│               ├── webhook.py           # Router FastAPI
│               └── adaptadores/
│                   ├── __init__.py
│                   └── insolvencia.py   # Adaptador de ejemplo (insolvencia)
├── frontend/
│   └── admin/
│       └── index.html                  # Portal de administración
├── database/
│   └── migrations/                     # Migraciones de PostgreSQL
├── tests/
│   └── test_whatsapp.py               # 28 pruebas
├── docs/
├── requirements.txt
├── .env.example
└── README.md
```

## Licencia

Propietario. Todos los derechos reservados.

## Soporte

Contacto: [tu-email@ejemplo.com]

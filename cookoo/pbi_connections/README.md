# PBI Connections

## Resumen
`pbi_connections` es un addon de Odoo 17 para centralizar la configuracion de acceso usada por Power BI y para exponer endpoints HTTP consumibles desde herramientas BI. Tambien incorpora una home administrativa, una vista de credenciales y un catalogo basico de endpoints.

## Objetivos funcionales
- Administrar el token interno usado para autenticar requests a endpoints BI.
- Mostrar una home del modulo con accesos a credenciales, endpoints y ajustes.
- Validar el estado del cliente contra un servicio externo antes de habilitar la operacion.
- Construir enlaces de instancia y soporte a partir de la key de instancia.
- Reutilizar o migrar configuracion legacy proveniente de `advanced_metrics`.

## Flujo funcional
1. El usuario entra al menu `PBI Connections`.
2. El modelo `pbi_connections.inicio` sincroniza la configuracion legacy si existe.
3. Se obtiene o crea un registro `pbi_connections.api.config`.
4. Ese registro valida el estado del cliente con el servicio externo.
5. Si la validacion es correcta, la home permite:
   - abrir credenciales Power BI;
   - ver endpoints;
   - abrir ajustes.

## Configuracion requerida
Se configura en `Ajustes > PBI Connections`.

Campos principales:
- `Key de instancia`
- `URL base de validacion`
- `Clave de cliente`
- `API Key de validacion`

Formato correcto:
- Base URL: `https://api.zoraen.com/api/production-v1-public`
- URL final: `https://api.zoraen.com/api/production-v1-public/clients/key/<client_key>`
- Soporte: `https://adm.zoraen.com/support?instance=<instance_key>`

El codigo normaliza automaticamente:
- comillas accidentales;
- URLs base mal pegadas que ya traen `/clients/key/...`.

## Modelos principales
### `pbi_connections.inicio`
Home administrativa del modulo.

Responsabilidades:
- mostrar estado general del modulo;
- reflejar el estado de validacion calculado desde `api.config`;
- abrir credenciales, endpoints, soporte, instancia y ajustes.

Archivo:
[models.py](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/pbi_connections/models/models.py)

### `pbi_connections.api.config`
Modelo central de configuracion del addon.

Responsabilidades:
- almacenar token interno de acceso;
- calcular URL segura de referencia con `token`;
- limitar cantidad maxima de registros;
- validar cliente contra servicio externo;
- construir URLs de soporte e instancia;
- migrar configuracion legacy desde tabla `advanced_metrics_api_config`.

Campos clave:
- `access_token`
- `record_limit`
- `api_url`
- `show_dashboard`
- `client_validation_state`
- `client_status_code`
- `client_status_title`
- `client_status_message`

Archivo:
[api_config.py](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/pbi_connections/models/api_config.py)

### `pbi_connections.endpoint`
Catalogo simple de endpoints.

Campos:
- `name`
- `technical_name`
- `description`
- `active`

### `res.config.settings` heredado
Configura el addon desde Ajustes y muestra vistas previas de URL final de validacion y soporte.

Archivo:
[res_config_settings.py](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/pbi_connections/models/res_config_settings.py)

## Vistas y UI
### Home del modulo
Definida en:
[views.xml](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/pbi_connections/views/views.xml)

Incluye:
- estado bloqueado con mensaje, soporte y acceso a ajustes;
- tarjeta para `Credenciales Power BI`;
- tarjeta para `Endpoints`;
- tarjeta para `Ajustes`.

### Vista de credenciales
Definida en:
[api_config_views.xml](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/pbi_connections/views/api_config_views.xml)

Incluye:
- botones de `Abrir Instancia`, `Contactar soporte`, `Settings` y `Generar Nuevo Token`;
- token de acceso;
- `record_limit`;
- `api_url` readonly;
- mensajes de ayuda para uso del token.

### Ajustes
Definidos en:
[res_config_settings.xml](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/pbi_connections/views/res_config_settings.xml)

## Endpoints HTTP expuestos
La autenticacion se hace por:
- header `Access-Token`
- header `Authorization: Bearer ...`
- query param `token`

Controlador base:
[base_dashboard.py](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/pbi_connections/controllers/base_dashboard.py)

### Clientes
Controlador:
[clients_dashboard.py](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/pbi_connections/controllers/clients_dashboard.py)

Rutas:
- `/api/bi/customer-dashboard/frequent-customers`
- `/api/bi/customer-dashboard/inactive-customers`
- `/api/bi/customer-dashboard/customer-value`

Tambien se exponen aliases bajo `/api/bi/advanced-metrics/...`.

### Inventario y produccion
Controlador:
[inventory_dashboard.py](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/pbi_connections/controllers/inventory_dashboard.py)

Rutas:
- `/api/bi/inventory-intelligent/top-products`
- `/api/bi/inventory-intelligent/products-sales`
- `/api/bi/inventory-intelligent/sales-trend`
- `/api/bi/inventory-intelligent/dead-products`
- `/api/bi/inventory-intelligent/high-rotation-products`
- `/api/bi/production/weekly-plan`

## Assets frontend
### JS
- [home_form_view.js](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/pbi_connections/static/src/js/home_form_view.js)
  agrega comportamiento al formulario home y al boton del control panel.

### XML Owl/QWeb
- [home_form_view.xml](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/pbi_connections/static/src/xml/home_form_view.xml)

### SCSS
- [dashboard.scss](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/pbi_connections/static/src/scss/dashboard.scss)

Incluye estilos para:
- tarjetas del dashboard;
- mensajes bloqueados;
- bloques informativos de la vista de credenciales;
- adaptacion visual a temas del backend de Odoo.

## Logica de validacion externa
La validacion ocurre en `pbi_connections.api.config`.

Comportamiento actual:
- si faltan parametros, bloquea con `Configuracion incompleta`;
- si la llamada falla, bloquea con `No se pudo validar el estado del cliente`;
- si `status == 5`, bloquea por cliente insolvente;
- si la respuesta es valida y no cae en esos casos, habilita el dashboard.

La llamada externa usa un `opener` sin proxies para evitar fallos de `urllib` cuando Python hereda proxies defectuosos del entorno.

## Migracion y compatibilidad
`_sync_legacy_config()` intenta leer desde la tabla `advanced_metrics_api_config` para no perder:
- `name`
- `access_token`
- `record_limit`

Ademas, el controlador base permite autenticar contra configuraciones tanto de `pbi_connections` como de `advanced_metrics`, facilitando compatibilidad durante la transicion.

## Dependencias
- `base`
- `sale_stock`
- `base_setup`

## Archivos clave
- [__manifest__.py](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/pbi_connections/__manifest__.py)
- [models.py](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/pbi_connections/models/models.py)
- [api_config.py](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/pbi_connections/models/api_config.py)
- [views.xml](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/pbi_connections/views/views.xml)
- [api_config_views.xml](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/pbi_connections/views/api_config_views.xml)
- [base_dashboard.py](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/pbi_connections/controllers/base_dashboard.py)


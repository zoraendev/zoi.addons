# Advanced Metrics

## Resumen
`advanced_metrics` es un addon de Odoo 17 orientado a exponer reportes operativos para consumo interno y para integraciones tipo BI. Hoy su foco principal es el reporte de planeacion semanal de ventas e inventario, junto con una pantalla home que valida el estado del cliente antes de habilitar el acceso.

## Objetivos funcionales
- Mostrar una pantalla inicial de acceso a `Advanced Metrics`.
- Validar si la instancia puede usar el modulo consultando un servicio externo.
- Abrir un reporte operativo de ordenes de venta e inventario.
- Permitir exportacion a Excel del reporte consolidado.
- Centralizar la configuracion tecnica en `Ajustes`.

## Flujo funcional
1. El usuario entra al menu `Advanced Metrics`.
2. El modelo `advanced_metrics.inicio` consulta los parametros guardados en `ir.config_parameter`.
3. Se arma una peticion `GET` al servicio externo `.../clients/key/<client_key>` con cabecera `x-api-key`.
4. Segun la respuesta, la home:
   - habilita el dashboard, o
   - bloquea el acceso y muestra acciones de soporte/configuracion.
5. Si la validacion es correcta, el usuario puede abrir el reporte de ventas e inventario.

## Configuracion requerida
Se configura en `Ajustes > Advanced Metrics`.

Campos principales:
- `Key de instancia`: se usa para armar links a ADM y soporte.
- `URL base de validacion`: debe ser solo la base, por ejemplo `https://api.zoraen.com/api/production-v1-public`.
- `Clave de cliente`: identificador del cliente en el servicio externo.
- `API Key de validacion`: valor enviado en la cabecera `x-api-key`.

La URL final esperada queda asi:
`https://api.zoraen.com/api/production-v1-public/clients/key/<client_key>`

El enlace de soporte queda asi:
`https://adm.zoraen.com/support?instance=<instance_key>`

## Modelos principales
### `advanced_metrics.inicio`
Pantalla principal del modulo.

Responsabilidades:
- leer configuracion de integracion;
- validar el estado del cliente;
- decidir si mostrar el dashboard;
- abrir soporte, instancia externa, ajustes y reporte principal.

Campos relevantes:
- `show_dashboard`
- `client_validation_state`
- `client_status_code`
- `client_status_title`
- `client_status_message`
- `support_url`

Archivo:
[models.py](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/advanced_metrics/models/models.py)

### `advanced_metrics.report.wizard`
Wizard transitorio para construir el reporte de ordenes de venta.

Responsabilidades:
- recibir filtros;
- consultar `sale.order.line` y `stock.quant`;
- calcular inventario disponible y libre de usar;
- estimar cantidad sugerida a producir;
- entregar datos listos para tabla web o exportacion.

Archivo:
[report_wizard.py](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/advanced_metrics/models/report_wizard.py)

### `advanced_metrics.report.wizard.line`
Lineas transitorias del resultado mostrado en la tabla del wizard.

### `res.config.settings` heredado
Define la configuracion del addon en Ajustes y las vistas previas de URL final.

Archivo:
[res_config_settings.py](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/advanced_metrics/models/res_config_settings.py)

## Vistas y UI
### Home del modulo
Definida en:
[views.xml](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/advanced_metrics/views/views.xml)

Incluye:
- tarjeta de acceso al reporte;
- acceso directo a `Settings`;
- estado bloqueado con mensaje y boton de soporte;
- boton extra en control panel para `Abrir Instancia`.

### Vista del reporte
Definida en:
[sales_orders.xml](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/advanced_metrics/views/sales_orders.xml)

Incluye:
- filtros por fecha y cliente;
- accion `Semana Siguiente`;
- generacion del reporte via JS;
- descarga XLS;
- tabla readonly con columnas operativas.

### Ajustes
Definidos en:
[res_config_settings.xml](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/advanced_metrics/views/res_config_settings.xml)

## Controladores HTTP
### `AdvancedMetricsController`
Archivo:
[controllers.py](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/advanced_metrics/controllers/controllers.py)

Rutas principales:
- `/advanced_metrics/report/next-week-dates`
- `/advanced_metrics/report/generate`

Responsabilidades:
- devolver fechas de la siguiente semana;
- devolver JSON para la tabla;
- generar XLSX si `xlsxwriter` esta disponible.

## Assets frontend
### JS
- [home_form_view.js](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/advanced_metrics/static/src/js/home_form_view.js)
  agrega acciones del control panel para la home.
- [sales_orders_form_view.js](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/advanced_metrics/static/src/js/sales_orders_form_view.js)
  personaliza el comportamiento del formulario del reporte.
- [sales_orders_report.js](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/advanced_metrics/static/src/js/sales_orders_report.js)
  maneja generacion, filtros y descarga.

### XML Owl/QWeb
- [home_form_view.xml](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/advanced_metrics/static/src/xml/home_form_view.xml)

### SCSS
- [dashboard.scss](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/advanced_metrics/static/src/scss/dashboard.scss)

## Logica de validacion externa
La validacion vive en `advanced_metrics.inicio`.

Puntos importantes:
- limpia comillas y sufijos incorrectos en keys/urls;
- tolera que el usuario pegue una URL completa y la normaliza a base URL;
- evita proxies rotos del entorno Python usando un `opener` sin proxies;
- bloquea el dashboard si falta configuracion;
- bloquea por insolvencia cuando `status == 5`;
- muestra error si la llamada externa falla.

## Dependencias
- `base`
- `sale_stock`
- `base_setup`

Dependencia opcional de runtime:
- `xlsxwriter` para exportacion Excel.

## Limitaciones actuales
- El manifest aun tiene texto placeholder en `summary`, `description`, `category` y le falta `license`.
- `advanced_metrics.registro` existe como modelo auxiliar pero no tiene reglas de acceso completas.
- El reporte principal esta implementado, pero `action_generate_report` del wizard aun devuelve una notificacion placeholder.

## Archivos clave
- [__manifest__.py](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/advanced_metrics/__manifest__.py)
- [models.py](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/advanced_metrics/models/models.py)
- [report_wizard.py](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/advanced_metrics/models/report_wizard.py)
- [controllers.py](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/advanced_metrics/controllers/controllers.py)
- [views.xml](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/advanced_metrics/views/views.xml)
- [sales_orders.xml](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/advanced_metrics/views/sales_orders.xml)


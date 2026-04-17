# Clients Dashboard Data Catalog

Este documento describe en detalle los endpoints del controlador `clients_dashboard`, el origen real de sus datos en Odoo, el significado de cada campo, por qué se expone cada métrica, qué necesidades resuelve y cómo puede usarse en Power BI u otros entornos de analítica.

Base técnica revisada en:

- [clients_dashboard.py](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/pbi_connections/controllers/clients_dashboard.py)
- [customer_dashboard.py](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/pbi_connections/models/customer_dashboard.py)

## Contexto General

Los tres endpoints de clientes trabajan sobre `sale.order` en estado `sale` o `done`, es decir, órdenes confirmadas o completadas. No usan prospectos, cotizaciones ni pedidos cancelados. El agrupamiento se hace por `partner_id.commercial_partner_id`, lo cual significa que la analítica consolida compras a nivel cliente comercial y no por cada contacto secundario.

Esto es importante porque el objetivo de estos endpoints no es solo listar registros, sino convertir transacciones de venta en indicadores de comportamiento del cliente: frecuencia, valor, antigüedad, recencia e inactividad.

## Endpoint 1: Frequent Customers

- Ruta: `/api/bi/customer-dashboard/frequent-customers`
- Método: `POST`
- Finalidad: identificar qué clientes compran más seguido y con mayor continuidad dentro de un período.

### Qué datos obtiene

Obtiene órdenes de venta desde `sale.order` filtradas por:

- `state in ('sale', 'done')`
- `partner_id != False`
- `date_order >= dateFrom 00:00:00` cuando se envía `dateFrom`
- `date_order <= dateTo 23:59:59` cuando se envía `dateTo`

Luego agrupa esas órdenes por cliente comercial y calcula métricas de recurrencia y valor.

### Filtros de entrada

- `dateFrom`: fecha inicial del análisis. Sirve para delimitar el período.
- `dateTo`: fecha final del análisis. Sirve para cerrar el período y para calcular recencia.
- `top`: cantidad máxima de clientes devueltos. Sirve para rankings o visualizaciones top N.
- `sortBy`: define cómo ordenar el ranking. Puede ser `totalOrders`, `totalAmount`, `averageOrderValue`, `averageDaysBetweenOrders`, `lastOrderDate`, `daysWithoutPurchase` o `customerName`.

### Campos de respuesta y definición

- `customerId`: ID del cliente en `res.partner`.
  Origen: `partner.id`.
  Razón de existir: permite relacionar el resultado con otras tablas o modelos.
  Uso: joins con maestro de clientes, segmentación avanzada, relaciones en Power BI.

- `customerName`: nombre visible del cliente.
  Origen: `partner.display_name`.
  Razón de existir: facilita lectura humana y uso en dashboards.
  Uso: rankings, tablas, etiquetas en visualizaciones.

- `customerCode`: código interno o referencia del cliente.
  Origen: `partner.ref`.
  Razón de existir: en muchas empresas el código es más confiable que el nombre para análisis operativo.
  Uso: conciliación con ERP, CRM o reportes contables.

- `totalOrders`: cantidad de órdenes del cliente en el período.
  Origen: contador de `sale.order` agrupadas por cliente.
  Razón de existir: es la métrica base de frecuencia.
  Uso: ranking de recurrencia, detección de clientes fieles, análisis de repetición de compra.

- `totalAmount`: monto total comprado por el cliente en el período.
  Origen: suma de `order.amount_total`.
  Razón de existir: frecuencia sin valor económico puede ser engañosa; esta métrica agrega peso financiero.
  Uso: identificar clientes frecuentes y rentables, priorizar atención comercial.

- `averageOrderValue`: ticket promedio del cliente.
  Origen: `totalAmount / totalOrders`.
  Razón de existir: diferencia clientes que compran mucho pero pequeño, de clientes que compran menos veces pero fuerte.
  Uso: segmentación comercial, pricing, diseño de promociones y paquetes.

- `averageDaysBetweenOrders`: promedio de días entre compras.
  Origen: diferencia entre fechas sucesivas de las órdenes del cliente.
  Razón de existir: mide cadencia real de recompra.
  Uso: pronóstico de recompra, campañas pre-vencimiento, modelos de retención.

- `lastOrderDate`: última fecha de compra del cliente dentro del conjunto analizado.
  Origen: mayor `date_order` del cliente.
  Razón de existir: representa recencia, una de las variables más importantes en analítica comercial.
  Uso: seguimiento de actividad reciente, detección de enfriamiento.

- `daysWithoutPurchase`: días transcurridos desde la última compra hasta `dateTo` o hasta hoy si no se envía `dateTo`.
  Origen: diferencia entre fecha ancla y `lastOrderDate`.
  Razón de existir: permite evaluar si el cliente sigue dentro de su ciclo natural de compra o si ya se está alejando.
  Uso: alertas de riesgo, churn, automatización comercial.

- `customerType`: clasifica al cliente como `new`, `occasional` o `recurring`.
  Origen: regla de negocio interna:
  si `totalOrders >= 5` es recurrente;
  si `totalOrders >= 2` y `averageDaysBetweenOrders <= 30` también es recurrente;
  si `totalOrders >= 2` pero no cumple lo anterior es ocasional;
  si no, es nuevo.
  Razón de existir: transformar métricas crudas en una categoría accionable.
  Uso: segmentación de campañas, tableros ejecutivos, reglas de priorización comercial.

### Qué necesidad resuelve

Resuelve la necesidad de saber qué clientes sostienen la recurrencia del negocio y cuáles forman el núcleo de compras repetidas. Ayuda a responder preguntas como:

- ¿Quiénes compran más seguido?
- ¿Quiénes tienen ciclos de compra cortos?
- ¿Qué clientes están dentro del patrón ideal de recompra?

### Aplicación en Power BI

Se puede usar para:

- rankings top N de recurrencia;
- segmentación por tipo de cliente;
- gráficos burbuja entre frecuencia y valor;
- matrices de recencia vs frecuencia;
- evolución de clientes recurrentes por período.

### Toma de decisiones que habilita

- priorizar seguimiento a clientes con mayor recurrencia;
- diseñar campañas de fidelización;
- detectar clientes que deberían comprar pronto y aún no lo han hecho;
- asignar ejecutivos a cuentas estratégicas.

### Cómo se puede escalar analíticamente

A partir de este endpoint se puede calcular:

- score RFM básico combinando `totalOrders`, `totalAmount` y `daysWithoutPurchase`;
- probabilidad de recompra con `averageDaysBetweenOrders`;
- cohortes de repetición de compra;
- comparación de frecuencia entre años, meses o segmentos;
- alertas de caída de recurrencia cuando `daysWithoutPurchase` supera el patrón histórico del cliente.

## Endpoint 2: Inactive Customers

- Ruta: `/api/bi/customer-dashboard/inactive-customers`
- Método: `POST`
- Finalidad: detectar clientes que ya no están comprando y priorizar recuperación.

### Qué datos obtiene

Usa también `sale.order` en `sale` o `done`, pero sin filtrar por rango de fechas del historial. La lógica toma el historial total del cliente para determinar su última compra y medir cuántos días lleva inactivo.

### Filtros de entrada

- `inactiveDays`: umbral mínimo de días sin comprar.
- `top`: cantidad máxima de clientes a devolver.

### Campos de respuesta y definición

- `customerId`: identificador del cliente.
  Origen: `res.partner`.
  Uso: relaciones con otras tablas y acciones comerciales.

- `customerName`: nombre del cliente.
  Origen: `display_name`.
  Uso: lectura y comunicación de listas de recuperación.

- `customerCode`: referencia interna del cliente.
  Origen: `partner.ref`.
  Uso: conciliación con otros sistemas o catálogos internos.

- `lastOrderDate`: última fecha de compra histórica.
  Origen: última `date_order` del cliente.
  Razón de existir: es la base para medir inactividad real.
  Uso: listas de reactivación, ageing de clientes.

- `daysWithoutPurchase`: días sin comprar.
  Origen: diferencia entre hoy y `lastOrderDate`.
  Razón de existir: es la métrica central del endpoint.
  Uso: alertas, segmentación por inactividad, disparadores comerciales.

- `totalOrdersHistorical`: número total de órdenes históricas.
  Origen: conteo del historial del cliente.
  Razón de existir: no todos los inactivos pesan igual; un cliente históricamente fuerte merece más atención.
  Uso: priorización de recuperación.

- `totalHistoricalAmount`: valor histórico total comprado.
  Origen: suma histórica de `amount_total`.
  Razón de existir: muestra cuánto aportó el cliente al negocio antes de inactivarse.
  Uso: rescate de clientes valiosos, cálculo de pérdida potencial.

- `averageOrderValue`: ticket promedio histórico.
  Origen: `totalHistoricalAmount / totalOrdersHistorical`.
  Razón de existir: ayuda a diferenciar entre clientes inactivos pequeños y clientes inactivos premium.
  Uso: priorización y ofertas personalizadas.

- `customerType`: para este endpoint se fija como `inactive`.
  Razón de existir: facilita modelado y visualización como segmento propio.
  Uso: slicers, colores, reglas automáticas en dashboards.

### Qué necesidad resuelve

Resuelve la necesidad de identificar fuga de clientes. Muchas empresas saben cuánto venden, pero no tienen visibilidad clara de quién dejó de comprar y cuánto riesgo representa esa pérdida.

### Aplicación en Power BI

Se puede usar para:

- tablero de clientes perdidos o dormidos;
- semáforo por tramos de inactividad;
- ranking de recuperación por monto histórico;
- análisis de abandono por segmento, zona o vendedor si luego se enriquece con más dimensiones.

### Toma de decisiones que habilita

- reactivar clientes con campañas específicas;
- llamar primero a los clientes históricamente más valiosos;
- detectar deterioro de cartera;
- medir el impacto de acciones de recuperación.

### Cómo se puede escalar analíticamente

A partir de este endpoint se puede construir:

- score de abandono;
- pérdida potencial de revenue por cartera inactiva;
- análisis de churn por ventanas de 30, 60, 90 o 180 días;
- campañas automáticas según nivel de valor histórico;
- modelos de win-back para recuperar clientes con alta probabilidad de retorno.

## Endpoint 3: Customer Value

- Ruta: `/api/bi/customer-dashboard/customer-value`
- Método: `POST`
- Finalidad: medir el aporte económico de cada cliente dentro de un período.

### Qué datos obtiene

Toma órdenes de `sale.order` en `sale` o `done`, filtradas por `dateFrom` y `dateTo`, y las agrupa por cliente comercial para estimar valor económico y antigüedad operativa dentro del conjunto analizado.

### Filtros de entrada

- `dateFrom`: fecha inicial del análisis.
- `dateTo`: fecha final del análisis.
- `top`: cantidad máxima de resultados.
- `sortBy`: campo de ordenamiento. Puede ser `totalAmount`, `totalOrders`, `averageOrderValue`, `ltvBasic`, `firstOrderDate`, `lastOrderDate` o `customerName`.

### Campos de respuesta y definición

- `customerId`: ID del cliente.
  Origen: `res.partner`.
  Uso: integración y modelado de relaciones.

- `customerName`: nombre visible del cliente.
  Origen: `display_name`.
  Uso: ranking y visualización.

- `customerCode`: referencia interna.
  Origen: `partner.ref`.
  Uso: trazabilidad interna y cruces.

- `totalOrders`: total de órdenes en el período.
  Origen: conteo de órdenes.
  Razón de existir: el valor monetario necesita contexto transaccional.
  Uso: distinguir clientes de alto valor por frecuencia o por volumen unitario.

- `totalAmount`: monto total comprado en el período.
  Origen: suma de `amount_total`.
  Razón de existir: es la métrica principal de valor.
  Uso: ranking de clientes, Pareto, concentración de ingresos.

- `averageOrderValue`: ticket promedio.
  Origen: `totalAmount / totalOrders`.
  Razón de existir: permite leer calidad del ingreso, no solo su volumen.
  Uso: análisis de clientes premium, diseño de bundles y descuentos.

- `ltvBasic`: en la implementación actual equivale a `totalAmount`.
  Razón de existir: funciona como una aproximación simple de valor acumulado en el período.
  Uso: dashboards de valor del cliente y puntos de partida para un LTV más avanzado.
  Nota: no es un LTV predictivo ni descontado; es un indicador básico.

- `firstOrderDate`: primera compra del cliente dentro del conjunto analizado.
  Origen: menor `date_order`.
  Razón de existir: ayuda a entender antigüedad relativa en el período.
  Uso: distinguir clientes recién activados de clientes con recorrido.

- `lastOrderDate`: última compra del cliente dentro del conjunto analizado.
  Origen: mayor `date_order`.
  Razón de existir: combina valor con vigencia comercial.
  Uso: priorizar clientes valiosos aún activos o clientes valiosos que comienzan a enfriarse.

- `customerType`: `new`, `occasional` o `recurring`.
  Origen: misma lógica de segmentación conductual del servicio.
  Razón de existir: aporta capa interpretativa de comportamiento.
  Uso: lectura ejecutiva del perfil de valor del cliente.

### Qué necesidad resuelve

Resuelve la necesidad de saber qué clientes sostienen el ingreso y cuáles aportan más valor económico, no solo más frecuencia. Es clave para empresas que necesitan priorizar cuentas, segmentar cartera o entender concentración de ingresos.

### Aplicación en Power BI

Se puede usar para:

- ranking de clientes VIP;
- curva de Pareto 80/20;
- concentración de revenue por cliente;
- análisis por tipo de cliente y valor;
- comparación entre valor, frecuencia y antigüedad.

### Toma de decisiones que habilita

- priorizar servicio a cuentas clave;
- definir descuentos escalonados;
- crear programas VIP;
- proteger ingresos concentrados en pocos clientes;
- evaluar dependencia comercial de ciertas cuentas.

### Cómo se puede escalar analíticamente

A partir de este endpoint se puede construir:

- análisis ABC de clientes;
- concentración de ingresos por segmento;
- valor esperado por cliente combinando recurrencia y monto;
- predicción de LTV más avanzado agregando margen, tiempo y retención;
- alertas sobre clientes de alto valor cuya recencia empieza a deteriorarse.

## Consideraciones Analíticas para los Tres Endpoints

- Todos los cálculos parten de órdenes confirmadas o completadas. Si una empresa trabaja mucho con cotizaciones no convertidas, estos endpoints no reflejarán esa demanda potencial.
- Los montos vienen de `amount_total`, por lo que incluyen la lógica monetaria ya registrada en Odoo.
- La agrupación por `commercial_partner_id` evita duplicar análisis cuando un mismo cliente compra con varios contactos.
- Estos endpoints son buenos para Power BI porque entregan métricas ya semiprocesadas, reduciendo transformaciones en Power Query y acelerando el modelado.

## Necesidades Empresariales que Cubren en Conjunto

- entender quién compra más y mejor;
- detectar clientes que se están enfriando;
- priorizar recuperación de clientes perdidos;
- segmentar clientes por comportamiento;
- orientar decisiones comerciales con base en datos y no intuición;
- crear tableros ejecutivos de cartera, retención y valor del cliente.

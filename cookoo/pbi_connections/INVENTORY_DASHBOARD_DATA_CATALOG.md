# Inventory Dashboard Data Catalog

Este documento describe en detalle los endpoints del controlador `inventory_dashboard`, el origen real de sus datos en Odoo, el significado de cada campo, por qué se expone cada métrica, qué necesidades resuelve y cómo puede usarse en Power BI u otros entornos de analítica.

Base técnica revisada en:

- [inventory_dashboard.py](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/pbi_connections/controllers/inventory_dashboard.py)
- [inventory_dashboard.py](C:/dev/odoo/zoraen-odoo/custom_addons/cookoo/pbi_connections/models/inventory_dashboard.py)

## Contexto General

Los endpoints de inventario y ventas por producto trabajan principalmente con:

- `sale.order.line` para leer ventas confirmadas o completadas;
- `product.product` para datos maestros del producto;
- `stock.quant` para stock actual en ubicaciones internas;
- `stock.warehouse` cuando se filtra por almacén.

La lógica mezcla datos comerciales y operativos para responder preguntas como:

- qué productos venden más;
- qué productos venden mejor y con mejor margen;
- qué productos no se mueven;
- qué productos tienen riesgo de quiebre;
- cómo evoluciona la venta en el tiempo.

No son endpoints transaccionales; son endpoints de lectura analítica pensados para dashboards, control de inventario y apoyo a decisiones de compras, logística y ventas.

## Reglas Generales de Datos

- Solo se consideran líneas de venta con órdenes en estado `sale` o `done`.
- Se excluyen líneas informativas o de sección con `display_type = False`.
- Se consideran productos vendibles (`sale_ok = True`).
- Para productos físicos/consumibles, la lógica usa `detailed_type` o `type` según disponibilidad del modelo.
- El stock se toma de ubicaciones internas (`location_id.usage = 'internal'`).

## Endpoint 1: Top Products

- Ruta: `/api/bi/inventory-intelligent/top-products`
- Método: `POST`
- Finalidad: identificar los productos más vendidos del período y compararlos contra stock y margen.

### Qué datos obtiene

Obtiene líneas de venta desde `sale.order.line` filtradas por rango de fechas. A partir de esas líneas:

- suma cantidad vendida por producto;
- suma importe de venta por producto;
- estima margen usando costo y subtotal;
- consulta stock actual en `stock.quant`.

### Filtros de entrada

- `dateFrom`: fecha inicial del análisis.
- `dateTo`: fecha final del análisis.
- `limit`: cantidad máxima de productos a devolver.

### Campos de respuesta y definición

- `productId`: ID del producto.
  Origen: `product.product.id`.
  Razón de existir: clave técnica para relaciones y modelos analíticos.
  Uso: joins con dimensiones de producto, categorías, marcas o costos.

- `productName`: nombre visible del producto.
  Origen: `product.display_name`.
  Razón de existir: lectura humana del ranking.
  Uso: tablas, barras, top N.

- `sku`: código interno.
  Origen: `product.default_code`.
  Razón de existir: en operación suele ser más confiable que el nombre para identificar producto.
  Uso: conciliación con inventario, picking, compras y ERP externo.

- `categoryName`: categoría del producto.
  Origen: `product.categ_id.display_name`.
  Razón de existir: permite agrupar y analizar familias de producto.
  Uso: análisis por categoría, surtido, portfolio.

- `quantitySold`: unidades vendidas.
  Origen: suma de `line.product_uom_qty`.
  Razón de existir: representa demanda bruta del producto.
  Uso: ranking de volumen, control de salida, planeación de abastecimiento.

- `salesAmount`: monto vendido.
  Origen: suma de `line.price_subtotal`.
  Razón de existir: no siempre el producto más vendido en unidades es el más importante en ingreso.
  Uso: ranking por facturación, mezcla de ventas.

- `currentStock`: inventario actual.
  Origen: suma de `stock.quant.quantity` en ubicaciones internas.
  Razón de existir: compara demanda contra existencia disponible.
  Uso: riesgo de quiebre, decisión de reposición, control operativo.

- `marginAmount`: margen monetario estimado.
  Origen: `salesAmount - (quantitySold * unit_cost)`, donde `unit_cost` se toma de `purchase_price` de la línea o `standard_price` del producto.
  Razón de existir: volumen sin rentabilidad puede llevar a decisiones equivocadas.
  Uso: detectar productos estrella y productos que venden pero dejan poco retorno.

- `marginPercent`: margen porcentual.
  Origen: `(marginAmount / salesAmount) * 100`.
  Razón de existir: permite comparar productos de distinto nivel de facturación.
  Uso: pricing, descuentos, estrategia comercial.

- `inventoryTurnover`: rotación simple de inventario.
  Origen: `quantitySold / currentStock` si hay stock.
  Razón de existir: indica qué tan rápido sale el producto respecto a lo que aún queda.
  Uso: planeación de compras y producción.

### Qué necesidad resuelve

Resuelve la necesidad de identificar qué productos sostienen la venta y si la empresa tiene suficiente stock para seguir capitalizando esa demanda.

### Aplicación en Power BI

Se puede usar para:

- top N por unidades;
- top N por ingreso;
- matriz volumen vs margen;
- ranking por categoría;
- semáforo de rotación y cobertura.

### Toma de decisiones que habilita

- priorizar compras;
- proteger productos estrella;
- ajustar precios o descuentos;
- enfocar esfuerzo comercial en productos con mejor margen;
- evitar quiebres en productos clave.

### Cómo se puede escalar analíticamente

A partir de este endpoint se puede calcular:

- análisis ABC de productos;
- clasificación volumen-margen;
- cobertura estimada si se incorpora venta diaria;
- concentración de ventas por familia;
- detección de dependencia en pocos SKU.

## Endpoint 2: Products Sales

- Ruta: `/api/bi/inventory-intelligent/products-sales`
- Método: `POST`
- Finalidad: obtener una vista más completa por producto, combinando ventas, costo, margen, última venta, stock y estado operativo.

### Qué datos obtiene

Lee ventas desde `sale.order.line`, stock desde `stock.quant` y catálogo desde `product.product`. Además:

- incluye productos con ventas;
- incluye productos con stock aunque no hayan vendido;
- calcula última fecha de venta por producto;
- clasifica el estado de movimiento y el estado de stock.

### Filtros de entrada

- `dateFrom`: fecha inicial.
- `dateTo`: fecha final.
- `warehouseId`: almacén específico.
- `categoryId`: categoría específica.

### Campos de respuesta y definición

- `productId`, `productName`, `sku`, `categoryName`
  Origen: maestro `product.product`.
  Uso: identificación, agrupación y lectura en dashboards.

- `quantitySold`: cantidad vendida.
  Origen: suma de `qty_delivered` o, si no existe, `product_uom_qty`.
  Razón de existir: intenta medir venta entregada o comprometida según disponibilidad del dato.
  Uso: análisis de demanda real por producto.

- `salesAmount`: ventas monetarias del producto.
  Origen: suma de `price_subtotal`.
  Uso: facturación por SKU.

- `costAmount`: costo estimado total.
  Origen: `quantitySold * unit_cost`.
  Razón de existir: permite ver rentabilidad monetaria.
  Uso: control de margen y análisis financiero por producto.

- `marginAmount`: utilidad bruta estimada.
  Origen: `salesAmount - costAmount`.
  Uso: detectar productos que venden bien y dejan dinero, o productos que venden pero no rentan.

- `marginPercent`: rentabilidad porcentual.
  Origen: `(marginAmount / salesAmount) * 100`.
  Uso: comparar mix comercial entre productos.

- `currentStock`: stock actual del producto.
  Origen: `stock.quant.quantity`.
  Razón de existir: muestra situación actual de inventario.
  Uso: decisiones de reposición, depuración, alertas.

- `averageStock`: en la implementación actual es igual a `currentStock`.
  Origen: mismo valor de stock actual.
  Razón de existir: deja preparada la estructura para una rotación basada en stock promedio, aunque hoy usa una aproximación simple.
  Uso: base de cálculo de rotación.
  Nota: analíticamente conviene entender que no es un promedio histórico real todavía.

- `inventoryTurnover`: rotación del producto.
  Origen: `quantitySold / averageStock`.
  Razón de existir: mide qué tan rápido se mueve el producto contra el stock disponible.
  Uso: compras, reabastecimiento, análisis operativo.

- `lastSaleDate`: última fecha de venta.
  Origen: búsqueda de la última `sale.order.line` del producto.
  Razón de existir: ayuda a medir recencia a nivel producto.
  Uso: productos calientes, fríos o próximos a inmovilizarse.

- `movementStatus`: clasificación operativa del movimiento.
  Origen: regla interna:
  `no_movement` si no vende;
  `high_rotation` si `inventoryTurnover >= 5` o `quantitySold >= 50`;
  `medium_rotation` si `inventoryTurnover >= 2` o `quantitySold >= 10`;
  si no, `low_rotation`.
  Razón de existir: convertir métricas crudas en una etiqueta accionable.
  Uso: semáforos, filtros, reglas automáticas.

- `stockStatus`: clasificación del estado de inventario.
  Origen: regla interna:
  `out_of_stock` si stock <= 0;
  `low` si el stock es muy bajo respecto al volumen vendido;
  `overstock` si el stock supera ampliamente la venta;
  en otro caso `normal`.
  Razón de existir: traducir stock numérico a un estado operativo entendible.
  Uso: alertas de reabastecimiento o sobreinventario.

### Qué necesidad resuelve

Resuelve la necesidad de tener una ficha analítica por producto que no solo diga cuánto vende, sino si deja margen, cuándo fue su última venta, cómo está su inventario y qué tan sano es su nivel de stock.

### Aplicación en Power BI

Se puede usar para:

- catálogo analítico completo por producto;
- matriz por categoría, almacén o estado;
- análisis de margen vs rotación;
- tablero de productos sin venta pero con stock;
- vista gerencial de salud del inventario.

### Toma de decisiones que habilita

- subir o bajar inventario;
- liquidar productos lentos;
- impulsar comercialmente productos rentables;
- revisar costos o precios;
- depurar surtido.

### Cómo se puede escalar analíticamente

A partir de este endpoint se puede construir:

- score de salud del producto;
- segmentación ABC/XYZ;
- análisis de días sin venta;
- escenarios de reposición por stock status;
- alertas automáticas por `movementStatus` y `stockStatus`.

## Endpoint 3: Sales Trend

- Ruta: `/api/bi/inventory-intelligent/sales-trend`
- Método: `POST`
- Finalidad: observar la evolución temporal de la venta en unidades y valor.

### Qué datos obtiene

Lee `sale.order.line` y agrupa la información por:

- día;
- semana;
- mes.

Además construye un resumen de ventanas recientes de 7, 15 y 30 días.

### Filtros de entrada

- `dateFrom`: inicio del período.
- `dateTo`: cierre del período.
- `warehouseId`: almacén específico.
- `groupBy`: `day`, `week` o `month`.

### Campos de respuesta y definición

- `date`: período agrupado.
  Origen: fecha del pedido normalizada según el agrupador.
  Razón de existir: eje temporal del dashboard.
  Uso: series de tiempo.

- `quantitySold`: cantidad vendida en el período.
  Origen: suma de `qty_delivered` o `product_uom_qty`.
  Uso: evolución de volumen.

- `salesAmount`: monto vendido en el período.
  Origen: suma de `price_subtotal`.
  Uso: evolución monetaria.

- `periodSummary.last7Days.quantitySold`, `periodSummary.last7Days.salesAmount`
- `periodSummary.last15Days.quantitySold`, `periodSummary.last15Days.salesAmount`
- `periodSummary.last30Days.quantitySold`, `periodSummary.last30Days.salesAmount`
  Origen: acumulados en ventanas móviles respecto a `dateTo` o a la fecha actual.
  Razón de existir: facilitar KPIs rápidos sin tener que recalcularlos en la capa visual.
  Uso: tarjetas KPI, comparativos cortos, análisis de aceleración.

### Qué necesidad resuelve

Resuelve la necesidad de entender si la venta está subiendo, bajando, estancándose o mostrando estacionalidad.

### Aplicación en Power BI

Se puede usar para:

- líneas de tendencia;
- comparación entre periodos;
- paneles ejecutivos con últimos 7, 15 y 30 días;
- análisis de estacionalidad por semana o mes.

### Toma de decisiones que habilita

- anticipar compras;
- ajustar metas comerciales;
- medir impacto de promociones;
- detectar desaceleraciones tempranas.

### Cómo se puede escalar analíticamente

A partir de este endpoint se puede calcular:

- variación WoW o MoM;
- promedios móviles;
- forecast de corto plazo;
- detección de anomalías;
- comparación real vs meta.

## Endpoint 4: Dead Products

- Ruta: `/api/bi/inventory-intelligent/dead-products`
- Método: `POST`
- Finalidad: identificar productos con stock que llevan demasiado tiempo sin movimiento.

### Qué datos obtiene

Parte de productos con stock en `stock.quant`. Luego consulta la última venta de esos productos en `sale.order.line`. Si no encuentra venta, usa como referencia la fecha de creación del producto cuando existe.

### Filtros de entrada

- `daysWithoutMovement`: mínimo de días sin venta.
- `warehouseId`: almacén específico.

### Campos de respuesta y definición

- `productId`, `productName`, `sku`, `categoryName`
  Origen: `product.product`.
  Uso: identificación y clasificación.

- `currentStock`: stock actual.
  Origen: `stock.quant.quantity`.
  Razón de existir: un producto sin movimiento solo es problema si todavía ocupa inventario.
  Uso: costo de inmovilización, decisiones de liquidación.

- `lastSaleDate`: última venta registrada.
  Origen: `sale.order.line`.
  Razón de existir: permite ver qué tan antigua fue la salida real.
  Uso: análisis de aging de inventario.

- `daysWithoutMovement`: días sin venta.
  Origen: diferencia entre fecha actual y fecha de referencia.
  Razón de existir: métrica central para inmovilización.
  Uso: cortes por 30, 60, 90, 180 días.

- `movementStatus`: se devuelve como `no_movement`.
  Razón de existir: simplifica clasificación y modelado.
  Uso: filtros y segmentación.

### Qué necesidad resuelve

Resuelve la necesidad de detectar inventario obsoleto o inmovilizado que consume espacio, capital y atención operativa.

### Aplicación en Power BI

Se puede usar para:

- dashboard de stock muerto;
- tablas de ageing;
- ranking de inventario inmovilizado por categoría;
- análisis del costo financiero del sobrestock sin rotación.

### Toma de decisiones que habilita

- liquidaciones;
- promociones;
- depuración de catálogo;
- reducción de compras en líneas lentas;
- reubicación de espacio en almacén.

### Cómo se puede escalar analíticamente

A partir de este endpoint se puede calcular:

- capital inmovilizado;
- riesgo de obsolescencia;
- aging buckets;
- ranking por costo de oportunidad;
- evaluación de productos a descontinuar.

## Endpoint 5: High Rotation Products

- Ruta: `/api/bi/inventory-intelligent/high-rotation-products`
- Método: `POST`
- Finalidad: identificar productos que se están moviendo tan rápido que merecen atención especial de abastecimiento.

### Qué datos obtiene

Este endpoint no consulta de cero; reutiliza la salida de `products-sales` y filtra solo productos con `movementStatus = high_rotation`. Luego añade cobertura estimada.

### Filtros de entrada

- `dateFrom`: inicio del período.
- `dateTo`: fin del período.
- `warehouseId`: almacén.
- `limit`: cantidad máxima.

### Campos de respuesta y definición

- `productId`, `productName`, `sku`
  Origen: heredado del análisis de ventas por producto.

- `quantitySold`: cantidad vendida.
  Origen: heredado de `products-sales`.
  Uso: magnitud de demanda.

- `currentStock`: stock actual.
  Origen: heredado.
  Uso: visión inmediata de cobertura.

- `averageStock`: stock usado como base de cálculo.
  Origen: heredado.
  Uso: soporte para rotación.

- `inventoryTurnover`: rotación.
  Origen: heredado.
  Uso: priorizar productos críticos.

- `daysOfCoverage`: días estimados que alcanza el stock actual.
  Origen: `currentStock / average_daily_sales`, donde `average_daily_sales = quantitySold / period_days`.
  Razón de existir: traduce stock a una métrica operativa mucho más accionable.
  Uso: saber cuántos días quedan antes del quiebre.

- `movementStatus`: fijo como `high_rotation`.
  Razón de existir: facilita segmentación.
  Uso: dashboards, alertas, reglas de negocio.

### Qué necesidad resuelve

Resuelve la necesidad de detectar productos críticos que pueden agotarse rápido si no se actúa a tiempo.

### Aplicación en Power BI

Se puede usar para:

- panel de riesgo de quiebre;
- semáforo por días de cobertura;
- top productos críticos por rotación;
- tablero de compras urgentes.

### Toma de decisiones que habilita

- acelerar reposición;
- redistribuir stock;
- priorizar producción;
- asegurar materiales;
- proteger ventas de alta salida.

### Cómo se puede escalar analíticamente

A partir de este endpoint se puede construir:

- alertas automáticas por cobertura;
- punto de reorden;
- stock de seguridad;
- modelos de quiebre probable;
- simulación de escenarios de crecimiento de demanda.

## Consideraciones Analíticas para los Cinco Endpoints

- El costo usado en márgenes depende de que `purchase_price` o `standard_price` estén bien mantenidos en Odoo.
- `averageStock` hoy es una aproximación basada en stock actual, no un promedio histórico.
- La rotación calculada es útil como indicador operativo rápido, no como métrica financiera de inventario formal.
- El filtro por almacén es importante para operaciones con inventario descentralizado.
- El filtro por categoría permite análisis tácticos por línea de producto o familia.

## Necesidades Empresariales que Cubren en Conjunto

- saber qué productos venden más;
- saber qué productos generan ingreso y margen;
- detectar productos lentos o inmovilizados;
- anticipar quiebres por alta rotación;
- observar evolución temporal de la venta;
- mejorar compras, surtido, producción y control de inventario.

## Soluciones que Brindan en la Práctica

- mejor planeación de reabastecimiento;
- reducción de sobrestock;
- menor riesgo de quiebre;
- mayor visibilidad de margen por producto;
- mejor selección de productos a impulsar, liquidar o descontinuar;
- base sólida para tableros de operaciones e inventario en Power BI.

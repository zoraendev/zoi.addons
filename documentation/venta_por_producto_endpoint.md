# Dashboard de Inventario - Endpoint de Venta por Producto

Este documento describe en detalle el endpoint de venta por producto del dashboard de inventario, el flujo interno de procesamiento, el origen de cada dato devuelto, la logica de calculo y la interpretacion de la visual de Power BI compartida, incluyendo explicacion de columnas y filas.

## 1. Objetivo del endpoint

El endpoint construye una vista analitica por producto que combina ventas, costo estimado, margen, stock actual, ultima fecha de venta, rotacion y estados operativos.

Su finalidad no es solo responder cuanto vende un producto. Tambien busca responder:

- cuanto ingreso genera cada producto
- cuanto costo estimado absorbe
- cuanto margen deja
- cuanto stock tiene disponible
- que tan rapido rota
- si su estado de movimiento y de stock es sano o riesgoso

Es un endpoint mas completo que `top-products`, porque no se limita a ranking. Funciona como una ficha operativa por SKU.

## 2. Rutas disponibles

El controlador expone dos rutas equivalentes:

- `/api/bi/inventory-intelligent/products-sales`
- `/api/bi/advanced-metrics/inventory-intelligent/products-sales`

Ambas llaman el mismo metodo de servicio: `get_products_sales_report_data`.

## 3. Metodo HTTP y autenticacion

- Metodo aceptado: `POST`
- Autenticacion: token obligatorio

El token puede enviarse en cualquiera de estas formas:

- Header `Access-Token: <token>`
- Header `Authorization: Bearer <token>`
- Query param `?token=<token>`

Si el token no existe o no coincide con un registro valido en `pbi_connections.api.config` o `advanced_metrics.api.config`, la respuesta es `401`.

## 4. Flujo tecnico completo

### 4.1 Controlador

El metodo `get_products_sales` del controlador no calcula datos. Su trabajo es:

1. Recibir la peticion.
2. Extraer filtros desde JSON body o query params.
3. Validar el token.
4. Delegar el procesamiento al modelo `pbi_connections.inventory.dashboard`.

### 4.2 Extraccion de filtros

Los filtros se toman desde:

- `payload.filters`
- o el JSON completo si no existe la clave `filters`
- y luego se complementan o sobreescriben con query params

Para este endpoint, el controlador acepta las claves generales del dashboard de inventario:

- `dateFrom`
- `dateTo`
- `warehouseId`
- `categoryId`
- `limit`
- `groupBy`
- `daysWithoutMovement`

Nota importante: en `products-sales`, el servicio realmente usa `dateFrom`, `dateTo`, `warehouseId` y `categoryId`. No usa `limit`, `groupBy` ni `daysWithoutMovement`.

### 4.3 Normalizacion y validacion de filtros

El servicio normaliza los filtros asi:

- `dateFrom`: fecha inicial en formato `YYYY-MM-DD`
- `dateTo`: fecha final en formato `YYYY-MM-DD`
- `warehouseId`: entero opcional
- `categoryId`: entero opcional

Reglas de validacion:

- Si una fecha no usa formato valido, el servicio responde error `400`.
- Si `dateFrom > dateTo`, el servicio responde error `400`.
- Si `warehouseId` o `categoryId` no son enteros cuando se envian, el servicio responde error `400`.

## 5. Origen real de los datos

El endpoint combina informacion de varios modelos:

- `sale.order.line` para ventas por producto
- `product.product` para datos maestros del producto
- `stock.quant` para stock actual
- `stock.warehouse` cuando se filtra por almacen

## 6. Que productos incluye realmente

Este endpoint no devuelve solo productos con venta. Construye su universo de productos asi:

1. toma productos que si tuvieron ventas en el rango consultado
2. toma productos que tienen stock actual, aunque no hayan vendido
3. une ambos conjuntos
4. filtra ese conjunto para quedarse con productos vendibles y, si aplica, de la categoria indicada

Esto es importante porque la visual puede mostrar:

- productos con ventas y stock
- productos con ventas pero sin stock
- productos con stock pero sin ventas

Eso lo hace mucho mas util para analitica operativa.

## 7. Dominio exacto sobre lineas de venta

La consulta de `sale.order.line` usa estas reglas:

- `order_id.state in ('sale', 'done')`
- `display_type = False`
- `product_id != False`
- `product_id.sale_ok = True`
- `product_id.detailed_type in ('product', 'consu')` o `type in ('product', 'consu')` segun disponibilidad
- `order_id.date_order >= dateFrom 00:00:00`, si se envio `dateFrom`
- `order_id.date_order <= dateTo 23:59:59`, si se envio `dateTo`
- `order_id.warehouse_id = warehouseId`, si se envio `warehouseId`
- `product_id.categ_id child_of categoryId`, si se envio `categoryId`

## 8. Como se construyen las metricas

El servicio crea primero una estructura base para cada producto con ventas o stock, incluso antes de sumar lineas. Luego recorre las lineas de venta y acumula metricas comerciales.

Ademas consulta:

- stock actual por producto
- ultima fecha de venta por producto

Finalmente calcula indicadores derivados y estados operativos.

## 9. Campos que devuelve la respuesta y como se calculan

La respuesta exitosa del controlador tiene esta estructura general:

```json
{
  "success": true,
  "message": "Ventas por producto obtenidas correctamente.",
  "generatedAt": "2026-04-16T12:00:00Z",
  "filters": {
    "dateFrom": "2026-01-01",
    "dateTo": "2026-03-31",
    "warehouseId": 1,
    "categoryId": 2
  },
  "data": [
    {
      "productId": 101,
      "productName": "Producto Ejemplo",
      "sku": "SKU-101",
      "categoryName": "Categoria X",
      "quantitySold": 120.0,
      "salesAmount": 22000.0,
      "costAmount": 15400.0,
      "marginAmount": 6600.0,
      "marginPercent": 30.0,
      "currentStock": 45.0,
      "averageStock": 45.0,
      "inventoryTurnover": 2.67,
      "lastSaleDate": "2026-03-28",
      "movementStatus": "high_rotation",
      "stockStatus": "normal"
    }
  ]
}
```

### Explicacion de cada campo de nivel raiz

#### success

- Origen: controlador.
- Significado: indica si la peticion fue exitosa.

#### message

- Origen: controlador.
- Significado: mensaje humano asociado al resultado.

#### generatedAt

- Origen: servicio.
- Significado: timestamp UTC de generacion de la respuesta.

#### filters

- Origen: servicio.
- Significado: filtros normalizados finales usados realmente por la consulta.

#### data

- Origen: servicio.
- Significado: lista de productos con su ficha analitica completa.

### Explicacion de cada campo dentro de data

#### productId

- Origen: `product.product.id`.
- Uso: llave tecnica para analitica o integracion.

#### productName

- Origen: `product.display_name`.
- Uso: etiqueta visible en tablas y dashboards.

#### sku

- Origen: `product.default_code`.
- Uso: identificacion interna del producto.

#### categoryName

- Origen: `product.categ_id.display_name`.
- Uso: agrupacion por familia de producto.

#### quantitySold

- Que es: cantidad vendida del producto en el periodo.
- Origen: suma de `qty_delivered` y, si no existe o es cero, toma `product_uom_qty`.
- Formula real:

```text
quantitySold = suma(qty_delivered o product_uom_qty por linea)
```

- Redondeo: a 2 decimales.
- Por que se calcula asi: intenta aproximarse primero a venta entregada. Si ese dato no esta disponible, usa la cantidad de la linea como respaldo.

#### salesAmount

- Que es: monto vendido del producto.
- Origen: suma de `sale.order.line.price_subtotal`.
- Formula:

```text
salesAmount = suma(price_subtotal de las lineas del producto)
```

- Redondeo: a 2 decimales.
- Por que se calcula asi: representa ingreso comercial antes de impuestos en la logica usada por la linea.

#### costAmount

- Que es: costo estimado total del producto.
- Origen: `quantitySold * unitCost` acumulado por linea.
- Formula por linea:

```text
unitCost = line.purchase_price o product.standard_price o 0
costAmountLinea = quantitySoldLinea * unitCost
```

- Formula agregada:

```text
costAmount = suma(costAmountLinea de las lineas del producto)
```

- Redondeo: a 2 decimales.
- Por que se calcula asi: permite estimar costo sin depender de un modelo contable mas complejo.

#### marginAmount

- Que es: margen monetario estimado del producto.
- Origen: `salesAmount - costAmount`.
- Formula:

```text
marginAmount = salesAmount - costAmount
```

Equivalente matematico:

$$
marginAmount = salesAmount - costAmount
$$

- Redondeo: a 2 decimales.
- Por que se calcula asi: da una lectura operativa de utilidad bruta por producto.

Nota importante: es un margen estimado, no necesariamente el margen financiero final.

#### marginPercent

- Que es: margen porcentual estimado del producto.
- Origen: derivado de `marginAmount` y `salesAmount`.
- Formula:

```text
marginPercent = (marginAmount / salesAmount) * 100
```

Equivalente matematico:

$$
marginPercent = \left(\frac{marginAmount}{salesAmount}\right) \times 100
$$

- Si `salesAmount = 0`, devuelve `0.0`.
- Redondeo: a 2 decimales.

#### currentStock

- Que es: stock actual disponible del producto.
- Origen: suma de `stock.quant.quantity` en ubicaciones internas, filtrada por almacen si corresponde.
- Redondeo: a 2 decimales.

#### averageStock

- Que es: stock promedio usado para la formula de rotacion.
- Origen real en esta implementacion: es exactamente el mismo valor que `currentStock`.
- Formula real actual:

```text
averageStock = currentStock
```

- Por que se calcula asi: deja la estructura preparada para una logica futura de stock promedio, aunque hoy usa una aproximacion simple.

Punto importante para la presentacion: el nombre `averageStock` puede sonar a promedio historico, pero en este codigo no lo es.

#### inventoryTurnover

- Que es: rotacion simple del producto.
- Origen: derivado de `quantitySold` y `averageStock`.
- Formula:

```text
inventoryTurnover = quantitySold / averageStock
```

Equivalente matematico:

$$
inventoryTurnover = \frac{quantitySold}{averageStock}
$$

- Si `averageStock <= 0`, devuelve `0.0`.
- Redondeo: a 2 decimales.
- Por que se calcula asi: da una senal rapida de que tan intensamente se mueve el producto frente al stock disponible.

#### lastSaleDate

- Que es: ultima fecha de venta conocida del producto.
- Origen: busqueda de la ultima `sale.order.line` historica del producto en pedidos `sale` o `done`, filtrada por almacen si se envio `warehouseId`.
- Formato: `YYYY-MM-DD`.

Punto importante: esta fecha no necesariamente queda restringida por `dateFrom` y `dateTo`. La funcion de ultima venta consulta el historial del producto, no solo las lineas del periodo principal.

#### movementStatus

- Que es: clasificacion operativa del movimiento del producto.
- Origen: regla interna del servicio.
- Regla exacta:

```text
si quantitySold <= 0 -> no_movement
si inventoryTurnover >= 5 o quantitySold >= 50 -> high_rotation
si inventoryTurnover >= 2 o quantitySold >= 10 -> medium_rotation
en otro caso -> low_rotation
```

- Por que se calcula asi: convierte metricas crudas en una etiqueta util para analitica y operacion.

#### stockStatus

- Que es: clasificacion operativa del estado del stock.
- Origen: regla interna del servicio.
- Regla exacta:

```text
si currentStock <= 0 -> out_of_stock
si quantitySold > 0 y currentStock <= max(quantitySold * 0.1, 1) -> low
si quantitySold > 0 y currentStock >= quantitySold * 2 -> overstock
en otro caso -> normal
```

- Por que se calcula asi: traduce el numero absoluto de stock a un estado util para toma de decisiones.

## 10. Como se ordena el resultado

El endpoint ordena el dataset con esta prioridad:

1. `quantitySold` descendente
2. `salesAmount` descendente
3. `productName` ascendente

Interpretacion:

- primero aparecen los productos con mayor salida
- si hay empate, sube el que vendio mas dinero
- si aun hay empate, se ordena alfabeticamente

## 11. Ejemplo de uso

### Request

```http
POST /api/bi/inventory-intelligent/products-sales
Access-Token: TU_TOKEN
Content-Type: application/json

{
  "filters": {
    "dateFrom": "2026-01-01",
    "dateTo": "2026-03-31",
    "warehouseId": 1,
    "categoryId": 2
  }
}
```

### Interpretacion del resultado

Con ese request, el endpoint devuelve una ficha analitica por producto para el rango consultado, con ventas, costo, margen, stock, rotacion, ultima fecha de venta y estados operativos.

## 12. Explicacion de la visual de Power BI compartida

La visual mostrada es una tabla o matriz por producto. Se observan estas columnas visibles:

- `productName`
- `Primera fecha: currentStock`
- `Primera fecha: inventoryTurnover`
- `Primera fecha: stockStatus`

### 12.1 Que esta mostrando realmente

La visual esta mostrando una ficha resumida por producto centrada en inventario y estado operativo. No es una grafica de tendencia, sino una tabla comparativa producto a producto.

Cada fila representa un producto. Cada columna representa un atributo o indicador de ese producto.

### 12.2 Explicacion de las columnas

#### Columna `productName`

- Que muestra: el nombre visible del producto.
- Origen: `product.display_name`.
- Como leerla: cada fila comienza con el producto al que pertenecen los demas valores de esa misma fila.

#### Columna `Primera fecha: currentStock`

- Que muestra: el stock actual del producto.
- Origen real: `currentStock` del endpoint, calculado desde `stock.quant`.
- Como leerla: indica cuantas unidades hay disponibles al momento de la consulta.

Nota importante sobre el prefijo `Primera fecha:`: ese texto parece venir de la configuracion del visual en Power BI, no del endpoint. Probablemente Power BI este aplicando una agregacion o etiquetado automatico. Para este caso, conceptualmente la columna sigue representando `currentStock`.

#### Columna `Primera fecha: inventoryTurnover`

- Que muestra: la rotacion simple del producto.
- Origen real: `inventoryTurnover = quantitySold / averageStock`.
- Como leerla: valores mas altos indican productos que se mueven mas intensamente respecto a su stock.

Ejemplo de lectura:

- un valor de `9.44` sugiere un producto con salida muy fuerte frente al stock considerado
- un valor de `2.78` indica menor intensidad relativa de movimiento

#### Columna `Primera fecha: stockStatus`

- Que muestra: el estado operativo del stock.
- Origen: clasificacion calculada por el endpoint.
- Valores esperados:
  - `out_of_stock`
  - `low`
  - `normal`
  - `overstock`

- Como leerla: traduce el dato numerico de stock a una alerta operativa.

En la captura:

- verde representa `normal`
- amarillo representa `low`

### 12.3 Explicacion de las filas

Cada fila corresponde a un producto individual. La fila debe leerse horizontalmente, uniendo todas sus columnas.

Ejemplo de lectura de una fila:

- si una fila muestra `Pizza de jamon y queso | 45 | 9.44 | normal`
- significa que ese producto tiene stock actual de 45 unidades, una rotacion calculada de 9.44 y un estado de stock clasificado como normal

Otro ejemplo:

- si una fila muestra `Bandeja de 2 muffin | 2 | 83.5 | low`
- significa que tiene muy poco stock actual, una rotacion muy alta y por eso cae en alerta de stock bajo

Eso vuelve la tabla util para lectura operativa inmediata: producto por producto, se puede ver si la intensidad de salida esta tensionando el inventario.

### 12.4 Lectura ejecutiva de la visual

La captura sugiere varias cosas:

- hay productos con rotaciones altas y stock todavia clasificado como normal
- hay otros con stock bajo aunque su rotacion o salida los hace sensibles a quiebre
- la tabla mezcla productos de muy distinta escala de stock, por lo que sirve mejor como herramienta de monitoreo puntual que como resumen ejecutivo de alto nivel

### 12.5 Riesgo de interpretacion

Hay varios puntos que conviene aclarar al presentar esta visual:

- `averageStock` no aparece visible, pero la rotacion depende de ese valor y hoy es igual a `currentStock`
- el prefijo `Primera fecha:` puede confundir, porque no representa una fecha del endpoint sino una etiqueta del visual
- una fila con `stockStatus = normal` no significa necesariamente que el producto este sobrado, solo que no cayo en las reglas de alerta `low`, `out_of_stock` u `overstock`

### 12.6 Recomendaciones para mejorar la visual

Opciones utiles para mejorar lectura y valor ejecutivo:

- renombrar columnas para quitar `Primera fecha:` y dejar solo `Stock actual`, `Rotacion`, `Estado de stock`
- agregar `quantitySold` y `salesAmount` como columnas visibles
- agregar `movementStatus` para cruzar movimiento y salud de stock
- agregar formato condicional tambien para `inventoryTurnover`
- ordenar la tabla por `inventoryTurnover` descendente o por `stockStatus` para priorizar alertas

## 13. Utilidades dentro del negocio

Este endpoint es especialmente valioso porque une venta e inventario a nivel de producto. Eso permite pasar de una lectura puramente comercial a una lectura operativa.

### 13.1 Aplicaciones practicas

- identificar productos con venta pero sin stock suficiente
- detectar productos con stock pero sin movimiento
- revisar rentabilidad por producto
- monitorear productos sensibles a quiebre
- comparar familias o categorias por salud de inventario

### 13.2 Utilidad por area

#### Ventas

- ayuda a evitar empujar productos con riesgo de quiebre
- permite enfocar promociones sobre productos con stock sano y buen margen
- facilita revisar que productos tienen salida real

#### Compras

- ayuda a priorizar pedidos de reposicion
- permite detectar productos con sobrestock o baja salida
- soporta negociacion sobre productos clave de alta rotacion

#### Operaciones e inventario

- da visibilidad producto por producto del equilibrio entre salida y disponibilidad
- ayuda a detectar alertas tempranas de stock bajo
- permite monitorear productos sin movimiento o con comportamiento atipico

#### Gerencia

- ayuda a leer salud del portafolio
- permite ver si el crecimiento en ventas esta acompanado por control operativo
- soporta decisiones de surtido, compra y precios

### 13.3 Ejemplos de decisiones que puede apoyar

#### Decision 1: reposicion inmediata

Si un producto tiene `stockStatus = low` y `inventoryTurnover` alto, conviene priorizar compra o produccion.

#### Decision 2: revision de rentabilidad

Si un producto vende bien pero su `marginPercent` es bajo, puede justificarse revisar costo, descuento o precio.

#### Decision 3: limpieza de catalogo

Si un producto aparece con stock pero `movementStatus = no_movement`, puede evaluarse liquidacion, sustitucion o reduccion de compra futura.

#### Decision 4: priorizacion de surtido

Si varios productos tienen buen movimiento y estado normal, pueden priorizarse en exhibicion, campañas o disponibilidad asegurada.

#### Decision 5: analisis por almacen o categoria

Usando `warehouseId` o `categoryId`, el negocio puede detectar si un problema de stock o rotacion esta concentrado en un almacen o familia especifica.

### 13.4 Valor analitico adicional

Con este endpoint se pueden construir analisis derivados:

- matriz movimiento vs stock
- tablero de riesgo de quiebre
- score de salud de producto
- comparativo por categoria o almacen
- ranking de productos sin venta pero con stock

El endpoint de venta por producto construye una ficha analitica completa por SKU combinando ventas, costo, margen, stock actual, rotacion y alertas operativas. Esto permite ver no solo que productos venden, sino si estan dejando margen y si el inventario actual es coherente con su demanda. La visual compartida funciona como una tabla de monitoreo producto a producto, donde cada fila resume la salud operativa del SKU y cada columna representa un indicador clave de disponibilidad o rotacion.

## 15. Conclusiones clave

- El endpoint combina ventas, inventario y catalogo de productos.
- Incluye productos con venta y tambien productos con stock aunque no hayan vendido.
- `quantitySold` usa `qty_delivered` y, si hace falta, `product_uom_qty`.
- `averageStock` hoy no es promedio historico real; es igual a `currentStock`.
- `inventoryTurnover` es una rotacion simple y operativa.
- `movementStatus` y `stockStatus` son clasificaciones por reglas de negocio internas.
- La visual de Power BI compartida se interpreta mejor como tabla operativa por producto, leyendo cada fila de forma horizontal.

## 16. Archivos tecnicos relacionados

- `custom_addons/cookoo/pbi_connections/controllers/inventory_dashboard.py`
- `custom_addons/cookoo/pbi_connections/controllers/base_dashboard.py`
- `custom_addons/cookoo/pbi_connections/models/inventory_dashboard.py`

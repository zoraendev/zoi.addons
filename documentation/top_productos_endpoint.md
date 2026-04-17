# Dashboard de Inventario - Endpoint de Top de Productos

Este documento describe en detalle el endpoint de top de productos del dashboard de inventario, el flujo interno de procesamiento, el origen de cada dato devuelto, la logica de calculo y la interpretacion de la grafica de Power BI compartida.

## 1. Objetivo del endpoint

El endpoint identifica los productos con mejor desempeno comercial dentro de un periodo, priorizando primero el volumen vendido y luego el monto vendido. Ademas del ranking, devuelve indicadores operativos y economicos para leer cada producto desde ventas, stock y margen.

En terminos de negocio, responde preguntas como:

- que productos salen mas
- cuales sostienen mas ingreso
- que margen estimado dejan
- con que stock actual se esta intentando sostener esa demanda

## 2. Rutas disponibles

El controlador expone dos rutas equivalentes:

- `/api/bi/inventory-intelligent/top-products`
- `/api/bi/advanced-metrics/inventory-intelligent/top-products`

Ambas llaman el mismo metodo de servicio: `get_top_products_report_data`.

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

El metodo `get_top_products` del controlador no calcula nada directamente. Su responsabilidad es:

1. Recibir la peticion.
2. Extraer filtros desde JSON body o query params.
3. Validar el token.
4. Delegar la logica al modelo `pbi_connections.inventory.dashboard`.

### 4.2 Extraccion de filtros

Los filtros se toman desde:

- `payload.filters`
- o el JSON completo si no existe la clave `filters`
- y luego se complementan o sobreescriben con query params

Para este endpoint, el controlador acepta estas claves generales del dashboard de inventario:

- `dateFrom`
- `dateTo`
- `warehouseId`
- `categoryId`
- `limit`
- `groupBy`
- `daysWithoutMovement`

Nota importante: aunque el controlador acepta varios filtros, el servicio de `top-products` solo usa `dateFrom`, `dateTo` y `limit`.

### 4.3 Normalizacion y validacion de filtros

El servicio normaliza los filtros asi:

- `dateFrom`: fecha inicial en formato `YYYY-MM-DD`
- `dateTo`: fecha final en formato `YYYY-MM-DD`
- `limit`: entero positivo, por defecto `10`, maximo `100`

Reglas de validacion:

- Si una fecha no usa formato valido, el servicio responde error `400`.
- Si `dateFrom > dateTo`, el servicio responde error `400`.
- Si `limit` no es entero positivo, el servicio responde error `400`.

## 5. Origen real de los datos

El endpoint combina informacion de varios modelos de Odoo:

- `sale.order.line` para leer la venta por producto
- `product.product` para datos maestros del producto
- `stock.quant` para leer stock actual

### 5.1 Dominio exacto sobre lineas de venta

La consulta base sobre `sale.order.line` usa estas reglas:

- `order_id.state in ('sale', 'done')`
- `display_type = False`
- `product_id != False`
- `product_id.sale_ok = True`
- `product_id.detailed_type in ('product', 'consu')` o `type in ('product', 'consu')` segun disponibilidad del modelo
- `order_id.date_order >= dateFrom 00:00:00`, si se envio `dateFrom`
- `order_id.date_order <= dateTo 23:59:59`, si se envio `dateTo`

Esto significa:

- solo entran lineas de pedidos confirmados o completados
- no entran lineas informativas, secciones o notas
- solo entran productos vendibles
- el analisis se centra en productos fisicos o consumibles

### 5.2 Origen del stock actual

El stock se calcula desde `stock.quant` con estas condiciones:

- `location_id.usage = 'internal'`
- producto vendible
- producto fisico o consumible

El stock se suma por producto en las ubicaciones internas disponibles.

## 6. Como se construyen las metricas

El servicio recorre las lineas de venta filtradas y agrupa por `product.id`. Para cada producto acumula:

- identificacion del producto
- unidades vendidas
- subtotal vendido
- stock actual
- margen estimado

## 7. Campos que devuelve la respuesta y como se calculan

La respuesta exitosa del controlador tiene esta estructura general:

```json
{
  "success": true,
  "message": "Top productos obtenido correctamente.",
  "generatedAt": "2026-04-16T12:00:00Z",
  "filters": {
    "dateFrom": "2026-01-01",
    "dateTo": "2026-03-31",
    "limit": 10
  },
  "data": [
    {
      "productId": 101,
      "productName": "Producto Ejemplo",
      "sku": "SKU-101",
      "categoryName": "Categoria X",
      "quantitySold": 140.0,
      "salesAmount": 25600.0,
      "currentStock": 18.0,
      "marginAmount": 6400.0,
      "marginPercent": 25.0,
      "inventoryTurnover": 7.78
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
- Significado: filtros normalizados que realmente se usaron.

#### data

- Origen: servicio.
- Significado: lista de productos agregados, ordenados y limitados.

### Explicacion de cada campo dentro de data

#### productId

- Origen: `product.product.id`.
- Uso: llave tecnica para relacionar con dimensiones de producto, costos, categorias o reportes auxiliares.

#### productName

- Origen: `product.display_name`.
- Uso: etiqueta visible para rankings y graficas.

#### sku

- Origen: `product.default_code`.
- Uso: identificacion interna del producto; suele ser mas confiable que el nombre para operacion.

#### categoryName

- Origen: `product.categ_id.display_name`.
- Uso: agrupacion por familia o categoria.

#### quantitySold

- Que es: unidades vendidas del producto en el periodo.
- Origen: suma de `sale.order.line.product_uom_qty`.
- Formula:

```text
quantitySold = suma(product_uom_qty de todas las lineas del producto)
```

- Regla especial: si una linea tiene cantidad menor o igual a cero, se excluye.
- Redondeo: a 2 decimales.
- Por que se calcula asi: porque el endpoint esta pensado como ranking de productos mas vendidos y la metrica primaria del servicio es volumen.

#### salesAmount

- Que es: monto total vendido del producto en el periodo.
- Origen: suma de `sale.order.line.price_subtotal`.
- Formula:

```text
salesAmount = suma(price_subtotal de todas las lineas del producto)
```

- Redondeo: a 2 decimales.
- Por que se calcula asi: porque volumen sin ingreso puede ocultar productos poco relevantes economicamente.

#### currentStock

- Que es: stock actual del producto al momento de la consulta.
- Origen: suma de `stock.quant.quantity` en ubicaciones internas.
- Formula:

```text
currentStock = suma(quantity de stock.quant para el producto en ubicaciones internas)
```

- Redondeo: a 2 decimales.
- Por que se calcula asi: porque el negocio necesita contrastar venta contra disponibilidad actual para detectar riesgo operativo.

#### marginAmount

- Que es: margen monetario estimado del producto.
- Origen: calculado por linea y luego acumulado.
- Formula real por linea:

```text
unitCost = line.purchase_price o product.standard_price o 0
marginAmountLinea = price_subtotal - (product_uom_qty * unitCost)
```

Formula agregada:

```text
marginAmount = suma(marginAmountLinea de todas las lineas del producto)
```

Equivalente matematico:

$$
marginAmount = \sum (subtotal\_linea - cantidad\_linea \times costo\_unitario)
$$

- Redondeo: a 2 decimales.
- Por que se calcula asi: porque permite una lectura de rentabilidad sin depender de un modulo contable adicional. Es una estimacion operativa de margen bruto.

Nota importante: este margen es estimado, no necesariamente coincide con margen contable final. Depende del costo disponible en la linea o del `standard_price` del producto.

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
- Por que se calcula asi: porque permite comparar rentabilidad relativa entre productos grandes y pequenos.

#### inventoryTurnover

- Que es: rotacion simple del inventario frente al stock actual.
- Origen: derivado de `quantitySold` y `currentStock`.
- Formula:

```text
inventoryTurnover = quantitySold / currentStock
```

Equivalente matematico:

$$
inventoryTurnover = \frac{quantitySold}{currentStock}
$$

- Si `currentStock <= 0`, devuelve `0.0`.
- Redondeo: a 2 decimales.
- Por que se calcula asi: porque da una senal rapida de que tan exigido esta el stock actual frente al volumen vendido.

Nota importante: en esta implementacion no es una rotacion contable clasica basada en inventario promedio historico. Es una aproximacion simple y operativa usando stock actual.

## 8. Como se ordena el ranking

El endpoint ordena el resultado con esta prioridad:

1. `quantitySold` descendente
2. `salesAmount` descendente

Interpretacion:

- primero suben los productos con mas unidades vendidas
- si hay empate en unidades, gana el que vendio mas monto

Esto significa que el endpoint se llama correctamente "top productos" en clave de salida o demanda, no necesariamente en clave de ingreso o margen.

## 9. Ejemplo de uso

### Request

```http
POST /api/bi/inventory-intelligent/top-products
Access-Token: TU_TOKEN
Content-Type: application/json

{
  "filters": {
    "dateFrom": "2026-01-01",
    "dateTo": "2026-03-31",
    "limit": 10
  }
}
```

### Interpretacion del resultado

Con ese request, el endpoint devuelve los 10 productos con mayor cantidad vendida entre el 1 de enero y el 31 de marzo de 2026, junto con monto vendido, stock actual, margen estimado, porcentaje de margen y rotacion simple.

## 10. Explicacion de la grafica de Power BI compartida

La visual mostrada es un grafico combinado por producto con estas caracteristicas visibles:

- categoria en eje X: `productName`
- barras: `salesAmount`
- linea: `marginAmount`
- titulo visible: `Suma de salesAmount y Suma de marginAmount por productName`

### 10.1 Que esta mostrando realmente

La grafica compara ingreso vendido y margen estimado por producto dentro del dataset cargado.

La lectura conceptual es correcta porque ambos campos existen en el endpoint. Sin embargo, la forma en que se ven en la captura sugiere un problema de escala visual o de calidad del dato del margen.

### 10.2 Lectura del grafico

Segun la captura:

- las barras de `salesAmount` muestran una caida progresiva desde productos con ventas cercanas a 25 mil hacia productos de menor ingreso
- la linea de `marginAmount` aparece casi plana alrededor de cero en la mayor parte de los productos
- en uno de los primeros productos se observa una caida muy fuerte de la linea, cercana a valores negativos muy altos en el eje derecho

Interpretacion posible:

- existe al menos un producto con margen fuertemente negativo o anomalo
- ese outlier esta forzando la escala del eje secundario
- por esa razon, el resto de los margenes quedan visualmente aplastados y parecen casi cero

### 10.3 Que relacion tiene con el endpoint

La grafica esta usando dos metricas validas del endpoint:

- `salesAmount`
- `marginAmount`

Pero hay una advertencia importante: el endpoint ordena productos por `quantitySold`, no por `salesAmount` ni por `marginAmount`. Si Power BI reordena por monto o si no mantiene el orden del endpoint, la narrativa visual cambia.

Ademas, como `marginAmount` depende de `purchase_price` o `standard_price`, una configuracion de costo incorrecta puede generar margenes negativos exagerados y distorsionar la visual.

### 10.4 Como explicarla en una presentacion

Puedes presentarla asi:

"Esta visual compara el ingreso generado por cada producto frente al margen estimado que deja. Las barras muestran cuales productos aportan mas venta, mientras la linea intenta reflejar la contribucion economica. En la captura se observa un outlier de margen muy negativo que comprime visualmente el resto de los productos, por lo que la lectura de rentabilidad debe hacerse con cautela y validando los costos base."

### 10.5 Riesgos de interpretacion

Hay varios riesgos que conviene aclarar:

- una venta alta no implica necesariamente un margen alto
- un margen negativo extremo puede deberse a un costo mal cargado, no solo a una decision comercial real
- al usar doble eje, la audiencia puede sobreestimar o subestimar diferencias si no entiende la escala

### 10.6 Recomendaciones para mejorar la visual

Opciones utiles para mejorar legibilidad y valor analitico:

- mostrar `marginPercent` en lugar de `marginAmount` si se quiere comparar rentabilidad relativa
- separar la vista en dos visuales: ventas por producto y margen por producto
- ordenar por `salesAmount` si el objetivo es facturacion, o por `marginAmount` si el objetivo es rentabilidad
- filtrar o tratar outliers de margen antes de presentar
- agregar tabla de detalle con `sku`, `salesAmount`, `marginAmount` y `marginPercent`

## 11. Utilidades dentro del negocio

Este endpoint sirve para mucho mas que un ranking de productos. Es una vista operativa y comercial de que productos venden, cuanto dinero mueven y que tension generan sobre el stock.

### 11.1 Aplicaciones practicas

- identificar productos estrella por volumen
- detectar productos importantes por ingreso
- revisar si los productos mas vendidos tambien son rentables
- priorizar compras o reposicion de productos de alta salida
- detectar productos con alta venta pero margen debil
- identificar productos con posible riesgo de quiebre de stock

### 11.2 Utilidad por area

#### Ventas

- ayuda a enfocar el esfuerzo comercial en productos que realmente salen
- permite revisar si las promociones estan empujando productos rentables o no
- facilita detectar productos tractores del portafolio

#### Compras

- ayuda a priorizar reabastecimiento de productos con alta salida
- permite detectar productos que exigen stock pero dejan poco margen
- sirve para negociar mejor costo con proveedores en productos clave

#### Operaciones e inventario

- ayuda a anticipar productos que pueden quedarse sin stock
- permite contrastar salida contra inventario actual
- da visibilidad sobre productos con rotacion alta que requieren seguimiento continuo

#### Gerencia

- permite ver si el volumen esta concentrado en pocos productos
- ayuda a entender si los productos mas vendidos tambien son los que mas rentan
- soporta decisiones de surtido, pricing y foco comercial

### 11.3 Ejemplos de decisiones que puede apoyar

#### Decision 1: reposicion prioritaria

Si un producto aparece con `quantitySold` alto y `currentStock` bajo, puede priorizarse en compras o produccion antes de que ocurra un quiebre.

#### Decision 2: revision de rentabilidad

Si un producto tiene `salesAmount` alto pero `marginAmount` bajo o negativo, conviene revisar costo, precio, descuentos o mermas antes de seguir empujandolo comercialmente.

#### Decision 3: foco promocional

Si un producto tiene buen margen y buena salida, puede convertirse en producto prioritario para campanas o exhibicion.

#### Decision 4: depuracion del portafolio

Si el negocio observa que pocos productos concentran la mayoria del ingreso y el resto tiene desempeno marginal, puede revisar el surtido para simplificar operacion y compras.

#### Decision 5: negociacion con proveedores

Si un SKU clave tiene alta salida pero margen insuficiente, ese producto puede priorizarse en renegociaciones de costo o condiciones.

### 11.4 Valor analitico adicional

Con este endpoint se pueden construir analisis derivados:

- clasificacion ABC por producto
- matriz volumen vs margen
- analisis de dependencia en pocos SKU
- tablero de riesgo de quiebre en productos estrella
- comparativo entre productos de alta venta y alta rentabilidad

El endpoint de top de productos consolida las lineas de venta confirmadas por producto y combina volumen, ingreso, margen estimado y stock actual. Esto permite identificar no solo que productos venden mas, sino cuales sostienen el negocio y cuales requieren una intervencion operativa o comercial. En la visual compartida se observa un outlier de margen que distorsiona la lectura de rentabilidad, por lo que conviene validar costos y complementar la presentacion con margen porcentual.

## 13. Conclusiones clave

- El origen principal del endpoint es `sale.order.line`.
- El stock actual proviene de `stock.quant` en ubicaciones internas.
- Solo considera lineas de ventas confirmadas o completadas.
- El ranking base se ordena por `quantitySold` y luego por `salesAmount`.
- `marginAmount` es una estimacion operativa, no un margen contable final.
- `inventoryTurnover` usa stock actual, no inventario promedio historico.
- La grafica de Power BI compartida es util, pero el eje de margen parece distorsionado por un outlier o por costos anómalos.

## 14. Archivos tecnicos relacionados

- `custom_addons/cookoo/pbi_connections/controllers/inventory_dashboard.py`
- `custom_addons/cookoo/pbi_connections/controllers/base_dashboard.py`
- `custom_addons/cookoo/pbi_connections/models/inventory_dashboard.py`

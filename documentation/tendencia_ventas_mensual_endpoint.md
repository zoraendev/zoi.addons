# Dashboard de Inventario - Endpoint de Tendencia de Ventas Mensual

Este documento describe en detalle el endpoint de tendencia de ventas del dashboard de inventario, el flujo interno de procesamiento, el origen de cada dato devuelto, la logica de calculo y la interpretacion de la visual de Power BI compartida.

Aunque el endpoint soporta agrupacion diaria, semanal o mensual, la visual enviada corresponde a una lectura mensual. Por eso este documento pone enfasis en ese uso.

## 1. Objetivo del endpoint

El endpoint mide la evolucion de las ventas a lo largo del tiempo. No trabaja a nivel cliente ni producto individual, sino a nivel periodo agregado.

Su objetivo es responder preguntas como:

- como se comportan las ventas a traves del tiempo
- si el ingreso sube o baja entre periodos
- si el volumen vendido acompana el ingreso o se mueve distinto
- cuanto se ha vendido en ventanas recientes de 7, 15 y 30 dias

## 2. Rutas disponibles

El controlador expone dos rutas equivalentes:

- `/api/bi/inventory-intelligent/sales-trend`
- `/api/bi/advanced-metrics/inventory-intelligent/sales-trend`

Ambas llaman el mismo metodo de servicio: `get_sales_trend_report_data`.

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

El metodo `get_sales_trend` del controlador no realiza calculos directos. Su trabajo es:

1. Recibir la peticion.
2. Extraer filtros desde JSON body o query params.
3. Validar el token.
4. Delegar el procesamiento al modelo `pbi_connections.inventory.dashboard`.

Ademas, este endpoint devuelve una clave adicional llamada `periodSummary`.

### 4.2 Extraccion de filtros

Los filtros se toman desde:

- `payload.filters`
- o el JSON completo si no existe la clave `filters`
- y luego se complementan o sobreescriben con query params

Para este endpoint, el controlador acepta estas claves generales:

- `dateFrom`
- `dateTo`
- `warehouseId`
- `categoryId`
- `limit`
- `groupBy`
- `daysWithoutMovement`

Nota importante: en `sales-trend`, el servicio realmente usa `dateFrom`, `dateTo`, `warehouseId` y `groupBy`. No usa `limit`, `daysWithoutMovement` ni `categoryId` en la consulta principal de este endpoint.

## 5. Normalizacion y validacion de filtros

El servicio normaliza los filtros asi:

- `dateFrom`: fecha inicial en formato `YYYY-MM-DD`
- `dateTo`: fecha final en formato `YYYY-MM-DD`
- `warehouseId`: entero opcional
- `categoryId`: entero opcional heredado de la normalizacion base, aunque este endpoint no lo usa despues
- `groupBy`: `day`, `week` o `month`

Reglas de validacion:

- Si una fecha no usa formato valido, responde error `400`.
- Si `dateFrom > dateTo`, responde error `400`.
- Si `warehouseId` o `categoryId` no son enteros cuando se envian, responde error `400`.
- Si `groupBy` no es `day`, `week` o `month`, responde error `400`.

## 6. Origen real de los datos

El origen principal del endpoint es `sale.order.line`.

La consulta usa estas reglas:

- `order_id.state in ('sale', 'done')`
- `display_type = False`
- `product_id != False`
- `product_id.sale_ok = True`
- `product_id.detailed_type in ('product', 'consu')` o `type in ('product', 'consu')` segun disponibilidad
- `order_id.date_order >= dateFrom 00:00:00`, si se envio `dateFrom`
- `order_id.date_order <= dateTo 23:59:59`, si se envio `dateTo`
- `order_id.warehouse_id = warehouseId`, si se envio `warehouseId`

Esto significa:

- solo entran ventas confirmadas o completadas
- no entran lineas informativas
- el analisis se hace sobre lineas de productos vendibles

## 7. Como se construyen las metricas

Por cada linea de venta valida, el servicio:

1. toma la fecha de la orden
2. la convierte en un bucket temporal segun `groupBy`
3. suma cantidad vendida y monto vendido a ese bucket
4. adicionalmente acumula un resumen movil de los ultimos 7, 15 y 30 dias

### 7.1 Como se define el bucket temporal

- Si `groupBy = day`, el bucket es la fecha exacta
- Si `groupBy = week`, el bucket se mueve al lunes de esa semana
- Si `groupBy = month`, el bucket se mueve al primer dia del mes

Formula conceptual:

```text
day   -> YYYY-MM-DD real de la venta
week  -> lunes de la semana de la venta
month -> primer dia del mes de la venta
```

Para la visual compartida, el comportamiento relevante es `groupBy = month`, por lo que enero 2026 se representa como `2026-01-01`, febrero 2026 como `2026-02-01`, etc.

### 7.2 Fecha ancla para periodSummary

El resumen de ultimos 7, 15 y 30 dias se calcula contra una fecha ancla:

- si se envio `dateTo`, la fecha ancla es `dateTo`
- si no se envio `dateTo`, la fecha ancla es la fecha actual del contexto Odoo

## 8. Campos que devuelve la respuesta y como se calculan

La respuesta exitosa del controlador tiene esta estructura general:

```json
{
  "success": true,
  "message": "Tendencia de ventas obtenida correctamente.",
  "generatedAt": "2026-04-16T12:00:00Z",
  "filters": {
    "dateFrom": "2026-01-01",
    "dateTo": "2026-03-31",
    "warehouseId": 1,
    "groupBy": "month"
  },
  "data": [
    {
      "date": "2026-01-01",
      "quantitySold": 5900.0,
      "salesAmount": 80000.0
    },
    {
      "date": "2026-02-01",
      "quantitySold": 5000.0,
      "salesAmount": 69000.0
    },
    {
      "date": "2026-03-01",
      "quantitySold": 15200.0,
      "salesAmount": 162000.0
    }
  ],
  "periodSummary": {
    "last7Days": {
      "quantitySold": 2400.0,
      "salesAmount": 28000.0
    },
    "last15Days": {
      "quantitySold": 5100.0,
      "salesAmount": 61000.0
    },
    "last30Days": {
      "quantitySold": 9800.0,
      "salesAmount": 120000.0
    }
  }
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
- Significado: filtros normalizados usados realmente en la consulta.

#### data

- Origen: servicio.
- Significado: serie temporal agregada por dia, semana o mes segun `groupBy`.

#### periodSummary

- Origen: servicio.
- Significado: resumen acumulado de ventas y cantidad para ventanas recientes de 7, 15 y 30 dias.
- Uso: KPI rapidos o tarjetas resumen en dashboard.

### Explicacion de cada campo dentro de data

#### date

- Que es: fecha representativa del bucket temporal.
- Origen: calculada por `_get_period_bucket`.
- Formato: `YYYY-MM-DD`.

Interpretacion segun agrupacion:

- en `day`, es la fecha exacta
- en `week`, es el lunes de la semana
- en `month`, es el primer dia del mes

#### quantitySold

- Que es: cantidad vendida total en ese periodo.
- Origen: suma de `qty_delivered` y, si hace falta, `product_uom_qty`.
- Formula:

```text
quantitySold = suma(qty_delivered o product_uom_qty dentro del bucket)
```

- Redondeo: a 2 decimales.
- Por que se calcula asi: busca representar el volumen fisico vendido dentro del periodo.

#### salesAmount

- Que es: monto vendido total en ese periodo.
- Origen: suma de `price_subtotal` de las lineas incluidas en el bucket.
- Formula:

```text
salesAmount = suma(price_subtotal dentro del bucket)
```

- Redondeo: a 2 decimales.
- Por que se calcula asi: representa el ingreso comercial del periodo.

### Explicacion de cada campo dentro de periodSummary

Cada bloque `last7Days`, `last15Days` y `last30Days` contiene:

- `quantitySold`: cantidad total vendida dentro de esa ventana movil
- `salesAmount`: monto total vendido dentro de esa ventana movil

La ventana se evalua contra `dateTo` o contra hoy si no hay `dateTo`.

Ejemplo conceptual para `last7Days`:

$$
ventana = [fecha\_ancla - 6, fecha\_ancla]
$$

El mismo criterio aplica para 15 y 30 dias.

## 9. Como se ordena el resultado

El servicio ordena la serie temporal por fecha ascendente.

Interpretacion:

- primero aparece el periodo mas antiguo
- al final aparece el periodo mas reciente

Esto es correcto para una visual de tendencia.

## 10. Ejemplo de uso

### Request

```http
POST /api/bi/inventory-intelligent/sales-trend
Access-Token: TU_TOKEN
Content-Type: application/json

{
  "filters": {
    "dateFrom": "2026-01-01",
    "dateTo": "2026-03-31",
    "warehouseId": 1,
    "groupBy": "month"
  }
}
```

### Interpretacion del resultado

Con ese request, el endpoint devuelve una serie mensual con ventas monetarias y cantidad vendida de enero a marzo de 2026, mas un resumen movil de ultimos 7, 15 y 30 dias al cierre del 31 de marzo.

## 11. Explicacion de la visual de Power BI compartida

La visual mostrada es un grafico de tendencia temporal con dos series sobre el eje X `date`:

- serie 1: `Suma de salesAmount`
- serie 2: `Suma de quantitySold`

Tambien usa doble eje vertical:

- eje izquierdo: `Suma de salesAmount`
- eje derecho: `Suma de quantitySold`

### 11.1 Que esta mostrando realmente

La visual compara la evolucion mensual del ingreso vendido y del volumen vendido. No compara rentabilidad, ni clientes, ni productos individuales. Mide comportamiento agregado del negocio por mes.

### 11.2 Como leer el eje X

En la captura se observan tres puntos temporales:

- `ene 2026`
- `feb 2026`
- `mar 2026`

Cada punto representa un bucket mensual construido por el endpoint cuando `groupBy = month`.

### 11.3 Como leer las dos series

#### Serie `salesAmount`

- mide ingreso total del mes
- usa el eje izquierdo
- en la captura pasa aproximadamente de 80 mil en enero a 69 mil en febrero y luego sube a mas de 160 mil en marzo

#### Serie `quantitySold`

- mide volumen total vendido del mes
- usa el eje derecho
- en la captura pasa aproximadamente de 6 mil en enero a 5 mil en febrero y luego sube a cerca de 15 mil en marzo

### 11.4 Lectura ejecutiva de la tendencia

La visual sugiere este comportamiento:

- enero arranca en un nivel medio-alto
- febrero muestra una caida tanto en ingreso como en cantidad
- marzo presenta un repunte muy fuerte en ambas metricas

Interpretacion de negocio:

- la subida de marzo no parece ser solo efecto de precio, porque tambien sube con fuerza `quantitySold`
- eso sugiere mayor demanda real, mayor salida de unidades o un impulso comercial importante
- febrero podria haber sido un mes de menor actividad, menor cobertura o menor ejecucion comercial

### 11.5 Que dice la relacion entre ambas lineas

Como ambas curvas se mueven casi en paralelo, la visual sugiere que el ingreso esta creciendo acompasado con el volumen. Eso implica que, al menos a nivel agregado, no se ve una divergencia fuerte entre vender mas dinero y vender mas unidades.

Si en otra lectura ambas series se separaran mucho, eso podria sugerir cambios de precio, mix de productos o descuentos.

### 11.6 Riesgo de interpretacion por doble eje

El doble eje facilita leer dos magnitudes distintas, pero tambien puede inducir a conclusiones visuales exageradas.

Riesgos concretos:

- dos lineas con pendiente similar no significan que las tasas de crecimiento sean identicas
- el ojo puede interpretar correlacion perfecta aunque las escalas sean diferentes
- la audiencia puede olvidar que `salesAmount` y `quantitySold` usan ejes distintos

Por eso, al presentar esta visual conviene decir explicitamente que:

- el eje izquierdo es dinero
- el eje derecho es unidades

### 11.7 Como explicarla en una presentacion

Puedes presentarla asi:

"Esta visual muestra la tendencia mensual de ventas comparando ingreso y volumen. En enero y febrero se observa una desaceleracion moderada, mientras que marzo presenta un crecimiento muy fuerte tanto en dinero como en unidades. Como ambas curvas suben en paralelo, la mejora de marzo parece venir de mayor salida real y no solo de cambios de precio o mix."

### 11.8 Recomendaciones para mejorar la visual

Opciones utiles para fortalecer la lectura:

- agregar etiquetas de datos por mes
- mostrar variacion porcentual mes contra mes
- incluir tarjetas con `periodSummary` de ultimos 7, 15 y 30 dias
- si la audiencia se confunde con doble eje, separar en dos visuales: monto y unidades
- agregar filtro por almacen para comparar comportamiento entre ubicaciones

## 12. Utilidades dentro del negocio

Este endpoint sirve para monitoreo directivo y comercial del pulso del negocio en el tiempo.

### 12.1 Aplicaciones practicas

- detectar caidas o repuntes de venta
- comparar comportamiento entre meses, semanas o dias
- medir si el volumen acompana al ingreso
- monitorear ultimos 7, 15 y 30 dias
- evaluar impacto de campañas o eventos comerciales

### 12.2 Utilidad por area

#### Ventas

- ayuda a medir ejecucion comercial en el tiempo
- permite detectar meses flojos o periodos de aceleracion
- sirve para evaluar impacto de promociones

#### Operaciones

- ayuda a anticipar necesidades si el volumen vendido acelera
- permite detectar periodos de mayor presion operativa

#### Gerencia

- da visibilidad clara sobre tendencia general del negocio
- permite separar crecimiento real de ruido temporal
- soporta decisiones de presupuesto, compra y capacidad

#### Planeacion

- permite contrastar desempeno reciente con ventanas moviles
- ayuda a ajustar proyecciones de demanda y abastecimiento

### 12.3 Ejemplos de decisiones que puede apoyar

#### Decision 1: reaccion ante caidas

Si la tendencia muestra dos periodos consecutivos a la baja, se puede activar una revision comercial, de surtido o de cobertura.

#### Decision 2: preparacion operativa

Si el volumen vendido acelera fuertemente, operaciones puede anticipar compras, produccion o refuerzo de inventario.

#### Decision 3: evaluacion de campanas

Si despues de una accion comercial suben `salesAmount` y `quantitySold`, el negocio tiene evidencia de impacto real en la salida.

#### Decision 4: deteccion de crecimiento no saludable

Si el ingreso sube pero la cantidad no acompana, puede revisarse si el crecimiento depende demasiado de precio o de pocos productos.

#### Decision 5: comparacion por almacen

Usando `warehouseId`, se puede ver si una tendencia positiva o negativa viene de una ubicacion especifica.

### 12.4 Valor analitico adicional

Con este endpoint se pueden construir analisis derivados:

- variacion porcentual por periodo
- acumulado YTD
- comparativo contra periodo anterior
- ritmo reciente con `periodSummary`
- estacionalidad por semana o mes

El endpoint de tendencia de ventas consolida las lineas de venta por periodo y compara ingreso con volumen vendido. Esto permite monitorear el pulso comercial del negocio y detectar caidas, recuperaciones o aceleraciones. En la visual compartida se observa una caida de febrero seguida por un repunte muy fuerte en marzo, con ambas curvas moviendose de forma paralela, lo que sugiere crecimiento real en unidades y no solo en valor monetario.

## 14. Conclusiones clave

- El origen principal del endpoint es `sale.order.line`.
- La serie puede agruparse por dia, semana o mes.
- La visual compartida corresponde a `groupBy = month`.
- `salesAmount` mide ingreso y `quantitySold` mide volumen.
- El endpoint devuelve ademas un `periodSummary` de ultimos 7, 15 y 30 dias.
- La visual con doble eje es util, pero conviene explicitar siempre que compara dinero contra unidades.

## 15. Archivos tecnicos relacionados

- `custom_addons/cookoo/pbi_connections/controllers/inventory_dashboard.py`
- `custom_addons/cookoo/pbi_connections/controllers/base_dashboard.py`
- `custom_addons/cookoo/pbi_connections/models/inventory_dashboard.py`

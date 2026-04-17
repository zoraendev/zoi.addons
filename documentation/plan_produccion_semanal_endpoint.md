# Dashboard de Produccion - Endpoint de Plan de Produccion Semanal

Este documento describe en detalle el endpoint de plan de produccion semanal, el flujo interno de procesamiento, el origen de cada dato devuelto, la logica de calculo y la interpretacion de las visuales de Power BI compartidas.

En este caso hay una diferencia importante frente a otros endpoints: el API de `pbi_connections.inventory.dashboard` funciona como wrapper y delega la logica principal a un asistente de `advanced_metrics.report.wizard`.

## 1. Objetivo del endpoint

El endpoint genera una vista operativa para planificacion de produccion a partir de pedidos de venta ya confirmados y el inventario actual disponible.

No mide facturacion ni rotacion. Su finalidad es responder preguntas operativas como:

- que productos deben entregarse en una fecha dada
- que cantidad ya esta cubierta por inventario
- que cantidad falta producir para cubrir la demanda
- como se distribuye la carga de produccion por fecha y por dia de semana

## 2. Rutas disponibles

El controlador expone dos rutas equivalentes:

- `/api/bi/production/weekly-plan`
- `/api/bi/advanced-metrics/production/weekly-plan`

Ambas llaman el mismo metodo de servicio: `get_weekly_production_plan_report_data`.

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

El metodo `get_weekly_production_plan` del controlador no calcula datos directamente. Su responsabilidad es:

1. Recibir la peticion.
2. Extraer filtros desde JSON body o query params.
3. Validar el token.
4. Delegar el procesamiento al modelo `pbi_connections.inventory.dashboard`.

### 4.2 Servicio intermedio en pbi_connections

El modelo `pbi_connections.inventory.dashboard` hace tres cosas:

1. normaliza filtros de fecha y filtros del asistente
2. detecta si existe `pbi_connections.report.wizard` o `advanced_metrics.report.wizard`
3. llama `get_sales_orders_report_rows(wizard_filters)` y devuelve esas filas como `data`

Esto significa que la logica real del plan de produccion no esta implementada en el endpoint mismo, sino en el asistente `advanced_metrics.report.wizard` visible en el workspace.

### 4.3 Extraccion de filtros

Los filtros se toman desde:

- `payload.filters`
- o el JSON completo si no existe la clave `filters`
- y luego se complementan o sobreescriben con query params

Para este endpoint, el servicio normaliza y soporta especialmente:

- `dateFrom`
- `dateTo`
- `fecha_entrega_desde`
- `fecha_entrega_hasta`
- `cliente_id`
- `cliente_nombre`

Cuando `dateFrom` y `dateTo` existen, el servicio los copia tambien como:

- `fecha_entrega_desde = dateFrom`
- `fecha_entrega_hasta = dateTo`

Esto asegura compatibilidad entre el endpoint de API y el asistente original del modulo.

## 5. Normalizacion y validacion de filtros

El servicio normaliza los filtros asi:

- `dateFrom`: fecha inicial en formato `YYYY-MM-DD`
- `dateTo`: fecha final en formato `YYYY-MM-DD`
- `cliente_id`: valor opcional
- `cliente_nombre`: valor opcional
- `fecha_entrega_desde`: valor opcional
- `fecha_entrega_hasta`: valor opcional

Reglas importantes:

- si `dateFrom` y `dateTo` vienen, deben ser fechas validas
- si `dateFrom > dateTo`, la peticion se invalida
- si existen los filtros del asistente, se pasan al wizard sin transformacion adicional salvo el mapeo de fechas

## 6. Origen real de los datos

La logica principal del asistente `advanced_metrics.report.wizard` trabaja con:

- `sale.order.line` para pedidos confirmados o completados
- `stock.quant` para inventario actual y libre de usar

### 6.1 Dominio exacto sobre ventas

El asistente consulta `sale.order.line` con estas condiciones base:

- `order_id.state in ('sale', 'done')`
- `display_type = False`

Filtros adicionales soportados:

- `order_id.commitment_date >= fecha_entrega_desde 00:00:00`
- `order_id.commitment_date <= fecha_entrega_hasta 23:59:59`
- `order_partner_id = cliente_id`, si se envia `cliente_id`
- `order_partner_id.name ilike cliente_nombre`, si se envia `cliente_nombre` y no existe `cliente_id`

Punto importante: el filtro de fecha principal usa `commitment_date`, no `date_order`.

Eso tiene sentido operativo porque este reporte busca planificar entregas y produccion, no analizar fecha de venta.

### 6.2 Respaldo de fecha cuando falta commitment_date

Para mostrar la fecha final de cada fila y para ordenar cronologicamente, el wizard usa esta cascada:

```text
fecha_entrega = commitment_date o date_order o fecha actual
```

Esto es importante porque:

- la busqueda principal se apoya en `commitment_date`
- pero si una orden no tiene ese campo, la fila aun puede apoyarse en `date_order` para representacion interna

## 7. Como se construye la cantidad sugerida a producir

Esta es la parte central del endpoint.

### 7.1 Inventario snapshot inicial

El wizard agrupa `stock.quant` por producto en ubicaciones internas y obtiene dos valores:

- `quantity`: stock fisico total
- `available_quantity`: stock libre de usar despues de reservas

Con eso arma dos memorias virtuales por producto:

- `running_stock_by_product`
- `running_free_stock_by_product`

### 7.2 Ordenamiento cronologico FIFO

Las lineas de venta se ordenan cronologicamente por fecha de entrega para consumir el inventario en secuencia.

La idea es:

- primero se atiende la entrega mas temprana
- luego la siguiente
- y asi sucesivamente

Eso evita sobreestimar el stock disponible para pedidos futuros.

### 7.3 Regla exacta de asignacion de stock y sugerencia

Para cada linea de venta:

- `sold_qty = product_uom_qty`
- `available_qty_before = stock virtual antes de procesar esta linea`
- `free_qty_before = inventario libre virtual antes de procesar esta linea`

Luego aplica esta regla:

```text
si available_qty_before >= sold_qty:
    cantidad_sugerida_producir = 0
    running_stock -= sold_qty

si available_qty_before < sold_qty:
    cantidad_sugerida_producir = sold_qty - available_qty_before
    running_stock = 0
```

Equivalente matematico:

$$
cantidad\_sugerida\_producir = max(cantidad\_vendida - inventario\_disponible\_antes, 0)
$$

Por que se calcula asi:

- si ya hay inventario suficiente, no hace falta producir
- si no alcanza, solo se sugiere producir el faltante neto

### 7.4 Que significa inventario disponible en cada fila

El campo `inventario_disponible` no es un stock estatico global. Es el stock que habia justo antes de consumir esa linea segun la simulacion cronologica.

Eso vuelve el reporte mucho mas util operativamente, porque cada fila refleja la disponibilidad real despues de considerar pedidos anteriores del mismo producto.

### 7.5 Que significa inventario libre de usar

El campo `inventario_libre_usar` viene de `available_quantity` en `stock.quant` y representa el stock no reservado.

El wizard tambien lo va descontando virtualmente durante el recorrido cronologico, aunque la sugerencia principal de produccion se basa en `inventario_disponible`.

## 8. Campos que devuelve la respuesta y como se calculan

La respuesta exitosa del endpoint contiene esta estructura general:

```json
{
  "success": true,
  "message": "Plan de produccion obtenido correctamente.",
  "generatedAt": "2026-04-16T12:00:00Z",
  "filters": {
    "dateFrom": "2026-03-26",
    "dateTo": "2026-04-06",
    "fecha_entrega_desde": "2026-03-26",
    "fecha_entrega_hasta": "2026-04-06"
  },
  "data": [
    {
      "fecha_entrega": "2026-03-30",
      "dia_semana": "Lunes",
      "cliente": "Cliente Ejemplo",
      "numero_orden_venta": "S00045",
      "producto": "Pizza de pepperoni",
      "cantidad_vendida": 56.0,
      "inventario_disponible": 0.0,
      "inventario_libre_usar": 0.0,
      "cantidad_sugerida_producir": 56.0
    }
  ]
}
```

### Explicacion de cada campo dentro de data

#### fecha_entrega

- Que es: fecha en la que debe atenderse la orden en el reporte.
- Origen: `commitment_date` o `date_order` como respaldo.
- Formato: `YYYY-MM-DD`.
- Uso: planificar el dia de produccion o despacho.

#### dia_semana

- Que es: nombre del dia de la semana en espanol.
- Origen: calculado desde `fecha_entrega`.
- Valores posibles: `Lunes`, `Martes`, `Miercoles`, `Jueves`, `Viernes`, `Sabado`, `Domingo`.
- Uso: organizar capacidad operativa por dia.

#### cliente

- Que es: nombre visible del cliente del pedido.
- Origen: `order_partner_id.display_name`.
- Uso: identificar para quien se esta produciendo o reservando producto.

#### numero_orden_venta

- Que es: identificador de la orden de venta.
- Origen: `order_id.name`.
- Uso: trazabilidad operativa.

#### producto

- Que es: nombre del producto o combo.
- Origen: `line.product_id.display_name`.
- Uso: agrupacion y consolidacion para plan de produccion.

#### cantidad_vendida

- Que es: cantidad pedida en esa linea.
- Origen: `product_uom_qty`.
- Uso: demanda bruta de la linea.

#### inventario_disponible

- Que es: stock virtual disponible justo antes de procesar esta fila.
- Origen: snapshot virtual en la simulacion cronologica.
- Uso: saber cuanto del pedido ya estaba cubierto.

#### inventario_libre_usar

- Que es: stock libre de usar antes de procesar esta fila.
- Origen: `available_quantity` de `stock.quant`, descontado virtualmente en la simulacion.
- Uso: visibilidad adicional sobre disponibilidad realmente no reservada.

#### cantidad_sugerida_producir

- Que es: faltante neto a producir para cubrir esa linea.
- Origen: diferencia entre `cantidad_vendida` e `inventario_disponible` previo, nunca negativa.
- Formula:

```text
cantidad_sugerida_producir = max(cantidad_vendida - inventario_disponible, 0)
```

- Uso: accion directa de planeacion y produccion.

## 9. Como se ordena el resultado

El wizard devuelve las filas ordenadas por:

1. `fecha_entrega` ascendente
2. `cliente` ascendente

Interpretacion:

- primero se ve el trabajo mas urgente en el tiempo
- dentro de cada dia, se ordena por cliente para facilitar lectura operativa

## 10. Ejemplo de uso

### Request

```http
POST /api/bi/production/weekly-plan
Access-Token: TU_TOKEN
Content-Type: application/json

{
  "filters": {
    "dateFrom": "2026-03-26",
    "dateTo": "2026-04-06"
  }
}
```

### Interpretacion del resultado

Con ese request, el endpoint devuelve las lineas de pedidos con fecha de entrega dentro de ese rango y calcula, para cada una, cuanto inventario habia disponible y cuanto faltaria producir para cubrir la demanda.

## 11. Explicacion de la matriz superior de Power BI

La visual superior es una matriz donde:

- las filas representan `producto`
- las columnas representan fechas individuales
- el valor mostrado en las celdas corresponde a `cantidad_sugerida_producir`
- la ultima columna `Total` es la suma total por producto en todo el rango visible
- la ultima fila `Total` es la suma de todas las cantidades por fecha

### 11.1 Como leer las filas

Cada fila corresponde a un producto.

Ejemplo de lectura:

- si `Pizza de pepperoni` tiene 56 en `2026-03-30` y 80 en `2026-04-06`, significa que para ese producto el sistema sugiere producir 56 unidades para cubrir la carga del 30 de marzo y 80 unidades para la del 6 de abril
- su `Total` de 136 representa la suma sugerida total del producto en todo el rango de fechas visible

### 11.2 Como leer las columnas

Cada columna de fecha representa la carga sugerida de produccion para ese dia.

Ejemplo de lectura:

- la columna `2026-04-06` muestra cuanto se necesita producir ese dia, distribuido por producto
- la fila final `Total` en esa columna suma toda la demanda sugerida del dia

En la captura:

- `2026-04-06` concentra una carga total de 424, lo que la convierte en la fecha mas pesada del recorte visible
- `2026-04-04` muestra 160
- `2026-03-30` muestra 138

### 11.3 Que responde esta matriz

La matriz responde tres preguntas operativas clave:

- que producir
- cuando producirlo
- cuanto pesa cada producto dentro de la carga total por dia

### 11.4 Riesgo de interpretacion

Un punto importante al presentar esta matriz es aclarar que no muestra ventas historicas ni despachos reales. Muestra una sugerencia operativa basada en pedidos y stock disponible simulado.

## 12. Explicacion de la grafica inferior de Power BI

La visual inferior muestra `Suma de cantidad_sugerida_producir por producto y dia_semana` en un grafico de barras horizontales apiladas al 100%.

Se observa:

- eje Y: `producto`
- eje X: participacion porcentual de `cantidad_sugerida_producir`
- leyenda: `dia_semana`

### 12.1 Que esta mostrando realmente

La grafica no muestra cantidades absolutas. Muestra como se distribuye porcentualmente la sugerencia de produccion de cada producto entre los distintos dias de la semana.

Eso significa que cada barra siempre suma 100%.

### 12.2 Como leer cada barra

Cada barra corresponde a un producto.

Los colores muestran que porcentaje de la carga sugerida de ese producto cae en:

- `Lunes`
- `Martes`
- `Miercoles`
- `Jueves`
- `Sabado`

Segun la visual visible, no todos los dias aparecen para todos los productos.

Ejemplo de lectura:

- si un producto tiene casi toda la barra en azul oscuro de `Lunes`, significa que casi toda su necesidad de produccion cae en lunes
- si una barra esta partida entre `Lunes` y `Sabado`, significa que la produccion sugerida de ese producto se distribuye entre ambos dias

### 12.3 Lectura ejecutiva de la grafica

La captura sugiere que muchos productos concentran casi toda su carga en un solo dia de la semana, mientras otros reparten la necesidad entre dos o tres dias.

Interpretacion de negocio:

- hay productos con una planificacion muy concentrada
- otros requieren preparacion escalonada en la semana
- esa mezcla sirve para anticipar picos de capacidad por dia y por familia de producto

### 12.4 Riesgo de interpretacion

Como la barra es 100% apilada, un producto con poca cantidad total puede verse igual de "importante" visualmente que uno con muchisima cantidad total.

Por eso esta visual debe leerse junto con la matriz superior o con totales absolutos.

### 12.5 Como explicarla en una presentacion

Puedes presentarla asi:

"Esta visual muestra como se distribuye la necesidad de produccion de cada producto a lo largo de la semana. No representa volumen absoluto, sino participacion porcentual por dia. Sirve para ver si un producto concentra su carga en un solo dia o si requiere preparacion repartida entre varios dias."

## 13. Utilidades dentro del negocio

Este endpoint es una herramienta de planeacion operativa directa.

### 13.1 Aplicaciones practicas

- definir que productos deben producirse cada dia
- anticipar faltantes de producto terminado
- balancear carga semanal de produccion
- priorizar ordenes mas urgentes por fecha de entrega
- detectar dias con sobrecarga operativa

### 13.2 Utilidad por area

#### Produccion

- ayuda a saber cuanto falta fabricar realmente
- permite programar lotes y secuencia diaria
- facilita ver picos de carga por fecha y producto

#### Logistica

- ayuda a alinear produccion con fechas de entrega comprometidas
- permite anticipar dias de mayor preparacion y despacho

#### Ventas

- facilita validar si la promesa de entrega esta soportada por stock o requiere fabricacion adicional
- da trazabilidad para explicar compromisos al cliente

#### Gerencia

- permite ver si la capacidad semanal alcanza para cubrir la demanda
- ayuda a priorizar recursos y turnos en dias criticos

### 13.3 Ejemplos de decisiones que puede apoyar

#### Decision 1: refuerzo de produccion

Si una fecha concentra una carga sugerida muy alta, puede justificarse ampliar turno, adelantar fabricacion o reasignar personal.

#### Decision 2: priorizacion por producto

Si un producto acumula un total muy alto en varios dias, puede programarse como producto critico de la semana.

#### Decision 3: revision de promesas de entrega

Si la sugerencia a producir es sistematicamente alta y el inventario previo es bajo, conviene revisar politica de stock o tiempos prometidos a cliente.

#### Decision 4: nivelacion de carga

Si la grafica por dia de semana muestra una concentracion excesiva en un solo dia, el equipo puede intentar mover o anticipar produccion para balancear la operacion.

#### Decision 5: control de inventario terminado

Si muchos pedidos generan sugerencias de produccion pese a tener demanda repetitiva, eso puede indicar que el stock objetivo de producto terminado es insuficiente.

### 13.4 Valor analitico adicional

Con este endpoint se pueden construir analisis derivados:

- carga total por dia
- carga total por producto
- mapa de calor por producto y fecha
- distribucion semanal de fabricacion
- alertas de sobrecarga operativa por dia

El endpoint de plan de produccion semanal toma pedidos confirmados con fecha compromiso, cruza esa demanda contra el inventario actual y simula su consumo en orden cronologico. Con eso calcula el faltante neto que conviene producir para cubrir cada pedido. La matriz superior muestra cuanto producir por producto y por fecha, mientras la grafica inferior muestra como se distribuye esa carga a lo largo de la semana.

## 15. Conclusiones clave

- El endpoint delega la logica principal a `advanced_metrics.report.wizard`.
- El filtro operativo principal usa `commitment_date`.
- La sugerencia de produccion se calcula como faltante neto contra inventario disponible.
- `inventario_disponible` es un snapshot virtual por fila, no un stock fijo global.
- El orden cronologico es clave para evitar doble contabilizacion del stock.
- La matriz superior muestra cantidades absolutas por fecha y producto.
- La grafica inferior muestra distribucion porcentual por dia de semana, no volumen absoluto.

## 16. Archivos tecnicos relacionados

- `custom_addons/cookoo/pbi_connections/controllers/inventory_dashboard.py`
- `custom_addons/cookoo/pbi_connections/models/inventory_dashboard.py`
- `custom_addons/cookoo/advanced_metrics/models/report_wizard.py`
- `custom_addons/cookoo/advanced_metrics/views/sales_orders.xml`
- `custom_addons/cookoo/advanced_metrics/controllers/controllers.py`

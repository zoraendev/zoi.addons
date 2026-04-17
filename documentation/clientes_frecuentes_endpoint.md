# Dashboard de Clientes - Endpoint de Clientes Mas Frecuentes

Este documento describe en detalle el endpoint de clientes mas frecuentes del dashboard de clientes, el flujo interno de procesamiento, el origen de cada dato devuelto y la lectura de la grafica de Power BI compartida.

## 1. Objetivo del endpoint

El endpoint identifica los clientes con mayor actividad de compra dentro de un periodo. En la implementacion actual, la palabra "frecuentes" no significa solamente "quienes compran mas veces". El servicio construye varias metricas por cliente y luego permite ordenar el resultado por diferentes criterios.

Por defecto, el orden se hace por `totalOrders`, por lo que el ranking inicial si representa frecuencia de compra. Sin embargo, tambien puede ordenarse por monto, ticket promedio, dias entre compras, ultima compra o dias sin compra.

## 2. Rutas disponibles

El controlador expone dos rutas equivalentes:

- `/api/bi/customer-dashboard/frequent-customers`
- `/api/bi/advanced-metrics/customer-dashboard/frequent-customers`

Ambas llaman el mismo metodo de servicio: `get_frequent_customers_report_data`.

## 3. Metodo HTTP y autenticacion

- Metodos aceptados: `GET` y `POST`
- Autenticacion: token obligatorio

El token puede enviarse en cualquiera de estas formas:

- Header `Access-Token: <token>`
- Header `Authorization: Bearer <token>`
- Query param `?token=<token>`

Si el token no existe o no coincide con un registro valido en `pbi_connections.api.config` o `advanced_metrics.api.config`, la respuesta es `401`.

## 4. Flujo tecnico completo

### 4.1 Controlador

El metodo `get_frequent_customers` del controlador no calcula datos directamente. Su trabajo es:

1. Recibir la peticion.
2. Extraer filtros desde JSON body o query params.
3. Validar el token.
4. Delegar el trabajo al modelo de servicio `pbi_connections.customer.dashboard`.

### 4.2 Extraccion de filtros

Los filtros se toman desde:

- `payload.filters`
- o el JSON completo si no existe la clave `filters`
- y luego se complementan o sobreescriben con query params

Para este endpoint, los filtros reconocidos por el controlador son:

- `dateFrom`
- `dateTo`
- `top`
- `sortBy`
- `inactiveDays`

Nota importante: aunque `inactiveDays` viaja como filtro permitido por el controlador, en este endpoint no se usa en la logica del servicio. Es irrelevante para `frequent-customers`.

### 4.3 Normalizacion y validacion de filtros

Antes de consultar datos, el servicio normaliza los filtros:

- `dateFrom`: debe venir en formato `YYYY-MM-DD`
- `dateTo`: debe venir en formato `YYYY-MM-DD`
- `top`: entero positivo, por defecto `10`, maximo `100`
- `sortBy`: por defecto `totalOrders`

Valores permitidos en `sortBy`:

- `totalOrders`
- `totalAmount`
- `averageOrderValue`
- `averageDaysBetweenOrders`
- `lastOrderDate`
- `daysWithoutPurchase`
- `customerName`

Reglas de validacion:

- Si una fecha no usa formato valido, el servicio responde error `400`.
- Si `dateFrom > dateTo`, el servicio responde error `400`.
- Si `top` no es entero positivo, el servicio responde error `400`.
- Si `sortBy` no pertenece a la lista permitida, el servicio responde error `400`.

## 5. Origen real de los datos

El origen del endpoint es el modelo `sale.order`.

El dominio exacto usado en la busqueda es:

- `state in ('sale', 'done')`
- `partner_id != False`
- `date_order >= dateFrom 00:00:00`, si se envio `dateFrom`
- `date_order <= dateTo 23:59:59`, si se envio `dateTo`

Esto significa:

- Solo se consideran ordenes de venta confirmadas o completadas.
- No entran cotizaciones en borrador ni canceladas.
- No entran ordenes sin cliente.
- El rango de fechas filtra por `date_order` de la orden de venta.

## 6. Nivel de agrupacion: por que usa cliente comercial

Las ordenes no se agrupan directamente por `order.partner_id`, sino por `order.partner_id.commercial_partner_id`.

Eso tiene una razon de negocio importante: si una empresa tiene varios contactos o sucursales hijas en Odoo, el dashboard consolida todas las compras al nivel del cliente comercial principal.

En la practica, esto evita que un mismo grupo empresarial aparezca fragmentado en varias barras o filas.

## 7. Como se construyen las metricas

El proceso interno ocurre en dos etapas:

### 7.1 Agregacion por cliente

Por cada orden de venta encontrada, el servicio acumula por cliente:

- `customerId`
- `customerName`
- `customerCode`
- cantidad de ordenes
- monto total
- primera fecha de orden
- ultima fecha de orden
- lista completa de fechas de orden

### 7.2 Construccion de metricas derivadas

Con esos acumulados, el servicio calcula metricas finales para cada cliente.

#### totalOrders

- Que es: cantidad total de ordenes del cliente en el periodo consultado.
- Origen: contador de registros `sale.order` agrupados por cliente comercial.
- Formula:

```text
totalOrders = numero de ordenes del cliente dentro del dominio consultado
```

- Por que se calcula asi: porque la frecuencia mas directa de compra es el numero de eventos de compra confirmados.

#### totalAmount

- Que es: monto total vendido al cliente en el periodo.
- Origen: suma de `sale.order.amount_total`.
- Formula:

```text
totalAmount = suma(amount_total de todas las ordenes del cliente)
```

- Redondeo: a 2 decimales.
- Por que se calcula asi: porque permite medir el peso economico del cliente, no solo su recurrencia.

#### averageOrderValue

- Que es: ticket promedio del cliente.
- Origen: derivado de `totalAmount` y `totalOrders`.
- Formula:

```text
averageOrderValue = totalAmount / totalOrders
```

- Si `totalOrders = 0`, devuelve `0.0`.
- Redondeo: a 2 decimales.
- Por que se calcula asi: porque separa clientes que compran seguido pero poco, de clientes que compran menos veces pero con tickets altos.

#### averageDaysBetweenOrders

- Que es: promedio de dias entre compras sucesivas del cliente.
- Origen: diferencias entre las fechas de las ordenes del cliente.
- Formula real usada por el codigo:

```text
1. Ordenar cronologicamente las fechas de compra
2. Calcular la diferencia en dias entre cada compra y la siguiente
3. Sacar el promedio de esos intervalos
4. Redondear al entero mas cercano
```

Equivalente matematico:

$$
averageDaysBetweenOrders = round\left(\frac{\sum_{i=2}^{n}(fecha_i - fecha_{i-1})}{n - 1}\right)
$$

- Si el cliente tiene una sola orden o ninguna fecha valida, devuelve `0`.
- Por que se calcula asi: porque mide la cadencia de recompra real y no solo el volumen acumulado.

#### lastOrderDate

- Que es: fecha de la ultima compra del cliente dentro del conjunto filtrado.
- Origen: maxima `date_order` de sus ordenes consideradas.
- Formato devuelto: `YYYY-MM-DD`.
- Por que se calcula asi: porque la ultima compra es la mejor señal de recencia dentro del periodo analizado.

#### daysWithoutPurchase

- Que es: dias transcurridos desde la ultima compra hasta una fecha ancla.
- Origen: calculado a partir de `lastOrderDate`.
- Fecha ancla usada por el servicio:
  - si se envio `dateTo`, la fecha ancla es `dateTo`
  - si no se envio `dateTo`, la fecha ancla es la fecha actual del contexto Odoo

- Formula:

```text
daysWithoutPurchase = max(anchorDate - lastOrderDate, 0)
```

Equivalente matematico:

$$
daysWithoutPurchase = max((fecha\_ancla - ultima\_compra).days, 0)
$$

- Por que se calcula asi: porque permite medir recencia de forma estable respecto al cierre del analisis. Si el dashboard se ejecuta con `dateTo`, la recencia queda congelada al final de ese periodo y no depende del dia en que se consulte.

#### customerType

- Que es: clasificacion simple del cliente segun recurrencia.
- Origen: regla interna del servicio.
- Regla exacta:

```text
si totalOrders >= 5 -> recurring
si totalOrders >= 2 y averageDaysBetweenOrders <= 30 -> recurring
si totalOrders >= 2 -> occasional
en cualquier otro caso -> new
```

- Por que se calcula asi: porque transforma metricas numericas en una categoria accionable para negocio. No pretende ser un modelo estadistico avanzado; es una segmentacion operativa simple.

## 8. Campos que devuelve la respuesta

La respuesta exitosa del controlador tiene esta estructura general:

```json
{
  "success": true,
  "message": "Clientes mas frecuentes obtenidos correctamente.",
  "generatedAt": "2026-04-16T12:00:00Z",
  "filters": {
    "dateFrom": "2026-01-01",
    "dateTo": "2026-03-31",
    "top": 10,
    "sortBy": "totalOrders"
  },
  "data": [
    {
      "customerId": 25,
      "customerName": "Cliente Ejemplo",
      "customerCode": "C-025",
      "totalOrders": 8,
      "totalAmount": 125000.5,
      "averageOrderValue": 15625.06,
      "averageDaysBetweenOrders": 11,
      "lastOrderDate": "2026-03-28",
      "daysWithoutPurchase": 3,
      "customerType": "recurring"
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
- Uso: auditoria, cache, trazabilidad de extraccion.

#### filters

- Origen: servicio.
- Significado: filtros normalizados finales usados realmente por la consulta.
- Uso: validar que Power BI o el cliente API consultaron lo esperado.

#### data

- Origen: servicio.
- Significado: lista de clientes ya calculada y ordenada.

### Explicacion de cada campo dentro de data

#### customerId

- Origen: `res.partner.id` del `commercial_partner_id`.
- Uso: llave tecnica para relacionar con otras tablas o modelos.

#### customerName

- Origen: `res.partner.display_name`.
- Uso: etiqueta visible para tablas, barras y segmentaciones.

#### customerCode

- Origen: `res.partner.ref`.
- Uso: codigo interno del cliente; sirve para conciliacion con otros sistemas.

#### totalOrders

- Origen: conteo de `sale.order` filtradas.
- Uso: metrica principal de frecuencia.

#### totalAmount

- Origen: suma de `sale.order.amount_total`.
- Uso: peso economico del cliente dentro del periodo.

#### averageOrderValue

- Origen: `totalAmount / totalOrders`.
- Uso: detectar ticket promedio del cliente.

#### averageDaysBetweenOrders

- Origen: promedio de los intervalos entre compras.
- Uso: medir el ritmo de recompra.

#### lastOrderDate

- Origen: ultima `date_order` del cliente en el dataset filtrado.
- Uso: medir recencia.

#### daysWithoutPurchase

- Origen: diferencia entre fecha ancla y `lastOrderDate`.
- Uso: detectar enfriamiento o proximidad a una recompra esperada.

#### customerType

- Origen: clasificacion derivada por regla de negocio.
- Uso: segmentacion rapida en visualizaciones y reportes.

## 9. Como se ordena el ranking

El endpoint no siempre devuelve "los mas frecuentes" en sentido estricto. Devuelve un ranking segun `sortBy`.

Comportamiento exacto:

- Si `sortBy = customerName`, orden alfabetico ascendente.
- Si `sortBy = lastOrderDate`, orden descendente por fecha mas reciente.
- Si `sortBy = averageDaysBetweenOrders` o `daysWithoutPurchase`, orden ascendente por el valor, lo cual favorece a quienes compran mas seguido o estuvieron mas recientemente activos.
- En los demas casos, orden descendente por la metrica elegida.

Esto es importante para la presentacion: si el dashboard se vende como "clientes mas frecuentes", el orden mas coherente es `totalOrders`. Si se usa `totalAmount`, realmente el ranking se vuelve "clientes de mayor facturacion".

## 10. Ejemplo de uso

### Request

```http
POST /api/bi/customer-dashboard/frequent-customers
Access-Token: TU_TOKEN
Content-Type: application/json

{
  "filters": {
    "dateFrom": "2026-01-01",
    "dateTo": "2026-03-31",
    "top": 10,
    "sortBy": "totalOrders"
  }
}
```

### Interpretacion del resultado

Con ese request, el endpoint devuelve los 10 clientes con mas ordenes confirmadas o completadas entre el 1 de enero y el 31 de marzo de 2026, junto con monto total, ticket promedio, cadencia de compra y recencia al cierre del 31 de marzo.

## 11. Explicacion de la grafica de Power BI compartida

La grafica mostrada es un grafico de barras horizontales con esta configuracion visible:

- Eje Y: `customerName`
- Eje X: `Suma de totalAmount`
- Titulo visible: `Suma de totalAmount por customerName`

### 11.1 Que esta mostrando realmente

La visual no esta mostrando frecuencia en el eje principal. Esta mostrando monto total vendido por cliente.

Eso significa que, aunque el tab o endpoint se llame "Clientes Frecuentes", la grafica responde esta pregunta:

"Que clientes acumularon mayor monto total en el dataset cargado?"

No responde directamente:

"Que clientes compraron mas veces?"

### 11.2 Lectura del grafico

Segun la captura:

- Existe un cliente claramente dominante, con una barra cercana a 100 mil.
- El resto de clientes queda muy por debajo, en una franja aproximada alrededor de 6 mil a 15 mil.
- La distribucion esta muy sesgada por un outlier, lo que aplana visualmente las demas barras.

Interpretacion de negocio:

- Hay alta concentracion del revenue del top 1 dentro de la seleccion visible.
- Los siguientes clientes son comparables entre si, pero quedan visualmente comprimidos por la diferencia con el primero.

### 11.3 Que relacion tiene con el endpoint

El endpoint si devuelve `totalAmount`, por lo que la grafica esta usando un campo valido del servicio. El punto clave es conceptual:

- Si el objetivo del dashboard es frecuencia, el campo mas representativo es `totalOrders`.
- Si el objetivo es valor economico, el campo correcto es `totalAmount`.

En otras palabras, la visual esta bien construida tecnicamente, pero puede estar desalineada semantica y ejecutivamente con el nombre "Clientes Frecuentes".

### 11.4 Como explicarla en una presentacion

Puedes presentarla asi:

"Esta visual muestra el monto total comprado por cada cliente dentro del conjunto clasificado como clientes frecuentes. Permite identificar quienes, ademas de comprar recurrentemente, representan mayor aporte economico. En la captura se observa una concentracion marcada en un cliente principal, mientras que el resto mantiene montos significativamente menores."

### 11.5 Riesgo de interpretacion

Si la audiencia ve el nombre de la pestana "Clientes Frecuentes" y luego una barra de `totalAmount`, puede asumir incorrectamente que la longitud de la barra representa cantidad de compras.

Ese riesgo de interpretacion existe porque:

- el nombre funcional habla de frecuencia
- la medida visual habla de monto

### 11.6 Recomendacion para alinear la visual con el endpoint

Si quieres que la grafica represente literalmente clientes mas frecuentes, la mejor opcion es:

- Eje Y: `customerName`
- Eje X: `totalOrders`
- Orden descendente por `totalOrders`

Si quieres conservar la visual actual, conviene renombrarla a algo como:

- `Valor de compra por cliente frecuente`
- `Top clientes frecuentes por monto`
- `Aporte economico de clientes frecuentes`

### 11.7 Recomendacion adicional por legibilidad

Como hay un outlier muy marcado, puedes mejorar lectura con alguna de estas opciones:

- mostrar etiquetas de datos
- aplicar Top N mas corto, por ejemplo Top 5
- separar en dos visuales: frecuencia y valor
- usar un scatter chart con `totalOrders` vs `totalAmount`
- usar escala logaritmica si el negocio acepta esa lectura

El endpoint de clientes mas frecuentes consolida las ordenes de venta confirmadas por cliente comercial y calcula frecuencia, valor, ticket promedio, recencia y ritmo de recompra. Esto permite diferenciar clientes que compran muchas veces, clientes que facturan mas y clientes que sostienen una cadencia estable. En la visual compartida, Power BI esta resaltando el valor economico por cliente, no la frecuencia pura; por eso conviene aclarar esa diferencia al presentar el dashboard.

## 13. Utilidades dentro del negocio

Este endpoint no sirve solo para ranking comercial. Tambien funciona como una base operativa para detectar comportamiento de compra y priorizar acciones.

### 13.1 Aplicaciones practicas

- identificar la cartera que sostiene la recurrencia del negocio
- detectar clientes con alta frecuencia pero bajo ticket promedio
- detectar clientes con alta facturacion pero baja frecuencia
- identificar patrones de recompra por cliente o segmento
- construir campañas de fidelizacion en funcion de la cadencia de compra
- anticipar clientes que deberian volver a comprar pronto
- alimentar scoring comercial o modelos simples de retencion

### 13.2 Utilidad por area

#### Ventas

- ayuda a priorizar visitas y seguimiento sobre clientes con alta recurrencia
- permite diferenciar cuentas estables de compras ocasionales
- facilita asignar ejecutivos a clientes con mayor constancia

#### Marketing

- permite crear campañas de recompra basadas en `averageDaysBetweenOrders`
- ayuda a segmentar promociones para clientes nuevos, ocasionales o recurrentes
- facilita automatizar recordatorios antes de la fecha esperada de recompra

#### Gerencia

- permite saber si la recurrencia del negocio esta concentrada en pocos clientes
- ayuda a medir si el crecimiento depende de clientes frecuentes o de compras aisladas
- da visibilidad sobre la calidad de la base de clientes, no solo sobre el ingreso total

#### Operaciones y planeacion

- ayuda a estimar demanda repetitiva de clientes habituales
- permite identificar cuentas que conviene considerar en planeacion de inventario o produccion
- mejora la lectura del ritmo comercial real frente al volumen vendido

### 13.3 Ejemplos de decisiones que puede apoyar

#### Decision 1: priorizacion comercial

Si un cliente tiene `totalOrders` alto, `averageDaysBetweenOrders` bajo y `daysWithoutPurchase` cercano a su patron normal, puede mantenerse en seguimiento estandar. Si ese mismo cliente supera su ritmo habitual de recompra, conviene activar contacto preventivo.

#### Decision 2: campanas de recompra

Si varios clientes recurrentes tienen una frecuencia promedio de 20 a 30 dias, se puede programar una campana automatica antes de ese rango para capturar la siguiente compra.

#### Decision 3: enfoque en rentabilidad

Si un cliente aparece con alta frecuencia pero ticket promedio bajo, la accion no necesariamente es fidelizar mas, sino revisar mix de productos, margen o estrategia de upselling.

#### Decision 4: gestion de cuentas clave

Si un cliente tiene alto `totalAmount` y alto `totalOrders`, puede clasificarse como cuenta clave. Eso justifica atencion preferente, revisiones periodicas o acuerdos comerciales especiales.

#### Decision 5: deteccion temprana de enfriamiento

Si un cliente historicamente frecuente incrementa `daysWithoutPurchase` por encima de su patron normal, el negocio puede intervenir antes de que caiga en inactividad abierta.

### 13.4 Valor analitico adicional

Con este endpoint tambien se pueden construir analisis derivados:

- matriz de frecuencia vs valor
- segmentacion tipo RFM basica usando `totalOrders`, `totalAmount` y `daysWithoutPurchase`
- alertas de clientes con ruptura del ciclo de recompra
- comparativos por periodo para ver si la recurrencia mejora o se deteriora

## 14. Conclusiones clave

- El origen del endpoint es `sale.order`, no facturas ni movimientos contables.
- Solo considera ventas confirmadas o completadas.
- Agrupa por `commercial_partner_id`, no por contacto individual.
- La frecuencia base se mide con `totalOrders`.
- La recencia se mide con `lastOrderDate` y `daysWithoutPurchase`.
- La cadencia de compra se mide con `averageDaysBetweenOrders`.
- La visual de Power BI compartida esta mostrando valor por cliente, no frecuencia directa.

## 15. Archivos tecnicos relacionados

- `custom_addons/cookoo/pbi_connections/controllers/clients_dashboard.py`
- `custom_addons/cookoo/pbi_connections/controllers/base_dashboard.py`
- `custom_addons/cookoo/pbi_connections/models/customer_dashboard.py`

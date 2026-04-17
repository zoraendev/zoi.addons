# Dashboard de Clientes - Endpoint de Clientes Inactivos

Este documento describe en detalle el endpoint de clientes inactivos del dashboard de clientes, el flujo interno de procesamiento, el origen de cada dato devuelto, la logica de calculo y la interpretacion de la grafica de Power BI compartida.

## 1. Objetivo del endpoint

El endpoint identifica clientes que dejaron de comprar durante un numero minimo de dias. Su proposito no es medir frecuencia dentro de un periodo, sino detectar inactividad usando el historial completo de ventas confirmadas del cliente.

En terminos de negocio, responde esta pregunta:

"Que clientes tienen suficiente tiempo sin comprar como para considerarlos inactivos o en riesgo de abandono?"

## 2. Rutas disponibles

El controlador expone dos rutas equivalentes:

- `/api/bi/customer-dashboard/inactive-customers`
- `/api/bi/advanced-metrics/customer-dashboard/inactive-customers`

Ambas llaman el mismo metodo de servicio: `get_inactive_customers_report_data`.

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

El metodo `get_inactive_customers` del controlador se limita a:

1. Recibir la peticion.
2. Extraer filtros desde JSON body o query params.
3. Validar el token.
4. Delegar el procesamiento al modelo de servicio `pbi_connections.customer.dashboard`.

### 4.2 Extraccion de filtros

Los filtros se toman desde:

- `payload.filters`
- o el JSON completo si no existe la clave `filters`
- y luego se complementan o sobreescriben con query params

Para este endpoint, el controlador reconoce estas claves:

- `dateFrom`
- `dateTo`
- `top`
- `sortBy`
- `inactiveDays`

Nota importante: aunque el controlador acepta `dateFrom`, `dateTo` y `sortBy`, el servicio de clientes inactivos no los usa. Para este endpoint, la logica real solo normaliza y utiliza `inactiveDays` y `top`.

### 4.3 Normalizacion y validacion de filtros

El servicio normaliza los filtros asi:

- `inactiveDays`: entero mayor o igual a `0`, por defecto `60`
- `top`: entero positivo, por defecto `50`, maximo `100`

Tambien acepta alias:

- `inactive_days` como alternativa a `inactiveDays`
- `limit` como alternativa a `top`

Reglas de validacion:

- Si `inactiveDays` no es entero, responde error `400`.
- Si `inactiveDays` es negativo, responde error `400`.
- Si `top` no es entero positivo, responde error `400`.

## 5. Origen real de los datos

El origen del endpoint es el modelo `sale.order`.

El dominio exacto usado en la consulta es:

- `state in ('sale', 'done')`
- `partner_id != False`

Punto clave: este endpoint no filtra por fecha. Toma el historico completo de ordenes confirmadas o completadas para identificar la ultima compra de cada cliente y medir cuantos dias lleva sin volver a comprar.

Esto significa:

- no trabaja sobre un periodo parcial
- no depende de `dateFrom` ni `dateTo`
- usa toda la historia transaccional disponible en `sale.order`

## 6. Nivel de agrupacion: por que usa cliente comercial

Igual que en el endpoint de clientes frecuentes, las ordenes se consolidan por `order.partner_id.commercial_partner_id`.

Eso evita fragmentar la inactividad cuando una empresa tiene varios contactos, sucursales o direcciones hijas en Odoo. Si cualquiera de esas entidades compra, el comportamiento se consolida al cliente comercial principal.

## 7. Como se construyen las metricas

El flujo interno tiene dos etapas:

### 7.1 Agregacion por cliente

Por cada orden de venta encontrada, el servicio acumula por cliente:

- `customerId`
- `customerName`
- `customerCode`
- cantidad total de ordenes historicas
- monto total historico
- primera fecha de orden
- ultima fecha de orden
- lista de fechas de orden

### 7.2 Construccion de metricas derivadas

El servicio reutiliza la misma funcion base de metricas que el endpoint de frecuentes, pero luego selecciona solo los campos relevantes para inactividad.

La fecha ancla para calcular inactividad es siempre la fecha actual del contexto Odoo.

#### lastOrderDate

- Que es: fecha de la ultima compra historica del cliente.
- Origen: maxima `date_order` del cliente considerando todas las ordenes validas.
- Formato devuelto: `YYYY-MM-DD`.
- Por que se calcula asi: porque la ultima compra es el punto de referencia natural para medir inactividad real.

#### daysWithoutPurchase

- Que es: cantidad de dias transcurridos desde la ultima compra hasta hoy.
- Origen: diferencia entre la fecha actual y `lastOrderDate`.
- Formula:

```text
daysWithoutPurchase = max(today - lastOrderDate, 0)
```

Equivalente matematico:

$$
daysWithoutPurchase = max((hoy - ultima\_compra).days, 0)
$$

- Por que se calcula asi: porque el objetivo del endpoint es detectar antiguedad de la ultima compra respecto al momento actual de consulta.

#### totalOrdersHistorical

- Que es: cantidad total de ordenes historicas del cliente.
- Origen: contador de `sale.order` agrupadas por cliente comercial.
- Formula:

```text
totalOrdersHistorical = numero total de ordenes historicas del cliente
```

- Por que se calcula asi: porque no todos los clientes inactivos tienen el mismo peso. Un cliente que compro muchas veces historicamente merece una lectura distinta a uno que compro una sola vez.

#### totalHistoricalAmount

- Que es: monto total historico vendido al cliente.
- Origen: suma de `sale.order.amount_total` de toda su historia valida.
- Formula:

```text
totalHistoricalAmount = suma historica de amount_total del cliente
```

- Redondeo: a 2 decimales.
- Por que se calcula asi: porque un cliente inactivo con alto aporte historico representa mas riesgo economico que uno de bajo valor.

#### averageOrderValue

- Que es: ticket promedio historico del cliente.
- Origen: derivado de `totalHistoricalAmount` y `totalOrdersHistorical`.
- Formula:

```text
averageOrderValue = totalHistoricalAmount / totalOrdersHistorical
```

- Si no hay ordenes, devuelve `0.0`.
- Redondeo: a 2 decimales.
- Por que se calcula asi: porque ayuda a distinguir clientes inactivos pequenos de clientes historicamente premium.

#### customerType

- Que es: etiqueta fija de clasificacion.
- Valor devuelto: `inactive`
- Por que se calcula asi: porque en este endpoint el foco es el estado de inactividad y no la recurrencia anterior del cliente.

## 8. Regla exacta para considerar a un cliente inactivo

El servicio calcula primero `daysWithoutPurchase` para cada cliente y luego aplica este filtro:

```text
si daysWithoutPurchase < inactiveDays -> se excluye
si daysWithoutPurchase >= inactiveDays -> se incluye
```

Eso significa que el umbral es inclusivo. Si `inactiveDays = 60`, un cliente con exactamente 60 dias sin compra si aparece en el resultado.

## 9. Campos que devuelve la respuesta

La respuesta exitosa del controlador tiene esta estructura general:

```json
{
  "success": true,
  "message": "Clientes inactivos obtenidos correctamente.",
  "generatedAt": "2026-04-16T12:00:00Z",
  "filters": {
    "inactiveDays": 60,
    "top": 50
  },
  "data": [
    {
      "customerId": 25,
      "customerName": "Cliente Ejemplo",
      "customerCode": "C-025",
      "lastOrderDate": "2026-02-12",
      "daysWithoutPurchase": 63,
      "totalOrdersHistorical": 14,
      "totalHistoricalAmount": 84500.0,
      "averageOrderValue": 6035.71,
      "customerType": "inactive"
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
- Significado: filtros normalizados que realmente se usaron para construir la respuesta.

#### data

- Origen: servicio.
- Significado: lista de clientes que cumplen el umbral de inactividad.

### Explicacion de cada campo dentro de data

#### customerId

- Origen: `res.partner.id` del `commercial_partner_id`.
- Uso: relacion con otras tablas, campañas o analitica extendida.

#### customerName

- Origen: `res.partner.display_name`.
- Uso: lectura humana en reportes y dashboards.

#### customerCode

- Origen: `res.partner.ref`.
- Uso: identificacion interna del cliente.

#### lastOrderDate

- Origen: ultima `date_order` historica valida.
- Uso: saber desde cuando dejo de comprar.

#### daysWithoutPurchase

- Origen: diferencia entre hoy y `lastOrderDate`.
- Uso: metrica central de riesgo o abandono.

#### totalOrdersHistorical

- Origen: conteo historico de ordenes del cliente.
- Uso: medir el peso transaccional historico del cliente perdido o dormido.

#### totalHistoricalAmount

- Origen: suma historica de `amount_total`.
- Uso: medir el impacto economico potencial de la inactividad.

#### averageOrderValue

- Origen: `totalHistoricalAmount / totalOrdersHistorical`.
- Uso: diferenciar clientes inactivos de ticket alto y ticket bajo.

#### customerType

- Origen: valor fijo asignado por el servicio.
- Uso: segmentacion rapida como cartera inactiva.

## 10. Como se ordena el ranking

El endpoint ordena siempre el resultado de forma descendente con esta prioridad:

1. `daysWithoutPurchase`
2. `totalOrdersHistorical`
3. `totalHistoricalAmount`
4. `customerName`

Interpretacion:

- primero aparecen los clientes con mas dias sin comprar
- si dos clientes tienen la misma inactividad, sube el que tuvo mas ordenes historicas
- si aun hay empate, sube el de mayor monto historico

Esto tiene sentido de negocio porque prioriza la antiguedad de la inactividad, pero sin perder de vista el peso historico del cliente.

## 11. Ejemplo de uso

### Request

```http
POST /api/bi/customer-dashboard/inactive-customers
Access-Token: TU_TOKEN
Content-Type: application/json

{
  "filters": {
    "inactiveDays": 60,
    "top": 20
  }
}
```

### Interpretacion del resultado

Con ese request, el endpoint devuelve los 20 clientes con al menos 60 dias sin comprar, ordenados por mayor inactividad y luego por peso historico.

## 12. Explicacion de la grafica de Power BI compartida

La visual mostrada es una grafica horizontal donde se observa:

- titulo visible: `Suma de daysWithoutPurchase por customerName`
- categoria: `customerName`
- medida: `daysWithoutPurchase`

Visualmente parece una representacion tipo embudo o barras con comparacion porcentual respecto al mayor valor.

### 12.1 Que esta mostrando realmente

La visual muestra cuantos dias lleva sin comprar cada cliente incluido en el dataset.

En la captura, los clientes visibles tienen valores de 63, 62, 61 y 60 dias, por lo que todos estan apenas por encima del umbral de inactividad de 60 dias.

### 12.2 Lectura del grafico

La grafica permite ver:

- quien es el cliente con mas tiempo sin comprar dentro del conjunto mostrado
- que las diferencias entre clientes visibles son pequenas
- que la cartera mostrada esta muy concentrada alrededor del umbral minimo de inactividad

Interpretacion de negocio:

- no se observa un cliente extremadamente abandonado frente a los demas
- el grupo visible parece corresponder a clientes recientemente clasificados como inactivos
- es un buen conjunto objetivo para acciones tempranas de reactivacion

### 12.3 Que relacion tiene con el endpoint

Esta visual esta bien alineada con el endpoint. El campo central del servicio para este caso es justamente `daysWithoutPurchase`, y el endpoint ya devuelve una fila por cliente, por lo que la agregacion tipo suma no distorsiona el valor mientras cada cliente aparezca una sola vez en el dataset cargado.

### 12.4 Como explicarla en una presentacion

Puedes presentarla asi:

"Esta visual muestra los clientes que ya superaron el umbral de inactividad definido y cuantos dias llevan sin comprar. En la captura, todos los clientes visibles estan entre 60 y 63 dias sin compra, lo que indica una cartera recientemente entrada en riesgo y apta para acciones de reactivacion temprana."

### 12.5 Riesgo de interpretacion

Hay dos puntos que conviene aclarar frente a la audiencia:

- la visual muestra dias sin compra, no perdida economica
- un cliente con mas dias sin comprar no necesariamente es el mas importante para recuperar

Por eso conviene complementar esta grafica con `totalHistoricalAmount` o `totalOrdersHistorical` en otra visual o tabla.

### 12.6 Recomendaciones para mejorar la visual

Opciones utiles para fortalecer el analisis:

- agregar etiquetas con `lastOrderDate`
- usar color por tramos, por ejemplo 60 a 90, 91 a 180, mas de 180 dias
- complementar con una tabla que incluya `totalHistoricalAmount`
- mostrar Top N por monto historico dentro de los inactivos
- construir una matriz de prioridad cruzando inactividad y valor historico

## 13. Utilidades dentro del negocio

Este endpoint es especialmente util para recuperacion comercial y gestion de churn. Su valor esta en convertir el historial de ventas en una lista accionable de clientes dormidos o perdidos.

### 13.1 Aplicaciones practicas

- detectar clientes en riesgo de abandono
- construir listas de reactivacion comercial
- identificar clientes valiosos que dejaron de comprar
- priorizar campañas win-back
- medir envejecimiento de cartera
- monitorear deterioro de relacion con clientes historicos

### 13.2 Utilidad por area

#### Ventas

- ayuda a organizar llamadas o visitas de reactivacion
- permite priorizar primero a los clientes de mayor valor historico
- facilita separar clientes realmente perdidos de clientes con ciclos de compra largos

#### Marketing

- permite lanzar campañas de retorno por tramos de inactividad
- ayuda a definir ofertas de reenganche para clientes dormidos
- facilita automatizar mensajes segun tiempo sin compra

#### Gerencia

- da visibilidad sobre fuga de cartera
- permite medir cuanto valor historico esta inactivo
- ayuda a detectar si el problema es puntual o estructural

#### Servicio y experiencia del cliente

- ayuda a identificar cuentas que pueden haberse enfriado por mala experiencia, tiempos de entrega o falta de seguimiento
- permite revisar causas de abandono sobre clientes relevantes

### 13.3 Ejemplos de decisiones que puede apoyar

#### Decision 1: priorizacion de recuperacion

Si dos clientes tienen inactividad similar pero uno tiene mucho mayor `totalHistoricalAmount`, conviene contactar primero al de mayor valor historico porque representa mayor oportunidad de recuperacion.

#### Decision 2: definicion de campanas

Si se identifica un grupo grande entre 60 y 90 dias sin compra, puede activarse una campana de reenganche temprana distinta a la de clientes con mas de 180 dias.

#### Decision 3: analisis de causas

Si un cliente con muchas ordenes historicas pasa repentinamente a estado inactivo, puede justificarse una revision comercial puntual para entender si hubo problemas de precio, servicio, inventario o competencia.

#### Decision 4: asignacion de recursos

Si la lista de inactivos es muy grande, el negocio puede priorizar solo los clientes con mayor `totalHistoricalAmount` o `totalOrdersHistorical` para optimizar el esfuerzo del equipo comercial.

#### Decision 5: seguimiento de cartera perdida

Si aumenta de forma sostenida el numero de clientes con alto `daysWithoutPurchase`, eso puede usarse como alerta temprana de churn y motivar cambios en fidelizacion, servicio o propuesta de valor.

### 13.4 Valor analitico adicional

Con este endpoint se pueden derivar analisis complementarios:

- matriz de inactividad vs valor historico
- score simple de churn
- clasificacion por tramos de riesgo
- seguimiento mensual de clientes recuperados vs no recuperados
- analisis de efectividad de campanas win-back

El endpoint de clientes inactivos toma el historico completo de ventas confirmadas, identifica la ultima compra de cada cliente y calcula cuantos dias lleva sin comprar. Esto permite detectar cartera dormida, priorizar acciones de recuperacion y diferenciar clientes poco relevantes de cuentas historicamente valiosas que hoy representan riesgo comercial. La visual compartida muestra que los clientes visibles estan apenas por encima del umbral de inactividad, lo que sugiere una ventana oportuna para reaccion tempranamente.

## 15. Conclusiones clave

- El origen del endpoint es `sale.order`, usando todo el historico valido.
- Solo considera ventas confirmadas o completadas.
- No usa `dateFrom`, `dateTo` ni `sortBy`, aunque el controlador acepte esas claves.
- Agrupa por `commercial_partner_id`, no por contacto individual.
- La metrica principal es `daysWithoutPurchase`.
- El orden prioriza mayor inactividad y luego peso historico.
- La grafica de Power BI compartida esta bien alineada con el concepto de clientes inactivos.

## 16. Archivos tecnicos relacionados

- `custom_addons/cookoo/pbi_connections/controllers/clients_dashboard.py`
- `custom_addons/cookoo/pbi_connections/controllers/base_dashboard.py`
- `custom_addons/cookoo/pbi_connections/models/customer_dashboard.py`

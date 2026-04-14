# API Endpoints para Dashboard de Inventario y Clientes (Power BI)

Este documento describe los endpoints disponibles para alimentar dashboards de Power BI, ejemplos de uso con `curl`, explicación de los datos que devuelve cada endpoint y sugerencias de visualizaciones y casos de negocio.

---

## Autenticación

Todos los endpoints requieren autenticación con el valor de `Token de Acceso` configurado en Odoo, en:

- `PBI Connections > Credenciales Power BI > Token de Acceso`

Formas válidas de enviarlo:

- Header `Access-Token: <token>` `Recomendado`
- Header `Authorization: Bearer <token>`
- Parámetro `?token=<token>` en la URL

Importante:

- No uses la `API Key de validación` del menú `Settings`; esa clave sirve para validar el cliente contra Zoraen, no para consumir estos endpoints.
- Si copias el token manualmente, evita espacios o comillas extra al inicio o al final.

---

## Endpoints de Clientes

### 1. Clientes más frecuentes

- **Endpoint:** `/api/bi/customer-dashboard/frequent-customers`
- **Método:** POST
- **Descripción:** Devuelve los clientes con mayor frecuencia de compra en el periodo indicado.
- **Body ejemplo:**
  ```json
  {
    "filters": {
      "dateFrom": "2024-01-01",
      "dateTo": "2024-12-31",
      "top": 10
    }
  }
  ```
- **Respuesta:**
  - `customerId`: ID del cliente
  - `customerName`: Nombre
  - `totalOrders`: Número de compras
  - `totalAmount`: Monto total comprado
- **Visualización sugerida:** Tabla o gráfico de barras de clientes más frecuentes.
- **Utilidad:** Identificar clientes clave, enfocar campañas de fidelización.

### 2. Clientes inactivos

- **Endpoint:** `/api/bi/customer-dashboard/inactive-customers`
- **Método:** POST
- **Descripción:** Lista clientes que no han comprado en X días.
- **Body ejemplo:**
  ```json
  {
    "filters": {
      "inactiveDays": 60,
      "top": 20
    }
  }
  ```
- **Respuesta:**
  - `customerId`, `customerName`, `lastOrderDate`, `inactiveDays`
- **Visualización sugerida:** Tabla de clientes inactivos, alertas.
- **Utilidad:** Recuperar clientes perdidos, campañas de reactivación.

### 3. Valor por cliente

- **Endpoint:** `/api/bi/customer-dashboard/customer-value`
- **Método:** POST
- **Descripción:** Muestra el valor monetario aportado por cada cliente.
- **Body ejemplo:**
  ```json
  {
    "filters": {
      "dateFrom": "2024-01-01",
      "dateTo": "2024-12-31",
      "top": 20
    }
  }
  ```
- **Respuesta:**
  - `customerId`, `customerName`, `totalAmount`, `averageTicket`
- **Visualización sugerida:** Gráfico de Pareto, ranking de valor.
- **Utilidad:** Identificar clientes VIP, segmentar estrategias comerciales.

---

## Endpoints de Inventario

### 4. Top productos vendidos

- **Endpoint:** `/api/bi/inventory-intelligent/top-products`
- **Método:** POST
- **Descripción:** Devuelve los productos más vendidos en el periodo.
- **Body ejemplo:**
  ```json
  {
    "filters": {
      "dateFrom": "2024-01-01",
      "dateTo": "2024-12-31",
      "limit": 10
    }
  }
  ```
- **Respuesta:**
  - `productId`, `productName`, `quantitySold`, `salesAmount`, `currentStock`, `marginPercent`, `inventoryTurnover`
- **Visualización sugerida:** Gráfico de barras, tabla de top productos.
- **Utilidad:** Identificar productos estrella, planificar inventario.

### 5. Ventas por producto

- **Endpoint:** `/api/bi/inventory-intelligent/products-sales`
- **Método:** POST
- **Descripción:** Ventas detalladas por producto, con filtros opcionales de almacén y categoría.
- **Body ejemplo:**
  ```json
  {
    "filters": {
      "dateFrom": "2024-01-01",
      "dateTo": "2024-12-31",
      "warehouseId": 1,
      "categoryId": 2
    }
  }
  ```
- **Respuesta:**
  - `productId`, `productName`, `quantitySold`, `salesAmount`, `currentStock`, `lastSaleDate`, `movementStatus`, `stockStatus`
- **Visualización sugerida:** Tabla dinámica, análisis ABC.
- **Utilidad:** Control de stock, análisis de rotación, evitar quiebres.

### 6. Tendencia de ventas

- **Endpoint:** `/api/bi/inventory-intelligent/sales-trend`
- **Método:** POST
- **Descripción:** Devuelve la evolución de ventas agregada por día, semana o mes.
- **Body ejemplo:**
  ```json
  {
    "filters": {
      "dateFrom": "2024-01-01",
      "dateTo": "2024-12-31",
      "groupBy": "month"
    }
  }
  ```
- **Respuesta:**
  - `date`, `quantitySold`, `salesAmount` (por periodo)
  - `periodSummary`: resumen últimos 7, 15 y 30 días
- **Visualización sugerida:** Gráfico de líneas o áreas.
- **Utilidad:** Detectar estacionalidad, medir impacto de campañas.

### 7. Productos sin movimiento

- **Endpoint:** `/api/bi/inventory-intelligent/dead-products`
- **Método:** POST
- **Descripción:** Lista productos con stock pero sin ventas en X días.
- **Body ejemplo:**
  ```json
  {
    "filters": {
      "daysWithoutMovement": 60
    }
  }
  ```
- **Respuesta:**
  - `productId`, `productName`, `currentStock`, `daysWithoutMovement`
- **Visualización sugerida:** Tabla de obsoletos, alertas.
- **Utilidad:** Depuración de inventario, promociones para liquidar stock.

### 8. Productos con alta rotación

- **Endpoint:** `/api/bi/inventory-intelligent/high-rotation-products`
- **Método:** POST
- **Descripción:** Productos con mayor rotación en el periodo.
- **Body ejemplo:**
  ```json
  {
    "filters": {
      "dateFrom": "2024-01-01",
      "dateTo": "2024-12-31",
      "limit": 10
    }
  }
  ```
- **Respuesta:**
  - `productId`, `productName`, `quantitySold`, `inventoryTurnover`, `daysOfCoverage`
- **Visualización sugerida:** Gráfico de barras, semáforo de cobertura.
- **Utilidad:** Prevenir quiebres, optimizar compras.

### 9. Plan de producción semanal

- **Endpoint:** `/api/bi/production/weekly-plan`
- **Método:** POST
- **Descripción:** Devuelve el plan de producción semanal según filtros de cliente y fechas.
- **Body ejemplo:**
  ```json
  {
    "filters": {
      "dateFrom": "2024-01-01",
      "dateTo": "2024-12-31",
      "cliente_id": 123
    }
  }
  ```
- **Respuesta:**
  - Depende de la configuración, típicamente: producto, cantidad, fecha entrega, cliente
- **Visualización sugerida:** Calendario, tabla de planificación.
- **Utilidad:** Planificación de producción, seguimiento de pedidos.

---

## Notas

- Todos los endpoints tienen versión "advanced-metrics" con la misma estructura, solo cambia la URL.
- Los filtros son opcionales salvo que se indique lo contrario.
- Si no tienes el ID de almacén (`warehouseId`), puedes omitirlo y el endpoint traerá datos de todos los almacenes.

---

## Ejemplo de petición curl

```sh
curl.exe -X POST "https://cookoo2b-pruebas-30314995.dev.odoo.com/api/bi/inventory-intelligent/top-products" ^
  -H "Access-Token: TU_TOKEN_AQUI" ^
  -H "Content-Type: application/json" ^
  -d "{\"filters\": {\"dateFrom\": \"2024-01-01\", \"dateTo\": \"2024-12-31\", \"limit\": 10}}"
```

## Ejemplo de petición con `Authorization: Bearer`

```sh
curl.exe -X POST "https://cookoo2b-pruebas-30314995.dev.odoo.com/api/bi/inventory-intelligent/top-products" ^
  -H "Authorization: Bearer TU_TOKEN_AQUI" ^
  -H "Content-Type: application/json" ^
  -d "{\"filters\": {\"dateFrom\": \"2024-01-01\", \"dateTo\": \"2024-12-31\", \"limit\": 10}}"
```

## Ejemplo en PowerShell (`Invoke-RestMethod`)

```powershell
$headers = @{
  "Access-Token" = "TU_TOKEN_AQUI"
  "Content-Type" = "application/json"
}

$body = @{
  filters = @{
    dateFrom = "2024-01-01"
    dateTo   = "2024-12-31"
    limit    = 10
  }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Uri "https://cookoo2b-pruebas-30314995.dev.odoo.com/api/bi/inventory-intelligent/top-products" `
  -Method Post `
  -Headers $headers `
  -Body $body
```

---

## Sugerencias de dashboards

- **Clientes:** Ranking de clientes, clientes inactivos, valor por cliente.
- **Inventario:** Top productos, productos sin movimiento, rotación, tendencia de ventas.
- **Producción:** Plan semanal, cumplimiento de entregas.

---

## Comandos curl listos para copiar

Reemplaza `TU_TOKEN_AQUI` por el valor de `Token de Acceso` mostrado en Odoo.

### Clientes más frecuentes

```powershell
$body = @{
  filters = @{
    dateFrom = "2024-01-01"
    dateTo   = "2024-12-31"
    top      = 10
  }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Uri "https://cookoo2b-pruebas-30314995.dev.odoo.com/api/bi/customer-dashboard/frequent-customers" `
  -Method Post `
  -Headers $headers `
  -Body $body
```

### Clientes inactivos

```powershell
$body = @{
  filters = @{
    inactiveDays = 60
    top          = 20
  }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Uri "https://cookoo2b-pruebas-30314995.dev.odoo.com/api/bi/customer-dashboard/inactive-customers" `
  -Method Post `
  -Headers $headers `
  -Body $body

```

### Valor por cliente

```powershell
$body = @{
  filters = @{
    dateFrom = "2024-01-01"
    dateTo   = "2024-12-31"
    top      = 20
  }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Uri "https://cookoo2b-pruebas-30314995.dev.odoo.com/api/bi/customer-dashboard/customer-value" `
  -Method Post `
  -Headers $headers `
  -Body $body
```

### Top productos vendidos

```powershell
$body = @{
  filters = @{
    dateFrom = "2024-01-01"
    dateTo   = "2024-12-31"
    limit    = 10
  }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Uri "https://cookoo2b-pruebas-30314995.dev.odoo.com/api/bi/inventory-intelligent/top-products" `
  -Method Post `
  -Headers $headers `
  -Body $body
```

### Ventas por producto

```powershell
$body = @{
  filters = @{
    dateFrom    = "2024-01-01"
    dateTo      = "2024-12-31"
    warehouseId = 1
    categoryId  = 2
  }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Uri "https://cookoo2b-pruebas-30314995.dev.odoo.com/api/bi/inventory-intelligent/products-sales" `
  -Method Post `
  -Headers $headers `
  -Body $body
```

### Tendencia de ventas

```powershell
$body = @{
  filters = @{
    dateFrom = "2024-01-01"
    dateTo   = "2024-12-31"
    groupBy  = "month"
  }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Uri "https://cookoo2b-pruebas-30314995.dev.odoo.com/api/bi/inventory-intelligent/sales-trend" `
  -Method Post `
  -Headers $headers `
  -Body $body
```

### Productos sin movimiento

```powershell
$body = @{
  filters = @{
    daysWithoutMovement = 60
  }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Uri "https://cookoo2b-pruebas-30314995.dev.odoo.com/api/bi/inventory-intelligent/dead-products" `
  -Method Post `
  -Headers $headers `
  -Body $body
```

### Productos con alta rotación

```powershell
$body = @{
  filters = @{
    dateFrom = "2024-01-01"
    dateTo   = "2024-12-31"
    limit    = 10
  }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Uri "https://cookoo2b-pruebas-30314995.dev.odoo.com/api/bi/inventory-intelligent/high-rotation-products" `
  -Method Post `
  -Headers $headers `
  -Body $body
```

### Plan de producción semanal

```powershell
$body = @{
  filters = @{
    dateFrom   = "2024-01-01"
    dateTo     = "2024-12-31"
    cliente_id = 123
  }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Uri "https://cookoo2b-pruebas-30314995.dev.odoo.com/api/bi/production/weekly-plan" `
  -Method Post `
  -Headers $headers `
  -Body $body
```

---

## Solución rápida si ves `Acceso no autorizado`

1. Verifica que el token sea el de `PBI Connections > Credenciales Power BI > Token de Acceso`.
2. Prueba primero con header `Access-Token` en lugar de `?token=` en la URL.
3. Si generaste un nuevo token en Odoo, actualízalo también en Power BI o en tu script.
4. Si haces la prueba en PowerShell, usa `curl.exe` o `Invoke-RestMethod`; no mezcles sintaxis de `bash` con cmdlets de PowerShell.

# API Endpoints para Dashboard de Inventario y Clientes (Power BI)

Este documento describe los endpoints disponibles para alimentar dashboards de Power BI, ejemplos de uso con `curl`, explicación de los datos que devuelve cada endpoint y sugerencias de visualizaciones y casos de negocio.

---

## Autenticación

Todos los endpoints requieren autenticación con el valor de `Token de Acceso` configurado en Odoo, en:

- `PBI Connections > Token de Acceso`

Formas válidas de enviarlo:

- Header `Access-Token: <token>` `Recomendado`
- Header `Authorization: Bearer <token>`
- Parámetro `?token=<token>` en la URL

Importante:

- No uses la `API Key de validación` del menú `Settings`; esa clave sirve para validar el cliente contra Zoraen, no para consumir estos endpoints.
- Si copias el token manualmente, evita espacios o comillas extra al inicio o al final.

---

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

Se declaran los headers para cada peticion, reemplaza `TU_TOKEN_AQUI` por el valor de `Token de Acceso` mostrado en Odoo.

```powershell
$headers = @{
  "Access-Token" = "TU_TOKEN_AQUI"
  "Content-Type" = "application/json"
}

```

### Clientes más frecuentes

```powershell
$body = @{
  filters = @{
    dateFrom = "2024-01-01"
    dateTo   = "2024-12-31"
    top      = 10
    groupBy  = "pointOfSale"
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
    groupBy      = "pointOfSale"
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
    groupBy  = "pointOfSale"
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

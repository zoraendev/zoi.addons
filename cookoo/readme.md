Top productos
curl.exe -X POST "$BASE/api/bi/inventory-intelligent/top-products" -H "Content-Type: application/json" -H "Access-Token: $TOKEN" -d "{"filters":{"dateFrom":"2026-01-01","dateTo":"2026-12-31","warehouseId":1,"categoryId":null,"limit":20}}"

Ventas por producto
curl.exe -X POST "$BASE/api/bi/inventory-intelligent/products-sales" -H "Content-Type: application/json" -H "Access-Token: $TOKEN" -d "{"filters":{"dateFrom":"2026-01-01","dateTo":"2026-12-31","warehouseId":1,"categoryId":null,"limit":50}}"

Tendencia de ventas
curl.exe -X POST "$BASE/api/bi/inventory-intelligent/sales-trend" -H "Content-Type: application/json" -H "Access-Token: $TOKEN" -d "{"filters":{"dateFrom":"2026-01-01","dateTo":"2026-12-31","groupBy":"month"}}"

Productos sin movimiento
curl.exe -X POST "$BASE/api/bi/inventory-intelligent/dead-products" -H "Content-Type: application/json" -H "Access-Token: $TOKEN" -d "{"filters":{"dateFrom":"2026-01-01","dateTo":"2026-12-31","daysWithoutMovement":60,"limit":50}}"

Productos de alta rotación
curl.exe -X POST "$BASE/api/bi/inventory-intelligent/high-rotation-products" -H "Content-Type: application/json" -H "Access-Token: $TOKEN" -d "{"filters":{"dateFrom":"2026-01-01","dateTo":"2026-12-31","limit":50}}"

Plan semanal de producción
curl.exe -X POST "$BASE/api/bi/production/weekly-plan" -H "Content-Type: application/json" -H "Access-Token: $TOKEN" -d "{"filters":{"dateFrom":"2026-01-01","dateTo":"2026-12-31","warehouseId":1}}"

Clientes frecuentes (GET)
curl.exe -X GET "$BASE/api/bi/customer-dashboard/frequent-customers?dateFrom=2026-01-01&dateTo=2026-12-31&top=20&sortBy=frequency" -H "Access-Token: $TOKEN"

Clientes frecuentes (POST)
curl.exe -X POST "$BASE/api/bi/customer-dashboard/frequent-customers" -H "Content-Type: application/json" -H "Access-Token: $TOKEN" -d "{"filters":{"dateFrom":"2026-01-01","dateTo":"2026-12-31","top":20,"sortBy":"frequency"}}"

Clientes inactivos (GET)
curl.exe -X GET "$BASE/api/bi/customer-dashboard/inactive-customers?dateFrom=2026-01-01&dateTo=2026-12-31&inactiveDays=90&top=20" -H "Access-Token: $TOKEN"

Clientes inactivos (POST)
curl.exe -X POST "$BASE/api/bi/customer-dashboard/inactive-customers" -H "Content-Type: application/json" -H "Access-Token: $TOKEN" -d "{"filters":{"dateFrom":"2026-01-01","dateTo":"2026-12-31","inactiveDays":90,"top":20}}"

Valor por cliente (GET)
curl.exe -X GET "$BASE/api/bi/customer-dashboard/customer-value?dateFrom=2026-01-01&dateTo=2026-12-31&top=20&sortBy=value" -H "Access-Token: $TOKEN"

Valor por cliente (POST)
curl.exe -X POST "$BASE/api/bi/customer-dashboard/customer-value" -H "Content-Type: application/json" -H "Access-Token: $TOKEN" -d "{"filters":{"dateFrom":"2026-01-01","dateTo":"2026-12-31","top":20,"sortBy":"value"}}"

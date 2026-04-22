# BI Endpoints Data Map

Este documento resume qué modelos/tablas y qué campos de Odoo consume cada endpoint del dashboard de inventario en `advanced_metrics`, para facilitar la conexión y trazabilidad desde Power BI.

---

## Endpoints cubiertos

- `POST /api/bi/inventory-intelligent/top-products`
- `POST /api/bi/inventory-intelligent/products-sales`
- `POST /api/bi/inventory-intelligent/sales-trend`
- `POST /api/bi/inventory-intelligent/dead-products`
- `POST /api/bi/inventory-intelligent/high-rotation-products`

---

## 1) `POST /api/bi/inventory-intelligent/top-products`

### Modelos / tablas principales

- `sale.order.line`
- `sale.order`
- `product.product`
- `product.template`
- `stock.quant`

### Campos consumidos

#### `sale.order.line`

- `product_id`
- `product_uom_qty`
- `price_subtotal`
- `purchase_price`
- `order_id`

#### `sale.order`

- `date_order`
- `state`
- `warehouse_id`

#### `product.product` / `product.template`

- `id`
- `display_name`
- `categ_id`

#### `stock.quant`

- `product_id`
- `quantity`
- `location_id`

### Uso funcional

- ranking de productos más vendidos
- cantidad vendida
- ventas netas
- margen estimado
- stock actual
- rotación estimada

---

## 2) `POST /api/bi/inventory-intelligent/products-sales`

### Modelos / tablas principales

- `sale.order.line`
- `sale.order`
- `product.product`
- `product.template`
- `stock.quant`

### Campos consumidos

#### `sale.order.line`

- `product_id`
- `product_uom_qty`
- `price_subtotal`
- `purchase_price`
- `order_id`

#### `sale.order`

- `date_order`
- `state`
- `warehouse_id`

#### `product.product` / `product.template`

- `display_name`
- `categ_id`

#### `stock.quant`

- `product_id`
- `quantity`

### Uso funcional

- ventas por producto
- costo
- margen
- stock disponible
- última fecha de venta
- estado de movimiento (`movementStatus`)
- estado de stock (`stockStatus`)

---

## 3) `POST /api/bi/inventory-intelligent/sales-trend`

### Modelos / tablas principales

- `sale.order.line`
- `sale.order`

### Campos consumidos

#### `sale.order.line`

- `product_uom_qty`
- `price_subtotal`
- `order_id`

#### `sale.order`

- `date_order`
- `state`
- `warehouse_id`

### Uso funcional

- agrupación de ventas por día / semana / mes
- cálculo de:
  - `quantitySold`
  - `salesAmount`
- resumen de periodos:
  - últimos 7 días
  - últimos 15 días
  - últimos 30 días

---

## 4) `POST /api/bi/inventory-intelligent/dead-products`

### Modelos / tablas principales

- `product.product`
- `product.template`
- `stock.quant`
- `sale.order.line`
- `sale.order`

### Campos consumidos

#### `product.product` / `product.template`

- `id`
- `display_name`
- `categ_id`

#### `stock.quant`

- `product_id`
- `quantity`
- `location_id`

#### `sale.order.line`

- `product_id`
- `order_id`

#### `sale.order`

- `date_order`
- `state`
- `warehouse_id`

### Uso funcional

- detectar productos con stock pero sin movimiento reciente
- obtener:
  - `currentStock`
  - `lastSaleDate`
  - `daysWithoutMovement`
  - `movementStatus = no_movement`

---

## 5) `POST /api/bi/inventory-intelligent/high-rotation-products`

### Modelos / tablas principales

- `sale.order.line`
- `sale.order`
- `product.product`
- `product.template`
- `stock.quant`

### Campos consumidos

#### `sale.order.line`

- `product_id`
- `product_uom_qty`
- `price_subtotal`
- `purchase_price`

#### `sale.order`

- `date_order`
- `state`
- `warehouse_id`

#### `stock.quant`

- `product_id`
- `quantity`

### Uso funcional

- filtrar productos con alta rotación (`movementStatus = high_rotation`)
- devolver:
  - `quantitySold`
  - `currentStock`
  - `averageStock`
  - `inventoryTurnover`
  - `daysOfCoverage`

---

## Filtros comunes usados por los endpoints

Estos endpoints suelen aplicar filtros sobre los siguientes campos:

- `dateFrom` / `dateTo` → `sale.order.date_order`
- `warehouseId` → `sale.order.warehouse_id`
- `categoryId` → `product.template.categ_id`
- `limit`

---

## Resumen rápido

| Endpoint                 | Modelos principales                                               |
| ------------------------ | ----------------------------------------------------------------- |
| `top-products`           | `sale.order.line`, `sale.order`, `product.product`, `stock.quant` |
| `products-sales`         | `sale.order.line`, `sale.order`, `product.product`, `stock.quant` |
| `sales-trend`            | `sale.order.line`, `sale.order`                                   |
| `dead-products`          | `product.product`, `stock.quant`, `sale.order.line`, `sale.order` |
| `high-rotation-products` | `sale.order.line`, `sale.order`, `product.product`, `stock.quant` |

---

## Archivo fuente principal

La lógica de agregación y consulta para estos endpoints vive principalmente en:

- `custom_addons/cookoo/advanced_metrics/models/report_wizard.py`
- `custom_addons/cookoo/advanced_metrics/controllers/inventory_dashboard.py`

# Automatizations Module Structure

Este addon expone datos y acciones para que un backend externo orqueste
automatizaciones comerciales completas. La toma de decisiones vive fuera de
Odoo; este modulo se limita a consultar informacion y ejecutar acciones
deterministicas.

## Dominios actuales

- `customers`: reconocimiento del cliente y consulta de contexto comercial.
- `products`: catalogo, disponibilidad comercial y datos de producto para venta.
- `sales_orders`: armado de pedido, borradores, resumenes y confirmacion.

## Capas

- `domain`: contratos y campos del dominio.
- `application`: casos de uso por dominio, separados en `queries`,
  `transactions` y `serializers`.
- `controllers`: endpoints HTTP expuestos por dominio.
- `models`: extensiones puntuales de modelos Odoo cuando haga falta preparar
  datos para automatizacion.

## Flujo objetivo

1. Reconocer cliente.
2. Consultar catalogo o productos filtrados.
3. Construir pedido o borrador.
4. Confirmar la orden de venta.

Cada paso debe poder consumirse de forma independiente desde el backend del
bot, usando endpoints claros y payloads consistentes.

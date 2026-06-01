# Zoraen Commercial

Addon comercial operativo para centralizar:

- marcas comerciales
- relaciones de productos por marca
- base futura para portafolio
- base futura para canales, pricing y calendario comercial

## Alcance inicial

Este addon nace separando la capa comercial operativa que hoy vivia dentro de `zrn_prodigyn`, sin mover todavia hubs ni reporterias.

Incluye:

- app propia de Zoraen Commercial
- maestro de marcas comerciales
- asignacion de productos vendibles por marca
- validaciones para evitar productos repetidos entre marcas
- validacion de logo y documentacion de base de datos

## Objetivo funcional

Permitir que el cliente:

- registre sus marcas comerciales reales
- agrupe productos vendibles bajo cada marca
- prepare una base consistente para metricas futuras
- compare despues inventario, ventas y compras por marca

## Documentacion adicional

- `docs/ui_ux.md`
- `docs/architecture.md`
- `docs/db/commercial_brands_schema.sql`
- `docs/db/commercial_brands_er.md`

# Zoraen Planning

Addon operativo para centralizar:

- planeacion de produccion
- planeacion de abastecimiento
- planeacion logistica
- planes desacoplados de la ejecucion real en Odoo

## Alcance inicial

Este addon nace separando la capa de planeacion operativa que hoy existia en `zrn_prodigyn`, sin mover todavia los hubs analiticos ni el frente comercial.

Incluye:

- centro principal de planeacion
- pantalla de produccion con accesos a fabricacion y abastecimiento
- wizard de planeacion de fabricacion
- wizard de planeacion de abastecimiento
- tablas `mfg_plan` para planes desacoplados
- placeholders de logistica listos para crecer

## Objetivo funcional

Permitir que el usuario planee antes de ejecutar:

- que fabricar
- que abastecer
- para cuando
- desde que demanda nace el plan
- que alertas operativas deben dispararse

## Documentacion adicional

- `docs/ui_ux.md`
- `docs/architecture.md`

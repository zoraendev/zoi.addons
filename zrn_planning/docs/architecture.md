# Arquitectura de Zoraen Planning

## Objetivo

Separar la capa de planeacion operativa del addon monolitico original para permitir que el stack evolucione por dominios.

## Incluido en esta migracion

- `production planning`
- `purchase planning`
- `delivery planning`
- `mfg_plan`
- assets visuales y controladores necesarios para estas vistas

## No incluido aun

- hubs de reporteria
- reporterias comerciales
- marcas comerciales
- planeacion comercial

## Estrategia

- mantener `zrn_prodigyn` intacto por ahora
- crear `zrn_planning` con namespace propio
- migrar primero lo operativo que ya esta avanzado
- dejar listas las bases para luego desenganchar menús y dependencias del addon legado

# ER Canales Comerciales

## Objetivo

Crear una entidad operativa de canal comercial para agrupar clientes y PDVs reales de Odoo bajo una sola clasificacion de negocio, evitando ambiguedad en reportes y filtros analiticos.

## Reglas base

- Un canal comercial puede tener muchos clientes o PDVs asignados.
- Un cliente o PDV de Odoo solo puede pertenecer a un canal comercial dentro de esta capa.
- La agrupacion es manual y custom: un canal puede mezclar PDVs o clientes de distintas empresas madre si esa es la logica comercial del negocio.
- La tabla puente guarda la asignacion explicita del partner hacia el canal.
- La asignacion se hace a nivel de `res.partner`, permitiendo trabajar tanto clientes individuales como PDVs.
- El `commercial_partner_id` se conserva como referencia analitica para rastrear grupos empresariales sin perder la granularidad del PDV.

## Diagrama ER

```mermaid
erDiagram
    ZRN_COMMERCIAL_COMMERCIAL_CHANNEL ||--o{ ZRN_COMMERCIAL_COMMERCIAL_CHANNEL_PARTNER : agrupa
    ZRN_COMMERCIAL_COMMERCIAL_CHANNEL }o--|| RES_COMPANY : pertenece_a
    ZRN_COMMERCIAL_COMMERCIAL_CHANNEL_PARTNER }o--|| RES_PARTNER : asigna_pdv_o_cliente
    ZRN_COMMERCIAL_COMMERCIAL_CHANNEL_PARTNER }o--|| RES_PARTNER : referencia_cliente_comercial
    ZRN_COMMERCIAL_COMMERCIAL_CHANNEL_PARTNER }o--|| RES_COUNTRY_STATE : departamento
    ZRN_COMMERCIAL_COMMERCIAL_CHANNEL_PARTNER }o--|| RES_COUNTRY : pais

    ZRN_COMMERCIAL_COMMERCIAL_CHANNEL {
        bigint id PK
        varchar name
        varchar code UK
        boolean active
        bigint company_id FK
        text description
        text notes
        timestamp create_date
        bigint create_uid
        timestamp write_date
        bigint write_uid
    }

    ZRN_COMMERCIAL_COMMERCIAL_CHANNEL_PARTNER {
        bigint id PK
        integer sequence
        bigint channel_id FK
        bigint company_id FK
        bigint partner_id FK UK
        bigint commercial_partner_id FK
        varchar vat
        varchar city
        bigint state_id FK
        bigint country_id FK
        boolean active
        text notes
        timestamp create_date
        bigint create_uid
        timestamp write_date
        bigint write_uid
    }
```
